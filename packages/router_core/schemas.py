from pydantic import BaseModel

from packages.config_core.loader import ModelConfig


class RouteDecision(BaseModel):
    mode: str
    model_alias: str
    selected_model: ModelConfig


class RoutePlanResponse(BaseModel):
    mode: str
    model_alias: str
    provider: str
    backend_model: str
    base_url: str
    max_context: int
