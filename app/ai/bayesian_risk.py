from dataclasses import dataclass
from math import isfinite, prod
from typing import Any

import networkx as nx


def _validate_probability(value: float, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric.")
    if not isfinite(float(value)) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be finite and between 0 and 1.")
    return float(value)


@dataclass(frozen=True)
class BayesianRiskResult:
    """
    Bayesian risk result for one candidate recovery plan.
    """

    supplier_failure_probability: float
    route_failure_probability: float | None
    stockout_probability: float | None
    plan_risk: float
    risk_is_partial: bool = False
    missing_evidence: tuple[str, ...] = ()

def _supplier_failure_probability(
    graph: nx.DiGraph,
    supplier_id: int,
) -> float:
    """
    Estimate the probability that a supplier fails.

    Supplier reliability represents the probability of successful
    operation.

        P(failure) = 1 - reliability

    An unavailable supplier is treated as certain failure in the
    current disruption scenario.
    """

    supplier_node = f"supplier:{supplier_id}"

    if supplier_node not in graph:
        raise ValueError(
            f"Supplier with ID {supplier_id} does not exist."
        )

    supplier = graph.nodes[supplier_node]

    # If the supplier is already disrupted/unavailable,
    # failure is certain for this scenario.
    if not supplier.get("available", True):
        return 1.0

    reliability = supplier.get("reliability")

    if reliability is None:
        raise ValueError(
            f"Supplier {supplier_id} has no reliability value."
        )

    reliability = _validate_probability(
        reliability,
        f"Supplier {supplier_id} reliability",
    )
    return 1.0 - reliability

def _route_failure_probability(
    graph: nx.DiGraph,
    path: list[str],
) -> tuple[float | None, tuple[str, ...]]:
    """
    Estimate the probability that at least one route in the
    candidate path fails.

    An unavailable route has failure probability 1.0. Available routes
    contribute only when an observed reliability value is present on the
    edge. Missing values remain unknown; no prior is synthesized.

    Assuming conditional independence:

        P(any route fails)
        = 1 - product(1 - P(route_i fails))
    """

    route_failure_probabilities: list[float] = []
    missing_evidence: list[str] = []

    for source, destination in zip(
        path,
        path[1:]
    ):

        if not graph.has_edge(
            source,
            destination
        ):
            raise ValueError(
                f"Route does not exist: "
                f"{source} -> {destination}."
            )

        edge = graph.edges[
            source,
            destination
        ]

        if not edge.get(
            "available",
            True
        ):
            route_failure_probabilities.append(1.0)
        else:
            reliability = edge.get("reliability")
            if reliability is None:
                route_id = edge.get("route_id")
                label = (
                    f"route:{route_id} reliability"
                    if route_id is not None
                    else f"{source} -> {destination} reliability"
                )
                missing_evidence.append(label)
                continue
            reliability = _validate_probability(
                reliability,
                f"Route {edge.get('route_id', f'{source} -> {destination}')} reliability",
            )
            route_failure_probabilities.append(1.0 - reliability)

    if 1.0 in route_failure_probabilities:
        return 1.0, ()

    if missing_evidence:
        return None, tuple(missing_evidence)

    if not route_failure_probabilities:
        return 0.0, ()

    probability_all_routes_survive = prod(
        1.0 - probability
        for probability
        in route_failure_probabilities
    )

    probability_any_route_fails = (
        1.0
        - probability_all_routes_survive
    )

    return probability_any_route_fails, ()

def estimate_plan_risk(
    graph: nx.DiGraph,
    plan: Any,
) -> BayesianRiskResult:
    """
    Estimate Bayesian reliability and stockout risk
    for a CandidatePlan.
    """

    required_fields = (
        "supplier_id",
        "customer_id",
        "path",
        "quantity",
        "total_days",
    )

    for field in required_fields:
        if not hasattr(
            plan,
            field
        ):
            raise ValueError(
                f"Candidate plan is missing "
                f"required field: {field}."
            )

    if plan.quantity <= 0:
        raise ValueError(
            "Candidate plan quantity "
            "must be greater than zero."
        )

    if not plan.path:
        raise ValueError(
            "Candidate plan path cannot be empty."
        )

    supplier_node = (
        f"supplier:{plan.supplier_id}"
    )

    customer_node = (
        f"customer:{plan.customer_id}"
    )

    if supplier_node not in graph:
        raise ValueError(
            f"Supplier with ID "
            f"{plan.supplier_id} does not exist."
        )

    if customer_node not in graph:
        raise ValueError(
            f"Customer with ID "
            f"{plan.customer_id} does not exist."
        )

    if plan.path[0] != supplier_node:
        raise ValueError(
            "Candidate plan path does not "
            "start at its supplier."
        )

    if plan.path[-1] != customer_node:
        raise ValueError(
            "Candidate plan path does not "
            "end at its customer."
        )

    supplier_failure = (
        _supplier_failure_probability(
            graph,
            plan.supplier_id
        )
    )

    route_failure, missing_evidence = (
        _route_failure_probability(
            graph,
            plan.path
        )
    )

    stockout_probability = None
    plan_risk = supplier_failure
    if supplier_failure == 1.0:
        stockout_probability = 1.0
        plan_risk = 1.0
    elif route_failure is not None:
        stockout_probability = 1.0 - (1.0 - supplier_failure) * (1.0 - route_failure)
        plan_risk = stockout_probability

    return BayesianRiskResult(
        supplier_failure_probability=round(
            supplier_failure,
            6
        ),
        route_failure_probability=(
            round(route_failure, 6) if route_failure is not None else None
        ),
        stockout_probability=(
            round(stockout_probability, 6)
            if stockout_probability is not None
            else None
        ),
        plan_risk=round(plan_risk, 6),
        risk_is_partial=route_failure is None,
        missing_evidence=missing_evidence,
    )


def estimate_risk_for_plans(
    graph: nx.DiGraph,
    plans: list[Any],
) -> list[dict]:
    """
    Estimate risk for multiple CSP-feasible plans.
    """

    results = []

    for plan in plans:

        risk = estimate_plan_risk(
            graph,
            plan
        )

        results.append(
            {
                "plan": plan,
                "risk": risk,
            }
        )

    return results