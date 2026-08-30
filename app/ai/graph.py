import networkx as nx
from sqlalchemy.orm import Session

from app.database.models import (
    Customer,
    Factory,
    Route,
    Supplier,
    Warehouse,
)


def build_supply_chain_graph(session: Session) -> nx.DiGraph:
    """
    Build an in-memory directed graph from the PostgreSQL
    supply-chain data.

    Graph structure:

        Supplier -> Factory
        Factory  -> Warehouse
        Warehouse -> Customer
    """

    graph = nx.DiGraph()

    # -----------------------------------------------------
    # Load database entities
    # -----------------------------------------------------

    suppliers = session.query(Supplier).all()
    factories = session.query(Factory).all()
    warehouses = session.query(Warehouse).all()
    customers = session.query(Customer).all()
    routes = session.query(Route).all()

    # -----------------------------------------------------
    # Add Supplier nodes
    # -----------------------------------------------------

    for supplier in suppliers:
        node_id = f"supplier:{supplier.id}"

        graph.add_node(
            node_id,
            node_type="supplier",
            database_id=supplier.id,
            code=supplier.supplier_code,
            name=supplier.name,
            capacity=supplier.capacity,
            unit_cost=supplier.unit_cost,
            reliability=supplier.reliability,
            available=supplier.available,
        )

    # -----------------------------------------------------
    # Add Factory nodes
    # -----------------------------------------------------

    for factory in factories:
        node_id = f"factory:{factory.id}"

        graph.add_node(
            node_id,
            node_type="factory",
            database_id=factory.id,
            code=factory.factory_code,
            name=factory.name,
            capacity=factory.capacity,
            available=factory.available,
        )

    # -----------------------------------------------------
    # Add Warehouse nodes
    # -----------------------------------------------------

    for warehouse in warehouses:
        node_id = f"warehouse:{warehouse.id}"

        graph.add_node(
            node_id,
            node_type="warehouse",
            database_id=warehouse.id,
            code=warehouse.warehouse_code,
            name=warehouse.name,
            capacity=warehouse.capacity,
            inventory=warehouse.inventory,
        )

    # -----------------------------------------------------
    # Add Customer nodes
    # -----------------------------------------------------

    for customer in customers:
        node_id = f"customer:{customer.id}"

        graph.add_node(
            node_id,
            node_type="customer",
            database_id=customer.id,
            code=customer.customer_code,
            name=customer.name,
            demand=customer.demand,
            deadline_days=customer.deadline_days,
        )

    # -----------------------------------------------------
    # Add Route edges
    # -----------------------------------------------------

    for route in routes:

        source_node = (
            f"{route.source_type}:{route.source_id}"
        )

        destination_node = (
            f"{route.destination_type}:{route.destination_id}"
        )

        # Only create an edge if both nodes exist.
        if (
            source_node in graph
            and destination_node in graph
        ):
            graph.add_edge(
                source_node,
                destination_node,
                route_id=route.id,
                route_code=route.route_code,
                transportation_cost=route.transportation_cost,
                delivery_time_days=route.delivery_time_days,
                capacity=route.capacity,
                available=route.available,
            )

    return graph