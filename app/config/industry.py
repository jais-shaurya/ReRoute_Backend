from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from app.ai.scoring import ScoringWeights


@dataclass(frozen=True)
class IndustryProfile:
    name: str
    default_weights: ScoringWeights
    max_demand_spike_percentage: float
    min_service_level: float
    mandatory_rules: tuple[str, ...]
    allowed_disruption_types: tuple[str, ...]


RETAIL_PROFILE = IndustryProfile(
    name="retail",
    default_weights=ScoringWeights(
        cost_weight=0.40,
        time_weight=0.35,
        risk_weight=0.25,
    ),
    max_demand_spike_percentage=35.0,
    min_service_level=0.90,
    mandatory_rules=(
        "supplier reliability must meet the profile minimum service level",
        "demand_spike_percentage cannot exceed the profile ceiling",
    ),
    allowed_disruption_types=("none", "supplier_failure", "demand_spike"),
)

MANUFACTURING_PROFILE = IndustryProfile(
    name="manufacturing",
    default_weights=ScoringWeights(
        cost_weight=0.30,
        time_weight=0.40,
        risk_weight=0.30,
    ),
    max_demand_spike_percentage=25.0,
    min_service_level=0.95,
    mandatory_rules=(
        "supplier reliability must meet the profile minimum service level",
        "demand_spike_percentage cannot exceed the profile ceiling",
    ),
    allowed_disruption_types=("none", "supplier_failure", "demand_spike"),
)

ECOMMERCE_PROFILE = IndustryProfile(
    name="ecommerce",
    default_weights=ScoringWeights(
        cost_weight=0.35,
        time_weight=0.30,
        risk_weight=0.35,
    ),
    max_demand_spike_percentage=45.0,
    min_service_level=0.85,
    mandatory_rules=(
        "supplier reliability must meet the profile minimum service level",
        "demand_spike_percentage cannot exceed the profile ceiling",
    ),
    allowed_disruption_types=("none", "supplier_failure", "demand_spike"),
)

HEALTHCARE_PROFILE = IndustryProfile(
    name="healthcare",
    default_weights=ScoringWeights(
        cost_weight=0.20,
        time_weight=0.30,
        risk_weight=0.50,
    ),
    max_demand_spike_percentage=15.0,
    min_service_level=0.98,
    mandatory_rules=(
        "supplier reliability must meet the profile minimum service level",
        "demand spikes above threshold are rejected as infeasible for the profile",
    ),
    allowed_disruption_types=("none", "supplier_failure", "demand_spike"),
)

INDUSTRY_PROFILES: dict[str, IndustryProfile] = {
    RETAIL_PROFILE.name: RETAIL_PROFILE,
    MANUFACTURING_PROFILE.name: MANUFACTURING_PROFILE,
    ECOMMERCE_PROFILE.name: ECOMMERCE_PROFILE,
    HEALTHCARE_PROFILE.name: HEALTHCARE_PROFILE,
}


def normalize_industry_name(value: str | None) -> str:
    if value is None:
        return RETAIL_PROFILE.name

    normalized = str(value).strip().lower()
    if not normalized:
        return RETAIL_PROFILE.name

    return normalized


def get_profile(name: str | IndustryProfile | None) -> IndustryProfile:
    if isinstance(name, IndustryProfile):
        return name

    profile_name = normalize_industry_name(name)
    profile = INDUSTRY_PROFILES.get(profile_name)

    if profile is None:
        supported = ", ".join(sorted(INDUSTRY_PROFILES))
        raise ValueError(
            f"Unknown industry '{name}'. Supported profiles: {supported}."
        )

    return profile


def validate_industry_configuration(
    name: str | IndustryProfile | None,
    demand_spike_percentage: float | None = None,
    weights: ScoringWeights | None = None,
    disruption_type: str | None = None,
) -> IndustryProfile:
    profile = get_profile(name)

    if demand_spike_percentage is not None:
        if not isfinite(float(demand_spike_percentage)) or demand_spike_percentage < 0:
            raise ValueError("Demand spike percentage must be finite and non-negative.")
        if demand_spike_percentage > profile.max_demand_spike_percentage:
            raise ValueError(
                f"Demand spike percentage {demand_spike_percentage}% exceeds the "
                f"{profile.name} profile maximum of "
                f"{profile.max_demand_spike_percentage}% for feasible planning."
            )

    if disruption_type is not None and disruption_type not in profile.allowed_disruption_types:
        raise ValueError(
            f"Disruption type '{disruption_type}' is not allowed for the "
            f"{profile.name} profile."
        )

    if weights is not None and not isinstance(weights, ScoringWeights):
        raise ValueError("weights must be a ScoringWeights instance.")

    return profile


def available_profiles() -> tuple[str, ...]:
    return tuple(sorted(INDUSTRY_PROFILES))
