import pytest

from app.services.planner import PlannerService
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


def test_planner_with_demand_spike_no_feasible_plan():
    db = SessionLocal()

    try:
        service = PlannerService(db)

        with pytest.raises(
            ValueError,
            match="No feasible recovery plans exist",
        ):
            service.recommend(
                customer_id=1,
                quantity=42,
                disruption_type="demand_spike",
                disruption_customer_id=1,
                demand_spike_percentage=20,
            )

    finally:
        db.close()
