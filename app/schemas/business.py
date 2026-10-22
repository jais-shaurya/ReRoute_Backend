from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OrganizationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    slug: str = Field(..., min_length=2, max_length=80)


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str


class UserCreateRequest(BaseModel):
    email: str = Field(..., min_length=3)
    full_name: str = Field(..., min_length=2)
    password: str = Field(..., min_length=12, max_length=256)
    role: Literal["planner", "analyst", "reader"] = "planner"


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    organization_id: int
    is_active: bool


class SupplierCreateRequest(BaseModel):
    supplier_code: str = Field(..., min_length=2)
    name: str = Field(..., min_length=2)
    capacity: int = Field(..., gt=0)
    unit_cost: float = Field(..., ge=0)
    reliability: float = Field(..., ge=0, le=1)
    available: bool = True


class SupplierUpdateRequest(SupplierCreateRequest):
    pass


class SupplierResponse(SupplierCreateRequest):
    id: int


class WarehouseCreateRequest(BaseModel):
    warehouse_code: str = Field(..., min_length=2)
    name: str = Field(..., min_length=2)
    capacity: int = Field(..., gt=0)
    inventory: int = Field(..., ge=0)


class WarehouseUpdateRequest(WarehouseCreateRequest):
    pass


class WarehouseResponse(WarehouseCreateRequest):
    id: int


class FactoryCreateRequest(BaseModel):
    factory_code: str = Field(..., min_length=2)
    name: str = Field(..., min_length=2)
    capacity: int = Field(..., gt=0)
    available: bool = True


class FactoryUpdateRequest(FactoryCreateRequest):
    pass


class FactoryResponse(FactoryCreateRequest):
    id: int


class CustomerCreateRequest(BaseModel):
    customer_code: str = Field(..., min_length=2)
    name: str = Field(..., min_length=2)
    demand: int = Field(..., gt=0)
    deadline_days: int = Field(..., gt=0)


class CustomerUpdateRequest(CustomerCreateRequest):
    pass


class CustomerResponse(CustomerCreateRequest):
    id: int


class RouteCreateRequest(BaseModel):
    route_code: str = Field(..., min_length=2)
    source_type: Literal["supplier", "factory", "warehouse"]
    source_id: int = Field(..., gt=0)
    destination_type: Literal["factory", "warehouse", "customer"]
    destination_id: int = Field(..., gt=0)
    transportation_cost: float = Field(..., ge=0)
    delivery_time_days: int = Field(..., gt=0)
    capacity: int = Field(..., gt=0)
    available: bool = True


class RouteUpdateRequest(RouteCreateRequest):
    pass


class RouteResponse(RouteCreateRequest):
    id: int


class ScenarioCreateRequest(BaseModel):
    name: str = Field(..., min_length=2)
    scenario_type: Literal["none", "supplier_failure", "demand_spike", "simultaneous"]
    customer_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    supplier_id: int | None = Field(default=None, gt=0)
    route_ids: list[int] = Field(default_factory=list)
    simultaneous_route_ids: list[int] = Field(default_factory=list)
    demand_spike_percentage: float | None = Field(default=None, gt=0)
    notes: str | None = None


class ScenarioResponse(BaseModel):
    id: int
    organization_id: int
    created_by_id: int
    name: str
    scenario_type: str
    customer_id: int
    quantity: int
    supplier_id: int | None = None
    route_ids: list[int] = Field(default_factory=list)
    simultaneous_route_ids: list[int] = Field(default_factory=list)
    demand_spike_percentage: float | None = None
    notes: str | None = None
    created_at: str


class PlanningRunResponse(BaseModel):
    id: int
    organization_id: int
    created_by_id: int
    scenario_id: int | None = None
    status: str
    requested_customer_id: int
    requested_quantity: int
    disruption_type: str
    supplier_id: int | None = None
    demand_spike_percentage: float | None = None
    recommendation: str | None = None
    explanation: str | None = None
    result_payload: dict | None = None
    created_at: str


class RecommendationComparisonResponse(BaseModel):
    selected_plan: dict
    alternatives: list[dict]
    explanation: str
    actions: list[dict]


class RiskExplanationResponse(BaseModel):
    explanation: str
    risk_summary: dict
    feasibility: dict
