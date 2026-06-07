from worker.main import main


def test_worker_entrypoint() -> None:
    assert main() == 0
