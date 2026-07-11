import asyncio
from collections.abc import AsyncIterator, Callable, Iterable
from typing import Any, Protocol

from knowledge_core import AgentTask, ProductEvent
from pydantic import BaseModel, Field


class HarnessMessage(BaseModel):
    """Message shape passed through the harness boundary."""

    role: str = Field(min_length=1)
    content: str = Field(min_length=1)


class HarnessRunRequest(BaseModel):
    """Product-owned request for starting a new agent run."""

    task: AgentTask
    messages: list[HarnessMessage]
    thread_id: str
    checkpoint_namespace: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HarnessResumeRequest(BaseModel):
    """Product-owned request for resuming an interrupted agent run."""

    task: AgentTask
    thread_id: str
    decisions: list[dict[str, Any]]
    checkpoint_namespace: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HarnessAdapter(Protocol):
    """Boundary API used by workers and APIs instead of calling DeepAgents directly."""

    async def start(self, request: HarnessRunRequest) -> AsyncIterator[ProductEvent]:
        """Start a new agent run and stream product events."""
        ...

    async def resume(self, request: HarnessResumeRequest) -> AsyncIterator[ProductEvent]:
        """Resume an interrupted run and stream product events."""
        ...


class FakeHarnessAdapter:
    """Deterministic adapter for tests and local API/worker wiring."""

    def __init__(self, event_types: Iterable[str] | None = None) -> None:
        self.event_types = list(event_types or ["run.started", "run.completed"])
        self.started: list[HarnessRunRequest] = []
        self.resumed: list[HarnessResumeRequest] = []

    async def start(self, request: HarnessRunRequest) -> AsyncIterator[ProductEvent]:
        self.started.append(request)
        for sequence, event_type in enumerate(self.event_types):
            yield _product_event(
                request.task,
                sequence,
                event_type,
                {"thread_id": request.thread_id},
            )

    async def resume(self, request: HarnessResumeRequest) -> AsyncIterator[ProductEvent]:
        self.resumed.append(request)
        payload = {"thread_id": request.thread_id, "decision_count": len(request.decisions)}
        for sequence, event_type in enumerate(["run.resumed", "run.completed"]):
            yield _product_event(request.task, sequence, event_type, payload)


class DeepAgentsAdapter:
    """Thin SDK adapter that hides DeepAgents details behind product contracts."""

    def __init__(
        self,
        *,
        model: str,
        system_prompt: str,
        tools: Iterable[Any] = (),
        create_agent: Callable[..., Any] | None = None,
        checkpointer: Any | None = None,
    ) -> None:
        self.model = model
        self.system_prompt = system_prompt
        self.tools = list(tools)
        self._create_agent = create_agent
        self.checkpointer = checkpointer

    async def start(self, request: HarnessRunRequest) -> AsyncIterator[ProductEvent]:
        yield _product_event(request.task, 0, "run.started", {"thread_id": request.thread_id})

        try:
            result = await asyncio.to_thread(
                self._invoke_agent,
                {"messages": [message.model_dump() for message in request.messages]},
                request.thread_id,
                request.checkpoint_namespace,
            )
        except Exception as exc:
            yield _product_event(request.task, 1, "run.failed", {"error": str(exc)})
            return

        yield _product_event(
            request.task,
            1,
            "run.completed",
            {"thread_id": request.thread_id, "result": _serializable_result(result)},
        )

    async def resume(self, request: HarnessResumeRequest) -> AsyncIterator[ProductEvent]:
        yield _product_event(request.task, 0, "run.resumed", {"thread_id": request.thread_id})

        try:
            result = await asyncio.to_thread(
                self._invoke_resume,
                {"decisions": request.decisions},
                request.thread_id,
                request.checkpoint_namespace,
            )
        except Exception as exc:
            yield _product_event(request.task, 1, "run.failed", {"error": str(exc)})
            return

        yield _product_event(
            request.task,
            1,
            "run.completed",
            {"thread_id": request.thread_id, "result": _serializable_result(result)},
        )

    def _agent(self) -> Any:
        create_agent = self._create_agent
        if create_agent is None:
            from deepagents import create_deep_agent

            create_agent = create_deep_agent

        kwargs: dict[str, Any] = {
            "model": self.model,
            "tools": self.tools,
            "system_prompt": self.system_prompt,
        }
        if self.checkpointer is not None:
            kwargs["checkpointer"] = self.checkpointer
        return create_agent(**kwargs)

    def _invoke_agent(
        self,
        input_payload: dict[str, Any],
        thread_id: str,
        checkpoint_namespace: str | None,
    ) -> Any:
        return self._agent().invoke(
            input_payload,
            config=_deepagents_config(thread_id, checkpoint_namespace),
            version="v2",
        )

    def _invoke_resume(
        self,
        resume_payload: dict[str, Any],
        thread_id: str,
        checkpoint_namespace: str | None,
    ) -> Any:
        from langgraph.types import Command

        return self._agent().invoke(
            Command(resume=resume_payload),
            config=_deepagents_config(thread_id, checkpoint_namespace),
            version="v2",
        )


def _product_event(
    task: AgentTask,
    sequence: int,
    event_type: str,
    payload: dict[str, Any],
) -> ProductEvent:
    return ProductEvent(
        project_id=task.project_id,
        conversation_id=task.conversation_id,
        agent_task_id=task.id,
        sequence=sequence,
        type=event_type,
        payload=payload,
    )


def _deepagents_config(thread_id: str, checkpoint_namespace: str | None) -> dict[str, Any]:
    configurable: dict[str, Any] = {"thread_id": thread_id}
    if checkpoint_namespace is not None:
        configurable["checkpoint_ns"] = checkpoint_namespace
    return {"configurable": configurable}


def _serializable_result(result: Any) -> Any:
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, dict | list | str | int | float | bool) or result is None:
        return result
    if hasattr(result, "value"):
        return _serializable_result(result.value)
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    return repr(result)
