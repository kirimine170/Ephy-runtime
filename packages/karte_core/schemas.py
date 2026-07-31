from pydantic import BaseModel, ConfigDict, Field


class KarteCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    title: str
    body: str
    project: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_path: str | None = None
    source_uri: str | None = None
    updated_at: str | None = None


class KarteBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    cards: list[KarteCard] = Field(default_factory=list)
