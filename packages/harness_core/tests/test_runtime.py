from harness_core.events import EventType
from harness_core.runtime import AgentRuntime, AgentTask
from harness_core.tools import Tool, ToolCall, ToolRegistry, ToolResult


async def test_runtime_emits_events_around_tool_calls() -> None:
    async def echo(call: ToolCall) -> ToolResult:
        return ToolResult(call_id=call.id, ok=True, output={"value": call.arguments["value"]})

    registry = ToolRegistry()
    registry.register(Tool(name="echo", description="Echo arguments", handler=echo))

    task = AgentTask(
        run_id="run_1",
        intent="exercise runtime",
        requested_tools=[ToolCall(name="echo", arguments={"value": "hello"})],
    )

    events = [event async for event in AgentRuntime(registry).run(task)]

    assert [event.type for event in events] == [
        EventType.RUN_STARTED,
        EventType.TOOL_CALLED,
        EventType.TOOL_COMPLETED,
        EventType.RUN_COMPLETED,
    ]
    assert events[2].payload["output"] == {"value": "hello"}
