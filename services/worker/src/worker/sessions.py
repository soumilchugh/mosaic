from __future__ import annotations

from typing import Any
from uuid import UUID

from harness_core import HarnessMessage, HarnessResumeRequest, HarnessRunRequest
from knowledge_core import AgentTaskType, ConversationSessionService
from knowledge_core.persistence import PlatformRepositories


def prepare_conversation_run(
    repositories: PlatformRepositories,
    *,
    conversation_id: UUID,
    user_id: UUID,
    content: str,
    context: dict[str, Any] | None = None,
) -> HarnessRunRequest:
    """Persist the user turn and mapping before returning executable work."""

    turn = ConversationSessionService(repositories).record_user_turn(
        conversation_id=conversation_id,
        user_id=user_id,
        content=content,
        task_type=AgentTaskType.CHAT_ANSWER,
    )
    messages = [
        HarnessMessage(role=message.role.value, content=message.content)
        for message in repositories.messages.list()
        if message.conversation_id == conversation_id
    ]
    return HarnessRunRequest(
        task=turn.task,
        messages=messages,
        thread_id=turn.thread.thread_id,
        checkpoint_namespace=turn.thread.checkpoint_namespace,
        context=context or {},
        metadata={"message_id": str(turn.message.id), "run_kind": "knowledge_chat"},
    )


def reconstruct_resume_request(
    repositories: PlatformRepositories,
    *,
    intervention_id: UUID,
    decisions: list[dict[str, Any]],
) -> HarnessResumeRequest:
    """Rebuild a DeepAgents resume call entirely from persisted product IDs."""

    state = ConversationSessionService(repositories).resume_state(intervention_id)
    return HarnessResumeRequest(
        task=state.task,
        thread_id=state.thread.thread_id,
        checkpoint_namespace=state.thread.checkpoint_namespace,
        checkpoint_id=state.intervention.checkpoint_id,
        decisions=decisions,
        metadata={"intervention_request_id": str(state.intervention.id)},
    )
