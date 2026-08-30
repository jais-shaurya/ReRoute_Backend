import math
import random

from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.database.models import (
    Customer,
    Factory,
    Order,
    Route,
    Supplier,
    Warehouse,
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

RANDOM_SEED = 42

NUM_SUPPLIERS = 10
NUM_FACTORIES = 2
NUM_WAREHOUSES = 4
NUM_CUSTOMERS = 8
NUM_ORDERS = 20

TARGET_ROUTES = 40


# ---------------------------------------------------------
# Random generator
# ---------------------------------------------------------

random.seed(RANDOM_SEED)


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


# ---------------------------------------------------------
# Clear existing development data
# ---------------------------------------------------------

def clear_existing_data(session: Session):
    print("Clearing existing development data...")

    session.query(Order).delete()
    session.query(Route).delete()
    session.query(Customer).delete()
    session.query(Warehouse).delete()
    session.query(Factory).delete()
    session.query(Supplier).delete()

    session.commit()

    print("Existing data cleared.")


# ---------------------------------------------------------
# Suppliers
# ---------------------------------------------------------

def create_suppliers(session: Session):
    suppliers = []

    for i in range(1, NUM_SUPPLIERS + 1):

        # Capacity roughly follows the project specification:
        # mean around 80 with variation.
        capacity = int(
            clamp(
                random.gauss(80, 20),
                40,
                130,
            )
        )

        # Unit cost varies realistically.
        unit_cost = round(
            random.uniform(8.0, 12.0),
            2,
        )

        # Most suppliers are reliable, but not perfect.
        reliability = round(
            random.uniform(0.85, 0.98),
            3,
        )

        supplier = Supplier(
            supplier_code=f"SUP-{i:03d}",
            name=f"Supplier {i}",
            capacity=capacity,
            unit_cost=unit_cost,
            reliability=reliability,
            available=True,
        )

        suppliers.append(supplier)

    session.add_all(suppliers)
    session.flush()

    print(f"Created {len(suppliers)} suppliers.")

    return suppliers


# ---------------------------------------------------------
# Factories
# ---------------------------------------------------------

def create_factories(session: Session):
    factories = []

    for i in range(1, NUM_FACTORIES + 1):

        capacity = int(
            clamp(
                random.gauss(180, 30),
                120,
                250,
            )
        )

        factory = Factory(
            factory_code=f"FAC-{i:03d}",
            name=f"Factory {i}",
            capacity=capacity,
            available=True,
        )

        factories.append(factory)

    session.add_all(factories)
    session.flush()

    print(f"Created {len(factories)} factories.")

    return factories


# ---------------------------------------------------------
# Warehouses
# ---------------------------------------------------------

def create_warehouses(session: Session):
    warehouses = []

    for i in range(1, NUM_WAREHOUSES + 1):

        # Warehouse capacity
        capacity = random.randint(180, 300)

        # Inventory is correlated with capacity.
        inventory_ratio = random.uniform(0.35, 0.75)

        inventory = int(
            capacity * inventory_ratio
        )

        warehouse = Warehouse(
            warehouse_code=f"WH-{i:03d}",
            name=f"Warehouse {i}",
            capacity=capacity,
            inventory=inventory,
        )

        warehouses.append(warehouse)

    session.add_all(warehouses)
    session.flush()

    print(f"Created {len(warehouses)} warehouses.")

    return warehouses


# ---------------------------------------------------------
# Customers
# ---------------------------------------------------------

def create_customers(session: Session):
    customers = []

    for i in range(1, NUM_CUSTOMERS + 1):

        demand = random.randint(15, 45)

        deadline_days = random.randint(2, 7)

        customer = Customer(
            customer_code=f"CUS-{i:03d}",
            name=f"Customer {i}",
            demand=demand,
            deadline_days=deadline_days,
        )

        customers.append(customer)

    session.add_all(customers)
    session.flush()

    print(f"Created {len(customers)} customers.")

    return customers


# ---------------------------------------------------------
# Route helper
# ---------------------------------------------------------

def calculate_distance(x1, y1, x2, y2):
    return math.sqrt(
        (x2 - x1) ** 2 +
        (y2 - y1) ** 2
    )


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

def create_routes(
    session: Session,
    suppliers,
    factories,
    warehouses,
    customers,
):
    routes = []

    # Give every node a synthetic position.
    positions = {}

    for supplier in suppliers:
        positions[("supplier", supplier.id)] = (
            random.uniform(0, 100),
            random.uniform(0, 100),
        )

    for factory in factories:
        positions[("factory", factory.id)] = (
            random.uniform(25, 75),
            random.uniform(25, 75),
        )

    for warehouse in warehouses:
        positions[("warehouse", warehouse.id)] = (
            random.uniform(25, 75),
            random.uniform(25, 75),
        )

    for customer in customers:
        positions[("customer", customer.id)] = (
            random.uniform(0, 100),
            random.uniform(0, 100),
        )

    # -----------------------------------------------------
    # Build the core supply-chain structure:
    #
    # Supplier -> Factory
    # Factory -> Warehouse
    # Warehouse -> Customer
    # -----------------------------------------------------

    route_candidates = []

    # Supplier -> Factory
    for supplier in suppliers:
        for factory in factories:

            route_candidates.append(
                (
                    "supplier",
                    supplier.id,
                    "factory",
                    factory.id,
                )
            )

    # Factory -> Warehouse
    for factory in factories:
        for warehouse in warehouses:

            route_candidates.append(
                (
                    "factory",
                    factory.id,
                    "warehouse",
                    warehouse.id,
                )
            )

    # Warehouse -> Customer
    for warehouse in warehouses:
        for customer in customers:

            route_candidates.append(
                (
                    "warehouse",
                    warehouse.id,
                    "customer",
                    customer.id,
                )
            )

    # We have more possible routes than required.
    # Randomly select approximately 40.
    random.shuffle(route_candidates)

    selected_routes = route_candidates[:TARGET_ROUTES]

    # Make sure every customer has at least one incoming route.
    selected_set = set(selected_routes)

    for customer in customers:

        has_route = any(
            destination_type == "customer"
            and destination_id == customer.id
            for (
                source_type,
                source_id,
                destination_type,
                destination_id,
            ) in selected_set
        )

        if not has_route:

            warehouse = random.choice(warehouses)

            candidate = (
                "warehouse",
                warehouse.id,
                "customer",
                customer.id,
            )

            selected_set.add(candidate)

    # Create database routes.
    for index, (
        source_type,
        source_id,
        destination_type,
        destination_id,
    ) in enumerate(selected_set, start=1):

        source_position = positions[
            (source_type, source_id)
        ]

        destination_position = positions[
            (destination_type, destination_id)
        ]

        distance = calculate_distance(
            source_position[0],
            source_position[1],
            destination_position[0],
            destination_position[1],
        )

        # Transportation cost increases with distance.
        transportation_cost = round(
            20 + (distance * 1.5) + random.uniform(5, 20),
            2,
        )

        # Delivery time also increases with distance.
        delivery_time_days = max(
            1,
            int(
                math.ceil(
                    distance / 30
                )
            ),
        )

        # Add realistic variation.
        delivery_time_days += random.choice(
            [0, 0, 0, 1]
        )

        capacity = random.randint(
            40,
            140,
        )

        route = Route(
            route_code=f"ROUTE-{index:03d}",
            source_type=source_type,
            source_id=source_id,
            destination_type=destination_type,
            destination_id=destination_id,
            transportation_cost=transportation_cost,
            delivery_time_days=delivery_time_days,
            capacity=capacity,
            available=True,
        )

        routes.append(route)

    session.add_all(routes)
    session.flush()

    print(f"Created {len(routes)} routes.")

    return routes


# ---------------------------------------------------------
# Orders
# ---------------------------------------------------------

def create_orders(
    session: Session,
    suppliers,
    warehouses,
    customers,
):
    orders = []

    for i in range(1, NUM_ORDERS + 1):

        customer = random.choice(customers)

        quantity = random.randint(
            10,
            max(10, customer.demand),
        )

        # Assign supplier/warehouse initially.
        supplier = random.choice(suppliers)
        warehouse = random.choice(warehouses)

        order = Order(
            order_code=f"ORD-{i:03d}",
            customer_id=customer.id,
            supplier_id=supplier.id,
            warehouse_id=warehouse.id,
            quantity=quantity,
            deadline_days=customer.deadline_days,
            status="pending",
        )

        orders.append(order)

    session.add_all(orders)
    session.flush()

    print(f"Created {len(orders)} orders.")

    return orders


# ---------------------------------------------------------
# Data validation
# ---------------------------------------------------------

def validate_data(
    session: Session,
    suppliers,
    factories,
    warehouses,
    customers,
    routes,
    orders,
):

    print("\nValidating generated data...")

    assert len(suppliers) == NUM_SUPPLIERS
    assert len(factories) == NUM_FACTORIES
    assert len(warehouses) == NUM_WAREHOUSES
    assert len(customers) == NUM_CUSTOMERS
    assert len(orders) == NUM_ORDERS

    # Supplier validation
    for supplier in suppliers:
        assert supplier.capacity > 0
        assert supplier.unit_cost > 0
        assert 0 <= supplier.reliability <= 1

    # Warehouse validation
    for warehouse in warehouses:
        assert warehouse.capacity > 0
        assert 0 <= warehouse.inventory <= warehouse.capacity

    # Factory validation
    for factory in factories:
        assert factory.capacity > 0

    # Customer validation
    for customer in customers:
        assert customer.demand > 0
        assert customer.deadline_days > 0

    # Route validation
    valid_source_types = {
        "supplier",
        "factory",
        "warehouse",
    }

    valid_destination_types = {
        "factory",
        "warehouse",
        "customer",
    }

    for route in routes:

        assert route.source_type in valid_source_types
        assert route.destination_type in valid_destination_types

        assert route.transportation_cost > 0
        assert route.delivery_time_days > 0
        assert route.capacity > 0

    # Order validation
    for order in orders:
        assert order.quantity > 0
        assert order.deadline_days > 0
        assert order.status == "pending"

    print("All validation checks passed!")


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

def print_summary(session: Session):

    print("\n========== DATABASE SUMMARY ==========")

    print(
        f"Suppliers:  {session.query(Supplier).count()}"
    )

    print(
        f"Factories:  {session.query(Factory).count()}"
    )

    print(
        f"Warehouses: {session.query(Warehouse).count()}"
    )

    print(
        f"Customers:  {session.query(Customer).count()}"
    )

    print(
        f"Routes:     {session.query(Route).count()}"
    )

    print(
        f"Orders:     {session.query(Order).count()}"
    )

    print("======================================\n")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def seed_database():

    session = SessionLocal()

    try:

        clear_existing_data(session)

        suppliers = create_suppliers(session)

        factories = create_factories(session)

        warehouses = create_warehouses(session)

        customers = create_customers(session)

        routes = create_routes(
            session,
            suppliers,
            factories,
            warehouses,
            customers,
        )

        orders = create_orders(
            session,
            suppliers,
            warehouses,
            customers,
        )

        validate_data(
            session,
            suppliers,
            factories,
            warehouses,
            customers,
            routes,
            orders,
        )

        session.commit()

        print_summary(session)

        print("Synthetic database seeding completed successfully!")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    seed_database()