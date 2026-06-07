from research_core.models import ResearchRun, ResearchRunStatus


def test_research_run_starts_created() -> None:
    run = ResearchRun(id="run_1", intent="Map the market")

    assert run.status == ResearchRunStatus.CREATED
    assert run.topics == []
