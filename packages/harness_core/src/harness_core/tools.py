import inspect
from collections.abc import Awaitable, Callable, Iterable
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    call_id: str
    ok: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


ToolHandler = Callable[[ToolCall], Awaitable[ToolResult]]
DeepAgentsTool = Callable[..., Any]


class ToolMetadata(BaseModel):
    name: str
    description: str
    permissions: list[str] = Field(default_factory=list)
    result_schema: dict[str, Any] = Field(default_factory=dict)


class Tool(BaseModel):
    name: str
    description: str
    permissions: list[str] = Field(default_factory=list)
    result_schema: dict[str, Any] = Field(default_factory=dict)
    handler: ToolHandler = Field(exclude=True)

    model_config = {"arbitrary_types_allowed": True}

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            description=self.description,
            permissions=self.permissions,
            result_schema=self.result_schema,
        )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    async def call(self, call: ToolCall) -> ToolResult:
        tool = self.get(call.name)
        return await tool.handler(call)


class DeepAgentsToolAdapter:
    """Expose product tools as DeepAgents-compatible callables."""

    def __init__(self) -> None:
        self._registry = ToolRegistry()
        self._passthrough_tools: list[DeepAgentsTool] = []
        self._metadata: dict[str, ToolMetadata] = {}

    def register(self, tool: Tool) -> None:
        self._registry.register(tool)
        self._metadata[tool.name] = tool.metadata()

    def register_deepagents_tool(self, tool: DeepAgentsTool, metadata: ToolMetadata) -> None:
        self._passthrough_tools.append(tool)
        self._metadata[metadata.name] = metadata

    def metadata(self) -> list[ToolMetadata]:
        return list(self._metadata.values())

    def tools(self) -> list[DeepAgentsTool]:
        wrapped_tools = [_wrap_product_tool(tool) for tool in self._registry.list()]
        return [*wrapped_tools, *self._passthrough_tools]

    @classmethod
    def from_tools(cls, tools: Iterable[Tool]) -> "DeepAgentsToolAdapter":
        adapter = cls()
        for tool in tools:
            adapter.register(tool)
        return adapter


def tool_result_to_event_payload(result: ToolResult) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "call_id": result.call_id,
        "ok": result.ok,
        "output": result.output,
    }
    if result.error is not None:
        payload["error"] = result.error
    return payload


def _wrap_product_tool(tool: Tool) -> DeepAgentsTool:
    async def invoke(**arguments: Any) -> dict[str, Any]:
        call = ToolCall(name=tool.name, arguments=arguments)
        try:
            result = await tool.handler(call)
        except Exception as exc:
            result = ToolResult(call_id=call.id, ok=False, error=str(exc))
        return tool_result_to_event_payload(result)

    invoke.__name__ = tool.name
    invoke.__doc__ = _tool_docstring(tool)
    invoke.__signature__ = inspect.Signature(
        parameters=[
            inspect.Parameter(
                "arguments",
                inspect.Parameter.VAR_KEYWORD,
                annotation=Any,
            )
        ],
        return_annotation=dict[str, Any],
    )
    return invoke


def _tool_docstring(tool: Tool) -> str:
    lines = [tool.description]
    if tool.permissions:
        lines.append(f"Permissions: {', '.join(tool.permissions)}.")
    if tool.result_schema:
        lines.append("Returns a structured result matching the product result schema.")
    return "\n\n".join(lines)
