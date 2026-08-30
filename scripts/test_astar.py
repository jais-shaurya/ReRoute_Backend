from app.database.connection import SessionLocal
from app.ai.graph import build_supply_chain_graph
from app.ai.astar import find_lowest_cost_path
from app.ai.disruption import simulate_supplier_failure


def test_normal_path(graph):
    print("\n========== TEST 1: NORMAL A* PATH ==========")

    supplier_id = 1
    customer_id = 1

    result = find_lowest_cost_path(
        graph,
        supplier_id,
        customer_id
    )

    assert result["path"][0] == f"supplier:{supplier_id}"
    assert result["path"][-1] == f"customer:{customer_id}"

    assert result["total_cost"] > 0
    assert result["total_days"] > 0

    print("Path found:")
    print(" -> ".join(result["path"]))

    print(f"Total transportation cost: {result['total_cost']}")
    print(f"Total delivery time: {result['total_days']} days")

    print("TEST 1 PASSED")


def test_supplier_disruption(graph):
    print(
        "\n========== TEST 2: A* AFTER SUPPLIER FAILURE =========="
    )

    supplier_id = 1
    customer_id = 1

    scenario = simulate_supplier_failure(
        graph,
        supplier_id
    )

    try:
        find_lowest_cost_path(
            scenario,
            supplier_id,
            customer_id
        )

        assert False, (
            "Failed supplier should not be usable."
        )

    except ValueError as error:
        print(f"A* correctly rejected failed supplier: {error}")

    print("TEST 2 PASSED")


def test_unavailable_route_is_ignored(graph):
    print(
        "\n========== TEST 3: UNAVAILABLE ROUTE =========="
    )

    supplier_id = 2
    customer_id = 1

    scenario = graph.copy()

    supplier_node = f"supplier:{supplier_id}"

    outgoing_routes = list(
        scenario.out_edges(supplier_node)
    )

    assert outgoing_routes, (
        "Selected supplier has no outgoing routes."
    )

    # Disable the first outgoing route
    source, destination = outgoing_routes[0]

    scenario.edges[
        source,
        destination
    ]["available"] = False

    try:
        result = find_lowest_cost_path(
            scenario,
            supplier_id,
            customer_id
        )

        # The disabled edge must not appear in the path
        disabled_edge = (
            source,
            destination
        )

        path_edges = list(
            zip(
                result["path"],
                result["path"][1:]
            )
        )

        assert disabled_edge not in path_edges

        print(
            f"Disabled route ignored: "
            f"{source} -> {destination}"
        )

        print("Alternative path found:")
        print(" -> ".join(result["path"]))

        print("TEST 3 PASSED")

    except ValueError:
        print(
            "No alternative path exists after disabling "
            "the selected route."
        )
        print(
            "TEST 3 PASSED "
            "(unavailable route correctly respected)"
        )


def test_invalid_supplier(graph):
    print(
        "\n========== TEST 4: INVALID SUPPLIER =========="
    )

    try:
        find_lowest_cost_path(
            graph,
            999999,
            1
        )

        assert False, (
            "Expected ValueError was not raised."
        )

    except ValueError:
        print("Invalid supplier rejected correctly.")
        print("TEST 4 PASSED")


def test_invalid_customer(graph):
    print(
        "\n========== TEST 5: INVALID CUSTOMER =========="
    )

    try:
        find_lowest_cost_path(
            graph,
            1,
            999999
        )

        assert False, (
            "Expected ValueError was not raised."
        )

    except ValueError:
        print("Invalid customer rejected correctly.")
        print("TEST 5 PASSED")


def main():
    session = SessionLocal()

    try:
        graph = build_supply_chain_graph(session)

        print("\n==============================================")
        print("       ReRoute Phase 2E A* Test Suite")
        print("==============================================")

        print(
            f"Base graph: "
            f"{graph.number_of_nodes()} nodes, "
            f"{graph.number_of_edges()} edges"
        )

        test_normal_path(graph)
        test_supplier_disruption(graph)
        test_unavailable_route_is_ignored(graph)
        test_invalid_supplier(graph)
        test_invalid_customer(graph)

        print("\n==============================================")
        print("       ALL PHASE 2E TESTS PASSED")
        print("==============================================")

    finally:
        session.close()


if __name__ == "__main__":
    main()