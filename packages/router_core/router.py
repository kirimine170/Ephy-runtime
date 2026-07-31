import math
import re

import httpx

from packages.config_core.loader import AppConfig, ModelConfig
from packages.llm_runtime.schemas import EmbeddingRequest
from packages.llm_runtime.schemas import ChatCompletionRequest
from .schemas import RouteDecision, RoutePlanResponse


class ModelRouter:
    _CODE_MARKERS = (
        "python",
        "pytest",
        "traceback",
        "bug",
        "implement",
        "refactor",
        "function",
        "class",
        "stack trace",
        "exception",
        "コード",
        "関数",
        "実装",
        "エラー",
        "修正",
    )
    _WORK_MARKERS = (
        "設計",
        "research",
        "仕様",
        "proposal",
        "long summary",
        "要約",
        "議事録",
        "比較",
        "整理",
        "方針",
        "計画",
        "strategy",
        "architecture",
    )
    _RAG_MARKERS = (
        "source",
        "document",
        "資料",
        "根拠",
        "based on notes",
        "引用",
        "出典",
        "docs",
        "manual",
        "readme",
        "according to",
    )
    _FAST_PROTOTYPE = "Give a concise direct answer to a short general question."
    _MODE_PROTOTYPES = {
        "fast": [
            _FAST_PROTOTYPE,
            "Answer a simple greeting or short factual question in a few sentences.",
        ],
        "work": [
            "Prepare a design proposal with tradeoffs, planning steps, and a structured summary.",
            "Summarize a long meeting transcript and organize key decisions and next steps.",
        ],
        "code": [
            "Implement a function, debug a traceback, refactor code, and add tests.",
            "Analyze source code, explain a bug, and propose a concrete patch.",
        ],
        "rag": [
            "Answer based on provided documents, sources, notes, and citations.",
            "Use project documents and source material as grounding before answering.",
        ],
    }

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._embedding_cache: dict[str, list[float]] = {}

    def route_chat(self, request: ChatCompletionRequest) -> RouteDecision:
        mode = self._resolve_mode(request)
        route_config = self._config.routes.get(mode)
        if route_config is None:
            raise ValueError(f"Unsupported mode '{mode}'")
        if route_config.model is None:
            raise ValueError(f"Route '{mode}' does not define a model")

        try:
            model_config = self._config.models[route_config.model]
        except KeyError as exc:
            raise ValueError(f"Route '{mode}' points to unknown model '{route_config.model}'") from exc

        return RouteDecision(mode=mode, model_alias=route_config.model, selected_model=model_config)

    def plan_chat(self, request: ChatCompletionRequest) -> RoutePlanResponse:
        decision = self.route_chat(request)
        model_config = self._config.models[decision.model_alias]
        return RoutePlanResponse(
            mode=decision.mode,
            model_alias=decision.model_alias,
            provider=model_config.provider,
            backend_model=model_config.model,
            base_url=model_config.base_url,
            max_context=model_config.max_context,
        )

    def _resolve_mode(self, request: ChatCompletionRequest) -> str:
        metadata_mode = request.metadata.mode if request.metadata else None
        requested_mode = metadata_mode or request.model or "auto"
        if requested_mode != "auto":
            return requested_mode
        return self._auto_mode(request)

    def _auto_mode(self, request: ChatCompletionRequest) -> str:
        combined = "\n".join(self._stringify_message_content(message.content) for message in request.messages)
        normalized = combined.lower()

        if request.metadata and request.metadata.rag_required:
            return "rag"
        if self._looks_like_rag_request(normalized):
            return "rag"
        if self._looks_like_code_request(combined, normalized):
            return "code"
        if self._looks_like_work_request(combined, normalized):
            return "work"

        scores = self._score_modes(combined, normalized)
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_mode, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else -1
        if top_score >= 3 and top_score-second_score >= 2:
            return top_mode
        if top_score >= 4:
            return top_mode

        embedding_mode = self._embedding_assisted_mode(combined)
        if embedding_mode:
            return embedding_mode

        if top_score > 0:
            return top_mode
        return "fast"

    def _looks_like_rag_request(self, normalized: str) -> bool:
        return any(marker in normalized for marker in self._RAG_MARKERS)

    def _looks_like_code_request(self, combined: str, normalized: str) -> bool:
        if "```" in combined:
            return True
        if any(marker in normalized for marker in self._CODE_MARKERS):
            return True
        if re.search(r"(^|\n)\s*(def |class |import |from .+ import |func |\{|\<\w+)", combined):
            return True
        if re.search(r"(error:|traceback|exception|failed test|assertionerror)", normalized):
            return True
        symbol_hits = sum(combined.count(token) for token in ("{", "}", "=>", "::", "();", "</", "/>"))
        return symbol_hits >= 3

    def _looks_like_work_request(self, combined: str, normalized: str) -> bool:
        line_count = combined.count("\n") + 1
        paragraph_count = combined.count("\n\n") + 1
        long_request = len(combined) >= 900 or len(normalized.split()) >= 180
        if any(marker in normalized for marker in self._WORK_MARKERS):
            return True
        if long_request and not self._looks_like_code_request(combined, normalized):
            return True
        return line_count >= 18 or paragraph_count >= 6

    def _score_modes(self, combined: str, normalized: str) -> dict[str, int]:
        scores = {"fast": 0, "work": 0, "code": 0, "rag": 0}
        scores["rag"] += sum(1 for marker in self._RAG_MARKERS if marker in normalized)
        scores["code"] += sum(1 for marker in self._CODE_MARKERS if marker in normalized)
        scores["work"] += sum(1 for marker in self._WORK_MARKERS if marker in normalized)

        if len(combined) < 240 and "\n" not in combined:
            scores["fast"] += 2
        if len(combined) >= 700:
            scores["work"] += 2
        if combined.count("\n") >= 10:
            scores["work"] += 1
        if "?" in combined and len(combined) < 180:
            scores["fast"] += 1
        if "```" in combined:
            scores["code"] += 4
        if re.search(r"\b(test|testing|coverage|fix|debug)\b", normalized):
            scores["code"] += 2
        if re.search(r"\b(summary|summarize|proposal|design|plan)\b", normalized):
            scores["work"] += 2
        if re.search(r"\b(source|citation|document|notes)\b", normalized):
            scores["rag"] += 2
        return scores

    def _embedding_assisted_mode(self, text: str) -> str | None:
        vector = self._embed_text(text)
        if not vector:
            return None

        best_mode = None
        best_score = -1.0
        second_score = -1.0
        for mode, prompts in self._MODE_PROTOTYPES.items():
            similarities = []
            for prompt in prompts:
                prototype_vector = self._embed_text(prompt, cache_key=f"prototype:{mode}:{prompt}")
                if prototype_vector:
                    similarities.append(self._cosine_similarity(vector, prototype_vector))
            if not similarities:
                continue
            score = sum(similarities) / len(similarities)
            if score > best_score:
                second_score = best_score
                best_score = score
                best_mode = mode
            elif score > second_score:
                second_score = score

        if not best_mode:
            return None
        if best_score < 0.20:
            return None
        if second_score >= 0 and best_score-second_score < 0.015:
            return None
        if best_mode == "fast" and best_score < 0.24:
            return None
        return best_mode

    def _embed_text(self, text: str, cache_key: str | None = None) -> list[float] | None:
        normalized_text = text.strip()
        if not normalized_text:
            return None

        cache_name = cache_key or normalized_text
        if cache_name in self._embedding_cache:
            return self._embedding_cache[cache_name]

        embedding_alias = self._config.rag.embedding_model_alias
        model_config = self._config.models.get(embedding_alias)
        if not model_config or not model_config.base_url:
            return None

        request_payload = EmbeddingRequest(model=embedding_alias, input=normalized_text)
        body = request_payload.model_dump(exclude_none=True)
        body["model"] = model_config.model

        try:
            with httpx.Client(timeout=0.8) as client:
                response = client.post(
                    f"{model_config.base_url.rstrip('/')}/embeddings",
                    json=body,
                )
                response.raise_for_status()
        except httpx.HTTPError:
            return None

        data = response.json().get("data", [])
        if not data:
            return None
        embedding = data[0].get("embedding")
        if not isinstance(embedding, list) or not embedding:
            return None

        vector = [float(value) for value in embedding]
        self._embedding_cache[cache_name] = vector
        return vector

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if len(left) != len(right) or not left:
            return -1.0
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return -1.0
        return numerator / (left_norm * right_norm)

    @staticmethod
    def _stringify_message_content(content: str | list[dict]) -> str:
        if isinstance(content, str):
            return content
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and "text" in item and isinstance(item["text"], str):
                text_parts.append(item["text"])
        return "\n".join(text_parts)
