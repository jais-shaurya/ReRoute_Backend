import networkx as nx

from app.services.planner import PlannerService


def _graph_with_customer_demand() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node(
        "supplier:1",
        node_type="supplier",
        database_id=1,
        capacity=100,
        available=True,
        reliability=0.95,
    )
    graph.add_node(
        "customer:1",
        node_type="customer",
        database_id=1,
        demand=42,
        deadline_days=10,
    )
    graph.add_edge(
        "supplier:1",
        "customer:1",
        available=True,
        capacity=100,
        transportation_cost=5.0,
        delivery_time_days=2,
    )
    return graph


def _service_for_graph(graph: nx.DiGraph) -> PlannerService:
    service = PlannerService(session=None)
    service.build_graph = lambda: graph
    return service


def test_requested_quantity_is_the_normal_plan_demand():
    graph = _graph_with_customer_demand()
    result = _service_for_graph(graph).recommend(
        customer_id=1,
        quantity=40,
    )

    assert result.recommendation.selected_plan.plan.quantity == 40
    assert graph.nodes["customer:1"]["demand"] == 42


def test_fractional_demand_spike_rounds_up_without_mutating_base_graph():
    graph = _graph_with_customer_demand()
    result = _service_for_graph(graph).recommend(
        customer_id=1,
        quantity=42,
        disruption_type="demand_spike",
        demand_spike_percentage=20,
    )

    assert result.scenario.quantity == 51
    assert result.recommendation.selected_plan.plan.quantity == 51
    assert graph.nodes["customer:1"]["demand"] == 42
