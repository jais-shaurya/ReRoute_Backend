import networkx as nx
from math import ceil, isfinite


def round_spiked_quantity(original_demand: float, percentage: float) -> int:
    """Round the resulting post-spike demand upward to a whole unit."""
    if not isinstance(original_demand, (int, float)) or isinstance(original_demand, bool):
        raise ValueError("Original demand must be numeric.")
    if not isinstance(percentage, (int, float)) or isinstance(percentage, bool):
        raise ValueError("Demand spike percentage must be numeric.")
    if not isfinite(float(original_demand)) or original_demand < 0:
        raise ValueError("Original demand must be finite and non-negative.")
    if not isfinite(float(percentage)) or percentage < 0:
        raise ValueError("Demand spike percentage must be finite and non-negative.")
    return ceil(original_demand * (1 + percentage / 100))


def simulate_supplier_failure(
    graph: nx.DiGraph,
    supplier_id: int
) -> nx.DiGraph:
    """
    Simulate the failure of a supplier.

    The original graph is not modified.

    The failed supplier becomes unavailable and
    all outgoing routes from that supplier become unavailable.
    """

    # Create a temporary scenario
    scenario = graph.copy()

    supplier_node = f"supplier:{supplier_id}"

    # Validate supplier
    if supplier_node not in scenario:
        raise ValueError(
            f"Supplier with ID {supplier_id} does not exist."
        )

    # Mark supplier as unavailable
    scenario.nodes[supplier_node]["available"] = False

    # Mark all outgoing routes as unavailable
    for _, destination in scenario.out_edges(supplier_node):
        scenario.edges[
            supplier_node,
            destination
        ]["available"] = False

    return scenario

def simulate_demand_spike(
    graph: nx.DiGraph,
    customer_id: int,
    percentage: float
) -> nx.DiGraph:
    """
    Simulate a percentage increase in customer demand.

    The original graph is not modified.

    Example:
        demand = 100
        percentage = 20
        new demand = 120
    """

    # Create a temporary scenario
    scenario = graph.copy()

    customer_node = f"customer:{customer_id}"

    # Validate customer
    if customer_node not in scenario:
        raise ValueError(
            f"Customer with ID {customer_id} does not exist."
        )

    # Validate percentage
    # Make sure the target is actually a customer
    if scenario.nodes[customer_node]["node_type"] != "customer":
        raise ValueError(
            f"Node {customer_node} is not a customer."
        )

    # Get original demand
    original_demand = scenario.nodes[
        customer_node
    ]["demand"]

    # Calculate increased demand
    new_demand = round_spiked_quantity(original_demand, percentage)

    # Update only the scenario
    scenario.nodes[
        customer_node
    ]["demand"] = new_demand

    return scenario