from typing import Any

from harness_core import (
    DeepAgentsToolAdapter,
    Tool,
    ToolCall,
    ToolMetadata,
    ToolResult,
    tool_result_to_event_payload,
)


async def test_product_tools_are_wrapped_as_deepagents_callables() -> None:
    async def echo(call: ToolCall) -> ToolResult:
        return ToolResult(call_id=call.id, ok=True, output={"value": call.arguments["value"]})

    adapter = DeepAgentsToolAdapter.from_tools(
        [
            Tool(
                name="echo",
                description="Echo a value.",
                permissions=["read:project"],
                result_schema={"type": "object"},
                handler=echo,
            )
        ]
    )

    [deepagents_tool] = adapter.tools()
    result = await deepagents_tool(value="hello")

    assert deepagents_tool.__name__ == "echo"
    assert "Echo a value." in (deepagents_tool.__doc__ or "")
    assert result["ok"] is True
    assert result["output"] == {"value": "hello"}
    assert adapter.metadata() == [
        ToolMetadata(
            name="echo",
            description="Echo a value.",
            permissions=["read:project"],
            result_schema={"type": "object"},
        )
    ]


async def test_product_tool_errors_are_structured() -> None:
    async def fail(call: ToolCall) -> ToolResult:
        raise RuntimeError("boom")

    adapter = DeepAgentsToolAdapter.from_tools(
        [Tool(name="explode", description="Fail predictably.", handler=fail)]
    )

    [deepagents_tool] = adapter.tools()
    result = await deepagents_tool()

    assert result["ok"] is False
    assert result["error"] == "boom"
    assert result["output"] == {}


def test_langchain_compatible_tools_can_be_registered_without_wrapping() -> None:
    def plain_tool(value: str) -> dict[str, Any]:
        """Already compatible with DeepAgents."""
        return {"value": value}

    adapter = DeepAgentsToolAdapter()
    adapter.register_deepagents_tool(
        plain_tool,
        ToolMetadata(name="plain_tool", description="Already compatible with DeepAgents."),
    )

    assert adapter.tools() == [plain_tool]
    assert adapter.metadata()[0].name == "plain_tool"


def test_tool_result_maps_to_product_event_payload() -> None:
    result = ToolResult(call_id="call-1", ok=False, error="denied")

    assert tool_result_to_event_payload(result) == {
        "call_id": "call-1",
        "ok": False,
        "output": {},
        "error": "denied",
    }
