import networkx as nx
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


def test_industry_minimum_service_level_filters_actual_candidates():
    graph = nx.DiGraph()
    for supplier_id, reliability in ((1, 0.94), (2, 0.99)):
        graph.add_node(
            f"supplier:{supplier_id}",
            node_type="supplier",
            database_id=supplier_id,
            capacity=100,
            available=True,
            reliability=reliability,
        )
        graph.add_edge(
            f"supplier:{supplier_id}",
            "customer:1",
            available=True,
            capacity=100,
            transportation_cost=10.0 + supplier_id,
            delivery_time_days=1,
        )
    graph.add_node(
        "customer:1",
        node_type="customer",
        database_id=1,
        demand=10,
        deadline_days=5,
    )

    service = PlannerService(session=None)
    service.build_graph = lambda: graph
    result = service.recommend(
        customer_id=1,
        quantity=10,
        industry="healthcare",
    )

    assert [item.plan.supplier_id for item in result.candidate_plans] == [2]
