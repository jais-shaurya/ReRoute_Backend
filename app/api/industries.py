from math import isfinite

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.connection import get_db
from app.database.models import (
    IndustryProfile,
    IndustryParameterDefinition,
    Organization,
    OrganizationParameterValue,
    OrganizationSettings,
)
from app.schemas.industry import (
    IndustryParameterResponse,
    IndustryRuleResponse,
    IndustryTemplateResponse,
    OrganizationSettingsResponse,
    OrganizationSettingsUpdateRequest,
)
from app.security.auth import AuthPrincipal
from app.security.permissions import Permission, require_permission


router = APIRouter(prefix="/api", tags=["Industry configuration"])


def _typed_value(value: str, value_type: str):
    if value_type == "integer":
        return int(value)
    if value_type == "number":
        return float(value)
    if value_type == "boolean":
        return value.lower() == "true"
    return value


def _normalize_value(
    definition: IndustryParameterDefinition,
    value: bool | int | float | str,
):
    if definition.value_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"{definition.key} must be a boolean.")
        return "true" if value else "false"

    if definition.value_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{definition.key} must be an integer.")
        numeric_value = value
        normalized = str(value)
    elif definition.value_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"{definition.key} must be numeric.")
        numeric_value = float(value)
        if not isfinite(numeric_value):
            raise ValueError(f"{definition.key} must be finite.")
        normalized = str(numeric_value)
    else:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{definition.key} must be a non-empty string.")
        return value.strip()

    if definition.minimum is not None and numeric_value < definition.minimum:
        raise ValueError(f"{definition.key} is below its minimum value.")
    if definition.maximum is not None and numeric_value > definition.maximum:
        raise ValueError(f"{definition.key} exceeds its maximum value.")
    return normalized


def _template_response(profile: IndustryProfile) -> IndustryTemplateResponse:
    return IndustryTemplateResponse(
        code=profile.code,
        name=profile.name,
        version=profile.version,
        entity_types=sorted(
            definition.entity_type
            for definition in profile.entity_definitions
        ),
        disruptions=sorted(
            definition.code
            for definition in profile.disruption_definitions
            if definition.enabled
        ),
        parameters=[
            IndustryParameterResponse(
                key=definition.key,
                label=definition.label,
                value_type=definition.value_type,
                value=_typed_value(
                    definition.default_value,
                    definition.value_type,
                ),
                required=definition.required,
                minimum=definition.minimum,
                maximum=definition.maximum,
                unit=definition.unit,
            )
            for definition in sorted(
                profile.parameter_definitions,
                key=lambda item: item.key,
            )
        ],
        rules=[
            IndustryRuleResponse(
                code=rule.code,
                name=rule.name,
                description=rule.description,
                mandatory=rule.mandatory,
            )
            for rule in sorted(
                profile.rule_definitions,
                key=lambda item: item.code,
            )
        ],
    )


def _load_profiles(db: Session) -> list[IndustryProfile]:
    return list(
        db.scalars(
            select(IndustryProfile)
            .where(IndustryProfile.is_active.is_(True))
            .options(
                selectinload(IndustryProfile.parameter_definitions),
                selectinload(IndustryProfile.entity_definitions),
                selectinload(IndustryProfile.disruption_definitions),
                selectinload(IndustryProfile.rule_definitions),
            )
            .order_by(IndustryProfile.code, IndustryProfile.version.desc())
        ).all()
    )


def _load_profile(db: Session, profile_id: int) -> IndustryProfile | None:
    return db.scalar(
        select(IndustryProfile)
        .where(IndustryProfile.id == profile_id)
        .options(
            selectinload(IndustryProfile.parameter_definitions),
            selectinload(IndustryProfile.entity_definitions),
            selectinload(IndustryProfile.disruption_definitions),
            selectinload(IndustryProfile.rule_definitions),
        )
    )


def _settings_response(
    organization_id: int,
    settings: OrganizationSettings,
    profile: IndustryProfile,
) -> OrganizationSettingsResponse:
    template = _template_response(profile)
    stored_values = {item.key: item.value for item in settings.parameters}
    parameters = [
        parameter.model_copy(
            update={
                "value": _typed_value(
                    stored_values.get(parameter.key, definition.default_value),
                    definition.value_type,
                )
            }
        )
        for parameter, definition in zip(
            template.parameters,
            sorted(profile.parameter_definitions, key=lambda item: item.key),
        )
    ]
    template = template.model_copy(update={"parameters": parameters})
    return OrganizationSettingsResponse(
        organization_id=organization_id,
        configuration_version=settings.configuration_version,
        profile=template,
        weights={
            "cost": settings.cost_weight,
            "time": settings.time_weight,
            "risk": settings.risk_weight,
        },
        max_alternatives=settings.max_alternatives,
    )


def _require_organization(
    db: Session,
    organization_id: int,
    principal: AuthPrincipal,
) -> Organization:
    if principal.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )
    organization = db.get(Organization, organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )
    return organization


@router.get("/industries", response_model=list[IndustryTemplateResponse])
def list_industries(
    _: AuthPrincipal = Depends(require_permission(Permission.PLANNER_READ)),
    db: Session = Depends(get_db),
) -> list[IndustryTemplateResponse]:
    latest_by_code: dict[str, IndustryProfile] = {}
    for profile in _load_profiles(db):
        latest_by_code.setdefault(profile.code, profile)
    return [
        _template_response(profile)
        for profile in sorted(latest_by_code.values(), key=lambda item: item.name)
    ]


@router.get(
    "/organizations/{organization_id}/settings",
    response_model=OrganizationSettingsResponse,
)
def get_organization_settings(
    organization_id: int,
    principal: AuthPrincipal = Depends(
        require_permission(Permission.PLANNER_READ)
    ),
    db: Session = Depends(get_db),
) -> OrganizationSettingsResponse:
    _require_organization(db, organization_id, principal)
    settings = db.scalar(
        select(OrganizationSettings)
        .where(OrganizationSettings.organization_id == organization_id)
        .options(selectinload(OrganizationSettings.parameters))
    )
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization settings are not configured.",
        )
    profile = _load_profile(db, settings.profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The configured industry profile is unavailable.",
        )
    return _settings_response(organization_id, settings, profile)


@router.put(
    "/organizations/{organization_id}/settings",
    response_model=OrganizationSettingsResponse,
)
def update_organization_settings(
    organization_id: int,
    request: OrganizationSettingsUpdateRequest,
    principal: AuthPrincipal = Depends(
        require_permission(Permission.ORGANIZATION_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> OrganizationSettingsResponse:
    _require_organization(db, organization_id, principal)
    profile = db.scalar(
        select(IndustryProfile)
        .where(
            IndustryProfile.code == request.profile_code,
            IndustryProfile.is_active.is_(True),
        )
        .order_by(IndustryProfile.version.desc())
        .options(
            selectinload(IndustryProfile.parameter_definitions),
            selectinload(IndustryProfile.entity_definitions),
            selectinload(IndustryProfile.disruption_definitions),
            selectinload(IndustryProfile.rule_definitions),
        )
        .limit(1)
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unknown or inactive industry profile.",
        )

    definitions = {item.key: item for item in profile.parameter_definitions}
    unknown_parameters = set(request.parameters) - set(definitions)
    if unknown_parameters:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Unsupported industry parameter(s): "
                + ", ".join(sorted(unknown_parameters))
            ),
        )

    try:
        normalized_values = {
            key: _normalize_value(definitions[key], value)
            for key, value in request.parameters.items()
        }
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from None

    settings = db.scalar(
        select(OrganizationSettings)
        .where(OrganizationSettings.organization_id == organization_id)
        .options(selectinload(OrganizationSettings.parameters))
    )
    if settings is None:
        settings = OrganizationSettings(
            organization_id=organization_id,
            profile_id=profile.id,
        )
        db.add(settings)
        db.flush()
    elif settings.profile_id != profile.id:
        settings.profile_id = profile.id
        settings.configuration_version += 1
        settings.parameters.clear()
        db.flush()
    else:
        settings.configuration_version += 1

    if request.weights is not None:
        settings.cost_weight = request.weights.cost
        settings.time_weight = request.weights.time
        settings.risk_weight = request.weights.risk
    if request.max_alternatives is not None:
        settings.max_alternatives = request.max_alternatives

    existing_values = {item.key: item for item in settings.parameters}
    for key, value in normalized_values.items():
        stored = existing_values.get(key)
        if stored is None:
            db.add(
                OrganizationParameterValue(
                    settings_id=settings.id,
                    key=key,
                    value=value,
                )
            )
        else:
            stored.value = value

    db.commit()
    db.refresh(settings)
    settings = db.scalar(
        select(OrganizationSettings)
        .where(OrganizationSettings.id == settings.id)
        .options(selectinload(OrganizationSettings.parameters))
    )
    return _settings_response(organization_id, settings, profile)
