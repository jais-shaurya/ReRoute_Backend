import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.database.connection as database_connection
from app.database.models import IndustryProfile


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


def test_organization_migration_backfills_and_preserves_legacy_rows(
    tmp_path: Path,
    monkeypatch,
):
    database_path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database_path) as connection:
        for table_name in BUSINESS_TABLES:
            code_column = CODE_COLUMNS[table_name]
            connection.execute(
                f"CREATE TABLE {table_name} ("
                f"id INTEGER PRIMARY KEY, {code_column} VARCHAR(50) NOT NULL)"
            )
            connection.execute(
                f"CREATE UNIQUE INDEX ix_{table_name}_{code_column} "
                f"ON {table_name} ({code_column})"
            )
            connection.execute(
                f"INSERT INTO {table_name} (id, {code_column}) "
                "VALUES (7, 'legacy-code')"
            )

    monkeypatch.setattr(
        database_connection,
        "DATABASE_URL",
        "sqlite:///" + database_path.as_posix(),
    )
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option(
        "script_location",
        str(backend_root / "migrations"),
    )

    command.stamp(config, "20261011_0001")
    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        for table_name in BUSINESS_TABLES:
            assert connection.execute(
                f"SELECT organization_id FROM {table_name} WHERE id = 7"
            ).fetchone() == (1,)

    command.downgrade(config, "20261011_0001")

    engine = create_engine("sqlite:///" + database_path.as_posix())
    try:
        inspector = inspect(engine)
        for table_name in BUSINESS_TABLES:
            assert "organization_id" not in {
                column["name"]
                for column in inspector.get_columns(table_name)
            }
            with sqlite3.connect(database_path) as connection:
                assert connection.execute(
                    f"SELECT id FROM {table_name} WHERE id = 7"
                ).fetchone() == (7,)
    finally:
        engine.dispose()


def test_fresh_database_upgrades_to_current_schema_and_profiles(
    tmp_path: Path,
    monkeypatch,
):
    database_path = tmp_path / "fresh.sqlite3"
    monkeypatch.setattr(
        database_connection,
        "DATABASE_URL",
        "sqlite:///" + database_path.as_posix(),
    )
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option(
        "script_location",
        str(backend_root / "migrations"),
    )

    command.upgrade(config, "head")

    engine = create_engine("sqlite:///" + database_path.as_posix())
    try:
        inspector = inspect(engine)
        assert {
            "organizations",
            "organization_memberships",
            "auth_sessions",
            "organization_settings",
            "organization_parameter_values",
            "suppliers",
            "orders",
        }.issubset(set(inspector.get_table_names()))
        with Session(engine) as session:
            assert set(
                session.scalars(select(IndustryProfile.code)).all()
            ) == {
                "manufacturing",
                "retail_distribution",
                "food_distribution",
                "healthcare_logistics",
            }
    finally:
        engine.dispose()
