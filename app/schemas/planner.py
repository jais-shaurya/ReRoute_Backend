from typing import Literal

from pydantic import BaseModel, Field, model_validator

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

    weights: ScoringWeightsRequest = Field(
        default_factory=lambda: ScoringWeightsRequest(
            cost=0.4,
            time=0.3,
            risk=0.3,
        )
    )

    max_alternatives: int = Field(
        default=3,
        ge=0,
        le=20,
    )

    @model_validator(mode="after")
    def validate_disruption_fields(self):
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
    route_failure_probability: float
    stockout_probability: float
    plan_risk: float


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