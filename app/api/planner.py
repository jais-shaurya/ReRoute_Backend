from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.scoring import ScoringWeights
from app.database.connection import get_db
from app.schemas.planner import (
    PlannerRequest,
    PlannerResponse,
)
from app.services.planner import PlannerService
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
        )

        return serialize_planner_result(result)

    except ValueError as exc:
        message = str(exc)

        if (
            "does not exist" in message
            or "unavailable" in message
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

        raise HTTPException(
            status_code=400,
            detail=message,
        )