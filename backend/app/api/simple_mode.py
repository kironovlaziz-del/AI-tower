import json
import logging
import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.core.database import get_db
from app.models.ai_provider import AIProvider
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.simple_mode import (
    FinalizeRAGResponse,
    ParsedQAPair,
    ParseUploadResponse,
    PreviewChatRequest,
    PreviewChatResponse,
)
from app.services import provider_adapters
from app.services.approach_recommender import recommend_approach
from app.services.rag_service import RAGService
from app.services.audit_service import AuditService
from app.services.simple_mode_parser import SUPPORTED_EXTENSIONS, parse_uploaded_file
from sqlalchemy import select

router = APIRouter()
logger = logging.getLogger("simple_mode")


@router.post("/parse-upload", response_model=ParseUploadResponse)
async def parse_upload(
    file: UploadFile = File(...),
    task_type: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    """
    Wizard screens 4->5: accepts whatever the person just dragged in and
    figures out its shape on its own (structured Q&A pairs vs plain
    documents) - see simple_mode_parser.py. Nothing is persisted here;
    this is pure analysis so the wizard can show screen 5's preview
    before anything is actually created.
    """
    safe_name = os.path.basename(file.filename or "upload")
    ext = Path(safe_name).suffix.lower().lstrip(".")
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '.{ext}'. Allowed: "
            f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    tmp_dir = Path(settings.RAG_DOCUMENTS_DIR) / "_tmp_wizard_uploads" / str(current_user.org_id)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{uuid.uuid4().hex}_{safe_name}"

    try:
        with open(tmp_path, "wb") as out_file:
            while True:
                block = await file.read(1024 * 1024)
                if not block:
                    break
                out_file.write(block)

        result = parse_uploaded_file(str(tmp_path), ext)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    recommendation = recommend_approach(
        task_type=task_type,
        has_documents=result.has_unstructured_text,
        qa_pair_count=len(result.qa_pairs),
    )

    return ParseUploadResponse(
        qa_pairs=[ParsedQAPair(question=p.question, answer=p.answer) for p in result.qa_pairs],
        error_row_count=result.error_row_count,
        has_unstructured_text=result.has_unstructured_text,
        detected_columns=result.detected_columns,
        preview_text=result.preview_text,
        recommended_approach=recommendation.approach,
        recommended_reason=recommendation.reason,
    )


@router.post("/preview-chat", response_model=PreviewChatResponse)
async def preview_chat(
    data: PreviewChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Wizard screen 8 ("Попробуйте модель") - a direct, ungrounded call to
    the chosen provider using only the screen-7 personality prompt, with
    no RAG retrieval and no fine-tuned model (there isn't one yet at this
    point in the wizard). This previews tone/personality only, not
    factual grounding - the wizard's own copy ("Задайте вопрос — посмотрите,
    как ответит") does not promise grounded answers at this stage either.
    """
    result = await db.execute(
        select(AIProvider).where(
            AIProvider.id == data.provider_id, AIProvider.org_id == current_user.org_id
        )
    )
    provider_row = result.scalar_one_or_none()
    if not provider_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    prompt = f"{data.system_prompt}\n\n{data.message}" if data.system_prompt else data.message

    api_key = (
        decrypt_secret(provider_row.api_key_encrypted) if provider_row.api_key_encrypted else None
    )
    answer, _raw = await provider_adapters.call_provider(
        provider_row.type, api_key, provider_row.base_url, provider_row.default_model, prompt
    )
    return PreviewChatResponse(answer=answer)


@router.post("/finalize-rag", response_model=FinalizeRAGResponse)
async def finalize_rag(
    name: str = Form(...),
    system_prompt: str = Form(""),
    qa_pairs_json: str = Form("[]"),
    files: List[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Wizard screen 9, RAG/rag_few_shot branch: creates the knowledge base
    in one call - the collection itself, any uploaded document(s) (the
    original file from screen 4, or one/more documents from the "no
    data" branch), and the person's own Q&A pairs indexed as a document
    too (see RAGService.add_qa_pairs_as_document). This is intentionally
    close to instant - unlike fine-tuning, there is no long-running job
    here, so screen 9's progress bar is largely cosmetic for this branch.
    """
    try:
        pairs_raw = json.loads(qa_pairs_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid qa_pairs_json")
    pairs = [(p["question"], p["answer"]) for p in pairs_raw]

    # Everything below used to be unwrapped, so any failure here (a bug
    # in a brand-new code path we haven't load-tested yet) surfaced as
    # Starlette's opaque generic 500 page instead of a diagnosable error.
    # Logging the real exception server-side and returning its message
    # (not just a generic "something went wrong") is deliberate here:
    # this endpoint is reached only by an authenticated org member acting
    # on their own org's data, so echoing the failure reason back is a
    # debugging aid, not an information-disclosure risk the way it would
    # be on a public or cross-tenant endpoint.
    try:
        service = RAGService(db)
        collection = await service.create_collection(
            current_user.org_id,
            current_user.id,
            name=name,
            description=None,
            system_prompt=system_prompt or None,
        )
        await AuditService(db).log(
            current_user.org_id, current_user.id, "document_collection", collection.id, "created",
            {"name": name, "source": "simple_mode_wizard"},
        )

        statuses: List[str] = []

        for f in files:
            doc = await service.add_document(collection.id, current_user.org_id, current_user.id, f)
            statuses.append(doc.status)

        if pairs:
            doc = await service.add_qa_pairs_as_document(
                collection.id, current_user.org_id, current_user.id, pairs
            )
            statuses.append(doc.status)

        return FinalizeRAGResponse(collection_id=collection.id, document_statuses=statuses)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - see comment above: intentionally broad
        logger.exception("finalize-rag failed for org %s", current_user.org_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{type(exc).__name__}: {exc}",
        )
