from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.ai.graph import build_supply_chain_graph
from app.database.connection import Base
from app.database.models import Customer, Organization, Route, Supplier


def test_graph_includes_only_selected_organization():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            first = Organization(name="First", slug="first")
            second = Organization(name="Second", slug="second")
            session.add_all([first, second])
            session.flush()

            first_supplier = Supplier(
                organization_id=first.id,
                supplier_code="SUP-A",
                name="First supplier",
                capacity=100,
                unit_cost=10.0,
                reliability=0.95,
                available=True,
            )
            first_customer = Customer(
                organization_id=first.id,
                customer_code="CUS-A",
                name="First customer",
                demand=10,
                deadline_days=5,
            )
            second_supplier = Supplier(
                organization_id=second.id,
                supplier_code="SUP-B",
                name="Second supplier",
                capacity=100,
                unit_cost=10.0,
                reliability=0.95,
                available=True,
            )
            second_customer = Customer(
                organization_id=second.id,
                customer_code="CUS-B",
                name="Second customer",
                demand=10,
                deadline_days=5,
            )
            session.add_all(
                [
                    first_supplier,
                    first_customer,
                    second_supplier,
                    second_customer,
                ]
            )
            session.flush()
            session.add_all(
                [
                    Route(
                        organization_id=first.id,
                        route_code="ROUTE-A",
                        source_type="supplier",
                        source_id=first_supplier.id,
                        destination_type="customer",
                        destination_id=first_customer.id,
                        transportation_cost=5.0,
                        delivery_time_days=2,
                        capacity=100,
                        available=True,
                    ),
                    Route(
                        organization_id=second.id,
                        route_code="ROUTE-B",
                        source_type="supplier",
                        source_id=second_supplier.id,
                        destination_type="customer",
                        destination_id=second_customer.id,
                        transportation_cost=5.0,
                        delivery_time_days=2,
                        capacity=100,
                        available=True,
                    ),
                ]
            )
            session.commit()

            graph = build_supply_chain_graph(session, first.id)

            assert set(graph.nodes) == {"supplier:1", "customer:1"}
            assert graph.number_of_edges() == 1
    finally:
        engine.dispose()
