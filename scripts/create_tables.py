from app.database.connection import Base, engine
from app.database.models import (
    Supplier,
    Warehouse,
    Factory,
    Customer,
    Route,
    Order,
)


def create_tables():
    print("Creating database tables...")

    Base.metadata.create_all(bind=engine)

    print("Database tables created successfully!")


if __name__ == "__main__":
    create_tables()