from app.database.connection import SessionLocal
from app.database.models import Supplier
from app.ai.graph import build_supply_chain_graph
from app.ai.disruption import (
    simulate_supplier_failure,
    simulate_demand_spike,
    round_spiked_quantity,
)


def test_supplier_failure(graph):
    print("\n========== TEST 1: SUPPLIER FAILURE ==========")

    # Select the first supplier in the graph
    supplier_node = next(
        node
        for node, data in graph.nodes(data=True)
        if data["node_type"] == "supplier"
    )

    supplier_id = graph.nodes[supplier_node]["database_id"]

    original_availability = graph.nodes[
        supplier_node
    ]["available"]

    outgoing_routes = list(
        graph.out_edges(supplier_node)
    )

    assert outgoing_routes, (
        "Selected supplier has no outgoing routes."
    )

    # Simulate failure
    scenario = simulate_supplier_failure(
        graph,
        supplier_id
    )

    # Supplier must become unavailable
    assert scenario.nodes[
        supplier_node
    ]["available"] is False

    # All outgoing routes must become unavailable
    for source, destination in outgoing_routes:
        assert scenario.edges[
            source,
            destination
        ]["available"] is False

    # Original graph must remain unchanged
    assert graph.nodes[
        supplier_node
    ]["available"] == original_availability

    print(f"Supplier tested: {supplier_node}")
    print("Supplier availability: False")
    print(
        f"Outgoing routes disabled: "
        f"{len(outgoing_routes)}"
    )
    print("Base graph preserved: YES")
    print("TEST 1 PASSED")


def test_demand_spike(graph):
    print("\n========== TEST 2: DEMAND SPIKE ==========")

    # Select the first customer in the graph
    customer_node = next(
        node
        for node, data in graph.nodes(data=True)
        if data["node_type"] == "customer"
    )

    customer_id = graph.nodes[
        customer_node
    ]["database_id"]

    original_demand = graph.nodes[
        customer_node
    ]["demand"]

    percentage = 20

    # Simulate 20% demand increase
    scenario = simulate_demand_spike(
        graph,
        customer_id,
        percentage
    )

    expected_demand = round_spiked_quantity(original_demand, percentage)

    actual_demand = scenario.nodes[
        customer_node
    ]["demand"]

    # Verify calculation
    assert actual_demand == expected_demand

    # Verify base graph was preserved
    assert graph.nodes[
        customer_node
    ]["demand"] == original_demand

    print(f"Customer tested: {customer_node}")
    print(f"Original demand: {original_demand}")
    print(f"Demand spike: {percentage}%")
    print(f"New demand: {actual_demand}")
    print("Base graph preserved: YES")
    print("TEST 2 PASSED")


def test_demand_spike_rounding_boundaries():
    assert round_spiked_quantity(42, 0) == 42
    assert round_spiked_quantity(42, 1) == 43
    assert round_spiked_quantity(42, 50) == 63
    assert round_spiked_quantity(42, 100) == 84


def test_demand_spike_rejects_non_finite_percentage():
    try:
        round_spiked_quantity(42, float("inf"))
    except ValueError as exc:
        assert "finite" in str(exc)
    else:
        raise AssertionError("Expected a non-finite percentage to be rejected")


def test_supplier_failure_simulation_does_not_mutate_database(graph):
    supplier_node = next(
        node
        for node, data in graph.nodes(data=True)
        if data["node_type"] == "supplier"
    )
    supplier_id = graph.nodes[supplier_node]["database_id"]
    db = SessionLocal()
    try:
        original_availability = db.get(Supplier, supplier_id).available
        simulate_supplier_failure(graph, supplier_id)
    finally:
        db.close()

    verification_db = SessionLocal()
    try:
        assert verification_db.get(Supplier, supplier_id).available == original_availability
    finally:
        verification_db.close()


def test_invalid_supplier(graph):
    print("\n========== TEST 3: INVALID SUPPLIER ==========")

    try:
        simulate_supplier_failure(
            graph,
            999999
        )

        assert False, (
            "Expected ValueError was not raised."
        )

    except ValueError:
        print("Invalid supplier rejected correctly.")
        print("TEST 3 PASSED")


def test_invalid_customer(graph):
    print("\n========== TEST 4: INVALID CUSTOMER ==========")

    try:
        simulate_demand_spike(
            graph,
            999999,
            20
        )

        assert False, (
            "Expected ValueError was not raised."
        )

    except ValueError:
        print("Invalid customer rejected correctly.")
        print("TEST 4 PASSED")


def test_negative_demand_spike(graph):
    print(
        "\n========== TEST 5: NEGATIVE DEMAND SPIKE =========="
    )

    customer_node = next(
        node
        for node, data in graph.nodes(data=True)
        if data["node_type"] == "customer"
    )

    customer_id = graph.nodes[
        customer_node
    ]["database_id"]

    try:
        simulate_demand_spike(
            graph,
            customer_id,
            -10
        )

        assert False, (
            "Expected ValueError was not raised."
        )

    except ValueError:
        print(
            "Negative demand spike rejected correctly."
        )
        print("TEST 5 PASSED")


def main():
    session = SessionLocal()

    try:
        graph = build_supply_chain_graph(session)

        print("\n==============================================")
        print("       ReRoute Phase 2D Test Suite")
        print("==============================================")

        print(
            f"Base graph: "
            f"{graph.number_of_nodes()} nodes, "
            f"{graph.number_of_edges()} edges"
        )

        test_supplier_failure(graph)
        test_demand_spike(graph)
        test_invalid_supplier(graph)
        test_invalid_customer(graph)
        test_negative_demand_spike(graph)

        print("\n==============================================")
        print("       ALL PHASE 2D TESTS PASSED")
        print("==============================================")

    finally:
        session.close()


if __name__ == "__main__":
    main()