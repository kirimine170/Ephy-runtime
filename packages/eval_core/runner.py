from __future__ import annotations

from time import perf_counter
from pathlib import Path

import yaml

from packages.config_core.loader import AppConfig
from packages.llm_runtime.adapter import LlamaCppChatAdapter
from packages.rag_core.schemas import RAGQueryRequest, SearchRequest
from packages.rag_core.service import RagService
from packages.router_core.router import ModelRouter
from .schemas import EvalCase, EvalCaseResult, EvalReport
from .style import assess_response_style


class EvalRunner:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._rag_service = RagService(config=config)
        self._router = ModelRouter(config=config)

    async def run_dataset(
        self,
        dataset_path: str,
        project: str | None = None,
        source_path: str | None = None,
        top_k: int = 5,
        with_answer: bool = False,
    ) -> EvalReport:
        cases = self._load_cases(dataset_path)
        results: list[EvalCaseResult] = []
        adapter = LlamaCppChatAdapter() if with_answer else None

        try:
            for case in cases:
                effective_project = project or case.project
                started_at = perf_counter()
                search_response = self._rag_service.search(
                    SearchRequest(query=case.query, project=effective_project, source_path=source_path, top_k=top_k)
                )
                sources = search_response["results"]
                source_paths = [item["source_path"] for item in sources]
                source_hit = self._source_hit(source_paths, case.expected_sources)

                answer = None
                keyword_hit = None
                prompt_tokens = None
                completion_tokens = None
                total_tokens = None
                style_assessment = None
                if with_answer and adapter is not None:
                    query_response = await self._rag_service.query(
                        payload=RAGQueryRequest(
                            query=case.query,
                            project=effective_project,
                            source_path=source_path,
                            top_k=top_k,
                            answer=True,
                        ),
                        router=self._router,
                        adapter=adapter,
                    )
                    answer = query_response.get("answer")
                    keyword_hit = self._keyword_hit(answer, case.expected_keywords)
                    raw_response = query_response.get("raw_response") or {}
                    usage = raw_response.get("usage") or {}
                    prompt_tokens = self._safe_int(usage.get("prompt_tokens"))
                    completion_tokens = self._safe_int(usage.get("completion_tokens"))
                    total_tokens = self._safe_int(usage.get("total_tokens"))
                    style_assessment = assess_response_style(
                        answer,
                        max_characters=case.max_answer_characters,
                        max_bullets=case.max_bullets,
                        max_headings=case.max_headings,
                    )

                latency_ms = round((perf_counter() - started_at) * 1000, 2)

                results.append(
                    EvalCaseResult(
                        id=case.id,
                        query=case.query,
                        matched_sources=source_paths,
                        source_hit=source_hit,
                        keyword_hit=keyword_hit,
                        answer=answer,
                        top_source=source_paths[0] if source_paths else None,
                        latency_ms=latency_ms,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        style_pass=style_assessment.passed if style_assessment else None,
                        style_violations=list(style_assessment.violations) if style_assessment else [],
                        answer_characters=style_assessment.character_count if style_assessment else None,
                        bullet_count=style_assessment.bullet_count if style_assessment else None,
                        heading_count=style_assessment.heading_count if style_assessment else None,
                    )
                )
        finally:
            if adapter is not None:
                await adapter.aclose()

        source_hit_rate = self._rate(sum(1 for item in results if item.source_hit), len(results))
        keyword_values = [item.keyword_hit for item in results if item.keyword_hit is not None]
        keyword_hit_rate = None
        if keyword_values:
            keyword_hit_rate = self._rate(sum(1 for item in keyword_values if item), len(keyword_values))

        latency_values = [item.latency_ms for item in results if item.latency_ms is not None]
        average_latency_ms = None
        if latency_values:
            average_latency_ms = round(sum(latency_values) / len(latency_values), 2)

        total_prompt_tokens = self._sum_optional_int(item.prompt_tokens for item in results)
        total_completion_tokens = self._sum_optional_int(item.completion_tokens for item in results)
        total_tokens = self._sum_optional_int(item.total_tokens for item in results)
        style_values = [item.style_pass for item in results if item.style_pass is not None]
        style_pass_rate = None
        if style_values:
            style_pass_rate = self._rate(sum(1 for item in style_values if item), len(style_values))

        return EvalReport(
            dataset_path=str(Path(dataset_path).resolve()),
            total_cases=len(results),
            source_hit_rate=source_hit_rate,
            keyword_hit_rate=keyword_hit_rate,
            average_latency_ms=average_latency_ms,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            style_pass_rate=style_pass_rate,
            results=results,
        )

    def _load_cases(self, dataset_path: str) -> list[EvalCase]:
        payload = yaml.safe_load(Path(dataset_path).read_text(encoding="utf-8")) or {}
        cases = payload.get("cases", [])
        return [EvalCase.model_validate(case) for case in cases]

    @staticmethod
    def _source_hit(actual_sources: list[str], expected_sources: list[str]) -> bool:
        if not expected_sources:
            return len(actual_sources) > 0
        return any(expected in actual for expected in expected_sources for actual in actual_sources)

    @staticmethod
    def _keyword_hit(answer: str | None, expected_keywords: list[str]) -> bool | None:
        if not expected_keywords:
            return None
        if not answer:
            return False
        lowered = answer.lower()
        return all(keyword.lower() in lowered for keyword in expected_keywords)

    @staticmethod
    def _rate(hits: int, total: int) -> float:
        if total == 0:
            return 0.0
        return round(hits / total, 4)

    @staticmethod
    def _safe_int(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _sum_optional_int(values) -> int | None:
        numbers = [value for value in values if value is not None]
        if not numbers:
            return None
        return sum(numbers)
