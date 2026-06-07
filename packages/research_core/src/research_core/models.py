from enum import StrEnum

from pydantic import BaseModel, Field


class ResearchRunStatus(StrEnum):
    CREATED = "created"
    PLANNING = "planning"
    RESEARCHING = "researching"
    WRITING = "writing"
    EDITING = "editing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchTopic(BaseModel):
    id: str
    title: str
    questions: list[str] = Field(default_factory=list)
    approved: bool = False


class ResearchRun(BaseModel):
    id: str
    intent: str
    status: ResearchRunStatus = ResearchRunStatus.CREATED
    topics: list[ResearchTopic] = Field(default_factory=list)
