from harness_core import FakeHarnessAdapter
from knowledge_core import MosaicSettings, ProviderRegistry
from worker.main import main


def test_worker_entrypoint() -> None:
    assert main(FakeHarnessAdapter()) == 0


def test_worker_entrypoint_accepts_injected_runtime_dependencies() -> None:
    settings = MosaicSettings(_env_file=None)
    registry = ProviderRegistry(settings)

    assert main(FakeHarnessAdapter(), settings, registry) == 0
