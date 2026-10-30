from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from knowledge_core.contracts import (
    AgentTask,
    AgentTaskType,
    Conversation,
    DeepAgentsThread,
    InterventionRequest,
    InterventionType,
    Message,
    MessageRole,
    ResearchRun,
)
from knowledge_core.persistence import PlatformRepositories


@dataclass(frozen=True)
class ConversationTurn:
    conversation: Conversation
    message: Message
    task: AgentTask
    thread: DeepAgentsThread


@dataclass(frozen=True)
class ResearchSession:
    turn: ConversationTurn
    research_run: ResearchRun
    thread: DeepAgentsThread


@dataclass(frozen=True)
class ResumeState:
    intervention: InterventionRequest
    task: AgentTask
    thread: DeepAgentsThread


class ConversationSessionService:
    """Creates durable product state before an agent is allowed to execute."""

    def __init__(self, repositories: PlatformRepositories) -> None:
        self.repositories = repositories

    def record_user_turn(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
        content: str,
        task_type: AgentTaskType = AgentTaskType.CHAT_ANSWER,
        task_settings: dict[str, Any] | None = None,
    ) -> ConversationTurn:
        conversation = self.repositories.conversations.get(conversation_id)
        sequence = self.repositories.messages.next_sequence(conversation_id)
        message = self.repositories.messages.add(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=content,
                sequence=sequence,
                user_id=user_id,
            )
        )
        thread = self._conversation_thread(conversation)
        task = self.repositories.tasks.add(
            AgentTask(
                project_id=conversation.project_id,
                conversation_id=conversation.id,
                created_by_user_id=user_id,
                task_type=task_type,
                intent=content,
                settings=task_settings or {},
            )
        )
        return ConversationTurn(conversation, message, task, thread)

    def start_research(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
        intent: str,
        settings: dict[str, Any] | None = None,
    ) -> ResearchSession:
        turn = self.record_user_turn(
            conversation_id=conversation_id,
            user_id=user_id,
            content=intent,
            task_type=AgentTaskType.DEEP_RESEARCH,
            task_settings=settings,
        )
        research_run = self.repositories.research_runs.add(
            ResearchRun(
                project_id=turn.conversation.project_id,
                conversation_id=turn.conversation.id,
                agent_task_id=turn.task.id,
                created_by_user_id=user_id,
                intent=intent,
                settings=settings or {},
            )
        )
        research_message = self.repositories.messages.update(
            turn.message.model_copy(update={"research_run_id": research_run.id})
        )
        turn = ConversationTurn(turn.conversation, research_message, turn.task, turn.thread)
        thread = self.repositories.deepagents_threads.add(
            DeepAgentsThread(
                project_id=turn.conversation.project_id,
                conversation_id=turn.conversation.id,
                agent_task_id=turn.task.id,
                research_run_id=research_run.id,
                thread_id=f"research:{research_run.id}",
                checkpoint_namespace="deep_research",
            )
        )
        return ResearchSession(turn, research_run, thread)

    def link_intervention(
        self,
        *,
        task_id: UUID,
        thread_id: UUID,
        checkpoint_id: str,
        intervention_type: InterventionType,
        request_payload: dict[str, Any],
        research_run_id: UUID | None = None,
    ) -> InterventionRequest:
        task = self.repositories.tasks.get(task_id)
        thread = self.repositories.deepagents_threads.get(thread_id)
        if thread.agent_task_id not in {None, task.id}:
            raise ValueError("DeepAgents thread belongs to a different task")
        if research_run_id is not None and thread.research_run_id != research_run_id:
            raise ValueError("DeepAgents thread belongs to a different research run")
        return self.repositories.interventions.add(
            InterventionRequest(
                project_id=task.project_id,
                conversation_id=task.conversation_id,
                agent_task_id=task.id,
                research_run_id=research_run_id,
                deepagents_thread_id=thread.id,
                checkpoint_id=checkpoint_id,
                type=intervention_type,
                request_payload=request_payload,
            )
        )

    def resume_state(self, intervention_id: UUID) -> ResumeState:
        intervention = self.repositories.interventions.get(intervention_id)
        if intervention.agent_task_id is None:
            raise ValueError("intervention is not linked to an agent task")
        task = self.repositories.tasks.get(intervention.agent_task_id)
        thread = self.repositories.deepagents_threads.get(intervention.deepagents_thread_id)
        return ResumeState(intervention, task, thread)

    def _conversation_thread(self, conversation: Conversation) -> DeepAgentsThread:
        for thread in self.repositories.deepagents_threads.list():
            if (
                thread.conversation_id == conversation.id
                and thread.agent_task_id is None
                and thread.research_run_id is None
            ):
                return thread
        return self.repositories.deepagents_threads.add(
            DeepAgentsThread(
                project_id=conversation.project_id,
                conversation_id=conversation.id,
                thread_id=f"conversation:{conversation.id}",
                checkpoint_namespace="knowledge_chat",
            )
        )
