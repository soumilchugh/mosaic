from collections.abc import AsyncIterator

from pydantic import BaseModel, Field

from harness_core.events import Event, EventType
from harness_core.tools import ToolCall, ToolRegistry


class AgentTask(BaseModel):
    run_id: str
    intent: str
    requested_tools: list[ToolCall] = Field(default_factory=list)


class AgentRuntime:
    def __init__(self, tools: ToolRegistry) -> None:
        self.tools = tools

    async def run(self, task: AgentTask) -> AsyncIterator[Event]:
        yield Event(run_id=task.run_id, type=EventType.RUN_STARTED, payload={"intent": task.intent})

        try:
            for call in task.requested_tools:
                yield Event(
                    run_id=task.run_id,
                    type=EventType.TOOL_CALLED,
                    payload={"tool": call.name, "call_id": call.id},
                )
                result = await self.tools.call(call)
                yield Event(
                    run_id=task.run_id,
                    type=EventType.TOOL_COMPLETED,
                    payload=result.model_dump(),
                )
        except Exception as exc:
            yield Event(run_id=task.run_id, type=EventType.RUN_FAILED, payload={"error": str(exc)})
            return

        yield Event(run_id=task.run_id, type=EventType.RUN_COMPLETED, payload={})
