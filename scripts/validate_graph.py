from app.database.connection import SessionLocal
from app.ai.graph import build_supply_chain_graph


ALLOWED_TRANSITIONS = {
    ("supplier", "factory"),
    ("factory", "warehouse"),
    ("warehouse", "customer"),
}


def validate_graph(graph):
    print("\n========== GRAPH VALIDATION ==========")

    errors = []

    # --------------------------------------------------
    # Validate node count
    # --------------------------------------------------

    expected_node_types = {
        "supplier": 10,
        "factory": 2,
        "warehouse": 4,
        "customer": 8,
    }

    for node_type, expected_count in expected_node_types.items():

        actual_count = sum(
            1
            for _, data in graph.nodes(data=True)
            if data["node_type"] == node_type
        )

        print(
            f"{node_type}: "
            f"{actual_count}/{expected_count}"
        )

        if actual_count != expected_count:
            errors.append(
                f"Expected {expected_count} "
                f"{node_type} nodes, found {actual_count}"
            )

    # --------------------------------------------------
    # Validate edges
    # --------------------------------------------------

    print("\nValidating route transitions...")

    for source, destination, data in graph.edges(data=True):

        source_type = graph.nodes[source]["node_type"]
        destination_type = graph.nodes[destination]["node_type"]

        transition = (
            source_type,
            destination_type,
        )

        if transition not in ALLOWED_TRANSITIONS:
            errors.append(
                f"Invalid transition: "
                f"{source_type} -> {destination_type}"
            )

        # Route attributes
        if data["transportation_cost"] <= 0:
            errors.append(
                f"{data['route_code']} has invalid cost"
            )

        if data["delivery_time_days"] <= 0:
            errors.append(
                f"{data['route_code']} has invalid delivery time"
            )

        if data["capacity"] <= 0:
            errors.append(
                f"{data['route_code']} has invalid capacity"
            )

    # --------------------------------------------------
    # Validate customer connectivity
    # --------------------------------------------------

    print("\nValidating customer connectivity...")

    for node, data in graph.nodes(data=True):

        if data["node_type"] == "customer":

            incoming = graph.in_degree(node)

            print(
                f"{node}: "
                f"{incoming} incoming route(s)"
            )

            if incoming == 0:
                errors.append(
                    f"{node} has no incoming route"
                )

    # --------------------------------------------------
    # Final result
    # --------------------------------------------------

    if errors:

        print("\nGRAPH VALIDATION FAILED")

        for error in errors:
            print(f"- {error}")

        raise AssertionError(
            "Graph validation failed."
        )

    print("\nAll graph validation checks passed!")
    print("====================================")


def main():

    session = SessionLocal()

    try:

        graph = build_supply_chain_graph(session)

        validate_graph(graph)

    finally:

        session.close()


if __name__ == "__main__":
    main()