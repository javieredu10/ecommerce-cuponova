from contextlib import asynccontextmanager
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.infrastructure.adapters.postgres.repository import engine, Base
from src.infrastructure.adapters.rabbitmq.consumer import start_consumer, register_create_delivery
from src.infrastructure.adapters.rabbitmq.publisher import get_publisher
from src.domain.entities.delivery import Delivery
from src.infrastructure.adapters.postgres.repository import async_session, DeliveryRepository
from src.infrastructure.api.routes.delivery_routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _auto_create_delivery(event: dict):
    async with async_session() as session:
        repo = DeliveryRepository(session)
        delivery = Delivery.create(
            tenant_id=event.get("tenant_id", ""),
            order_id=event.get("order_id", ""),
            customer_id=event.get("customer_id", ""),
            delivery_address=event.get("delivery_address", ""),
        )
        await repo.save(delivery)
        logger.info("Auto-created delivery %s for order %s",
                    delivery.id, delivery.order_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    register_create_delivery(_auto_create_delivery)
    consumer_task = asyncio.create_task(start_consumer())
    logger.info("Deliveries service started")
    yield
    consumer_task.cancel()
    await engine.dispose()


app = FastAPI(
    title="Deliveries Service",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1/deliveries", tags=["Deliveries"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "deliveries-service"}
