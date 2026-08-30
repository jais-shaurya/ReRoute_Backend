from app.database.connection import SessionLocal
from app.ai.graph import build_supply_chain_graph
from app.ai.csp import (
    CandidatePlan,
    candidate_plan_from_astar,
    validate_candidate_plan,
    generate_feasible_plans,
)
from app.ai.disruption import simulate_supplier_failure


def find_valid_candidate(graph, customer_id, quantity):
    """
    Find the first candidate that satisfies all CSP constraints.
    """

    suppliers = [
        node
        for node, data in graph.nodes(data=True)
        if (
            data.get("node_type") == "supplier"
            and data.get("available", True)
        )
    ]

    for supplier_node in suppliers:

        supplier_id = int(
            supplier_node.split(":")[1]
        )

        try:
            plan = candidate_plan_from_astar(
                graph,
                supplier_id,
                customer_id,
                quantity
            )

            valid, _ = validate_candidate_plan(
                graph,
                plan
            )

            if valid:
                return plan

        except ValueError:
            continue

    return None


def test_valid_candidate_plan(graph):
    print(
        "\n========== TEST 1: VALID CANDIDATE PLAN =========="
    )

    customer_id = 1

    customer_node = f"customer:{customer_id}"

    demand = graph.nodes[
        customer_node
    ]["demand"]

    # Demand from the database is normally an integer.
    quantity = int(demand)

    plan = find_valid_candidate(
        graph,
        customer_id,
        quantity
    )

    assert plan is not None, (
        "No valid candidate plan was found "
        "in the current dataset."
    )

    valid, violations = validate_candidate_plan(
        graph,
        plan
    )

    assert valid is True
    assert violations == []

    print("Candidate plan:")
    print(" -> ".join(plan.path))

    print(f"Quantity: {plan.quantity}")
    print(f"Total cost: {plan.total_cost}")
    print(f"Total days: {plan.total_days}")

    print("CSP accepted the candidate.")
    print("TEST 1 PASSED")


def test_capacity_violation(graph):
    print(
        "\n========== TEST 2: CAPACITY VIOLATION =========="
    )

    customer_id = 1

    customer_node = f"customer:{customer_id}"

    demand = int(
        graph.nodes[customer_node]["demand"]
    )

    plan = find_valid_candidate(
        graph,
        customer_id,
        demand
    )

    assert plan is not None, (
        "Need a valid baseline plan before "
        "testing capacity violation."
    )

    scenario = graph.copy()

    supplier_node = (
        f"supplier:{plan.supplier_id}"
    )

    original_capacity = scenario.nodes[
        supplier_node
    ]["capacity"]

    # Force supplier capacity below demand.
    scenario.nodes[
        supplier_node
    ]["capacity"] = max(
        0,
        plan.quantity - 1
    )

    valid, violations = validate_candidate_plan(
        scenario,
        plan
    )

    assert valid is False

    assert any(
        "Supplier capacity violation"
        in violation
        for violation in violations
    )

    print(
        f"Original supplier capacity: "
        f"{original_capacity}"
    )

    print(
        f"Forced supplier capacity: "
        f"{scenario.nodes[supplier_node]['capacity']}"
    )

    print("CSP correctly rejected the plan.")
    print("TEST 2 PASSED")


def test_inventory_violation(graph):
    print(
        "\n========== TEST 3: INVENTORY VIOLATION =========="
    )

    customer_id = 1

    customer_node = f"customer:{customer_id}"

    demand = int(
        graph.nodes[customer_node]["demand"]
    )

    plan = find_valid_candidate(
        graph,
        customer_id,
        demand
    )

    assert plan is not None

    assert plan.warehouse_id is not None, (
        "A* candidate should contain a warehouse."
    )

    scenario = graph.copy()

    warehouse_node = (
        f"warehouse:{plan.warehouse_id}"
    )

    original_inventory = scenario.nodes[
        warehouse_node
    ]["inventory"]

    # Force inventory below the required quantity.
    scenario.nodes[
        warehouse_node
    ]["inventory"] = max(
        0,
        plan.quantity - 1
    )

    valid, violations = validate_candidate_plan(
        scenario,
        plan
    )

    assert valid is False

    assert any(
        "Warehouse inventory violation"
        in violation
        for violation in violations
    )

    print(
        f"Original inventory: {original_inventory}"
    )

    print(
        f"Forced inventory: "
        f"{scenario.nodes[warehouse_node]['inventory']}"
    )

    print("CSP correctly rejected the plan.")
    print("TEST 3 PASSED")


def test_demand_violation(graph):
    print(
        "\n========== TEST 4: DEMAND VIOLATION =========="
    )

    customer_id = 1

    customer_node = f"customer:{customer_id}"

    demand = int(
        graph.nodes[customer_node]["demand"]
    )

    plan = find_valid_candidate(
        graph,
        customer_id,
        demand
    )

    assert plan is not None

    invalid_quantity = demand - 1

    if invalid_quantity <= 0:
        invalid_quantity = demand + 1

    invalid_plan = CandidatePlan(
        supplier_id=plan.supplier_id,
        customer_id=plan.customer_id,
        quantity=invalid_quantity,
        path=plan.path,
        total_cost=plan.total_cost,
        total_days=plan.total_days,
        factory_id=plan.factory_id,
        warehouse_id=plan.warehouse_id,
    )

    valid, violations = validate_candidate_plan(
        graph,
        invalid_plan
    )

    assert valid is False

    assert any(
        "Demand violation"
        in violation
        for violation in violations
    )

    print(
        f"Customer demand: {demand}"
    )

    print(
        f"Invalid plan quantity: {invalid_quantity}"
    )

    print("CSP correctly rejected the plan.")
    print("TEST 4 PASSED")


def test_deadline_violation(graph):
    print(
        "\n========== TEST 5: DEADLINE VIOLATION =========="
    )

    customer_id = 1

    customer_node = f"customer:{customer_id}"

    demand = int(
        graph.nodes[customer_node]["demand"]
    )

    plan = find_valid_candidate(
        graph,
        customer_id,
        demand
    )

    assert plan is not None

    scenario = graph.copy()

    scenario.nodes[
        customer_node
    ]["deadline_days"] = max(
        0,
        plan.total_days - 1
    )

    valid, violations = validate_candidate_plan(
        scenario,
        plan
    )

    assert valid is False

    assert any(
        "Deadline violation"
        in violation
        for violation in violations
    )

    print(
        f"Plan delivery time: "
        f"{plan.total_days} days"
    )

    print(
        f"Forced deadline: "
        f"{scenario.nodes[customer_node]['deadline_days']} days"
    )

    print("CSP correctly rejected the plan.")
    print("TEST 5 PASSED")


def test_unavailable_supplier(graph):
    print(
        "\n========== TEST 6: UNAVAILABLE SUPPLIER =========="
    )

    customer_id = 1

    customer_node = f"customer:{customer_id}"

    demand = int(
        graph.nodes[customer_node]["demand"]
    )

    plan = find_valid_candidate(
        graph,
        customer_id,
        demand
    )

    assert plan is not None

    scenario = graph.copy()

    supplier_node = (
        f"supplier:{plan.supplier_id}"
    )

    scenario.nodes[
        supplier_node
    ]["available"] = False

    valid, violations = validate_candidate_plan(
        scenario,
        plan
    )

    assert valid is False

    assert any(
        "Supplier" in violation
        and "unavailable" in violation
        for violation in violations
    )

    print(
        f"Supplier disabled: "
        f"{supplier_node}"
    )

    print("CSP correctly rejected the plan.")
    print("TEST 6 PASSED")


def test_unavailable_route(graph):
    print(
        "\n========== TEST 7: UNAVAILABLE ROUTE =========="
    )

    customer_id = 1

    customer_node = f"customer:{customer_id}"

    demand = int(
        graph.nodes[customer_node]["demand"]
    )

    plan = find_valid_candidate(
        graph,
        customer_id,
        demand
    )

    assert plan is not None

    scenario = graph.copy()

    source = plan.path[0]
    destination = plan.path[1]

    scenario.edges[
        source,
        destination
    ]["available"] = False

    valid, violations = validate_candidate_plan(
        scenario,
        plan
    )

    assert valid is False

    assert any(
        "Route unavailable"
        in violation
        for violation in violations
    )

    print(
        f"Disabled route: "
        f"{source} -> {destination}"
    )

    print("CSP correctly rejected the plan.")
    print("TEST 7 PASSED")


def test_backtracking_finds_feasible_plans(graph):
    print(
        "\n========== TEST 8: BACKTRACKING =========="
    )

    customer_id = 1

    customer_node = f"customer:{customer_id}"

    demand = int(
        graph.nodes[customer_node]["demand"]
    )

    plans = generate_feasible_plans(
        graph,
        customer_id,
        demand
    )

    assert isinstance(plans, list)

    print(
        f"Feasible plans found: {len(plans)}"
    )

    for index, plan in enumerate(
        plans,
        start=1
    ):
        print(
            f"\nPlan {index}:"
        )
        print(
            " -> ".join(plan.path)
        )
        print(
            f"Cost: {plan.total_cost}"
        )
        print(
            f"Days: {plan.total_days}"
        )

    assert len(plans) > 0, (
        "Backtracking should find at least "
        "one feasible plan."
    )

    print("Backtracking found feasible plans.")
    print("TEST 8 PASSED")


def test_no_feasible_solution(graph):
    print(
        "\n========== TEST 9: NO FEASIBLE SOLUTION =========="
    )

    scenario = graph.copy()

    customer_id = 1

    customer_node = f"customer:{customer_id}"

    demand = int(
        scenario.nodes[customer_node]["demand"]
    )

    # Disable every supplier.
    for node, data in scenario.nodes(
        data=True
    ):
        if data.get("node_type") == "supplier":
            data["available"] = False

    plans = generate_feasible_plans(
        scenario,
        customer_id,
        demand
    )

    assert plans == []

    print(
        "All suppliers disabled."
    )

    print(
        "CSP correctly reported no feasible solution."
    )

    print("TEST 9 PASSED")

def test_forward_checking(graph):
    print(
        "\n========== TEST 10: FORWARD CHECKING =========="
    )

    customer_id = 1

    customer_node = f"customer:{customer_id}"

    demand = int(
        graph.nodes[customer_node]["demand"]
    )

    scenario = graph.copy()

    # Find an available supplier and deliberately make
    # its capacity insufficient for the demand.
    pruned_supplier = None

    for node, data in scenario.nodes(data=True):

        if (
            data.get("node_type") == "supplier"
            and data.get("available", True)
        ):
            data["capacity"] = max(
                0,
                demand - 1
            )

            pruned_supplier = node
            break

    assert pruned_supplier is not None

    plans = generate_feasible_plans(
        scenario,
        customer_id,
        demand
    )

    # The supplier with insufficient capacity should
    # never appear in any generated feasible plan.
    for plan in plans:
        assert (
            f"supplier:{plan.supplier_id}"
            != pruned_supplier
        )

    print(
        f"Pruned supplier: {pruned_supplier}"
    )

    print(
        f"Customer demand: {demand}"
    )

    print(
        "Supplier was removed from the domain "
        "by forward checking."
    )

    print("TEST 10 PASSED")

def main():
    session = SessionLocal()

    try:
        graph = build_supply_chain_graph(
            session
        )

        print("\n==============================================")
        print("       ReRoute Phase 2F CSP Test Suite")
        print("==============================================")

        print(
            f"Base graph: "
            f"{graph.number_of_nodes()} nodes, "
            f"{graph.number_of_edges()} edges"
        )

        test_valid_candidate_plan(graph)
        test_capacity_violation(graph)
        test_inventory_violation(graph)
        test_demand_violation(graph)
        test_deadline_violation(graph)
        test_unavailable_supplier(graph)
        test_unavailable_route(graph)
        test_backtracking_finds_feasible_plans(graph)
        test_no_feasible_solution(graph)
        test_forward_checking(graph)

        print("\n==============================================")
        print("       ALL PHASE 2F TESTS PASSED")
        print("==============================================")

    finally:
        session.close()



if __name__ == "__main__":
    main()