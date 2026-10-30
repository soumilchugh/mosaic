from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from knowledge_core.config import ProviderKind, ProviderRegistry
from knowledge_core.contracts import AgentTask, AgentTaskType


def utc_now() -> datetime:
    return datetime.now(UTC)


class QueueItemState(StrEnum):
    AVAILABLE = "available"
    LEASED = "leased"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


class TaskQueueMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    project_id: UUID
    task_type: AgentTaskType
    idempotency_key: str = Field(min_length=1, max_length=300)
    max_attempts: int = Field(default=3, ge=1, le=100)
    trace_id: str | None = Field(default=None, max_length=300)
    enqueued_at: datetime = Field(default_factory=utc_now)

    @field_validator("enqueued_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("enqueued_at must be timezone-aware")
        return value

    @classmethod
    def from_task(
        cls,
        task: AgentTask,
        *,
        idempotency_key: str,
        max_attempts: int = 3,
        trace_id: str | None = None,
    ) -> TaskQueueMessage:
        return cls(
            task_id=task.id,
            project_id=task.project_id,
            task_type=task.task_type,
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
            trace_id=trace_id,
        )


class QueueDelivery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: UUID
    message: TaskQueueMessage
    delivery_count: int = Field(ge=1)
    lease_expires_at: datetime


class EnqueueResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    message: TaskQueueMessage
    accepted: bool


class TaskQueueError(RuntimeError):
    pass


class UnknownDeliveryError(TaskQueueError):
    pass


class DeliveryLeaseExpiredError(TaskQueueError):
    pass


@runtime_checkable
class TaskQueue(Protocol):
    async def enqueue(self, message: TaskQueueMessage) -> EnqueueResult: ...

    async def receive(
        self,
        *,
        max_messages: int = 1,
        visibility_timeout: timedelta = timedelta(minutes=5),
    ) -> list[QueueDelivery]: ...

    async def complete(self, delivery: QueueDelivery) -> None: ...

    async def retry(
        self,
        delivery: QueueDelivery,
        *,
        delay: timedelta = timedelta(0),
        error: str | None = None,
    ) -> QueueItemState: ...

    async def cancel(self, task_id: UUID) -> bool: ...

    async def state(self, task_id: UUID) -> QueueItemState | None: ...


@dataclass
class _QueueEntry:
    message: TaskQueueMessage
    state: QueueItemState
    available_at: datetime
    delivery_count: int = 0
    receipt_id: UUID | None = None
    lease_expires_at: datetime | None = None
    last_error: str | None = None


class InMemoryTaskQueue:
    """Deterministic task queue implementing production-style delivery leases."""

    def __init__(self, clock: Callable[[], datetime] = utc_now) -> None:
        self._clock = clock
        self._lock = asyncio.Lock()
        self._entries: dict[UUID, _QueueEntry] = {}
        self._task_index: dict[UUID, UUID] = {}
        self._idempotency_index: dict[str, UUID] = {}

    async def enqueue(self, message: TaskQueueMessage) -> EnqueueResult:
        async with self._lock:
            existing_id = self._task_index.get(message.task_id) or self._idempotency_index.get(
                message.idempotency_key
            )
            if existing_id is not None:
                return EnqueueResult(message=self._entries[existing_id].message, accepted=False)

            self._entries[message.id] = _QueueEntry(
                message=message,
                state=QueueItemState.AVAILABLE,
                available_at=message.enqueued_at,
            )
            self._task_index[message.task_id] = message.id
            self._idempotency_index[message.idempotency_key] = message.id
            return EnqueueResult(message=message, accepted=True)

    async def receive(
        self,
        *,
        max_messages: int = 1,
        visibility_timeout: timedelta = timedelta(minutes=5),
    ) -> list[QueueDelivery]:
        if max_messages < 1:
            raise ValueError("max_messages must be at least one")
        if visibility_timeout <= timedelta(0):
            raise ValueError("visibility_timeout must be positive")

        async with self._lock:
            now = self._now()
            self._release_expired_leases(now)
            available = sorted(
                (
                    entry
                    for entry in self._entries.values()
                    if entry.state is QueueItemState.AVAILABLE and entry.available_at <= now
                ),
                key=lambda entry: (entry.available_at, entry.message.enqueued_at, entry.message.id),
            )[:max_messages]

            deliveries = []
            for entry in available:
                entry.state = QueueItemState.LEASED
                entry.delivery_count += 1
                entry.receipt_id = uuid4()
                entry.lease_expires_at = now + visibility_timeout
                deliveries.append(self._delivery(entry))
            return deliveries

    async def complete(self, delivery: QueueDelivery) -> None:
        async with self._lock:
            entry = self._active_entry(delivery)
            entry.state = QueueItemState.COMPLETED
            self._clear_lease(entry)

    async def retry(
        self,
        delivery: QueueDelivery,
        *,
        delay: timedelta = timedelta(0),
        error: str | None = None,
    ) -> QueueItemState:
        if delay < timedelta(0):
            raise ValueError("retry delay cannot be negative")
        async with self._lock:
            entry = self._active_entry(delivery)
            entry.last_error = error
            if entry.delivery_count >= entry.message.max_attempts:
                entry.state = QueueItemState.DEAD_LETTER
            else:
                entry.state = QueueItemState.AVAILABLE
                entry.available_at = self._now() + delay
            self._clear_lease(entry)
            return entry.state

    async def cancel(self, task_id: UUID) -> bool:
        async with self._lock:
            message_id = self._task_index.get(task_id)
            if message_id is None:
                return False
            entry = self._entries[message_id]
            if entry.state in {
                QueueItemState.COMPLETED,
                QueueItemState.CANCELLED,
                QueueItemState.DEAD_LETTER,
            }:
                return False
            entry.state = QueueItemState.CANCELLED
            self._clear_lease(entry)
            return True

    async def state(self, task_id: UUID) -> QueueItemState | None:
        async with self._lock:
            message_id = self._task_index.get(task_id)
            if message_id is None:
                return None
            self._release_expired_leases(self._now())
            return self._entries[message_id].state

    def _active_entry(self, delivery: QueueDelivery) -> _QueueEntry:
        entry = self._entries.get(delivery.message.id)
        if (
            entry is None
            or entry.state is not QueueItemState.LEASED
            or entry.receipt_id != delivery.receipt_id
        ):
            raise UnknownDeliveryError(f"delivery receipt {delivery.receipt_id} is not active")
        if entry.lease_expires_at is None or entry.lease_expires_at <= self._now():
            self._release_expired_entry(entry)
            raise DeliveryLeaseExpiredError(f"delivery receipt {delivery.receipt_id} expired")
        return entry

    def _release_expired_leases(self, now: datetime) -> None:
        for entry in self._entries.values():
            if (
                entry.state is QueueItemState.LEASED
                and entry.lease_expires_at is not None
                and entry.lease_expires_at <= now
            ):
                self._release_expired_entry(entry)

    def _release_expired_entry(self, entry: _QueueEntry) -> None:
        if entry.delivery_count >= entry.message.max_attempts:
            entry.state = QueueItemState.DEAD_LETTER
        else:
            entry.state = QueueItemState.AVAILABLE
            entry.available_at = self._now()
        self._clear_lease(entry)

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("task queue clock must return a timezone-aware datetime")
        return value

    @staticmethod
    def _clear_lease(entry: _QueueEntry) -> None:
        entry.receipt_id = None
        entry.lease_expires_at = None

    @staticmethod
    def _delivery(entry: _QueueEntry) -> QueueDelivery:
        assert entry.receipt_id is not None
        assert entry.lease_expires_at is not None
        return QueueDelivery(
            receipt_id=entry.receipt_id,
            message=entry.message,
            delivery_count=entry.delivery_count,
            lease_expires_at=entry.lease_expires_at,
        )


def register_task_queue_providers(registry: ProviderRegistry) -> None:
    if "memory" not in registry.registered_names(ProviderKind.QUEUE):
        registry.register(ProviderKind.QUEUE, "memory", lambda _: InMemoryTaskQueue())
