import os
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from src.infrastructure.adapters.postgres.repository import async_session, PostgresUserRepository
from src.infrastructure.adapters.redis.cache import RedisTokenCache, get_redis
from src.application.use_cases.auth_use_cases import OAuthLoginUseCase
from src.application.dtos import TokenResponse

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

config = Config(environ={"GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID, "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET})
oauth = OAuth(config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google/login")
async def google_login(request: Request, tenant_id: str):
    redirect_uri = request.url_for("google_callback")
    request.session["tenant_id"] = tenant_id
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request) -> TokenResponse:
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to retrieve user info from Google")

    sub = user_info["sub"]
    email = user_info["email"]
    tenant_id = request.session.get("tenant_id", "default")

    async with async_session() as session:
        repo = PostgresUserRepository(session)
        cache = RedisTokenCache(await get_redis())
        uc = OAuthLoginUseCase(repo, cache)
        return await uc.execute("google", sub, email, tenant_id)
