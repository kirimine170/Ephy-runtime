from __future__ import annotations

import httpx

from packages.config_core.loader import WebSearchConfig
from .schemas import WebSearchSource
from .security import has_injection_markers, sanitize_plain_text, validate_public_web_url


class WebResultSanitizer:
    def __init__(self, config: WebSearchConfig) -> None:
        self._config = config

    def sanitize(self, raw_results: list[dict]) -> list[dict]:
        sources: list[dict] = []
        context_chars = 0
        for item in raw_results:
            if len(sources) >= self._config.max_results:
                break
            url = validate_public_web_url(str(item.get("url", "")))
            if not url:
                continue
            title = sanitize_plain_text(str(item.get("title", "")), 240) or url
            snippet = sanitize_plain_text(str(item.get("content") or item.get("snippet") or ""), self._config.max_snippet_chars)
            remaining = self._config.max_context_chars - context_chars
            if remaining <= 0:
                break
            snippet = snippet[:remaining].strip()
            context_chars += len(snippet)
            sources.append(
                WebSearchSource(
                    source_id=f"W{len(sources) + 1}",
                    title=title,
                    url=url,
                    snippet=snippet,
                    injection_suspected=has_injection_markers(f"{title}\n{snippet}"),
                ).model_dump()
            )
        return sources


class SearxngProvider:
    def __init__(self, config: WebSearchConfig, client: httpx.AsyncClient | None = None) -> None:
        self._config = config
        self._client = client or httpx.AsyncClient(
            base_url=config.base_url.rstrip("/"),
            timeout=httpx.Timeout(config.timeout_seconds),
            follow_redirects=False,
        )
        self._owns_client = client is None
        self._sanitizer = WebResultSanitizer(config)

    async def search(self, query: str) -> list[dict]:
        try:
            response = await self._client.post(
                "/search",
                data={
                    "q": query,
                    "format": "json",
                    "engines": self._config.engine,
                    "safesearch": str(self._config.safe_search),
                },
                headers={
                    "Accept": "application/json",
                    "X-Forwarded-For": "127.0.0.1",
                    "X-Real-IP": "127.0.0.1",
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError(f"SearXNG search failed: {exc}") from exc
        results = payload.get("results", []) if isinstance(payload, dict) else []
        if not isinstance(results, list):
            raise RuntimeError("SearXNG returned an invalid results payload")
        return self._sanitizer.sanitize([item for item in results if isinstance(item, dict)])

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
