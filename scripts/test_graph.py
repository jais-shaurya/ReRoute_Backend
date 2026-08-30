from app.database.connection import SessionLocal
from app.ai.graph import build_supply_chain_graph


def test_graph():
    session = SessionLocal()

    try:
        graph = build_supply_chain_graph(session)

        print("\n========== GRAPH SUMMARY ==========")

        print(f"Nodes: {graph.number_of_nodes()}")
        print(f"Edges: {graph.number_of_edges()}")

        print("\nNode types:")

        node_type_counts = {}

        for _, data in graph.nodes(data=True):
            node_type = data["node_type"]

            node_type_counts[node_type] = (
                node_type_counts.get(node_type, 0) + 1
            )

        for node_type, count in sorted(
            node_type_counts.items()
        ):
            print(f"{node_type}: {count}")

        print("\nSample nodes:")

        for node_id, data in list(
            graph.nodes(data=True)
        )[:5]:
            print(
                node_id,
                "->",
                data["name"]
            )

        print("\nSample edges:")

        for source, destination, data in list(
            graph.edges(data=True)
        )[:5]:

            print(
                f"{source} -> {destination} "
                f"| {data['route_code']} "
                f"| cost={data['transportation_cost']} "
                f"| days={data['delivery_time_days']}"
            )

        print("\n===================================")

    finally:
        session.close()


if __name__ == "__main__":
    test_graph()