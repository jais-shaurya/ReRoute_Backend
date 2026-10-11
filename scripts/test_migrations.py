from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def test_upgrade_preserves_existing_data_and_adds_password_column(tmp_path):
    database_path = tmp_path / "legacy.sqlite3"
    engine = sa.create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "CREATE TABLE organizations ("
                "id INTEGER PRIMARY KEY, name VARCHAR(120) NOT NULL UNIQUE, "
                "slug VARCHAR(80) NOT NULL UNIQUE, created_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            sa.text(
                "CREATE TABLE app_users ("
                "id INTEGER PRIMARY KEY, email VARCHAR(160) NOT NULL UNIQUE, "
                "full_name VARCHAR(160) NOT NULL, role VARCHAR(40) NOT NULL, "
                "organization_id INTEGER NOT NULL, is_active BOOLEAN NOT NULL, "
                "created_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            sa.text(
                "CREATE TABLE suppliers ("
                "id INTEGER PRIMARY KEY, supplier_code VARCHAR(50) NOT NULL UNIQUE, "
                "name VARCHAR(150) NOT NULL, capacity INTEGER NOT NULL, "
                "unit_cost FLOAT NOT NULL, reliability FLOAT NOT NULL, available BOOLEAN NOT NULL)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO organizations (id, name, slug, created_at) "
                "VALUES (1, 'Legacy Org', 'legacy', CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO suppliers "
                "(id, supplier_code, name, capacity, unit_cost, reliability, available) "
                "VALUES (12, 'LEGACY-12', 'Legacy Supplier', 100, 2.5, 0.9, 1)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO app_users "
                "(id, email, full_name, role, organization_id, is_active, created_at) "
                "VALUES (7, 'legacy@example.test', 'Legacy Admin', 'admin', 1, 1, CURRENT_TIMESTAMP)"
            )
        )

    repository_root = Path(__file__).resolve().parents[1]
    config = Config(str(repository_root / "alembic.ini"))
    config.set_main_option("script_location", str(repository_root / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    command.upgrade(config, "head")

    inspector = sa.inspect(engine)
    assert "password_hash" in {column["name"] for column in inspector.get_columns("app_users")}
    with engine.connect() as connection:
        user = connection.execute(
            sa.text("SELECT id, email, role FROM app_users WHERE id = 7")
        ).one()
        assert tuple(user) == (7, "legacy@example.test", "admin")
        assert connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM organization_entity_access "
                "WHERE organization_id = 1 AND entity_type = 'supplier' AND entity_id = 12"
            )
        ).scalar_one() == 1
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == "20261011_0002"
    engine.dispose()