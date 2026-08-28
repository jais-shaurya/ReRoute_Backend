from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    reliability: Mapped[float] = mapped_column(Float, nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    orders: Mapped[list["Order"]] = relationship(
        back_populates="supplier"
    )


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    warehouse_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    inventory: Mapped[int] = mapped_column(Integer, nullable=False)

    orders: Mapped[list["Order"]] = relationship(
        back_populates="warehouse"
    )


class Factory(Base):
    __tablename__ = "factories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    factory_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    demand: Mapped[int] = mapped_column(Integer, nullable=False)
    deadline_days: Mapped[int] = mapped_column(Integer, nullable=False)

    orders: Mapped[list["Order"]] = relationship(
        back_populates="customer"
    )


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    route_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    source_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    destination_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    destination_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    transportation_cost: Mapped[float] = mapped_column(
        Float, nullable=False
    )

    delivery_time_days: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    capacity: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    available: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    order_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id"),
        nullable=True
    )

    warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=True
    )

    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    deadline_days: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="orders"
    )

    supplier: Mapped["Supplier | None"] = relationship(
        back_populates="orders"
    )

    warehouse: Mapped["Warehouse | None"] = relationship(
        back_populates="orders"
    )