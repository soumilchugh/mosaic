import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from knowledge_core import (
    AgentTask,
    AgentTaskType,
    DeliveryLeaseExpiredError,
    InMemoryTaskQueue,
    QueueItemState,
    TaskQueue,
    TaskQueueMessage,
    UnknownDeliveryError,
)
from pydantic import ValidationError


@dataclass
class FakeClock:
    current: datetime

    def __call__(self) -> datetime:
        return self.current

    def advance(self, duration: timedelta) -> None:
        self.current += duration


def make_clock() -> FakeClock:
    return FakeClock(datetime(2026, 10, 30, 12, 0, tzinfo=UTC))


def make_message(
    clock: FakeClock,
    *,
    task_id=None,
    idempotency_key: str | None = None,
    max_attempts: int = 3,
) -> TaskQueueMessage:
    task_id = task_id or uuid4()
    return TaskQueueMessage(
        task_id=task_id,
        project_id=uuid4(),
        task_type=AgentTaskType.CHAT_ANSWER,
        idempotency_key=idempotency_key or f"task:{task_id}",
        max_attempts=max_attempts,
        enqueued_at=clock.current,
    )


def test_message_can_be_created_from_persisted_agent_task() -> None:
    task = AgentTask(
        project_id=uuid4(),
        task_type=AgentTaskType.DEEP_RESEARCH,
        intent="Research durable queues",
    )

    message = TaskQueueMessage.from_task(
        task,
        idempotency_key="request:research-1",
        trace_id="trace-1",
    )

    assert message.task_id == task.id
    assert message.project_id == task.project_id
    assert message.task_type is AgentTaskType.DEEP_RESEARCH
    assert message.trace_id == "trace-1"


def test_message_rejects_naive_enqueue_time() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        TaskQueueMessage(
            task_id=uuid4(),
            project_id=uuid4(),
            task_type=AgentTaskType.CHAT_ANSWER,
            idempotency_key="request:naive",
            enqueued_at=datetime(2026, 10, 30, 12, 0),
        )


@pytest.mark.asyncio
async def test_enqueue_is_idempotent_by_task_and_request_key() -> None:
    clock = make_clock()
    queue = InMemoryTaskQueue(clock)
    original = make_message(clock, idempotency_key="request:1")

    first = await queue.enqueue(original)
    same_task = await queue.enqueue(
        make_message(clock, task_id=original.task_id, idempotency_key="request:2")
    )
    same_request = await queue.enqueue(make_message(clock, idempotency_key="request:1"))

    assert first.accepted is True
    assert same_task.accepted is False
    assert same_request.accepted is False
    assert same_task.message.id == original.id
    assert same_request.message.id == original.id


@pytest.mark.asyncio
async def test_receive_uses_exclusive_lease_and_complete_is_terminal() -> None:
    clock = make_clock()
    queue = InMemoryTaskQueue(clock)
    message = make_message(clock)
    await queue.enqueue(message)

    first_worker, second_worker = await asyncio.gather(
        queue.receive(visibility_timeout=timedelta(seconds=30)),
        queue.receive(visibility_timeout=timedelta(seconds=30)),
    )
    deliveries = first_worker + second_worker

    assert isinstance(queue, TaskQueue)
    assert len(deliveries) == 1
    assert deliveries[0].delivery_count == 1
    assert await queue.state(message.task_id) is QueueItemState.LEASED

    await queue.complete(deliveries[0])

    assert await queue.state(message.task_id) is QueueItemState.COMPLETED
    assert await queue.receive() == []
    with pytest.raises(UnknownDeliveryError):
        await queue.complete(deliveries[0])


@pytest.mark.asyncio
async def test_expired_lease_is_redelivered_with_a_new_receipt() -> None:
    clock = make_clock()
    queue = InMemoryTaskQueue(clock)
    message = make_message(clock)
    await queue.enqueue(message)
    original = (await queue.receive(visibility_timeout=timedelta(seconds=10)))[0]
    clock.advance(timedelta(seconds=10))

    with pytest.raises(DeliveryLeaseExpiredError):
        await queue.complete(original)

    redelivered = (await queue.receive(visibility_timeout=timedelta(seconds=10)))[0]
    assert redelivered.receipt_id != original.receipt_id
    assert redelivered.delivery_count == 2


@pytest.mark.asyncio
async def test_retry_delay_and_attempt_limit_move_failed_work_to_dead_letter() -> None:
    clock = make_clock()
    queue = InMemoryTaskQueue(clock)
    message = make_message(clock, max_attempts=2)
    await queue.enqueue(message)
    first = (await queue.receive())[0]

    state = await queue.retry(first, delay=timedelta(minutes=1), error="temporary")
    assert state is QueueItemState.AVAILABLE
    assert await queue.receive() == []

    clock.advance(timedelta(minutes=1))
    second = (await queue.receive())[0]
    state = await queue.retry(second, error="permanent")

    assert state is QueueItemState.DEAD_LETTER
    assert await queue.state(message.task_id) is QueueItemState.DEAD_LETTER
    assert await queue.receive() == []


@pytest.mark.asyncio
async def test_cancel_prevents_available_or_leased_work_from_running() -> None:
    clock = make_clock()
    queue = InMemoryTaskQueue(clock)
    available = make_message(clock)
    leased = make_message(clock)
    await queue.enqueue(available)
    await queue.enqueue(leased)
    delivery = (await queue.receive(max_messages=1))[0]
    leased_task_id = delivery.message.task_id
    available_task_id = available.task_id if available.task_id != leased_task_id else leased.task_id

    assert await queue.cancel(leased_task_id) is True
    assert await queue.cancel(available_task_id) is True
    assert await queue.cancel(uuid4()) is False
    assert await queue.receive() == []
    with pytest.raises(UnknownDeliveryError):
        await queue.complete(delivery)
