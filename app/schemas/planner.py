from typing import Literal
from math import isfinite

from pydantic import AliasChoices, BaseModel, Field, model_validator

from app.config.industry import get_profile

# ============================================================
# Disruption Requests
# ============================================================

class SupplierFailureRequest(BaseModel):
    type: Literal["supplier_failure"]
    supplier_id: int = Field(gt=0)


class DemandSpikeRequest(BaseModel):
    type: Literal["demand_spike"]
    customer_id: int = Field(gt=0)
    percentage: float = Field(gt=0)


# ============================================================
# Scoring Weights
# ============================================================

class ScoringWeightsRequest(BaseModel):
    cost: float = Field(ge=0)
    time: float = Field(ge=0)
    risk: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_sum(self):
        if not all(isfinite(value) for value in (self.cost, self.time, self.risk)):
            raise ValueError("Scoring weights must be finite.")
        total = self.cost + self.time + self.risk

        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                "Scoring weights must sum to 1.0."
            )

        return self


# ============================================================
# Planner Request
# ============================================================

class PlannerRequest(BaseModel):
    customer_id: int = Field(gt=0)
    quantity: int = Field(gt=0)

    industry: str = Field(
        default="retail",
        validation_alias=AliasChoices(
            "industry",
            "industry_profile",
        ),
    )

    disruption_type: Literal[
        "none",
        "supplier_failure",
        "demand_spike",
    ] = "none"

    supplier_id: int | None = Field(
        default=None,
        gt=0,
    )

    disruption_customer_id: int | None = Field(
        default=None,
        gt=0,
    )

    demand_spike_percentage: float | None = Field(
        default=None,
        gt=0,
    )

    weights: ScoringWeightsRequest | None = None

    max_alternatives: int = Field(
        default=3,
        ge=0,
        le=20,
    )

    @model_validator(mode="after")
    def validate_industry_and_disruption_fields(self):
        profile = get_profile(self.industry)

        if self.disruption_type == "supplier_failure":
            if self.supplier_id is None:
                raise ValueError(
                    "supplier_id is required for "
                    "supplier_failure."
                )

        if self.disruption_type == "demand_spike":
            if self.demand_spike_percentage is None:
                raise ValueError(
                    "demand_spike_percentage is required "
                    "for demand_spike."
                )

            if self.demand_spike_percentage > profile.max_demand_spike_percentage:
                raise ValueError(
                    f"Demand spike percentage {self.demand_spike_percentage}% exceeds the "
                    f"{profile.name} profile maximum of "
                    f"{profile.max_demand_spike_percentage}% for feasible planning."
                )

        if self.disruption_type not in profile.allowed_disruption_types:
            raise ValueError(
                f"Disruption type '{self.disruption_type}' is not allowed for "
                f"the {profile.name} profile."
            )

        if self.weights is None:
            profile_weights = profile.default_weights
            self.weights = ScoringWeightsRequest(
                cost=profile_weights.cost_weight,
                time=profile_weights.time_weight,
                risk=profile_weights.risk_weight,
            )

        return self


# ============================================================
# Candidate Plan Response
# ============================================================

class CandidatePlanResponse(BaseModel):
    supplier_id: int
    customer_id: int
    quantity: int

    path: list[str]

    total_cost: float
    total_days: int

    factory_id: int | None = None
    warehouse_id: int | None = None


# ============================================================
# Risk Response
# ============================================================

class RiskResponse(BaseModel):
    supplier_failure_probability: float
    route_failure_probability: float | None
    stockout_probability: float | None
    plan_risk: float
    risk_is_partial: bool
    missing_evidence: list[str]


# ============================================================
# Scored Plan Response
# ============================================================

class ScoredPlanResponse(BaseModel):
    plan: CandidatePlanResponse
    risk: RiskResponse

    normalized_cost: float
    normalized_time: float
    normalized_risk: float

    overall_score: float
    rank: int
    cost_weight: float
    time_weight: float
    risk_weight: float


# ============================================================
# Recommendation Action Response
# ============================================================

class RecommendationActionResponse(BaseModel):
    name: str
    description: str
    preconditions: list[str]
    effects: list[str]


# ============================================================
# Scenario Response
# ============================================================

class ScenarioResponse(BaseModel):
    type: str

    customer_id: int
    quantity: int

    supplier_id: int | None = None
    percentage: float | None = None


# ============================================================
# Complete Planner Response
# ============================================================

class PlannerResponse(BaseModel):
    recommended_plan: ScoredPlanResponse

    alternatives: list[ScoredPlanResponse]

    explanation: str

    actions: list[RecommendationActionResponse]

    scenario: ScenarioResponse

    candidate_plans: list[ScoredPlanResponse]
    rejected_candidates: list["CandidateRejectionResponse"] = Field(default_factory=list)


class CandidateRejectionResponse(BaseModel):
    supplier_id: int
    path: list[str]
    reasons: list[str]