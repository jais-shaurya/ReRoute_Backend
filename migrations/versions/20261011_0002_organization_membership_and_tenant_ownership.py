"""Add organization membership and backfill existing business records.

Revision ID: 20261011_0002
Revises: 20261011_0001
Create Date: 2026-10-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261011_0002"
down_revision = "20261011_0001"
branch_labels = None
depends_on = None

BUSINESS_TABLES = (
    "suppliers",
    "factories",
    "warehouses",
    "customers",
    "routes",
    "orders",
)
CODE_COLUMNS = {
    "suppliers": "supplier_code",
    "factories": "factory_code",
    "warehouses": "warehouse_code",
    "customers": "customer_code",
    "routes": "route_code",
    "orders": "order_code",
}


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_memberships_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_organization_memberships_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_memberships_org_user",
        ),
        sa.CheckConstraint(
            "role IN ('organization_admin', 'operations_manager', 'analyst', 'viewer')",
            name="ck_organization_memberships_role",
        ),
    )
    op.create_index(
        "ix_organization_memberships_organization_id",
        "organization_memberships",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_memberships_user_id",
        "organization_memberships",
        ["user_id"],
    )

    bind = op.get_bind()
    inspector = inspect(bind)
    missing_tables = [
        table_name
        for table_name in BUSINESS_TABLES
        if not inspector.has_table(table_name)
    ]
    if missing_tables:
        raise RuntimeError(
            "The legacy schema is incomplete; expected tables: "
            + ", ".join(missing_tables)
        )

    organizations = sa.table(
        "organizations",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
    )
    op.execute(
        sa.insert(organizations).values(
            name="Legacy Organization",
            slug="legacy",
        )
    )
    legacy_organization_id = bind.execute(
        sa.select(organizations.c.id).where(
            organizations.c.slug == "legacy"
        )
    ).scalar_one()

    for table_name in BUSINESS_TABLES:
        op.add_column(
            table_name,
            sa.Column("organization_id", sa.Integer(), nullable=True),
        )
        table = sa.table(
            table_name,
            sa.column("organization_id", sa.Integer()),
        )
        op.execute(
            sa.update(table)
            .where(table.c.organization_id.is_(None))
            .values(organization_id=legacy_organization_id)
        )

        with op.batch_alter_table(table_name) as batch_op:
            code_column = CODE_COLUMNS[table_name]
            batch_op.drop_index(f"ix_{table_name}_{code_column}")
            batch_op.alter_column(
                "organization_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
            batch_op.create_foreign_key(
                f"fk_{table_name}_organization_id_organizations",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="RESTRICT",
            )
            batch_op.create_index(
                f"ix_{table_name}_organization_id",
                ["organization_id"],
            )
            batch_op.create_unique_constraint(
                f"uq_{table_name}_organization_code",
                ["organization_id", code_column],
            )


def downgrade() -> None:
    bind = op.get_bind()
    organizations = sa.table(
        "organizations",
        sa.column("id", sa.Integer()),
    )
    users = sa.table("users", sa.column("id", sa.Integer()))
    memberships = sa.table(
        "organization_memberships",
        sa.column("id", sa.Integer()),
    )

    organization_count = bind.execute(
        sa.select(sa.func.count()).select_from(organizations)
    ).scalar_one()
    user_count = bind.execute(
        sa.select(sa.func.count()).select_from(users)
    ).scalar_one()
    membership_count = bind.execute(
        sa.select(sa.func.count()).select_from(memberships)
    ).scalar_one()

    if organization_count != 1 or user_count or membership_count:
        raise RuntimeError(
            "Downgrade is blocked because organization or user data would "
            "be lost. Export and verify that data before planning a rollback."
        )

    for table_name, code_column in CODE_COLUMNS.items():
        table = sa.table(
            table_name,
            sa.column(code_column, sa.String()),
        )
        duplicate_code = bind.execute(
            sa.select(table.c[code_column])
            .group_by(table.c[code_column])
            .having(sa.func.count() > 1)
            .limit(1)
        ).first()
        if duplicate_code is not None:
            raise RuntimeError(
                f"Downgrade is blocked because {table_name} contains "
                "duplicate business codes across organizations."
            )

    for table_name in reversed(BUSINESS_TABLES):
        with op.batch_alter_table(table_name) as batch_op:
            code_column = CODE_COLUMNS[table_name]
            batch_op.drop_index(f"ix_{table_name}_organization_id")
            batch_op.drop_constraint(
                f"uq_{table_name}_organization_code",
                type_="unique",
            )
            batch_op.drop_constraint(
                f"fk_{table_name}_organization_id_organizations",
                type_="foreignkey",
            )
            batch_op.drop_column("organization_id")
            batch_op.create_index(
                f"ix_{table_name}_{code_column}",
                [code_column],
                unique=True,
            )

    op.drop_index(
        "ix_organization_memberships_user_id",
        table_name="organization_memberships",
    )
    op.drop_index(
        "ix_organization_memberships_organization_id",
        table_name="organization_memberships",
    )
    op.drop_table("organization_memberships")
    op.drop_table("users")
    op.drop_table("organizations")
