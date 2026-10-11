"""Add nullable password hashes and assign legacy data when ownership is unambiguous."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261011_0002"
down_revision = "20261011_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    app_user_columns = {column["name"] for column in inspector.get_columns("app_users")}
    if "password_hash" not in app_user_columns:
        op.add_column("app_users", sa.Column("password_hash", sa.String(length=255), nullable=True))

    organizations = bind.execute(sa.text("SELECT id FROM organizations ORDER BY id")).scalars().all()
    if len(organizations) != 1:
        return

    organization_id = organizations[0]
    entity_tables = (
        ("suppliers", "supplier"),
        ("customers", "customer"),
        ("warehouses", "warehouse"),
        ("factories", "factory"),
        ("routes", "route"),
    )
    for table, entity_type in entity_tables:
        bind.execute(
            sa.text(
                "INSERT INTO organization_entity_access "
                "(organization_id, entity_type, entity_id) "
                "SELECT :organization_id, :entity_type, entity.id "
                f"FROM {table} AS entity "
                "WHERE NOT EXISTS (SELECT 1 FROM organization_entity_access AS access "
                "WHERE access.organization_id = :organization_id "
                "AND access.entity_type = :entity_type AND access.entity_id = entity.id)"
            ),
            {"organization_id": organization_id, "entity_type": entity_type},
        )


def downgrade() -> None:
    raise RuntimeError("Password hashes and tenant ownership are retained; downgrade would risk data loss.")