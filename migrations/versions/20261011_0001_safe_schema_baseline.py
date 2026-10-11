"""Create missing ReRoute tables without altering existing tables."""

from alembic import op

from app.database.connection import Base
from app.database import models  # noqa: F401

revision = "20261011_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    raise RuntimeError("This baseline migration is non-destructive and cannot be downgraded automatically.")