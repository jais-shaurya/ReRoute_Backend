from dataclasses import dataclass
from math import isfinite
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


@dataclass(frozen=True)
class CandidateRejection:
    supplier_id: int
    path: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CandidateSearchResult:
    plans: tuple[CandidatePlan, ...]
    rejected_candidates: tuple[CandidateRejection, ...]


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

    return candidate_plan_from_path(
        graph,
        result["path"],
        supplier_id,
        customer_id,
        quantity,
    )


def candidate_plan_from_path(
    graph: nx.DiGraph,
    path: list[str],
    supplier_id: int,
    customer_id: int,
    quantity: int,
) -> CandidatePlan:
    total_cost = 0.0
    total_days = 0
    for source, destination in zip(path, path[1:]):
        edge = graph.edges[source, destination]
        edge_cost = edge.get("transportation_cost")
        edge_days = edge.get("delivery_time_days")
        if isinstance(edge_cost, (int, float)) and not isinstance(edge_cost, bool):
            total_cost += edge_cost
        if isinstance(edge_days, int) and not isinstance(edge_days, bool):
            total_days += edge_days

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
        total_cost=round(total_cost, 2),
        total_days=total_days,
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

    quantity_is_integer = isinstance(plan.quantity, int) and not isinstance(plan.quantity, bool)
    if not quantity_is_integer:
        violations.append("Plan quantity must be an integer.")
    if not isinstance(plan.total_cost, (int, float)) or isinstance(plan.total_cost, bool):
        violations.append("Plan total cost must be numeric.")
    elif not isfinite(float(plan.total_cost)) or plan.total_cost < 0:
        violations.append("Plan total cost must be finite and non-negative.")
    if not isinstance(plan.total_days, int) or isinstance(plan.total_days, bool):
        violations.append("Plan delivery time must be a non-negative integer.")
    elif plan.total_days < 0:
        violations.append("Plan delivery time must be a non-negative integer.")

    if violations:
        return False, violations

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

    if quantity_is_integer and plan.quantity <= 0:
        violations.append(
            "Plan quantity must be greater than zero."
        )

    customer = graph.nodes[customer_node]

    customer_demand = customer.get(
        "demand",
        0
    )

    if quantity_is_integer and plan.quantity != customer_demand:
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

    if (
        not isinstance(supplier_capacity, (int, float))
        or isinstance(supplier_capacity, bool)
        or not isfinite(float(supplier_capacity))
        or plan.quantity > supplier_capacity
    ):
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

    if len(set(plan.path)) != len(plan.path):
        violations.append("Candidate path cannot visit the same node more than once.")

    observed_cost = 0.0
    observed_days = 0
    has_complete_route_metrics = True

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

        route_cost = edge.get("transportation_cost")
        if (
            not isinstance(route_cost, (int, float))
            or isinstance(route_cost, bool)
            or not isfinite(float(route_cost))
            or route_cost < 0
        ):
            violations.append(
                f"Route {source} -> {destination} has missing or invalid transportation cost."
            )
            has_complete_route_metrics = False
        else:
            observed_cost += route_cost

        route_days = edge.get("delivery_time_days")
        if not isinstance(route_days, int) or isinstance(route_days, bool) or route_days < 0:
            violations.append(
                f"Route {source} -> {destination} has missing or invalid delivery time."
            )
            has_complete_route_metrics = False
        else:
            observed_days += route_days

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

        if (
            not isinstance(route_capacity, (int, float))
            or isinstance(route_capacity, bool)
            or not isfinite(float(route_capacity))
            or plan.quantity > route_capacity
        ):
            violations.append(
                f"Route capacity violation: "
                f"{source} -> {destination} "
                f"has capacity {route_capacity}, "
                f"but plan requires {plan.quantity}."
            )

    if has_complete_route_metrics:
        if (
            isinstance(plan.total_cost, (int, float))
            and not isinstance(plan.total_cost, bool)
            and isfinite(float(plan.total_cost))
            and abs(float(plan.total_cost) - round(observed_cost, 2)) > 1e-6
        ):
            violations.append(
                "Candidate total cost does not match the route costs on its path."
            )
        if (
            isinstance(plan.total_days, int)
            and not isinstance(plan.total_days, bool)
            and plan.total_days != observed_days
        ):
            violations.append(
                "Candidate delivery time does not match the route times on its path."
            )

    path_factory_ids = []
    path_warehouse_ids = []
    for node in plan.path[1:-1]:
        if node not in graph:
            continue
        attributes = graph.nodes[node]
        node_type = attributes.get("node_type")
        database_id = attributes.get("database_id")
        if node_type == "factory":
            path_factory_ids.append(database_id)
            if not attributes.get("available", True):
                violations.append(f"Factory {database_id} is unavailable.")
            capacity = attributes.get("capacity")
            if (
                not isinstance(capacity, (int, float))
                or isinstance(capacity, bool)
                or not isfinite(float(capacity))
                or plan.quantity > capacity
            ):
                violations.append(
                    f"Factory capacity violation: quantity {plan.quantity} "
                    f"exceeds factory {database_id} capacity {capacity}."
                )
        elif node_type == "warehouse":
            path_warehouse_ids.append(database_id)
            if not attributes.get("available", True):
                violations.append(f"Warehouse {database_id} is unavailable.")
            capacity = attributes.get("capacity")
            inventory = attributes.get("inventory")
            if (
                not isinstance(capacity, (int, float))
                or isinstance(capacity, bool)
                or not isfinite(float(capacity))
                or plan.quantity > capacity
            ):
                violations.append(
                    f"Warehouse capacity violation: quantity {plan.quantity} "
                    f"exceeds warehouse {database_id} capacity {capacity}."
                )
            if (
                not isinstance(inventory, (int, float))
                or isinstance(inventory, bool)
                or not isfinite(float(inventory))
                or plan.quantity > inventory
            ):
                violations.append(
                    f"Warehouse inventory violation: quantity {plan.quantity} "
                    f"exceeds warehouse {database_id} inventory {inventory}."
                )

    if plan.factory_id not in path_factory_ids:
        if plan.factory_id is not None or path_factory_ids:
            violations.append("Candidate factory_id does not match its path.")
    if plan.warehouse_id not in path_warehouse_ids:
        if plan.warehouse_id is not None or path_warehouse_ids:
            violations.append("Candidate warehouse_id does not match its path.")

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


def search_feasible_plans(
    graph: nx.DiGraph,
    customer_id: int,
    quantity: int,
    min_supplier_reliability: float = 0.0,
) -> CandidateSearchResult:
    """
    Find the least-cost feasible simple path for each supplier and retain
    rejection reasons for suppliers and paths that cannot satisfy the CSP.
    """
    if quantity <= 0:
        raise ValueError("Planning quantity must be greater than zero.")
    if not isfinite(min_supplier_reliability) or not 0.0 <= min_supplier_reliability <= 1.0:
        raise ValueError("Minimum supplier reliability must be between 0 and 1.")

    customer_node = f"customer:{customer_id}"
    if customer_node not in graph:
        return CandidateSearchResult((), ())

    path_graph = graph.copy()
    path_graph.remove_edges_from(
        [
            (source, destination)
            for source, destination, edge in graph.edges(data=True)
            if not edge.get("available", True)
        ]
    )
    path_graph.remove_nodes_from(
        [
            node
            for node, data in graph.nodes(data=True)
            if data.get("node_type") in {"factory", "warehouse"}
            and not data.get("available", True)
        ]
    )

    plans: list[CandidatePlan] = []
    rejected: list[CandidateRejection] = []
    supplier_nodes = sorted(
        (
            node
            for node, data in graph.nodes(data=True)
            if data.get("node_type") == "supplier"
        ),
        key=lambda node: graph.nodes[node].get("database_id", _extract_node_id(node, "supplier")),
    )

    for supplier_node in supplier_nodes:
        supplier_id = _extract_node_id(supplier_node, "supplier")
        supplier = graph.nodes[supplier_node]
        supplier_reasons = []

        if not supplier.get("available", True):
            supplier_reasons.append("supplier is unavailable")
        capacity = supplier.get("capacity")
        if capacity is None or quantity > capacity:
            supplier_reasons.append(
                f"supplier capacity {capacity} is below required quantity {quantity}"
            )
        reliability = supplier.get("reliability")
        if reliability is None:
            if min_supplier_reliability > 0:
                supplier_reasons.append(
                    "supplier reliability is unknown and cannot satisfy the "
                    f"minimum service level {min_supplier_reliability:.3f}"
                )
        else:
            if not isinstance(reliability, (int, float)) or isinstance(reliability, bool):
                raise ValueError(f"Supplier {supplier_id} reliability must be numeric.")
            if not isfinite(float(reliability)) or not 0.0 <= reliability <= 1.0:
                raise ValueError(f"Supplier {supplier_id} reliability must be between 0 and 1.")
            if reliability < min_supplier_reliability:
                supplier_reasons.append(
                    f"supplier reliability {reliability:.3f} is below minimum "
                    f"service level {min_supplier_reliability:.3f}"
                )

        if supplier_reasons:
            rejected.append(CandidateRejection(supplier_id, (), tuple(supplier_reasons)))
            continue

        found_path = False
        try:
            path_iterator = nx.shortest_simple_paths(
                path_graph,
                supplier_node,
                customer_node,
                weight="transportation_cost",
            )
            for path in path_iterator:
                plan = candidate_plan_from_path(
                    graph,
                    path,
                    supplier_id,
                    customer_id,
                    quantity,
                )
                valid, violations = validate_candidate_plan(graph, plan)
                if valid:
                    plans.append(plan)
                    found_path = True
                    break
                rejected.append(
                    CandidateRejection(supplier_id, tuple(path), tuple(violations))
                )
        except nx.NetworkXNoPath:
            pass

        if not found_path and not any(item.supplier_id == supplier_id for item in rejected):
            rejected.append(
                CandidateRejection(
                    supplier_id,
                    (),
                    ("no available route path reaches the requested customer",),
                )
            )

    return CandidateSearchResult(tuple(plans), tuple(rejected))


def generate_feasible_plans(
    graph: nx.DiGraph,
    customer_id: int,
    quantity: int,
    min_supplier_reliability: float = 0.0,
) -> list[CandidatePlan]:
    """Compatibility wrapper returning only CSP-feasible plans."""
    return list(
        search_feasible_plans(
            graph,
            customer_id,
            quantity,
            min_supplier_reliability,
        ).plans
    )