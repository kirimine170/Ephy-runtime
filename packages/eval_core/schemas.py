from pydantic import BaseModel, ConfigDict, Field


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    query: str
    expected_sources: list[str] = Field(default_factory=list)
    expected_keywords: list[str] = Field(default_factory=list)
    project: str | None = None


class EvalCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    query: str
    matched_sources: list[str] = Field(default_factory=list)
    source_hit: bool
    keyword_hit: bool | None = None
    answer: str | None = None
    top_source: str | None = None
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class EvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_path: str
    total_cases: int
    source_hit_rate: float
    keyword_hit_rate: float | None = None
    average_latency_ms: float | None = None
    total_prompt_tokens: int | None = None
    total_completion_tokens: int | None = None
    total_tokens: int | None = None
    results: list[EvalCaseResult] = Field(default_factory=list)
