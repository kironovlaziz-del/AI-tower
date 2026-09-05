from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, users, policies, use_cases
from app.api import auth, users, policies, use_cases, requests

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(policies.router, prefix=f"{settings.API_V1_STR}/policies", tags=["policies"])
app.include_router(use_cases.router, prefix=f"{settings.API_V1_STR}/use-cases", tags=["use-cases"])
app.include_router(requests.router, prefix=f"{settings.API_V1_STR}/requests", tags=["requests"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
