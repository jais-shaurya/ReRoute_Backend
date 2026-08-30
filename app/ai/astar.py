import networkx as nx


def _minimum_available_edge_cost(
    graph: nx.DiGraph
) -> float:
    """
    Return the minimum transportation cost among
    currently available edges.
    """

    costs = [
        data["transportation_cost"]
        for _, _, data in graph.edges(data=True)
        if data.get("available", True)
    ]

    if not costs:
        return 0.0

    return min(costs)


def _heuristic(
    graph: nx.DiGraph,
    current: str,
    goal: str
) -> float:
    """
    Admissible heuristic for A*.

    The heuristic uses:

        minimum available edge cost
        ×
        minimum number of hops from current to goal

    The minimum edge cost cannot overestimate the cost
    of an individual edge, and the minimum-hop distance
    cannot overestimate the number of edges required.

    Therefore the heuristic does not overestimate the
    true remaining transportation cost.
    """

    try:
        minimum_hops = nx.shortest_path_length(
            graph,
            source=current,
            target=goal
        )
    except nx.NetworkXNoPath:
        return 0.0

    minimum_edge_cost = (
        _minimum_available_edge_cost(graph)
    )

    return minimum_hops * minimum_edge_cost


def find_lowest_cost_path(
    graph: nx.DiGraph,
    supplier_id: int,
    customer_id: int
) -> dict:
    """
    Find the lowest-transportation-cost available path
    from a supplier to a customer using A*.

    Unavailable routes are ignored.

    Returns:
        {
            "path": [...],
            "total_cost": ...,
            "total_days": ...
        }
    """

    supplier_node = f"supplier:{supplier_id}"
    customer_node = f"customer:{customer_id}"

    # Validate supplier
    if supplier_node not in graph:
        raise ValueError(
            f"Supplier with ID {supplier_id} does not exist."
        )

    # Validate customer
    if customer_node not in graph:
        raise ValueError(
            f"Customer with ID {customer_id} does not exist."
        )

    # Supplier must be available
    if not graph.nodes[supplier_node].get(
        "available",
        True
    ):
        raise ValueError(
            f"Supplier with ID {supplier_id} is unavailable."
        )

    def edge_cost(source, destination, data):
        """
        Return transportation cost for available routes.

        Returning None tells NetworkX that the edge
        cannot be used.
        """

        if not data.get("available", True):
            return None

        return data["transportation_cost"]

    try:
        path = nx.astar_path(
            graph,
            supplier_node,
            customer_node,
            heuristic=lambda current, goal: _heuristic(
                graph,
                current,
                goal
            ),
            weight=edge_cost
        )

    except nx.NetworkXNoPath:
        raise ValueError(
            f"No available path exists from "
            f"Supplier {supplier_id} to "
            f"Customer {customer_id}."
        )

    total_cost = 0.0
    total_days = 0

    for source, destination in zip(
        path,
        path[1:]
    ):
        edge = graph.edges[
            source,
            destination
        ]

        total_cost += edge[
            "transportation_cost"
        ]

        total_days += edge[
            "delivery_time_days"
        ]

    return {
        "path": path,
        "total_cost": round(total_cost, 2),
        "total_days": total_days
    }