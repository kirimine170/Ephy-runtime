from pydantic import BaseModel, ConfigDict


class EvalRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_path: str
    project: str | None = None
    source_path: str | None = None
    top_k: int = 5
    with_answer: bool = False
