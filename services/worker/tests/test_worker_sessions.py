from uuid import uuid4

from knowledge_core import Conversation, ConversationSessionService, InterventionType, Project
from knowledge_core.persistence import (
    InMemoryRepositories,
    InMemoryRepositoryStore,
    ProjectContext,
)
from worker.sessions import prepare_conversation_run, reconstruct_resume_request


def make_repositories():
    owner_id = uuid4()
    project = Project(
        name="Worker session test",
        slug=f"worker-session-{uuid4().hex}",
        created_by_user_id=owner_id,
    )
    store = InMemoryRepositoryStore(projects={project.id: project})
    repositories = InMemoryRepositories(store, ProjectContext(project.id, owner_id))
    conversation = repositories.conversations.add(
        Conversation(project_id=project.id, created_by_user_id=owner_id)
    )
    return repositories, store, conversation, owner_id


def test_worker_prepares_execution_only_after_user_message_is_persisted() -> None:
    repositories, _, conversation, owner_id = make_repositories()

    request = prepare_conversation_run(
        repositories,
        conversation_id=conversation.id,
        user_id=owner_id,
        content="Use the project knowledge",
    )

    [persisted_message] = repositories.messages.list()
    assert persisted_message.content == "Use the project knowledge"
    assert request.metadata["message_id"] == str(persisted_message.id)
    assert request.task.id == repositories.tasks.list()[0].id
    assert request.thread_id == f"conversation:{conversation.id}"


def test_worker_reconstructs_resume_request_after_repository_restart() -> None:
    repositories, store, conversation, owner_id = make_repositories()
    session = ConversationSessionService(repositories).start_research(
        conversation_id=conversation.id,
        user_id=owner_id,
        intent="Research restart-safe agents",
    )
    intervention = ConversationSessionService(repositories).link_intervention(
        task_id=session.turn.task.id,
        thread_id=session.thread.id,
        research_run_id=session.research_run.id,
        checkpoint_id="checkpoint-persisted",
        intervention_type=InterventionType.TOPIC_APPROVAL,
        request_payload={"topics": ["checkpoints"]},
    )
    restarted = InMemoryRepositories(store, ProjectContext(conversation.project_id, owner_id))

    request = reconstruct_resume_request(
        restarted,
        intervention_id=intervention.id,
        decisions=[{"type": "approve"}],
    )

    assert request.task.id == session.turn.task.id
    assert request.thread_id == f"research:{session.research_run.id}"
    assert request.checkpoint_namespace == "deep_research"
    assert request.checkpoint_id == "checkpoint-persisted"
    assert request.metadata["intervention_request_id"] == str(intervention.id)
