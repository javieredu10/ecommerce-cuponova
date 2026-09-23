from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.infrastructure.adapters.postgres.repository import engine, Base
from src.infrastructure.api.routes.user_routes import router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Users Service",
    description="Gestión de perfiles: Administradores, Proveedores y Clientes",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api/v1/users", tags=["Users"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "users-service"}
