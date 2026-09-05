"""
Schemas define the contract between:
  - what we ask the LLM to produce
  - what Express (backend) receives from this AI service

Keeping this in one place means the prompt, the validation, and the
API response all stay in sync automatically.
"""

from typing import Literal
from pydantic import BaseModel, Field


class CommitAnalysis(BaseModel):
    summary: str = Field(
        ..., description="One or two sentence plain-English summary of the change"
    )
    changed_components: list[str] = Field(
        default_factory=list,
        description="Names of files, modules, or functions affected",
    )
    change_type: Literal["feature", "bugfix", "refactor", "docs", "test", "chore"]
    risk_level: Literal["low", "medium", "high"]
    reasoning: str = Field(
        ..., description="Brief justification for the risk_level and change_type"
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Short exact lines copied from the supplied diff",
    )
    analysis_scope: Literal["full", "partial"] = "full"
    omitted_characters: int = Field(default=0, ge=0)
    limitations: list[str] = Field(default_factory=list)
    documentation_impact: bool = False
    documentation_topics: list[str] = Field(default_factory=list)


class CommitAnalysisRequest(BaseModel):
    diff: str = Field(..., min_length=1, description="Git unified diff to analyze")
    commit_message: str = Field(default="", description="Original commit message")
    stat_summary: str = Field(
        default="", description="Optional deterministic git --stat output"
    )
    project_context: str = Field(
        default="",
        max_length=12000,
        description="Targeted surrounding code and project metadata",
    )


class RepositoryRequest(BaseModel):
    path: str


class CommitRequest(RepositoryRequest):
    commit: str = "HEAD"


class HistoryRequest(RepositoryRequest):
    limit: int = Field(default=20, ge=1, le=100)


class QueryRequest(RepositoryRequest):
    question: str = Field(..., min_length=2, max_length=2000)
    limit: int = Field(default=5, ge=1, le=10)


class ProjectAnswer(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    grounded: bool
