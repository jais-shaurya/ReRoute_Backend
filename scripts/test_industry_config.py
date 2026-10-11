import pytest

from app.config.industry import IndustryProfile, get_profile
from app.schemas.planner import PlannerRequest
from app.services.planner import PlannerService
from app.database.connection import SessionLocal


def test_industry_profiles_are_valid_and_defaulted():
    profile = get_profile("retail")

    assert profile.name == "retail"
    assert profile.default_weights.cost_weight > 0
    assert profile.max_demand_spike_percentage > 0
    assert profile.mandatory_rules


def test_planner_rejects_excessive_demand_spike_for_profile():
    db = SessionLocal()

    try:
        service = PlannerService(db)

        with pytest.raises(ValueError, match="Demand spike.*retail"):
            service.recommend(
                customer_id=1,
                quantity=42,
                disruption_type="demand_spike",
                disruption_customer_id=1,
                demand_spike_percentage=80,
                industry="retail",
            )
    finally:
        db.close()


def test_planner_request_validates_unknown_industry():
    with pytest.raises(ValueError, match="Unknown industry"):
        PlannerRequest(
            customer_id=1,
            quantity=42,
            industry="unknown-profile",
        )
