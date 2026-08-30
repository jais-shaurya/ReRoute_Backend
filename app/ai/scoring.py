"""
Multi-objective scoring for ReRoute recovery plans.

Phase 2H:
    CSP-feasible plans
        -> Bayesian risk
        -> normalized cost/time/risk
        -> weighted score
        -> deterministic ranking

All three objectives are minimization objectives:
    lower cost  = better
    lower time   = better
    lower risk   = better
"""

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from app.ai.bayesian_risk import BayesianRiskResult
from app.ai.csp import CandidatePlan


@dataclass(frozen=True)
class ScoringWeights:
    """Weights for the three Phase 2H objectives."""

    cost_weight: float = 0.40
    time_weight: float = 0.30
    risk_weight: float = 0.30

    def __post_init__(self) -> None:
        weights = (
            self.cost_weight,
            self.time_weight,
            self.risk_weight,
        )

        for name, weight in zip(
            ("cost_weight", "time_weight", "risk_weight"),
            weights,
        ):
            if not isinstance(weight, (int, float)) or isinstance(weight, bool):
                raise ValueError(f"{name} must be a numeric value.")

            if not isfinite(float(weight)):
                raise ValueError(f"{name} must be finite.")

            if weight < 0:
                raise ValueError(f"{name} must be greater than or equal to zero.")

        total = sum(float(weight) for weight in weights)

        # Small tolerance prevents floating-point representation issues such
        # as 0.1 + 0.2 + 0.7 being represented slightly above/below 1.0.
        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                "Scoring weights must sum to 1.0."
            )


@dataclass(frozen=True)
class ScoredPlan:
    """A candidate plan together with normalized objectives and its rank."""

    plan: CandidatePlan
    risk: BayesianRiskResult

    normalized_cost: float
    normalized_time: float
    normalized_risk: float

    overall_score: float
    rank: int


def normalize_minimization(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    """
    Normalize a minimization objective into [0, 1].

    Formula:
        (maximum - value) / (maximum - minimum)

    Therefore:
        1.0 = best (minimum value)
        0.0 = worst (maximum value)

    If all candidates have the same value, every candidate receives 1.0
    because there is no meaningful distinction on that objective.
    """

    for name, number in (
        ("value", value),
        ("minimum", minimum),
        ("maximum", maximum),
    ):
        if not isinstance(number, (int, float)) or isinstance(number, bool):
            raise ValueError(f"{name} must be numeric.")

        if not isfinite(float(number)):
            raise ValueError(f"{name} must be finite.")

    if maximum < minimum:
        raise ValueError("maximum must be greater than or equal to minimum.")

    if value < minimum or value > maximum:
        raise ValueError(
            "value must lie between minimum and maximum."
        )

    if maximum == minimum:
        return 1.0

    normalized = (maximum - value) / (maximum - minimum)

    # Protect against tiny floating-point drift outside [0, 1].
    return max(0.0, min(1.0, normalized))


def _validate_plan(plan: CandidatePlan) -> None:
    """Validate the numeric fields required by the scoring layer."""

    if not isinstance(plan, CandidatePlan):
        raise ValueError("Each plan must be a CandidatePlan.")

    if not isinstance(plan.total_cost, (int, float)) or isinstance(
        plan.total_cost, bool
    ):
        raise ValueError("Plan total_cost must be numeric.")

    if not isfinite(float(plan.total_cost)):
        raise ValueError("Plan total_cost must be finite.")

    if plan.total_cost < 0:
        raise ValueError("Plan total_cost cannot be negative.")

    if not isinstance(plan.total_days, int) or isinstance(plan.total_days, bool):
        raise ValueError("Plan total_days must be an integer.")

    if plan.total_days < 0:
        raise ValueError("Plan total_days cannot be negative.")


def _validate_risk(risk: BayesianRiskResult) -> None:
    """Validate the Bayesian risk consumed by the scoring layer."""

    if not isinstance(risk, BayesianRiskResult):
        raise ValueError("Each risk result must be a BayesianRiskResult.")

    probability = risk.plan_risk

    if not isinstance(probability, (int, float)) or isinstance(probability, bool):
        raise ValueError("Bayesian plan_risk must be numeric.")

    if not isfinite(float(probability)):
        raise ValueError("Bayesian plan_risk must be finite.")

    if not 0.0 <= probability <= 1.0:
        raise ValueError("Bayesian plan_risk must be between 0 and 1.")


def _ranking_key(scored: ScoredPlan) -> tuple:
    """
    Deterministic ranking key.

    Primary objective:
        higher overall score is better.

    Tie-breakers:
        1. lower Bayesian risk
        2. lower cost
        3. lower delivery time
        4. lexicographically smaller path
        5. lower supplier ID
        6. lower customer ID
    """

    return (
        -scored.overall_score,
        scored.risk.plan_risk,
        scored.plan.total_cost,
        scored.plan.total_days,
        tuple(scored.plan.path),
        scored.plan.supplier_id,
        scored.plan.customer_id,
    )


def score_plans(
    plans: Sequence[CandidatePlan],
    risks: Sequence[BayesianRiskResult],
    weights: ScoringWeights | None = None,
) -> list[ScoredPlan]:
    """
    Score and rank CSP-feasible candidate plans.

    `plans[i]` must correspond to `risks[i]`.

    The objective values are normalized against the candidate set before
    applying the configured weighted sum.

    Returns:
        A list sorted from best plan (rank 1) to worst plan.
    """

    if len(plans) != len(risks):
        raise ValueError(
            "The number of plans must match the number of risk results."
        )

    if not plans:
        return []

    if weights is None:
        weights = ScoringWeights()

    for plan in plans:
        _validate_plan(plan)

    for risk in risks:
        _validate_risk(risk)

    costs = [float(plan.total_cost) for plan in plans]
    times = [float(plan.total_days) for plan in plans]
    risks_values = [float(risk.plan_risk) for risk in risks]

    min_cost, max_cost = min(costs), max(costs)
    min_time, max_time = min(times), max(times)
    min_risk, max_risk = min(risks_values), max(risks_values)

    scored: list[ScoredPlan] = []

    for plan, risk in zip(plans, risks):
        normalized_cost = normalize_minimization(
            float(plan.total_cost),
            min_cost,
            max_cost,
        )

        normalized_time = normalize_minimization(
            float(plan.total_days),
            min_time,
            max_time,
        )

        normalized_risk = normalize_minimization(
            float(risk.plan_risk),
            min_risk,
            max_risk,
        )

        overall_score = (
            weights.cost_weight * normalized_cost
            + weights.time_weight * normalized_time
            + weights.risk_weight * normalized_risk
        )

        scored.append(
            ScoredPlan(
                plan=plan,
                risk=risk,
                normalized_cost=round(normalized_cost, 6),
                normalized_time=round(normalized_time, 6),
                normalized_risk=round(normalized_risk, 6),
                overall_score=round(overall_score, 6),
                rank=0,
            )
        )

    scored.sort(key=_ranking_key)

    ranked: list[ScoredPlan] = []

    for rank, result in enumerate(scored, start=1):
        ranked.append(
            ScoredPlan(
                plan=result.plan,
                risk=result.risk,
                normalized_cost=result.normalized_cost,
                normalized_time=result.normalized_time,
                normalized_risk=result.normalized_risk,
                overall_score=result.overall_score,
                rank=rank,
            )
        )

    return ranked
