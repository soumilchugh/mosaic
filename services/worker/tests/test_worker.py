from harness_core import FakeHarnessAdapter
from worker.main import main


def test_worker_entrypoint() -> None:
    assert main(FakeHarnessAdapter()) == 0
