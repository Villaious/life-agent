from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.models.booking import ServiceCandidate


@dataclass(frozen=True)
class HousekeepingScore:
    candidate: ServiceCandidate
    value: float
    explanation: str


class HousekeepingScoringAgent:
    HOUSEKEEPING_TERMS = {
        "home_cleaning",
        "housekeeping",
        "cleaning",
        "家政",
        "家政服务",
        "保洁",
        "清洁",
        "钟点工",
    }
    EXCLUDED_TERMS = {"搬家", "维修", "修理", "管道", "疏通", "美甲", "美容", "美发"}
    CATEGORY_TERMS = {
        "repair": {"repair", "维修", "修理", "管道", "疏通", "家电"},
        "beauty": {"beauty", "美甲", "美容", "美发"},
        "moving": {"moving", "搬家"},
    }

    def select_best(
        self,
        candidates: Iterable[ServiceCandidate | dict],
        service_category: str,
    ) -> list[ServiceCandidate]:
        normalized = [
            candidate
            if isinstance(candidate, ServiceCandidate)
            else ServiceCandidate.model_validate(candidate)
            for candidate in candidates
        ]
        matched = [
            candidate
            for candidate in normalized
            if self._matches_requested_service(candidate, service_category)
        ]
        if not matched:
            return []

        priced = [candidate.price.amount for candidate in matched if candidate.price.amount]
        min_price = min(priced) if priced else None
        max_price = max(priced) if priced else None

        scored = [
            self._score_candidate(candidate, min_price=min_price, max_price=max_price)
            for candidate in matched
        ]
        scored.sort(key=lambda item: item.value, reverse=True)

        return [self._with_score(item) for item in scored]

    def _matches_requested_service(
        self,
        candidate: ServiceCandidate,
        service_category: str,
    ) -> bool:
        if service_category != "home_cleaning":
            terms = self.CATEGORY_TERMS.get(service_category, {service_category})
            text = self._candidate_text(candidate)
            return any(term in text for term in terms)

        text = self._candidate_text(candidate)
        if any(term in text for term in self.EXCLUDED_TERMS):
            return False
        return any(term in text for term in self.HOUSEKEEPING_TERMS)

    def _candidate_text(self, candidate: ServiceCandidate) -> str:
        return " ".join(
            str(value or "")
            for value in [
                candidate.name,
                candidate.category,
                candidate.raw.get("type"),
                candidate.raw.get("typecode"),
            ]
        )

    def _score_candidate(
        self,
        candidate: ServiceCandidate,
        min_price: float | None,
        max_price: float | None,
    ) -> HousekeepingScore:
        distance_score = self._distance_score(candidate)
        price_score = self._price_score(candidate, min_price, max_price)
        provider_score = self._provider_score(candidate)
        value = round(distance_score * 0.45 + price_score * 0.35 + provider_score * 0.20, 2)
        explanation = (
            f"距离 {distance_score:.0f} / 价格 {price_score:.0f} / 商家基础评分 {provider_score:.0f}"
        )
        return HousekeepingScore(candidate=candidate, value=value, explanation=explanation)

    def _distance_score(self, candidate: ServiceCandidate) -> float:
        raw_distance = candidate.raw.get("distance")
        try:
            distance = float(raw_distance)
        except (TypeError, ValueError):
            return 70.0
        if distance <= 500:
            return 100.0
        if distance >= 5000:
            return 45.0
        return max(45.0, 100.0 - (distance - 500.0) / 4500.0 * 55.0)

    def _price_score(
        self,
        candidate: ServiceCandidate,
        min_price: float | None,
        max_price: float | None,
    ) -> float:
        amount = candidate.price.amount
        if amount is None:
            return 70.0
        if min_price is None or max_price is None or max_price <= min_price:
            return 85.0
        return max(45.0, 100.0 - (amount - min_price) / (max_price - min_price) * 55.0)

    def _provider_score(self, candidate: ServiceCandidate) -> float:
        if candidate.score is None:
            return 75.0
        if candidate.score <= 1:
            return max(0.0, min(100.0, candidate.score * 100))
        return max(0.0, min(100.0, candidate.score))

    def _with_score(self, score: HousekeepingScore) -> ServiceCandidate:
        candidate = score.candidate.model_copy(deep=True)
        candidate.expected_score = score.value
        candidate.score = score.value
        candidate.score_explanation = score.explanation
        candidate.raw = {
            **candidate.raw,
            "expected_score": score.value,
            "score_explanation": score.explanation,
        }
        return candidate
