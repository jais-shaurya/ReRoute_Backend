"""
Recommendation and explanation layer for ReRoute.

Phase 2I:
    ranked scored plans
        -> selected recommendation
        -> deterministic alternatives
        -> human-readable explanation
        -> STRIPS-style action sequence

This module does not recompute A*, CSP, Bayesian risk, or scoring.
It consumes the ranked output of app.ai.scoring.
"""

from dataclasses import dataclass
from typing import Sequence

from app.ai.scoring import ScoredPlan


@dataclass(frozen=True)
class RecommendationAction:
    """A deterministic planning action with STRIPS-style semantics."""

    name: str
    description: str
    preconditions: tuple[str, ...]
    effects: tuple[str, ...]


@dataclass(frozen=True)
class RecommendationResult:
    """Final recommendation produced from already-ranked plans."""

    selected_plan: ScoredPlan
    alternatives: tuple[ScoredPlan, ...]
    explanation: str
    actions: tuple[RecommendationAction, ...]


def _validate_ranked_plans(
    ranked_plans: Sequence[ScoredPlan],
) -> None:
    """Validate that the recommendation layer receives ranked results."""

    if not ranked_plans:
        raise ValueError("At least one scored plan is required.")

    for index, result in enumerate(ranked_plans, start=1):
        if not isinstance(result, ScoredPlan):
            raise ValueError("Each item must be a ScoredPlan.")

        expected_rank = index
        if result.rank != expected_rank:
            raise ValueError(
                "Scored plans must be ranked consecutively starting at rank 1."
            )


def _build_explanation(selected: ScoredPlan) -> str:
    """
    Build a deterministic explanation from the winning plan.

    The explanation only uses values already produced by CSP, Bayesian
    risk, and multi-objective scoring; it does not independently make
    another optimization decision.
    """

    plan = selected.plan
    risk = selected.risk

    route = " -> ".join(plan.path)

    return (
        f"Plan ranked #1 is recommended with an overall score of "
        f"{selected.overall_score:.6f}. "
        f"It routes {plan.quantity} units from supplier "
        f"{plan.supplier_id} to customer {plan.customer_id} "
        f"along {route}. "
        f"The plan has transportation cost {plan.total_cost:.2f}, "
        f"delivery time {plan.total_days} day(s), and Bayesian "
        f"plan risk {risk.plan_risk:.6f}. "
        f"The score combines normalized cost, delivery time, and risk "
        f"using the configured multi-objective weights."
    )


def _build_actions(selected: ScoredPlan) -> tuple[RecommendationAction, ...]:
    """
    Convert the winning candidate into a small deterministic action plan.

    Only facts represented by CandidatePlan are turned into actions.
    Inventory-buffer usage, shipment delay, or order splitting are not
    inferred unless a future planner explicitly represents those decisions.
    """

    plan = selected.plan
    route = " -> ".join(plan.path)

    actions = [
        RecommendationAction(
            name="reroute",
            description=(
                f"Reroute {plan.quantity} units from supplier "
                f"{plan.supplier_id} to customer {plan.customer_id} "
                f"using {route}."
            ),
            preconditions=(
                f"supplier:{plan.supplier_id} is available",
                "candidate plan satisfies CSP hard constraints",
                "all edges in the selected path are available",
            ),
            effects=(
                f"{plan.quantity} units are assigned to the selected recovery path",
                f"customer:{plan.customer_id} receives the planned quantity",
            ),
        )
    ]

    if plan.factory_id is not None:
        actions.append(
            RecommendationAction(
                name="allocate_factory",
                description=(
                    f"Use factory {plan.factory_id} as the factory stage "
                    f"of the selected recovery path."
                ),
                preconditions=(
                    f"factory:{plan.factory_id} is available",
                    "factory capacity is sufficient for the candidate quantity",
                ),
                effects=(
                    f"factory:{plan.factory_id} participates in the recovery flow",
                ),
            )
        )

    if plan.warehouse_id is not None:
        actions.append(
            RecommendationAction(
                name="allocate_warehouse",
                description=(
                    f"Use warehouse {plan.warehouse_id} as the warehouse "
                    f"stage of the selected recovery path."
                ),
                preconditions=(
                    f"warehouse:{plan.warehouse_id} satisfies capacity/inventory constraints",
                ),
                effects=(
                    f"warehouse:{plan.warehouse_id} participates in the recovery flow",
                ),
            )
        )

    return tuple(actions)


def recommend_plan(
    ranked_plans: Sequence[ScoredPlan],
    max_alternatives: int = 3,
) -> RecommendationResult:
    """
    Select the best ranked plan and expose a small set of alternatives.

    Args:
        ranked_plans:
            Output from score_plans(), ordered from rank 1 onward.
        max_alternatives:
            Maximum number of alternatives to expose.

    Returns:
        RecommendationResult containing the winner, alternatives,
        deterministic explanation, and action sequence.
    """

    _validate_ranked_plans(ranked_plans)

    if (
        not isinstance(max_alternatives, int)
        or isinstance(max_alternatives, bool)
    ):
        raise ValueError("max_alternatives must be an integer.")

    if max_alternatives < 0:
        raise ValueError("max_alternatives cannot be negative.")

    selected = ranked_plans[0]

    alternatives = tuple(
        ranked_plans[1 : 1 + max_alternatives]
    )

    return RecommendationResult(
        selected_plan=selected,
        alternatives=alternatives,
        explanation=_build_explanation(selected),
        actions=_build_actions(selected),
    )
