from app.ai.bayesian_risk import BayesianRiskResult
from app.ai.csp import CandidatePlan
from app.ai.recommendation import (
    RecommendationAction,
    RecommendationResult,
    recommend_plan,
)
from app.ai.scoring import ScoredPlan


def make_plan(
    supplier_id=1,
    customer_id=1,
    quantity=10,
    path=None,
    total_cost=100.0,
    total_days=2,
    factory_id=1,
    warehouse_id=1,
):
    return CandidatePlan(
        supplier_id=supplier_id,
        customer_id=customer_id,
        quantity=quantity,
        path=path or [
            f"supplier:{supplier_id}",
            f"factory:{factory_id}",
            f"warehouse:{warehouse_id}",
            f"customer:{customer_id}",
        ],
        total_cost=total_cost,
        total_days=total_days,
        factory_id=factory_id,
        warehouse_id=warehouse_id,
    )


def make_scored(
    rank,
    score,
    cost=100.0,
    days=2,
    risk_value=0.10,
    supplier_id=1,
):
    plan = make_plan(
        supplier_id=supplier_id,
        total_cost=cost,
        total_days=days,
    )

    risk = BayesianRiskResult(
        supplier_failure_probability=risk_value,
        route_failure_probability=0.05,
        stockout_probability=risk_value,
        plan_risk=risk_value,
    )

    return ScoredPlan(
        plan=plan,
        risk=risk,
        normalized_cost=0.8,
        normalized_time=0.7,
        normalized_risk=0.9,
        overall_score=score,
        rank=rank,
    )


def test_valid_ranked_plans_produce_recommendation():
    ranked = [
        make_scored(1, 0.90),
        make_scored(2, 0.70, supplier_id=2),
    ]

    result = recommend_plan(ranked)

    assert isinstance(result, RecommendationResult)
    assert result.selected_plan == ranked[0]
    assert result.alternatives == (ranked[1],)


def test_rank_one_is_selected():
    ranked = [
        make_scored(1, 0.95),
        make_scored(2, 0.80),
        make_scored(3, 0.60),
    ]

    result = recommend_plan(ranked)

    assert result.selected_plan.rank == 1
    assert result.selected_plan.overall_score == 0.95


def test_alternatives_are_limited():
    ranked = [
        make_scored(1, 0.95),
        make_scored(2, 0.80, supplier_id=2),
        make_scored(3, 0.70, supplier_id=3),
        make_scored(4, 0.60, supplier_id=4),
        make_scored(5, 0.50, supplier_id=5),
    ]

    result = recommend_plan(ranked, max_alternatives=2)

    assert [plan.rank for plan in result.alternatives] == [2, 3]


def test_zero_alternatives_are_supported():
    ranked = [
        make_scored(1, 0.95),
        make_scored(2, 0.80, supplier_id=2),
    ]

    result = recommend_plan(ranked, max_alternatives=0)

    assert result.alternatives == ()


def test_explanation_contains_decision_factors():
    ranked = [make_scored(1, 0.91)]

    result = recommend_plan(ranked)

    assert "ranked #1" in result.explanation
    assert "0.910000" in result.explanation
    assert "cost 100.00" in result.explanation
    assert "delivery time 2 day(s)" in result.explanation
    assert "risk 0.100000" in result.explanation
    assert "cost, delivery time, and risk" in result.explanation


def test_explanation_contains_route_and_entities():
    ranked = [make_scored(1, 0.91)]

    result = recommend_plan(ranked)

    assert "supplier 1" in result.explanation
    assert "customer 1" in result.explanation
    assert "supplier:1 -> factory:1 -> warehouse:1 -> customer:1" in result.explanation


def test_reroute_action_is_generated():
    ranked = [make_scored(1, 0.91)]

    result = recommend_plan(ranked)

    action = result.actions[0]

    assert isinstance(action, RecommendationAction)
    assert action.name == "reroute"
    assert "supplier 1" in action.description
    assert "customer 1" in action.description
    assert "candidate plan satisfies CSP hard constraints" in action.preconditions


def test_factory_and_warehouse_actions_are_generated_when_present():
    ranked = [make_scored(1, 0.91)]

    result = recommend_plan(ranked)

    names = [action.name for action in result.actions]

    assert names == [
        "reroute",
        "allocate_factory",
        "allocate_warehouse",
    ]


def test_no_factory_or_warehouse_actions_when_not_represented():
    plan = make_plan(factory_id=None, warehouse_id=None)
    scored = ScoredPlan(
        plan=plan,
        risk=BayesianRiskResult(
            supplier_failure_probability=0.05,
            route_failure_probability=0.05,
            stockout_probability=0.0975,
            plan_risk=0.0975,
        ),
        normalized_cost=1.0,
        normalized_time=1.0,
        normalized_risk=1.0,
        overall_score=1.0,
        rank=1,
    )

    result = recommend_plan([scored])

    assert [action.name for action in result.actions] == ["reroute"]


def test_empty_ranked_plans_are_rejected():
    try:
        recommend_plan([])
    except ValueError as exc:
        assert "At least one scored plan" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_non_consecutive_ranks_are_rejected():
    ranked = [
        make_scored(1, 0.90),
        make_scored(3, 0.70, supplier_id=2),
    ]

    try:
        recommend_plan(ranked)
    except ValueError as exc:
        assert "ranked consecutively" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_non_scored_input_is_rejected():
    try:
        recommend_plan([object()])
    except ValueError as exc:
        assert "Each item must be a ScoredPlan" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_invalid_alternative_limit_is_rejected():
    ranked = [make_scored(1, 0.90)]

    try:
        recommend_plan(ranked, max_alternatives=-1)
    except ValueError as exc:
        assert "cannot be negative" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_recommendation_is_deterministic():
    ranked = [
        make_scored(1, 0.90),
        make_scored(2, 0.70, supplier_id=2),
    ]

    first = recommend_plan(ranked)
    second = recommend_plan(ranked)

    assert first == second
    assert first.explanation == second.explanation
    assert first.actions == second.actions
