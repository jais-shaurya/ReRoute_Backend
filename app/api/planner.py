from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.scoring import ScoringWeights
from app.database.connection import get_db
from app.schemas.planner import (
    PlannerRequest,
    PlannerResponse,
)
from app.services.planner import InfeasiblePlanningError, PlannerService
from app.services.planner_serializer import (
    serialize_planner_result,
)


router = APIRouter(
    prefix="/api/planner",
    tags=["Planner"],
)


@router.post(
    "/recommend",
    response_model=PlannerResponse,
)
def recommend_plan(
    request: PlannerRequest,
    db: Session = Depends(get_db),
):
    """
    Generate a disruption-aware recovery recommendation.
    """

    service = PlannerService(db)

    try:
        weights = None
        if request.weights is not None:
            weights = ScoringWeights(
                cost_weight=request.weights.cost,
                time_weight=request.weights.time,
                risk_weight=request.weights.risk,
            )

        result = service.recommend(
            customer_id=request.customer_id,
            quantity=request.quantity,
            disruption_type=(
                None
                if request.disruption_type == "none"
                else request.disruption_type
            ),
            supplier_id=request.supplier_id,
            disruption_customer_id=(
                request.disruption_customer_id
            ),
            demand_spike_percentage=(
                request.demand_spike_percentage
            ),
            weights=weights,
            max_alternatives=request.max_alternatives,
            industry=request.industry,
        )

        return serialize_planner_result(result)

    except InfeasiblePlanningError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    except ValueError as exc:
        message = str(exc)

        if (
            "does not exist" in message.lower()
            or "unavailable" in message.lower()
        ):
            raise HTTPException(
                status_code=404,
                detail=message,
            )

        if "No feasible recovery plans" in message:
            raise HTTPException(
                status_code=409,
                detail=message,
            )

        client_error_fragments = (
            "must be greater than zero",
            "cannot be negative",
            "is required",
            "Unknown industry",
            "Demand spike percentage",
            "Unsupported disruption",
        )
        if any(fragment.lower() in message.lower() for fragment in client_error_fragments):
            raise HTTPException(status_code=400, detail=message)

        raise HTTPException(
            status_code=500,
            detail="The planner encountered an internal error.",
        ) from exc