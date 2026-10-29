from uuid import uuid4

from harness_core import (
    FakeHarnessAdapter,
    KnowledgeChatInput,
    build_minimal_knowledge_chat_adapter,
    project_context_tool,
    run_knowledge_chat,
)


async def test_knowledge_chat_runs_through_fake_harness_adapter() -> None:
    adapter = FakeHarnessAdapter()
    request = KnowledgeChatInput(
        project_id=uuid4(),
        conversation_id=uuid4(),
        created_by_user_id=uuid4(),
        user_message="What do we know about the project?",
        thread_id="conversation-1",
        context={"source_count": 0},
    )

    events = [event async for event in run_knowledge_chat(request, adapter)]

    assert [event.type for event in events] == ["run.started", "run.completed"]
    [harness_request] = adapter.started
    assert harness_request.task.intent == "What do we know about the project?"
    assert harness_request.task.task_type == "chat_answer"
    assert harness_request.messages[0].content == "What do we know about the project?"
    assert harness_request.checkpoint_namespace == "knowledge_chat"
    assert harness_request.metadata == {"run_kind": "knowledge_chat"}


async def test_knowledge_chat_propagates_adapter_failure_event() -> None:
    adapter = FakeHarnessAdapter(event_types=["run.started", "run.failed"])
    request = KnowledgeChatInput(
        project_id=uuid4(),
        user_message="fail gracefully",
        thread_id="conversation-1",
    )

    events = [event async for event in run_knowledge_chat(request, adapter)]

    assert [event.type for event in events] == ["run.started", "run.failed"]


async def test_minimal_project_context_tool_returns_structured_placeholder() -> None:
    tool = project_context_tool()
    [deepagents_tool] = build_minimal_knowledge_chat_adapter(
        model="test:model",
        create_agent=lambda **kwargs: None,
    ).tools

    result = await deepagents_tool(topic="architecture")

    assert tool.name == "read_project_context"
    assert result["ok"] is True
    assert result["output"] == {
        "topic": "architecture",
        "summary": "No indexed project knowledge has been attached yet.",
    }


async def test_minimal_deepagents_adapter_can_run_with_injected_agent() -> None:
    calls = []

    class StubAgent:
        def invoke(self, payload, *, config, version):
            calls.append((payload, config, version))
            return {"messages": [{"role": "assistant", "content": "hello"}]}

    def create_agent(**kwargs):
        calls.append(("create", kwargs))
        return StubAgent()

    adapter = build_minimal_knowledge_chat_adapter(
        model="test:model",
        create_agent=create_agent,
    )
    request = KnowledgeChatInput(
        project_id=uuid4(),
        user_message="hello?",
        thread_id="conversation-1",
    )

    events = [event async for event in run_knowledge_chat(request, adapter)]

    assert [event.type for event in events] == ["run.started", "run.completed"]
    assert calls[0][0] == "create"
    assert calls[0][1]["model"] == "test:model"
    assert len(calls[0][1]["tools"]) == 1
    assert calls[1] == (
        {"messages": [{"role": "user", "content": "hello?"}]},
        {
            "configurable": {
                "thread_id": "conversation-1",
                "checkpoint_ns": "knowledge_chat",
            }
        },
        "v2",
    )
