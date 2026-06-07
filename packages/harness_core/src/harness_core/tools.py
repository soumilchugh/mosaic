from collections.abc import Awaitable, Callable
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


class Tool(BaseModel):
    name: str
    description: str
    handler: ToolHandler = Field(exclude=True)

    model_config = {"arbitrary_types_allowed": True}


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
