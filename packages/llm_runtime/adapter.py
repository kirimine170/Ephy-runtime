from collections.abc import Sequence

import httpx

from packages.config_core.loader import ModelConfig
from .schemas import ChatCompletionRequest, EmbeddingRequest


class LlamaCppChatAdapter:
    def __init__(self, timeout: float = 120.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def create_chat_completion(
        self,
        model_config: ModelConfig,
        request_payload: ChatCompletionRequest,
    ) -> dict:
        if not model_config.base_url:
            raise RuntimeError(f"Model '{model_config.model}' is missing base_url")

        body = self._build_payload(model_config=model_config, request_payload=request_payload)

        try:
            response = await self._client.post(
                f"{model_config.base_url.rstrip('/')}/chat/completions",
                json=body,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Backend request failed for model '{model_config.model}': {exc}") from exc

        return response.json()

    async def stream_chat_completion(
        self,
        model_config: ModelConfig,
        request_payload: ChatCompletionRequest,
    ):
        if not model_config.base_url:
            raise RuntimeError(f"Model '{model_config.model}' is missing base_url")

        body = self._build_payload(model_config=model_config, request_payload=request_payload)

        try:
            async with self._client.stream(
                "POST",
                f"{model_config.base_url.rstrip('/')}/chat/completions",
                json=body,
                headers={"Accept": "text/event-stream"},
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Backend request failed for model '{model_config.model}': {exc}") from exc

    async def create_embedding(
        self,
        model_config: ModelConfig,
        request_payload: EmbeddingRequest,
    ) -> dict:
        if not model_config.base_url:
            raise RuntimeError(f"Model '{model_config.model}' is missing base_url")

        body = request_payload.model_dump(exclude_none=True)
        body["model"] = model_config.model

        try:
            response = await self._client.post(
                f"{model_config.base_url.rstrip('/')}/embeddings",
                json=body,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Backend request failed for model '{model_config.model}': {exc}") from exc

        return response.json()

    def _build_payload(
        self,
        model_config: ModelConfig,
        request_payload: ChatCompletionRequest,
    ) -> dict:
        body = request_payload.model_dump(exclude_none=True)
        body["model"] = model_config.model
        if "metadata" in body:
            body.pop("metadata")
        if "temperature" not in body and model_config.default_temperature is not None:
            body["temperature"] = model_config.default_temperature
        return body
