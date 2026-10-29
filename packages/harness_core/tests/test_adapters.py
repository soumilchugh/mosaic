from uuid import uuid4

from harness_core.adapters import (
    DeepAgentsAdapter,
    FakeHarnessAdapter,
    HarnessMessage,
    HarnessResumeRequest,
    HarnessRunRequest,
)
from knowledge_core import AgentTask, AgentTaskType


def make_task() -> AgentTask:
    return AgentTask(
        project_id=uuid4(),
        conversation_id=uuid4(),
        created_by_user_id=uuid4(),
        task_type=AgentTaskType.CHAT_ANSWER,
        intent="answer a question",
    )


async def test_fake_adapter_starts_and_resumes_without_model_calls() -> None:
    task = make_task()
    adapter = FakeHarnessAdapter()
    start_request = HarnessRunRequest(
        task=task,
        messages=[HarnessMessage(role="user", content="hello")],
        thread_id="thread-1",
    )
    resume_request = HarnessResumeRequest(
        task=task,
        thread_id="thread-1",
        decisions=[{"type": "approve"}],
    )

    started_events = [event async for event in adapter.start(start_request)]
    resumed_events = [event async for event in adapter.resume(resume_request)]

    assert adapter.started == [start_request]
    assert adapter.resumed == [resume_request]
    assert [event.type for event in started_events] == ["run.started", "run.completed"]
    assert [event.type for event in resumed_events] == ["run.resumed", "run.completed"]
    assert resumed_events[0].payload["decision_count"] == 1


async def test_deepagents_adapter_uses_injected_agent_factory() -> None:
    task = make_task()
    calls = []

    class StubAgent:
        def invoke(self, payload, *, config, version):
            calls.append((payload, config, version))
            return {"ok": True}

    def create_agent(**kwargs):
        calls.append(("create", kwargs))
        return StubAgent()

    adapter = DeepAgentsAdapter(
        model="test:model",
        system_prompt="Be useful.",
        create_agent=create_agent,
    )
    request = HarnessRunRequest(
        task=task,
        messages=[HarnessMessage(role="user", content="hello")],
        thread_id="thread-1",
        checkpoint_namespace="chat",
    )

    events = [event async for event in adapter.start(request)]

    assert [event.type for event in events] == ["run.started", "run.completed"]
    assert calls[0] == (
        "create",
        {"model": "test:model", "tools": [], "system_prompt": "Be useful."},
    )
    assert calls[1] == (
        {"messages": [{"role": "user", "content": "hello"}]},
        {"configurable": {"thread_id": "thread-1", "checkpoint_ns": "chat"}},
        "v2",
    )
