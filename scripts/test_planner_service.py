import networkx as nx
import pytest

from app.services.planner import InfeasiblePlanningError, PlannerService
from app.database.connection import SessionLocal


def test_planner_without_disruption():
    db = SessionLocal()

    try:
        service = PlannerService(db)

        result = service.recommend(
            customer_id=1,
            quantity=42,
        )

        assert result is not None
        assert result.recommendation is not None
        assert result.recommendation.selected_plan is not None
        assert len(result.candidate_plans) > 0
        assert result.scenario.type == "none"
        assert result.scenario.customer_id == 1
        assert result.scenario.quantity == 42

    finally:
        db.close()


def test_planner_with_supplier_failure():
    db = SessionLocal()

    try:
        service = PlannerService(db)

        result = service.recommend(
            customer_id=1,
            quantity=42,
            disruption_type="supplier_failure",
            supplier_id=1,
        )

        assert result is not None
        assert result.recommendation is not None
        assert result.recommendation.selected_plan is not None
        assert len(result.candidate_plans) > 0

        assert result.scenario.type == "supplier_failure"
        assert result.scenario.customer_id == 1
        assert result.scenario.quantity == 42
        assert result.scenario.supplier_id == 1

    finally:
        db.close()


def test_planner_custom_weights():
    from app.ai.scoring import ScoringWeights

    db = SessionLocal()

    try:
        service = PlannerService(db)

        weights = ScoringWeights(
            cost_weight=0.5,
            time_weight=0.3,
            risk_weight=0.2,
        )

        result = service.recommend(
            customer_id=1,
            quantity=42,
            weights=weights,
        )

        assert result is not None
        assert result.recommendation.selected_plan is not None

    finally:
        db.close()


def test_planner_reports_real_capacity_infeasibility():
    graph = nx.DiGraph()
    graph.add_node(
        "supplier:1",
        node_type="supplier",
        database_id=1,
        capacity=9,
        available=True,
        reliability=0.99,
    )
    graph.add_node(
        "customer:1",
        node_type="customer",
        database_id=1,
        demand=10,
        deadline_days=5,
    )
    graph.add_edge(
        "supplier:1",
        "customer:1",
        available=True,
        capacity=20,
        transportation_cost=5.0,
        delivery_time_days=1,
    )
    service = PlannerService(session=None)
    service.build_graph = lambda: graph

    with pytest.raises(InfeasiblePlanningError, match="supplier capacity") as error:
        service.recommend(customer_id=1, quantity=10)

    assert error.value.rejected_candidates[0].supplier_id == 1
