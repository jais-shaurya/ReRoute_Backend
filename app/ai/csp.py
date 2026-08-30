from dataclasses import dataclass
from typing import Optional

import networkx as nx

from app.ai.astar import find_lowest_cost_path


@dataclass
class CandidatePlan:
    """
    Represents a candidate recovery plan generated
    from the supply-chain graph.
    """

    supplier_id: int
    customer_id: int
    quantity: int

    path: list[str]
    total_cost: float
    total_days: int

    factory_id: Optional[int] = None
    warehouse_id: Optional[int] = None


def _extract_node_id(
    node: str,
    expected_type: str
) -> int:
    """
    Extract the database ID from a graph node.

    Example:
        supplier:1 -> 1
    """

    prefix, database_id = node.split(":", 1)

    if prefix != expected_type:
        raise ValueError(
            f"Expected {expected_type} node, "
            f"got {node}."
        )

    return int(database_id)


def candidate_plan_from_astar(
    graph: nx.DiGraph,
    supplier_id: int,
    customer_id: int,
    quantity: int
) -> CandidatePlan:
    """
    Generate a CandidatePlan from an A* result.
    """

    if quantity <= 0:
        raise ValueError(
            "Plan quantity must be greater than zero."
        )

    result = find_lowest_cost_path(
        graph,
        supplier_id,
        customer_id
    )

    path = result["path"]

    factory_id = None
    warehouse_id = None

    for node in path:

        node_type = graph.nodes[node].get(
            "node_type"
        )

        if node_type == "factory":
            factory_id = _extract_node_id(
                node,
                "factory"
            )

        elif node_type == "warehouse":
            warehouse_id = _extract_node_id(
                node,
                "warehouse"
            )

    return CandidatePlan(
        supplier_id=supplier_id,
        customer_id=customer_id,
        quantity=quantity,
        path=path,
        total_cost=result["total_cost"],
        total_days=result["total_days"],
        factory_id=factory_id,
        warehouse_id=warehouse_id,
    )


def validate_candidate_plan(
    graph: nx.DiGraph,
    plan: CandidatePlan
) -> tuple[bool, list[str]]:
    """
    Validate a candidate plan against hard CSP constraints.

    Returns:

        (
            True,
            []
        )

    when the plan is feasible.

    Otherwise:

        (
            False,
            [reason1, reason2, ...]
        )
    """

    violations = []

    supplier_node = f"supplier:{plan.supplier_id}"
    customer_node = f"customer:{plan.customer_id}"

    # -----------------------------------------------------
    # Basic node validation
    # -----------------------------------------------------

    if supplier_node not in graph:
        violations.append(
            f"Supplier {plan.supplier_id} does not exist."
        )
        return False, violations

    if customer_node not in graph:
        violations.append(
            f"Customer {plan.customer_id} does not exist."
        )
        return False, violations

    # -----------------------------------------------------
    # Quantity validation
    # -----------------------------------------------------

    if plan.quantity <= 0:
        violations.append(
            "Plan quantity must be greater than zero."
        )

    customer = graph.nodes[customer_node]

    customer_demand = customer.get(
        "demand",
        0
    )

    if plan.quantity != customer_demand:
        violations.append(
            f"Demand violation: plan quantity "
            f"{plan.quantity} does not satisfy "
            f"customer demand {customer_demand}."
        )

    # -----------------------------------------------------
    # Supplier availability
    # -----------------------------------------------------

    supplier = graph.nodes[supplier_node]

    if not supplier.get("available", True):
        violations.append(
            f"Supplier {plan.supplier_id} is unavailable."
        )

    # -----------------------------------------------------
    # Supplier capacity
    # -----------------------------------------------------

    supplier_capacity = supplier.get(
        "capacity",
        0
    )

    if plan.quantity > supplier_capacity:
        violations.append(
            f"Supplier capacity violation: "
            f"quantity {plan.quantity} exceeds "
            f"supplier capacity {supplier_capacity}."
        )

    # -----------------------------------------------------
    # Path validation
    # -----------------------------------------------------

    if not plan.path:
        violations.append(
            "Candidate plan contains an empty path."
        )
        return False, violations

    if plan.path[0] != supplier_node:
        violations.append(
            "Path does not start at the selected supplier."
        )

    if plan.path[-1] != customer_node:
        violations.append(
            "Path does not end at the selected customer."
        )

    # -----------------------------------------------------
    # Route and intermediate-node validation
    # -----------------------------------------------------

    for source, destination in zip(
        plan.path,
        plan.path[1:]
    ):

        if not graph.has_edge(
            source,
            destination
        ):
            violations.append(
                f"Route does not exist: "
                f"{source} -> {destination}."
            )
            continue

        edge = graph.edges[
            source,
            destination
        ]

        # Route availability
        if not edge.get("available", True):
            violations.append(
                f"Route unavailable: "
                f"{source} -> {destination}."
            )

        # Route capacity
        route_capacity = edge.get(
            "capacity",
            0
        )

        if plan.quantity > route_capacity:
            violations.append(
                f"Route capacity violation: "
                f"{source} -> {destination} "
                f"has capacity {route_capacity}, "
                f"but plan requires {plan.quantity}."
            )

    # -----------------------------------------------------
    # Factory validation
    # -----------------------------------------------------

    if plan.factory_id is not None:

        factory_node = f"factory:{plan.factory_id}"

        if factory_node in graph:

            factory = graph.nodes[
                factory_node
            ]

            if not factory.get(
                "available",
                True
            ):
                violations.append(
                    f"Factory {plan.factory_id} "
                    f"is unavailable."
                )

            factory_capacity = factory.get(
                "capacity",
                0
            )

            if plan.quantity > factory_capacity:
                violations.append(
                    f"Factory capacity violation: "
                    f"quantity {plan.quantity} exceeds "
                    f"factory capacity {factory_capacity}."
                )

    # -----------------------------------------------------
    # Warehouse validation
    # -----------------------------------------------------

    if plan.warehouse_id is not None:

        warehouse_node = (
            f"warehouse:{plan.warehouse_id}"
        )

        if warehouse_node in graph:

            warehouse = graph.nodes[
                warehouse_node
            ]

            warehouse_capacity = warehouse.get(
                "capacity",
                0
            )

            if plan.quantity > warehouse_capacity:
                violations.append(
                    f"Warehouse capacity violation: "
                    f"quantity {plan.quantity} exceeds "
                    f"warehouse capacity "
                    f"{warehouse_capacity}."
                )

            inventory = warehouse.get(
                "inventory",
                0
            )

            if plan.quantity > inventory:
                violations.append(
                    f"Warehouse inventory violation: "
                    f"quantity {plan.quantity} exceeds "
                    f"available inventory {inventory}."
                )

    # -----------------------------------------------------
    # Deadline validation
    # -----------------------------------------------------

    customer_deadline = customer.get(
        "deadline_days"
    )

    if (
        customer_deadline is not None
        and plan.total_days > customer_deadline
    ):
        violations.append(
            f"Deadline violation: delivery takes "
            f"{plan.total_days} days, but customer "
            f"deadline is {customer_deadline} days."
        )

    return (
        len(violations) == 0,
        violations
    )


def generate_feasible_plans(
    graph: nx.DiGraph,
    customer_id: int,
    quantity: int
) -> list[CandidatePlan]:
    """
    Generate feasible recovery plans using
    available suppliers and A*.

    The function uses backtracking:
    each available supplier is considered as a
    candidate assignment, and infeasible candidates
    are rejected by the CSP validator.
    """

    feasible_plans = []

    suppliers = []

    for node, data in graph.nodes(data=True):

        if data.get("node_type") != "supplier":
            continue

        if not data.get("available", True):
            continue

        # -------------------------------------------------
        # Forward checking:
        # A supplier whose capacity cannot satisfy the
        # required quantity is removed from the domain
        # before backtracking begins.
        # -------------------------------------------------

        supplier_capacity = data.get(
            "capacity",
            0
        )

        if supplier_capacity < quantity:
            continue

        suppliers.append(node)

    def backtrack(
        supplier_nodes: list[str],
        index: int
    ) -> None:

        if index >= len(supplier_nodes):
            return

        supplier_node = supplier_nodes[index]

        supplier_id = _extract_node_id(
            supplier_node,
            "supplier"
        )

        try:
            plan = candidate_plan_from_astar(
                graph,
                supplier_id,
                customer_id,
                quantity
            )

            is_valid, _ = validate_candidate_plan(
                graph,
                plan
            )

            if is_valid:
                feasible_plans.append(plan)

        except ValueError:
            pass

        # Backtrack to the next supplier
        backtrack(
            supplier_nodes,
            index + 1
        )

    backtrack(
        suppliers,
        0
    )

    return feasible_plans