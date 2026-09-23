from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Base class for all domain events (Event-Driven Architecture)."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    tenant_id: str
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainEvent":
        return cls(**data)
