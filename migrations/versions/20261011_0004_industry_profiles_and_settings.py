"""Add versioned industry profiles and organization settings.

Revision ID: 20261011_0004
Revises: 20261011_0003
Create Date: 2026-10-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20261011_0004"
down_revision = "20261011_0003"
branch_labels = None
depends_on = None

ENTITY_TYPES = ("supplier", "factory", "warehouse", "customer", "route", "order")
PROFILES = (
    {
        "code": "manufacturing",
        "name": "Manufacturing",
        "parameters": (
            ("production_capacity", "Production capacity", "integer", "0", True, 0, None, "units"),
            ("supplier_lead_time_days", "Supplier lead time", "integer", "1", True, 0, None, "days"),
            ("raw_material_available", "Raw materials available", "boolean", "true", True, None, None, None),
        ),
        "rules": (
            ("production_capacity", "Production capacity", "Planned production must not exceed available factory capacity."),
            ("raw_material_availability", "Raw material availability", "Required raw materials must be available before production."),
        ),
    },
    {
        "code": "retail_distribution",
        "name": "Retail and distribution",
        "parameters": (
            ("service_level_target", "Service-level target", "number", "0.95", True, 0, 1, "fraction"),
            ("replenishment_days", "Replenishment lead time", "integer", "2", True, 0, None, "days"),
            ("distribution_center_capacity", "Distribution-center capacity", "integer", "0", True, 0, None, "units"),
        ),
        "rules": (
            ("service_level", "Service level", "Configured service-level targets are preferences and do not disable feasibility constraints."),
            ("distribution_capacity", "Distribution capacity", "Distribution-center throughput must remain within configured capacity."),
        ),
    },
    {
        "code": "food_distribution",
        "name": "Food distribution",
        "parameters": (
            ("shelf_life_days", "Shelf life", "integer", "7", True, 1, None, "days"),
            ("cold_chain_required", "Cold chain required", "boolean", "false", True, None, None, None),
            ("delivery_window_hours", "Delivery window", "integer", "24", True, 1, None, "hours"),
        ),
        "rules": (
            ("shelf_life", "Shelf life", "Products must arrive before their configured shelf life expires."),
            ("cold_chain", "Cold chain", "Products marked cold-chain-required must use routes and storage that satisfy handling requirements."),
        ),
    },
    {
        "code": "healthcare_logistics",
        "name": "Healthcare logistics",
        "parameters": (
            ("criticality", "Default shipment criticality", "text", "standard", True, None, None, None),
            ("temperature_controlled", "Temperature controlled", "boolean", "false", True, None, None, None),
            ("delivery_window_hours", "Delivery window", "integer", "24", True, 1, None, "hours"),
            ("stockout_priority", "Stockout priority", "integer", "5", True, 1, 10, "scale 1-10"),
        ),
        "rules": (
            ("criticality_priority", "Criticality priority", "Higher-criticality demand must retain its configured delivery priority."),
            ("temperature_handling", "Temperature handling", "Temperature-controlled products require compatible routes and storage."),
        ),
    },
)


def upgrade() -> None:
    op.create_table(
        "industry_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.UniqueConstraint("code", "version", name="uq_industry_profiles_code_version"),
    )
    op.create_table(
        "industry_parameter_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("value_type", sa.String(length=20), nullable=False),
        sa.Column("default_value", sa.String(length=255), nullable=False),
        sa.Column("required", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("minimum", sa.Float(), nullable=True),
        sa.Column("maximum", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["industry_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_id", "key", name="uq_industry_parameter_profile_key"),
        sa.CheckConstraint("value_type IN ('integer', 'number', 'boolean', 'text')", name="ck_industry_parameter_value_type"),
    )
    op.create_index("ix_industry_parameter_definitions_profile_id", "industry_parameter_definitions", ["profile_id"])
    op.create_table(
        "industry_entity_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("required", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["industry_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_id", "entity_type", name="uq_industry_entity_profile_type"),
    )
    op.create_index("ix_industry_entity_definitions_profile_id", "industry_entity_definitions", ["profile_id"])
    op.create_table(
        "industry_disruption_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["industry_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_id", "code", name="uq_industry_disruption_profile_code"),
    )
    op.create_index("ix_industry_disruption_definitions_profile_id", "industry_disruption_definitions", ["profile_id"])
    op.create_table(
        "industry_rule_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("mandatory", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["industry_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_id", "code", name="uq_industry_rule_profile_code"),
    )
    op.create_index("ix_industry_rule_definitions_profile_id", "industry_rule_definitions", ["profile_id"])
    op.create_table(
        "organization_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("configuration_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("cost_weight", sa.Float(), server_default="0.4", nullable=False),
        sa.Column("time_weight", sa.Float(), server_default="0.3", nullable=False),
        sa.Column("risk_weight", sa.Float(), server_default="0.3", nullable=False),
        sa.Column("max_alternatives", sa.Integer(), server_default="3", nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["industry_profiles.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", name="uq_organization_settings_org"),
        sa.CheckConstraint("cost_weight >= 0 AND time_weight >= 0 AND risk_weight >= 0", name="ck_organization_settings_weights_nonnegative"),
        sa.CheckConstraint("abs(cost_weight + time_weight + risk_weight - 1.0) < 0.000000001", name="ck_organization_settings_weights_sum"),
        sa.CheckConstraint("max_alternatives BETWEEN 0 AND 20", name="ck_organization_settings_max_alternatives"),
    )
    op.create_index("ix_organization_settings_organization_id", "organization_settings", ["organization_id"])
    op.create_index("ix_organization_settings_profile_id", "organization_settings", ["profile_id"])
    op.create_table(
        "organization_parameter_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("settings_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["settings_id"], ["organization_settings.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("settings_id", "key", name="uq_organization_parameter_settings_key"),
    )
    op.create_index("ix_organization_parameter_values_settings_id", "organization_parameter_values", ["settings_id"])

    profiles = sa.table(
        "industry_profiles",
        sa.column("id", sa.Integer()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    parameters = sa.table(
        "industry_parameter_definitions",
        *[
            sa.column(name, type_)
            for name, type_ in (
                ("profile_id", sa.Integer()),
                ("key", sa.String()),
                ("label", sa.String()),
                ("value_type", sa.String()),
                ("default_value", sa.String()),
                ("required", sa.Boolean()),
                ("minimum", sa.Float()),
                ("maximum", sa.Float()),
                ("unit", sa.String()),
            )
        ],
    )
    entities = sa.table(
        "industry_entity_definitions",
        sa.column("profile_id", sa.Integer()),
        sa.column("entity_type", sa.String()),
        sa.column("required", sa.Boolean()),
    )
    disruptions = sa.table(
        "industry_disruption_definitions",
        sa.column("profile_id", sa.Integer()),
        sa.column("code", sa.String()),
        sa.column("label", sa.String()),
        sa.column("enabled", sa.Boolean()),
    )
    rules = sa.table(
        "industry_rule_definitions",
        sa.column("profile_id", sa.Integer()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("mandatory", sa.Boolean()),
    )
    settings = sa.table(
        "organization_settings",
        sa.column("organization_id", sa.Integer()),
        sa.column("profile_id", sa.Integer()),
    )
    bind = op.get_bind()
    for profile in PROFILES:
        op.execute(
            sa.insert(profiles).values(
                code=profile["code"],
                name=profile["name"],
                version=1,
                is_active=True,
            )
        )
        profile_id = bind.execute(
            sa.select(profiles.c.id).where(
                profiles.c.code == profile["code"],
                profiles.c.version == 1,
            )
        ).scalar_one()
        op.bulk_insert(
            parameters,
            [
                {
                    "profile_id": profile_id,
                    "key": key,
                    "label": label,
                    "value_type": value_type,
                    "default_value": default,
                    "required": required,
                    "minimum": minimum,
                    "maximum": maximum,
                    "unit": unit,
                }
                for key, label, value_type, default, required, minimum, maximum, unit
                in profile["parameters"]
            ],
        )
        op.bulk_insert(
            entities,
            [
                {"profile_id": profile_id, "entity_type": entity, "required": True}
                for entity in ENTITY_TYPES
            ],
        )
        op.bulk_insert(
            disruptions,
            [
                {"profile_id": profile_id, "code": code, "label": label, "enabled": True}
                for code, label in (
                    ("supplier_failure", "Supplier failure"),
                    ("demand_spike", "Demand spike"),
                )
            ],
        )
        op.bulk_insert(
            rules,
            [
                {
                    "profile_id": profile_id,
                    "code": code,
                    "name": name,
                    "description": description,
                    "mandatory": True,
                }
                for code, name, description in profile["rules"]
            ],
        )

    manufacturing_id = bind.execute(
        sa.select(profiles.c.id).where(
            profiles.c.code == "manufacturing",
            profiles.c.version == 1,
        )
    ).scalar_one()
    organization_table = sa.table(
        "organizations",
        sa.column("id", sa.Integer()),
    )
    op.bulk_insert(
        settings,
        [
            {"organization_id": row.id, "profile_id": manufacturing_id}
            for row in bind.execute(sa.select(organization_table.c.id))
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_organization_parameter_values_settings_id", table_name="organization_parameter_values")
    op.drop_table("organization_parameter_values")
    op.drop_index("ix_organization_settings_profile_id", table_name="organization_settings")
    op.drop_index("ix_organization_settings_organization_id", table_name="organization_settings")
    op.drop_table("organization_settings")
    op.drop_index("ix_industry_rule_definitions_profile_id", table_name="industry_rule_definitions")
    op.drop_table("industry_rule_definitions")
    op.drop_index("ix_industry_disruption_definitions_profile_id", table_name="industry_disruption_definitions")
    op.drop_table("industry_disruption_definitions")
    op.drop_index("ix_industry_entity_definitions_profile_id", table_name="industry_entity_definitions")
    op.drop_table("industry_entity_definitions")
    op.drop_index("ix_industry_parameter_definitions_profile_id", table_name="industry_parameter_definitions")
    op.drop_table("industry_parameter_definitions")
    op.drop_table("industry_profiles")
