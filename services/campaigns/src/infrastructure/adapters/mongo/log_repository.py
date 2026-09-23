import os
from datetime import datetime
from typing import Any, Dict
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://admin:secret@localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "ecommerce_logs")


class CampaignLogRepository:
    """Non-transactional audit logs stored in MongoDB."""

    def __init__(self):
        self._client = AsyncIOMotorClient(MONGO_URL)
        self._db = self._client[MONGO_DB]
        self._col = self._db["campaign_logs"]

    async def log_action(self, tenant_id: str, action: str, data: Dict[str, Any]) -> None:
        await self._col.insert_one({
            "tenant_id": tenant_id,
            "action": action,
            "data": data,
            "timestamp": datetime.utcnow(),
        })

    async def get_logs(self, tenant_id: str, limit: int = 50):
        cursor = self._col.find(
            {"tenant_id": tenant_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)


_log_repo = CampaignLogRepository()

def get_log_repo() -> CampaignLogRepository:
    return _log_repo
