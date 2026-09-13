from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, users, policies, use_cases
from app.api import auth, users, policies, use_cases, requests
from app.api import auth, users, policies, use_cases, requests, approvals
from app.api import auth, users, policies, use_cases, requests, approvals, incidents
from app.api import providers
from app.api import audit
from app.api import overrides
from app.api import shadow_ai
from app.api import datasets
from app.api import compute
from app.api import training_jobs
from app.api import notification_channels
from app.api import deployments


_is_prod = settings.ENVIRONMENT == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    # OpenAPI schema and the interactive /docs are disabled in production
    # so the API surface is not publicly enumerable.
    openapi_url=None if _is_prod else f"{settings.API_V1_STR}/openapi.json",
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
)

# CORS - origins come from settings so production can lock this down
# without a code change. Wildcard + credentials is intentionally avoided:
# browsers reject that combination, and it would let any site issue
# authenticated requests as the logged-in user.
_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(policies.router, prefix=f"{settings.API_V1_STR}/policies", tags=["policies"])
app.include_router(use_cases.router, prefix=f"{settings.API_V1_STR}/use-cases", tags=["use-cases"])
app.include_router(requests.router, prefix=f"{settings.API_V1_STR}/requests", tags=["requests"])
app.include_router(approvals.router, prefix=f"{settings.API_V1_STR}/approvals", tags=["approvals"])
app.include_router(incidents.router, prefix=f"{settings.API_V1_STR}/incidents", tags=["incidents"])
app.include_router(providers.router, prefix=f"{settings.API_V1_STR}/providers", tags=["providers"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit-logs", tags=["audit"])
app.include_router(overrides.router, prefix=f"{settings.API_V1_STR}/overrides", tags=["overrides"])
app.include_router(shadow_ai.router, prefix=f"{settings.API_V1_STR}/shadow-ai", tags=["shadow-ai"])
app.include_router(datasets.router, prefix=f"{settings.API_V1_STR}/datasets", tags=["datasets"])
app.include_router(compute.router, prefix=f"{settings.API_V1_STR}/compute", tags=["compute"])
app.include_router(training_jobs.router, prefix=f"{settings.API_V1_STR}/training-jobs", tags=["training-jobs"])
app.include_router(notification_channels.router, prefix=f"{settings.API_V1_STR}/notification-channels", tags=["notifications"])
app.include_router(deployments.router, prefix=f"{settings.API_V1_STR}/deployments", tags=["deployments"])



@app.get("/health")
async def health_check():
    return {"status": "ok"}
