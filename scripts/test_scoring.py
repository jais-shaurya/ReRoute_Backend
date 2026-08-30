"""
Tests for Phase 2H — Cost + Multi-Objective Scoring.
"""

import pytest

from app.ai.bayesian_risk import BayesianRiskResult
from app.ai.csp import CandidatePlan
from app.ai.scoring import (
    ScoringWeights,
    normalize_minimization,
    score_plans,
)


def make_plan(
    supplier_id: int,
    cost: float,
    days: int,
    customer_id: int = 1,
) -> CandidatePlan:
    return CandidatePlan(
        supplier_id=supplier_id,
        customer_id=customer_id,
        quantity=100,
        path=[
            f"supplier:{supplier_id}",
            "factory:1",
            "warehouse:1",
            f"customer:{customer_id}",
        ],
        total_cost=cost,
        total_days=days,
        factory_id=1,
        warehouse_id=1,
    )


def make_risk(plan_risk: float) -> BayesianRiskResult:
    return BayesianRiskResult(
        supplier_failure_probability=plan_risk,
        route_failure_probability=0.0,
        stockout_probability=plan_risk,
        plan_risk=plan_risk,
    )


def test_valid_candidate_receives_score():
    plans = [make_plan(1, 100.0, 2)]
    risks = [make_risk(0.10)]

    result = score_plans(plans, risks)

    assert len(result) == 1
    assert result[0].rank == 1
    assert result[0].overall_score == 1.0


def test_lower_cost_improves_score_when_other_objectives_are_equal():
    plans = [
        make_plan(1, 100.0, 2),
        make_plan(2, 200.0, 2),
    ]
    risks = [
        make_risk(0.10),
        make_risk(0.10),
    ]

    result = score_plans(
        plans,
        risks,
        ScoringWeights(cost_weight=1.0, time_weight=0.0, risk_weight=0.0),
    )

    assert result[0].plan.supplier_id == 1
    assert result[0].overall_score == 1.0
    assert result[1].overall_score == 0.0


def test_faster_delivery_improves_score_when_other_objectives_are_equal():
    plans = [
        make_plan(1, 100.0, 2),
        make_plan(2, 100.0, 5),
    ]
    risks = [
        make_risk(0.10),
        make_risk(0.10),
    ]

    result = score_plans(
        plans,
        risks,
        ScoringWeights(cost_weight=0.0, time_weight=1.0, risk_weight=0.0),
    )

    assert result[0].plan.supplier_id == 1
    assert result[0].overall_score == 1.0
    assert result[1].overall_score == 0.0


def test_lower_risk_improves_score_when_other_objectives_are_equal():
    plans = [
        make_plan(1, 100.0, 2),
        make_plan(2, 100.0, 2),
    ]
    risks = [
        make_risk(0.10),
        make_risk(0.40),
    ]

    result = score_plans(
        plans,
        risks,
        ScoringWeights(cost_weight=0.0, time_weight=0.0, risk_weight=1.0),
    )

    assert result[0].plan.supplier_id == 1
    assert result[0].overall_score == 1.0
    assert result[1].overall_score == 0.0


def test_weights_change_ranking():
    plans = [
        make_plan(1, 100.0, 5),
        make_plan(2, 200.0, 1),
    ]
    risks = [
        make_risk(0.10),
        make_risk(0.10),
    ]

    cost_focused = score_plans(
        plans,
        risks,
        ScoringWeights(cost_weight=0.8, time_weight=0.2, risk_weight=0.0),
    )
    time_focused = score_plans(
        plans,
        risks,
        ScoringWeights(cost_weight=0.2, time_weight=0.8, risk_weight=0.0),
    )

    assert cost_focused[0].plan.supplier_id == 1
    assert time_focused[0].plan.supplier_id == 2


def test_min_max_normalization():
    assert normalize_minimization(10, 10, 20) == 1.0
    assert normalize_minimization(20, 10, 20) == 0.0
    assert normalize_minimization(15, 10, 20) == 0.5


def test_equal_objective_values_do_not_divide_by_zero():
    assert normalize_minimization(10, 10, 10) == 1.0


def test_invalid_weights_are_rejected():
    invalid_weights = [
        (0.5, 0.3, 0.1),
        (-0.1, 0.6, 0.5),
        (0.4, 0.4, 0.3),
    ]

    for weights in invalid_weights:
        with pytest.raises(ValueError):
            ScoringWeights(*weights)

def test_invalid_weights_raise():
    with pytest.raises(ValueError):
        ScoringWeights(0.5, 0.3, 0.1)

    with pytest.raises(ValueError):
        ScoringWeights(-0.1, 0.6, 0.5)

    with pytest.raises(ValueError):
        ScoringWeights(0.4, 0.4, 0.3)


def test_mismatched_plan_and_risk_counts_are_rejected():
    plans = [make_plan(1, 100.0, 2)]
    risks = []

    with pytest.raises(ValueError):
        score_plans(plans, risks)


def test_invalid_risk_probability_is_rejected():
    plans = [make_plan(1, 100.0, 2)]

    invalid_risk = BayesianRiskResult(
        supplier_failure_probability=0.1,
        route_failure_probability=0.1,
        stockout_probability=1.2,
        plan_risk=1.2,
    )

    with pytest.raises(ValueError):
        score_plans(plans, [invalid_risk])


def test_multiple_plans_receive_deterministic_ranks():
    plans = [
        make_plan(1, 100.0, 2),
        make_plan(2, 150.0, 3),
        make_plan(3, 200.0, 4),
    ]
    risks = [
        make_risk(0.05),
        make_risk(0.20),
        make_risk(0.40),
    ]

    first = score_plans(plans, risks)
    second = score_plans(list(reversed(plans)), list(reversed(risks)))

    assert [item.rank for item in first] == [1, 2, 3]
    assert [item.plan.supplier_id for item in first] == [1, 2, 3]
    assert [item.plan.supplier_id for item in first] == [
        item.plan.supplier_id for item in second
    ]


def test_tie_breaking_is_deterministic():
    plans = [
        make_plan(2, 100.0, 2),
        make_plan(1, 100.0, 2),
    ]
    risks = [
        make_risk(0.10),
        make_risk(0.10),
    ]

    result = score_plans(
        plans,
        risks,
        ScoringWeights(cost_weight=1.0, time_weight=0.0, risk_weight=0.0),
    )

    # Same score, risk, cost, and time -> path/supplier ordering resolves tie.
    assert result[0].plan.supplier_id == 1
    assert result[1].plan.supplier_id == 2
    assert result[0].rank == 1
    assert result[1].rank == 2
