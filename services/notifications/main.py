from contextlib import asynccontextmanager
import asyncio
import json
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import base64
import aio_pika
from aio_pika import ExchangeType
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:secret@localhost:5672/")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://admin:secret@localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "ecommerce_logs")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client[MONGO_DB]


async def log_notification(tenant_id: str, event_type: str, recipient: str, status: str, data: dict):
    """Store notification log in MongoDB (non-transactional)."""
    await db["notification_logs"].insert_one({
        "tenant_id": tenant_id,
        "event_type": event_type,
        "recipient": recipient,
        "status": status,
        "data": data,
        "created_at": datetime.utcnow(),
    })


def send_email(to: str, subject: str, body_html: str, qr_image_b64: str = None):
    msg = MIMEMultipart("related")
    msg["From"] = SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))
    if qr_image_b64:
        img_data = base64.b64decode(qr_image_b64)
        img = MIMEImage(img_data, name="qr.png")
        img.add_header("Content-ID", "<qr_code>")
        msg.attach(img)
    if SMTP_USER and SMTP_PASSWORD:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to, msg.as_string())


async def handle_order_paid(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        tenant_id = body.get("tenant_id", "")
        customer_id = body.get("customer_id", "")
        order_id = body.get("order_id", "")
        logger.info("Sending order confirmation email for order %s", order_id)
        html = f"""
        <h2>Order Confirmed!</h2>
        <p>Your order <strong>{order_id}</strong> has been paid successfully.</p>
        <p>Amount: ${body.get('amount', 0):.2f}</p>
        """
        try:
            send_email(customer_id, f"Order Confirmation - {order_id}", html)
            await log_notification(tenant_id, "order.paid", customer_id, "sent", body)
        except Exception as e:
            logger.error("Email error: %s", e)
            await log_notification(tenant_id, "order.paid", customer_id, "failed", {"error": str(e)})


async def handle_delivery_completed(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        tenant_id = body.get("tenant_id", "")
        customer_id = body.get("customer_id", "")
        order_id = body.get("order_id", "")
        qr_code = body.get("qr_code", "")
        logger.info("Sending delivery QR email for order %s", order_id)
        html = f"""
        <h2>Your order has been delivered!</h2>
        <p>Order <strong>{order_id}</strong> was delivered successfully.</p>
        <p>Scan the QR code below as your delivery receipt:</p>
        <img src="cid:qr_code" alt="QR Code" />
        """
        try:
            send_email(customer_id, f"Delivery Complete - {order_id}", html, qr_code)
            await log_notification(tenant_id, "delivery.completed", customer_id, "sent", body)
        except Exception as e:
            logger.error("QR email error: %s", e)
            await log_notification(tenant_id, "delivery.completed", customer_id, "failed", {"error": str(e)})


async def start_consumer():
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=5)

        orders_exchange = await channel.declare_exchange("orders.topic", ExchangeType.TOPIC, durable=True)
        deliveries_exchange = await channel.declare_exchange("deliveries.topic", ExchangeType.TOPIC, durable=True)

        q_paid = await channel.declare_queue("notifications.order.paid", durable=True)
        await q_paid.bind(orders_exchange, routing_key="order.paid")
        await q_paid.consume(handle_order_paid)

        q_delivered = await channel.declare_queue("notifications.delivery.completed", durable=True)
        await q_delivered.bind(deliveries_exchange, routing_key="delivery.completed")
        await q_delivered.consume(handle_delivery_completed)

        logger.info("Notifications consumer started")
        await asyncio.Future()
    except Exception as e:
        logger.error("Notifications consumer error: %s", e)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(start_consumer())
    yield
    task.cancel()


app = FastAPI(title="Notifications Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "notifications-service"}


@app.get("/api/v1/notifications/logs/{tenant_id}")
async def get_logs(tenant_id: str, limit: int = 50):
    cursor = db["notification_logs"].find({"tenant_id": tenant_id}, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)
