from typing import Union

from pydantic import BaseModel, Field, field_validator, model_validator


IndustryValue = Union[bool, int, float, str]


class ObjectiveWeightsRequest(BaseModel):
    cost: float = Field(ge=0, le=1)
    time: float = Field(ge=0, le=1)
    risk: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_sum(self):
        if abs(self.cost + self.time + self.risk - 1.0) > 1e-9:
            raise ValueError("Scoring weights must sum to 1.0.")
        return self


class OrganizationSettingsUpdateRequest(BaseModel):
    profile_code: str = Field(min_length=1, max_length=50)
    weights: ObjectiveWeightsRequest | None = None
    max_alternatives: int | None = Field(default=None, ge=0, le=20)
    parameters: dict[str, IndustryValue] = Field(default_factory=dict)

    @field_validator("profile_code")
    @classmethod
    def strip_profile_code(cls, value: str) -> str:
        return value.strip().lower()


class IndustryParameterResponse(BaseModel):
    key: str
    label: str
    value_type: str
    value: IndustryValue
    required: bool
    minimum: float | None
    maximum: float | None
    unit: str | None


class IndustryRuleResponse(BaseModel):
    code: str
    name: str
    description: str
    mandatory: bool


class IndustryTemplateResponse(BaseModel):
    code: str
    name: str
    version: int
    entity_types: list[str]
    disruptions: list[str]
    parameters: list[IndustryParameterResponse]
    rules: list[IndustryRuleResponse]


class OrganizationSettingsResponse(BaseModel):
    organization_id: int
    configuration_version: int
    profile: IndustryTemplateResponse
    weights: ObjectiveWeightsRequest
    max_alternatives: int
