from collections.abc import AsyncIterator, Callable
from typing import Any
from uuid import UUID

from knowledge_core import AgentTask, AgentTaskType, ProductEvent
from pydantic import BaseModel, Field

from harness_core.adapters import (
    DeepAgentsAdapter,
    HarnessAdapter,
    HarnessMessage,
    HarnessRunRequest,
)
from harness_core.tools import DeepAgentsToolAdapter, Tool, ToolCall, ToolResult


class KnowledgeChatInput(BaseModel):
    """Minimal product request for a knowledge chat run."""

    project_id: UUID
    user_message: str = Field(min_length=1)
    conversation_id: UUID | None = None
    created_by_user_id: UUID | None = None
    thread_id: str
    context: dict[str, Any] = Field(default_factory=dict)


async def run_knowledge_chat(
    request: KnowledgeChatInput,
    adapter: HarnessAdapter,
) -> AsyncIterator[ProductEvent]:
    """Run the minimal knowledge-chat path through the harness adapter boundary."""

    task = AgentTask(
        project_id=request.project_id,
        conversation_id=request.conversation_id,
        created_by_user_id=request.created_by_user_id,
        task_type=AgentTaskType.CHAT_ANSWER,
        intent=request.user_message,
    )
    harness_request = HarnessRunRequest(
        task=task,
        messages=[HarnessMessage(role="user", content=request.user_message)],
        thread_id=request.thread_id,
        checkpoint_namespace="knowledge_chat",
        context=request.context,
        metadata={"run_kind": "knowledge_chat"},
    )

    async for event in adapter.start(harness_request):
        yield event


def build_minimal_knowledge_chat_adapter(
    *,
    model: str,
    create_agent: Callable[..., Any] | None = None,
) -> DeepAgentsAdapter:
    """Create a DeepAgents-backed adapter with one safe project-context tool."""

    tool_adapter = DeepAgentsToolAdapter.from_tools([project_context_tool()])
    return DeepAgentsAdapter(
        model=model,
        system_prompt=(
            "You answer questions using the provided project context. "
            "Use tools when useful, and cite uncertainty instead of inventing facts."
        ),
        tools=tool_adapter.tools(),
        create_agent=create_agent,
    )


def project_context_tool() -> Tool:
    async def read_project_context(call: ToolCall) -> ToolResult:
        topic = call.arguments.get("topic", "project")
        return ToolResult(
            call_id=call.id,
            ok=True,
            output={
                "topic": topic,
                "summary": "No indexed project knowledge has been attached yet.",
            },
        )

    return Tool(
        name="read_project_context",
        description="Read minimal project context available to the knowledge chat run.",
        permissions=["read:project"],
        result_schema={
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": ["topic", "summary"],
        },
        handler=read_project_context,
    )
