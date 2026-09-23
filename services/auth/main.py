from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from src.infrastructure.api.routes.auth_routes import router as auth_router
from src.infrastructure.api.routes.oauth_routes import router as oauth_router
from src.infrastructure.adapters.postgres.database import engine, Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Auth service started — tables ready")
    yield
    # Shutdown
    await engine.dispose()
    logger.info("Auth service stopped")


app = FastAPI(
    title="Auth Service",
    description="JWT + OAuth2 authentication for multitenant ecommerce",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(oauth_router, prefix="/api/v1/oauth", tags=["OAuth2"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth-service"}
