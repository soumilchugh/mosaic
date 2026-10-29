from uuid import UUID, uuid4

import pytest
from knowledge_core import (
    AgentTask,
    AgentTaskType,
    Asset,
    AssetKind,
    Conversation,
    KnowledgeFile,
    KnowledgeFileType,
    KnowledgeScope,
    KnowledgeScopeType,
    KnowledgeScopeVisibility,
    Message,
    MessageRole,
    ProductEvent,
    Project,
)
from pydantic import ValidationError


def test_core_contracts_share_project_identity_and_serialize_to_json() -> None:
    user_id = uuid4()
    project = Project(name="Research", slug="research", created_by_user_id=user_id)
    scope = KnowledgeScope(
        scope_type=KnowledgeScopeType.PROJECT,
        name="Research knowledge",
        visibility=KnowledgeScopeVisibility.PROJECT,
        project_id=project.id,
    )
    conversation = Conversation(project_id=project.id, created_by_user_id=user_id)
    message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content="What does the evidence show?",
        sequence=0,
    )
    task = AgentTask(
        project_id=project.id,
        conversation_id=conversation.id,
        task_type=AgentTaskType.CHAT_ANSWER,
        intent=message.content,
    )
    event = ProductEvent(
        project_id=project.id,
        conversation_id=conversation.id,
        agent_task_id=task.id,
        sequence=0,
        type="run.started",
    )

    payload = event.model_dump_json()

    assert str(project.id) in payload
    assert str(task.id) in payload
    assert isinstance(message.id, UUID)
    assert scope.project_id == project.id


def test_asset_and_knowledge_file_are_storage_provider_neutral() -> None:
    scope_id = uuid4()
    asset = Asset(
        knowledge_scope_id=scope_id,
        kind=AssetKind.UPLOAD,
        filename="brief.md",
        mime_type="text/markdown",
        size_bytes=12,
        checksum_sha256="a" * 64,
        storage_uri="object://private-assets/brief.md",
    )
    knowledge_file = KnowledgeFile(
        knowledge_scope_id=scope_id,
        asset_id=asset.id,
        path="/workspace/sources/brief.md",
        file_type=KnowledgeFileType.SOURCE_CARD,
        title="Brief",
        content_hash="sha256:abc",
    )

    assert asset.storage_uri.startswith("object://")
    assert knowledge_file.asset_id == asset.id


@pytest.mark.parametrize(
    ("scope_type", "owner_fields"),
    [
        (KnowledgeScopeType.USER_GLOBAL, {}),
        (KnowledgeScopeType.ORGANIZATION_GLOBAL, {"owner_user_id": uuid4()}),
        (KnowledgeScopeType.PROJECT, {"owner_organization_id": uuid4()}),
    ],
)
def test_knowledge_scope_requires_matching_owner(
    scope_type: KnowledgeScopeType,
    owner_fields: dict[str, UUID],
) -> None:
    with pytest.raises(ValidationError, match="matching owner ID"):
        KnowledgeScope(
            scope_type=scope_type,
            name="Invalid scope",
            visibility=KnowledgeScopeVisibility.PRIVATE,
            **owner_fields,
        )


def test_contracts_reject_unknown_fields_and_invalid_values() -> None:
    with pytest.raises(ValidationError):
        Message(
            conversation_id=uuid4(),
            role=MessageRole.USER,
            content="hello",
            sequence=-1,
            unexpected=True,
        )

    with pytest.raises(ValidationError):
        Asset(
            knowledge_scope_id=uuid4(),
            kind=AssetKind.UPLOAD,
            filename="brief.md",
            mime_type="text/markdown",
            size_bytes=1,
            checksum_sha256="not-a-checksum",
            storage_uri="object://brief.md",
        )
