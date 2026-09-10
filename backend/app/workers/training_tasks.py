import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.sync_database import SyncSessionLocal
from app.models.training_job import TrainingJob
from app.models.dataset import Dataset
from app.services import notification_service


def _build_sklearn_model(algorithm: str, hyperparameters: dict):
    if algorithm == "logistic_regression":
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(max_iter=hyperparameters.get("max_iter", 1000))

    if algorithm == "random_forest_classifier":
        from sklearn.ensemble import RandomForestClassifier

        return RandomForestClassifier(
            n_estimators=hyperparameters.get("n_estimators", 100),
            max_depth=hyperparameters.get("max_depth"),
            random_state=42,
        )

    if algorithm == "linear_regression":
        from sklearn.linear_model import LinearRegression

        return LinearRegression()

    if algorithm == "random_forest_regressor":
        from sklearn.ensemble import RandomForestRegressor

        return RandomForestRegressor(
            n_estimators=hyperparameters.get("n_estimators", 100),
            max_depth=hyperparameters.get("max_depth"),
            random_state=42,
        )

    raise ValueError(f"Unknown algorithm: {algorithm}")


def _run_sklearn_training(job: "TrainingJob", dataset: "Dataset") -> None:
    import joblib
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, r2_score
    from sklearn.preprocessing import LabelEncoder

    sep = "\t" if dataset.file_format == "tsv" else ","
    df = pd.read_csv(dataset.file_path, sep=sep)

    if job.target_column not in df.columns:
        raise ValueError(
            f"Target column '{job.target_column}' not found in dataset. "
            f"Available columns: {', '.join(df.columns)}"
        )

    y_raw = df[job.target_column]
    X = df.drop(columns=[job.target_column]).select_dtypes(include="number")

    if X.shape[1] == 0:
        raise ValueError(
            "No numeric feature columns found after dropping the target. "
            "The tabular track only supports numeric features."
        )

    combined = X.copy()
    combined["__target__"] = y_raw
    combined = combined.dropna()
    X = combined.drop(columns=["__target__"])
    y_raw = combined["__target__"]

    if len(X) < 10:
        raise ValueError(
            f"Only {len(X)} usable rows after dropping missing values - "
            "need at least 10 to train a meaningful model."
        )

    label_classes = None
    is_classification = job.task_type == "tabular_classification"
    if is_classification and y_raw.dtype == object:
        encoder = LabelEncoder()
        y = encoder.fit_transform(y_raw)
        label_classes = encoder.classes_.tolist()
    else:
        y = y_raw

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = _build_sklearn_model(job.algorithm, job.hyperparameters_json or {})
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    if is_classification:
        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "f1_weighted": float(f1_score(y_test, y_pred, average="weighted")),
            "test_rows": int(len(X_test)),
            "train_rows": int(len(X_train)),
        }
    else:
        metrics = {
            "mse": float(mean_squared_error(y_test, y_pred)),
            "r2": float(r2_score(y_test, y_pred)),
            "test_rows": int(len(X_test)),
            "train_rows": int(len(X_train)),
        }

    models_dir = Path(settings.MODELS_DIR) / str(job.org_id)
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / f"job_{job.id}.joblib"
    joblib.dump(
        {"model": model, "feature_columns": list(X.columns), "label_classes": label_classes},
        model_path,
    )

    job.feature_columns_json = list(X.columns)
    job.metrics_json = metrics
    job.model_path = str(model_path)
    job.status = "completed"
    job.error_message = None


def _run_transformer_training(job: "TrainingJob", dataset: "Dataset") -> None:
    """
    Fine-tunes a Hugging Face sequence classification model on a CSV text
    dataset. This is a single code path for both CPU and GPU: PyTorch's
    torch.cuda.is_available() decides the device at runtime, and the
    Trainer moves the model there automatically. Nothing here needs to
    change if this worker later runs on a GPU box - only which base_model
    is allowed to be selected changes (see transformer_models.py), and the
    torch wheel installed (CPU-only vs CUDA build).
    """
    import pandas as pd
    import torch
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    hyperparameters = job.hyperparameters_json or {}
    text_column = hyperparameters.get("text_column")
    if not text_column:
        raise ValueError("hyperparameters.text_column is required for this task type.")

    sep = "\t" if dataset.file_format == "tsv" else ","
    df = pd.read_csv(dataset.file_path, sep=sep)

    for col in (text_column, job.target_column):
        if col not in df.columns:
            raise ValueError(
                f"Column '{col}' not found in dataset. Available columns: {', '.join(df.columns)}"
            )

    df = df[[text_column, job.target_column]].dropna()
    if len(df) < 20:
        raise ValueError(
            f"Only {len(df)} usable rows after dropping missing values - "
            "need at least 20 to fine-tune a text classifier meaningfully."
        )

    texts = df[text_column].astype(str).tolist()
    encoder = LabelEncoder()
    labels = encoder.fit_transform(df[job.target_column].astype(str))
    label_classes = encoder.classes_.tolist()
    num_labels = len(label_classes)

    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=42
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    tokenizer = AutoTokenizer.from_pretrained(job.base_model)
    max_length = int(hyperparameters.get("max_length", 256))
    train_encodings = tokenizer(
        train_texts, truncation=True, padding=True, max_length=max_length
    )
    test_encodings = tokenizer(
        test_texts, truncation=True, padding=True, max_length=max_length
    )

    class _TextDataset(torch.utils.data.Dataset):
        def __init__(self, encodings, labels):
            self.encodings = encodings
            self.labels = labels

        def __len__(self):
            return len(self.labels)

        def __getitem__(self, idx):
            item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
            item["labels"] = torch.tensor(int(self.labels[idx]))
            return item

    train_dataset = _TextDataset(train_encodings, train_labels)
    test_dataset = _TextDataset(test_encodings, test_labels)

    model = AutoModelForSequenceClassification.from_pretrained(
        job.base_model, num_labels=num_labels
    )

    models_dir = Path(settings.MODELS_DIR) / str(job.org_id) / f"job_{job.id}"
    models_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(models_dir / "_trainer_tmp"),
        num_train_epochs=float(hyperparameters.get("epochs", 1)),
        per_device_train_batch_size=int(hyperparameters.get("batch_size", 8)),
        per_device_eval_batch_size=int(hyperparameters.get("batch_size", 8)),
        learning_rate=float(hyperparameters.get("learning_rate", 5e-5)),
        logging_steps=10,
        save_strategy="no",
        report_to=[],
        disable_tqdm=True,
        use_cpu=(device.type == "cpu"),
    )

    trainer = Trainer(model=model, args=training_args, train_dataset=train_dataset)

    try:
        trainer.train()
    except RuntimeError as exc:
        # Covers both CUDA OOM and CPU allocation failures - torch raises
        # RuntimeError for both, just with different message text.
        if "out of memory" in str(exc).lower() or "alloc" in str(exc).lower():
            raise ValueError(
                f"Out of memory while training '{job.base_model}' "
                f"(batch_size={training_args.per_device_train_batch_size}, "
                f"device={device.type}). Try a smaller model, a smaller "
                f"batch_size, or a shorter max_length."
            ) from exc
        raise

    predictions = trainer.predict(test_dataset)
    y_pred = predictions.predictions.argmax(axis=-1)

    metrics = {
        "accuracy": float(accuracy_score(test_labels, y_pred)),
        "f1_weighted": float(f1_score(test_labels, y_pred, average="weighted")),
        "train_rows": int(len(train_texts)),
        "test_rows": int(len(test_texts)),
        "device_used": device.type,
    }

    model.save_pretrained(models_dir)
    tokenizer.save_pretrained(models_dir)
    (models_dir / "meta.json").write_text(
        json.dumps({"label_classes": label_classes, "mode": "transformer"})
    )

    job.feature_columns_json = [text_column]
    job.metrics_json = metrics
    job.model_path = str(models_dir)
    job.status = "completed"
    job.error_message = None


def _run_generation_training(job: "TrainingJob", dataset: "Dataset") -> None:
    """
    Fine-tunes a GPT-2-family causal language model on a text column for
    free-form generation. Unsupervised (next-token prediction) - there's no
    separate label column, unlike the classification branch. Same
    CPU/GPU-agnostic pattern as _run_transformer_training: torch decides the
    device, only which base_model is allowed differs by hardware.
    """
    import math

    import pandas as pd
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    hyperparameters = job.hyperparameters_json or {}
    text_column = hyperparameters.get("text_column")
    if not text_column:
        raise ValueError("hyperparameters.text_column is required for this task type.")

    sep = "\t" if dataset.file_format == "tsv" else ","
    df = pd.read_csv(dataset.file_path, sep=sep)
    if text_column not in df.columns:
        raise ValueError(
            f"Column '{text_column}' not found in dataset. Available columns: {', '.join(df.columns)}"
        )

    texts = [t for t in df[text_column].dropna().astype(str).tolist() if t.strip()]
    if len(texts) < 20:
        raise ValueError(
            f"Only {len(texts)} usable rows after dropping missing/empty values - "
            "need at least 20 to fine-tune a generator meaningfully."
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    tokenizer = AutoTokenizer.from_pretrained(job.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    max_length = int(hyperparameters.get("max_length", 128))

    class _GenDataset(torch.utils.data.Dataset):
        def __init__(self, examples):
            self.examples = examples

        def __len__(self):
            return len(self.examples)

        def __getitem__(self, idx):
            return {"input_ids": self.examples[idx]}

    tokenized = [
        tokenizer(t, truncation=True, max_length=max_length)["input_ids"] for t in texts
    ]
    split_idx = max(1, int(len(tokenized) * 0.9))
    train_dataset = _GenDataset(tokenized[:split_idx])
    eval_examples = tokenized[split_idx:] or tokenized[-2:]
    eval_dataset = _GenDataset(eval_examples)

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    model = AutoModelForCausalLM.from_pretrained(job.base_model)
    model.resize_token_embeddings(len(tokenizer))

    models_dir = Path(settings.MODELS_DIR) / str(job.org_id) / f"job_{job.id}"
    models_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(models_dir / "_trainer_tmp"),
        num_train_epochs=float(hyperparameters.get("epochs", 1)),
        per_device_train_batch_size=int(hyperparameters.get("batch_size", 4)),
        per_device_eval_batch_size=int(hyperparameters.get("batch_size", 4)),
        learning_rate=float(hyperparameters.get("learning_rate", 5e-5)),
        logging_steps=10,
        save_strategy="no",
        report_to=[],
        disable_tqdm=True,
        use_cpu=(device.type == "cpu"),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=data_collator,
    )

    try:
        trainer.train()
    except RuntimeError as exc:
        if "out of memory" in str(exc).lower() or "alloc" in str(exc).lower():
            raise ValueError(
                f"Out of memory while training '{job.base_model}' "
                f"(batch_size={training_args.per_device_train_batch_size}, "
                f"device={device.type}). Try a smaller model, a smaller "
                f"batch_size, or a shorter max_length."
            ) from exc
        raise

    eval_metrics = trainer.evaluate(eval_dataset=eval_dataset)
    eval_loss = float(eval_metrics.get("eval_loss", 0))
    try:
        perplexity = math.exp(eval_loss)
    except OverflowError:
        perplexity = None

    metrics = {
        "eval_loss": eval_loss,
        "perplexity": perplexity,
        "train_rows": int(len(train_dataset)),
        "eval_rows": int(len(eval_dataset)),
        "device_used": device.type,
    }

    model.save_pretrained(models_dir)
    tokenizer.save_pretrained(models_dir)
    (models_dir / "meta.json").write_text(json.dumps({"mode": "transformer_generation"}))

    job.feature_columns_json = [text_column]
    job.metrics_json = metrics
    job.model_path = str(models_dir)
    job.status = "completed"
    job.error_message = None


@celery_app.task(name="training.train_model")
def train_model(job_id: int) -> None:
    db = SyncSessionLocal()
    try:
        job = db.get(TrainingJob, job_id)
        if not job:
            return
        if job.status == "cancelled":
            # Revoked while still queued - the API already set the final
            # status, nothing to do here.
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            dataset = db.get(Dataset, job.dataset_id)
            if not dataset:
                raise ValueError("Dataset no longer exists")

            if job.task_type == "transformer_text_classification":
                _run_transformer_training(job, dataset)
            elif job.task_type == "transformer_text_generation":
                _run_generation_training(job, dataset)
            else:
                _run_sklearn_training(job, dataset)

        except Exception as exc:  # noqa: BLE001 - report any failure back to the job row
            job.status = "failed"
            job.error_message = f"{exc}\n{traceback.format_exc(limit=3)}"

        job.finished_at = datetime.now(timezone.utc)
        db.commit()

        if job.status == "completed":
            notification_service.notify_sync(
                db, job.org_id, "training_completed",
                f"Обучение завершено: {job.name}",
                f"Задание #{job.id} ({job.base_model or job.algorithm}) успешно завершено.",
                {"job_id": job.id, "metrics": job.metrics_json},
            )
        elif job.status == "failed":
            notification_service.notify_sync(
                db, job.org_id, "training_failed",
                f"Обучение не удалось: {job.name}",
                f"Задание #{job.id} завершилось с ошибкой: {job.error_message[:300] if job.error_message else 'см. детали в интерфейсе'}",
                {"job_id": job.id},
            )
    finally:
        db.close()
