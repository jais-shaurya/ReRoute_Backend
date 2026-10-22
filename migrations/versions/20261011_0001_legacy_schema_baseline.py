"""Mark the existing SQLAlchemy schema as the migration baseline.

Revision ID: 20261011_0001
Revises:
Create Date: 2026-10-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20261011_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the pre-tenancy schema for a fresh database."""
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Float(), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_suppliers_supplier_code",
        "suppliers",
        ["supplier_code"],
        unique=True,
    )

    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("warehouse_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("inventory", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_warehouses_warehouse_code",
        "warehouses",
        ["warehouse_code"],
        unique=True,
    )

    op.create_table(
        "factories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("factory_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_factories_factory_code",
        "factories",
        ["factory_code"],
        unique=True,
    )

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("demand", sa.Integer(), nullable=False),
        sa.Column("deadline_days", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_customers_customer_code",
        "customers",
        ["customer_code"],
        unique=True,
    )

    op.create_table(
        "routes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("route_code", sa.String(length=50), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("destination_type", sa.String(length=30), nullable=False),
        sa.Column("destination_id", sa.Integer(), nullable=False),
        sa.Column("transportation_cost", sa.Float(), nullable=False),
        sa.Column("delivery_time_days", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_routes_route_code",
        "routes",
        ["route_code"],
        unique=True,
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_code", sa.String(length=50), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("warehouse_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("deadline_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
    )
    op.create_index(
        "ix_orders_order_code",
        "orders",
        ["order_code"],
        unique=True,
    )


def downgrade() -> None:
    """The baseline has no safe downgrade target."""
    raise RuntimeError(
        "Downgrade to base is blocked to protect legacy business records."
    )