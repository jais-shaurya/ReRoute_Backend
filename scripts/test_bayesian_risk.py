import networkx as nx
import pytest

from app.ai.bayesian_risk import (
    BayesianRiskResult,
    estimate_plan_risk,
    estimate_risk_for_plans,
)

from app.ai.csp import CandidatePlan


# ============================================================
# TEST GRAPH
# ============================================================

def build_test_graph() -> nx.DiGraph:
    """
    Build a small controlled supply-chain graph for testing
    Bayesian Risk.
    """

    graph = nx.DiGraph()

    # --------------------------------------------------------
    # Suppliers
    # --------------------------------------------------------

    graph.add_node(
        "supplier:1",
        node_type="supplier",
        reliability=0.95,
        available=True,
        capacity=100,
    )

    graph.add_node(
        "supplier:2",
        node_type="supplier",
        reliability=0.60,
        available=True,
        capacity=100,
    )

    graph.add_node(
        "supplier:3",
        node_type="supplier",
        reliability=0.99,
        available=False,
        capacity=100,
    )

    # --------------------------------------------------------
    # Factory
    # --------------------------------------------------------

    graph.add_node(
        "factory:1",
        node_type="factory",
        available=True,
        capacity=200,
    )

    # --------------------------------------------------------
    # Warehouse
    # --------------------------------------------------------

    graph.add_node(
        "warehouse:1",
        node_type="warehouse",
        capacity=200,
        inventory=200,
    )

    # --------------------------------------------------------
    # Customer
    # --------------------------------------------------------

    graph.add_node(
        "customer:1",
        node_type="customer",
        demand=40,
        deadline_days=5,
    )

    # --------------------------------------------------------
    # Supplier -> Factory
    # --------------------------------------------------------

    for supplier_id in (1, 2, 3):

        graph.add_edge(
            f"supplier:{supplier_id}",
            "factory:1",
            transportation_cost=50.0,
            delivery_time_days=1,
            capacity=100,
            available=True,
        )

    # --------------------------------------------------------
    # Factory -> Warehouse
    # --------------------------------------------------------

    graph.add_edge(
        "factory:1",
        "warehouse:1",
        transportation_cost=40.0,
        delivery_time_days=1,
        capacity=200,
        available=True,
    )

    # --------------------------------------------------------
    # Warehouse -> Customer
    # --------------------------------------------------------

    graph.add_edge(
        "warehouse:1",
        "customer:1",
        transportation_cost=30.0,
        delivery_time_days=1,
        capacity=200,
        available=True,
    )

    return graph


# ============================================================
# CANDIDATE PLAN HELPER
# ============================================================

def create_plan(supplier_id: int) -> CandidatePlan:
    """
    Create a valid CandidatePlan for testing.
    """

    return CandidatePlan(
        supplier_id=supplier_id,
        customer_id=1,
        quantity=40,
        path=[
            f"supplier:{supplier_id}",
            "factory:1",
            "warehouse:1",
            "customer:1",
        ],
        total_cost=120.0,
        total_days=3,
        factory_id=1,
        warehouse_id=1,
    )


# ============================================================
# TEST 1
# ============================================================

def test_valid_plan_receives_risk_result():
    """
    A valid CandidatePlan should receive a BayesianRiskResult.
    """

    graph = build_test_graph()

    plan = create_plan(1)

    result = estimate_plan_risk(
        graph,
        plan,
    )

    assert isinstance(
        result,
        BayesianRiskResult,
    )

    assert (
        0
        <= result.supplier_failure_probability
        <= 1
    )

    assert (
        0
        <= result.route_failure_probability
        <= 1
    )

    assert (
        0
        <= result.stockout_probability
        <= 1
    )

    assert (
        result.plan_risk
        == result.stockout_probability
    )


# ============================================================
# TEST 2
# ============================================================

def test_higher_supplier_reliability_produces_lower_risk():
    """
    A more reliable supplier should produce lower
    supplier-failure probability and lower overall risk.
    """

    graph = build_test_graph()

    reliable_plan = create_plan(1)
    unreliable_plan = create_plan(2)

    reliable_result = estimate_plan_risk(
        graph,
        reliable_plan,
    )

    unreliable_result = estimate_plan_risk(
        graph,
        unreliable_plan,
    )

    assert (
        reliable_result.supplier_failure_probability
        <
        unreliable_result.supplier_failure_probability
    )

    assert (
        reliable_result.stockout_probability
        <
        unreliable_result.stockout_probability
    )


# ============================================================
# TEST 3
# ============================================================

def test_unavailable_supplier_has_certain_failure_risk():
    """
    An unavailable supplier should have 100% supplier
    failure probability.
    """

    graph = build_test_graph()

    plan = create_plan(3)

    result = estimate_plan_risk(
        graph,
        plan,
    )

    assert (
        result.supplier_failure_probability
        == 1.0
    )

    assert (
        result.stockout_probability
        == 1.0
    )


# ============================================================
# TEST 4
# ============================================================

def test_unavailable_route_has_certain_route_failure_risk():
    """
    An unavailable route should produce 100% route
    failure probability.
    """

    graph = build_test_graph()

    graph.edges[
        "factory:1",
        "warehouse:1"
    ]["available"] = False

    plan = create_plan(1)

    result = estimate_plan_risk(
        graph,
        plan,
    )

    assert (
        result.route_failure_probability
        == 1.0
    )

    assert (
        result.stockout_probability
        == 1.0
    )


# ============================================================
# TEST 5
# ============================================================

def test_route_risk_increases_with_more_routes():
    """
    A path containing more available routes should have
    a higher probability that at least one route fails.
    """

    graph = build_test_graph()

    long_plan = create_plan(1)

    long_result = estimate_plan_risk(
        graph,
        long_plan,
    )

    # --------------------------------------------------------
    # Create a shorter path:
    #
    # supplier -> customer
    #
    # Only one route.
    # --------------------------------------------------------

    short_graph = nx.DiGraph()

    short_graph.add_node(
        "supplier:1",
        node_type="supplier",
        reliability=0.95,
        available=True,
        capacity=100,
    )

    short_graph.add_node(
        "customer:1",
        node_type="customer",
        demand=40,
        deadline_days=5,
    )

    short_graph.add_edge(
        "supplier:1",
        "customer:1",
        transportation_cost=80.0,
        delivery_time_days=2,
        capacity=100,
        available=True,
    )

    short_plan = CandidatePlan(
        supplier_id=1,
        customer_id=1,
        quantity=40,
        path=[
            "supplier:1",
            "customer:1",
        ],
        total_cost=80.0,
        total_days=2,
    )

    short_result = estimate_plan_risk(
        short_graph,
        short_plan,
    )

    assert (
        long_result.route_failure_probability
        >
        short_result.route_failure_probability
    )


# ============================================================
# TEST 6
# ============================================================

def test_identical_evidence_is_deterministic():
    """
    The same graph and CandidatePlan should always produce
    exactly the same Bayesian result.
    """

    graph = build_test_graph()

    plan = create_plan(1)

    first_result = estimate_plan_risk(
        graph,
        plan,
    )

    second_result = estimate_plan_risk(
        graph,
        plan,
    )

    assert first_result == second_result


# ============================================================
# TEST 7
# ============================================================

def test_multiple_plans_receive_risk_estimates():
    """
    Multiple CSP-feasible plans should each receive
    an independent risk estimate.
    """

    graph = build_test_graph()

    plans = [
        create_plan(1),
        create_plan(2),
    ]

    results = estimate_risk_for_plans(
        graph,
        plans,
    )

    assert len(results) == 2

    assert (
        results[0]["risk"]
        .plan_risk
        <
        results[1]["risk"]
        .plan_risk
    )


# ============================================================
# TEST 8
# ============================================================

def test_missing_supplier_is_rejected():
    """
    A plan referencing a supplier that does not exist
    should raise ValueError.
    """

    graph = build_test_graph()

    plan = create_plan(99)

    with pytest.raises(
        ValueError,
        match="does not exist",
    ):
        estimate_plan_risk(
            graph,
            plan,
        )


# ============================================================
# TEST 9
# ============================================================

def test_invalid_path_start_is_rejected():
    """
    The path must start at the selected supplier.
    """

    graph = build_test_graph()

    plan = create_plan(1)

    plan.path = [
        "supplier:2",
        "factory:1",
        "warehouse:1",
        "customer:1",
    ]

    with pytest.raises(
        ValueError,
        match="does not start",
    ):
        estimate_plan_risk(
            graph,
            plan,
        )


# ============================================================
# TEST 10
# ============================================================

def test_probability_values_are_bounded():
    """
    All returned probability values must remain inside
    the valid probability range [0, 1].
    """

    graph = build_test_graph()

    plan = create_plan(1)

    result = estimate_plan_risk(
        graph,
        plan,
    )

    assert (
        0.0
        <= result.supplier_failure_probability
        <= 1.0
    )

    assert (
        0.0
        <= result.route_failure_probability
        <= 1.0
    )

    assert (
        0.0
        <= result.stockout_probability
        <= 1.0
    )

    assert (
        0.0
        <= result.plan_risk
        <= 1.0
    )