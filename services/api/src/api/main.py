from fastapi import FastAPI
from harness_core import FakeHarnessAdapter, HarnessAdapter

app = FastAPI(title="Agent Harness API")
app.state.harness_adapter = FakeHarnessAdapter()


def get_harness_adapter() -> HarnessAdapter:
    return app.state.harness_adapter


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
