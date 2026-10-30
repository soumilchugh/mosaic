from __future__ import annotations

import os
from uuid import uuid4

import pytest
from knowledge_core import (
    AgentTaskType,
    Conversation,
    ConversationSessionService,
    InterventionType,
    Project,
)
from knowledge_core.persistence import (
    InMemoryRepositories,
    InMemoryRepositoryStore,
    ProjectContext,
    ProjectRecord,
    SqlAlchemyRepositories,
    UserRecord,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def make_session_service():
    owner_id = uuid4()
    project = Project(
        name="Session test",
        slug=f"session-test-{uuid4().hex}",
        created_by_user_id=owner_id,
    )
    store = InMemoryRepositoryStore(projects={project.id: project})
    repositories = InMemoryRepositories(store, ProjectContext(project.id, owner_id))
    conversation = repositories.conversations.add(
        Conversation(project_id=project.id, created_by_user_id=owner_id)
    )
    return ConversationSessionService(repositories), repositories, store, conversation, owner_id


def test_user_turns_are_persisted_in_order_and_reuse_conversation_thread() -> None:
    service, repositories, _, conversation, owner_id = make_session_service()

    first = service.record_user_turn(
        conversation_id=conversation.id,
        user_id=owner_id,
        content="What is Mosaic?",
    )
    second = service.record_user_turn(
        conversation_id=conversation.id,
        user_id=owner_id,
        content="What did I ask before?",
    )

    messages = repositories.messages.list()
    assert [message.sequence for message in messages] == [0, 1]
    assert [message.content for message in messages] == [
        "What is Mosaic?",
        "What did I ask before?",
    ]
    assert repositories.messages.get(first.message.id) == first.message
    assert first.task.task_type is AgentTaskType.CHAT_ANSWER
    assert first.thread.id == second.thread.id
    assert first.thread.thread_id == f"conversation:{conversation.id}"


def test_research_run_gets_isolated_thread_and_checkpoint_link() -> None:
    service, repositories, _, conversation, owner_id = make_session_service()

    session = service.start_research(
        conversation_id=conversation.id,
        user_id=owner_id,
        intent="Research durable agent memory",
    )
    intervention = service.link_intervention(
        task_id=session.turn.task.id,
        thread_id=session.thread.id,
        research_run_id=session.research_run.id,
        checkpoint_id="checkpoint-42",
        intervention_type=InterventionType.TOPIC_APPROVAL,
        request_payload={"topics": ["memory"]},
    )
    resume = service.resume_state(intervention.id)

    assert session.thread.thread_id == f"research:{session.research_run.id}"
    assert session.thread.checkpoint_namespace == "deep_research"
    assert session.thread.id != session.turn.thread.id
    assert session.turn.message.research_run_id == session.research_run.id
    assert resume.task.id == session.turn.task.id
    assert resume.thread.id == session.thread.id
    assert resume.intervention.checkpoint_id == "checkpoint-42"
    assert repositories.research_runs.get(session.research_run.id) == session.research_run


def test_resume_state_can_be_loaded_from_a_fresh_repository_instance() -> None:
    service, repositories, store, conversation, owner_id = make_session_service()
    turn = service.record_user_turn(
        conversation_id=conversation.id,
        user_id=owner_id,
        content="Approve this tool call",
    )
    task_thread = repositories.deepagents_threads.add(
        turn.thread.model_copy(
            update={
                "id": uuid4(),
                "agent_task_id": turn.task.id,
                "thread_id": f"task:{turn.task.id}",
            }
        )
    )
    intervention = service.link_intervention(
        task_id=turn.task.id,
        thread_id=task_thread.id,
        checkpoint_id="checkpoint-after-restart",
        intervention_type=InterventionType.TOOL_APPROVAL,
        request_payload={"tool": "write_file"},
    )

    restarted_repositories = InMemoryRepositories(
        store, ProjectContext(conversation.project_id, owner_id)
    )
    restarted = ConversationSessionService(restarted_repositories).resume_state(intervention.id)

    assert restarted.task.id == turn.task.id
    assert restarted.thread.thread_id == f"task:{turn.task.id}"
    assert restarted.intervention.id == intervention.id


@pytest.mark.skipif(
    not os.getenv("MOSAIC_TEST_DATABASE_URL"),
    reason="MOSAIC_TEST_DATABASE_URL is required for the PostgreSQL integration test",
)
def test_postgres_resume_state_survives_a_new_database_session() -> None:
    engine = create_engine(os.environ["MOSAIC_TEST_DATABASE_URL"])
    owner_id = uuid4()
    project_id = uuid4()
    conversation_id = uuid4()
    suffix = uuid4().hex

    with Session(engine) as session, session.begin():
        session.add(UserRecord(id=owner_id, email=f"session-{suffix}@mosaic.local"))
        session.flush()
        session.add(
            ProjectRecord(
                id=project_id,
                name="Persisted session",
                slug=f"persisted-session-{suffix}",
                created_by_user_id=owner_id,
            )
        )
        session.flush()
        repositories = SqlAlchemyRepositories(
            session, ProjectContext(project_id, owner_id)
        )
        conversation = repositories.conversations.add(
            Conversation(
                id=conversation_id,
                project_id=project_id,
                created_by_user_id=owner_id,
            )
        )
        research = ConversationSessionService(repositories).start_research(
            conversation_id=conversation.id,
            user_id=owner_id,
            intent="Persist this research session",
        )
        intervention = ConversationSessionService(repositories).link_intervention(
            task_id=research.turn.task.id,
            thread_id=research.thread.id,
            research_run_id=research.research_run.id,
            checkpoint_id="postgres-checkpoint",
            intervention_type=InterventionType.TOPIC_APPROVAL,
            request_payload={"topics": ["persistence"]},
        )

    with Session(engine) as restarted_session, restarted_session.begin():
        restarted = ConversationSessionService(
            SqlAlchemyRepositories(
                restarted_session, ProjectContext(project_id, owner_id)
            )
        ).resume_state(intervention.id)
        assert restarted.task.id == research.turn.task.id
        assert restarted.thread.thread_id == f"research:{research.research_run.id}"
        assert restarted.intervention.checkpoint_id == "postgres-checkpoint"

    engine.dispose()
