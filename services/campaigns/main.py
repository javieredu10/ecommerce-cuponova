from contextlib import asynccontextmanager
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.infrastructure.adapters.postgres.database import engine, Base
from src.infrastructure.adapters.rabbitmq.consumer import start_consumer
from src.infrastructure.api.routes.campaign_routes import router as campaign_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Start event consumer in background
    consumer_task = asyncio.create_task(start_consumer())
    logger.info("Campaigns service started")
    yield
    consumer_task.cancel()
    await engine.dispose()


app = FastAPI(title="Campaigns Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(campaign_router, prefix="/api/v1/campaigns", tags=["Campaigns"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "campaigns-service"}
