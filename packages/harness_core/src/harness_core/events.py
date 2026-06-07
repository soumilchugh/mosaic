from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    RUN_STARTED = "run.started"
    TOOL_CALLED = "tool.called"
    TOOL_COMPLETED = "tool.completed"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"


class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
