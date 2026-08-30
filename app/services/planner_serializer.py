from app.schemas.planner import (
    CandidatePlanResponse,
    PlannerResponse,
    RecommendationActionResponse,
    RiskResponse,
    ScenarioResponse,
    ScoredPlanResponse,
)
from app.services.planner import PlannerResult


def serialize_scored_plan(
    scored_plan,
) -> ScoredPlanResponse:
    plan = scored_plan.plan
    risk = scored_plan.risk

    return ScoredPlanResponse(
        plan=CandidatePlanResponse(
            supplier_id=plan.supplier_id,
            customer_id=plan.customer_id,
            quantity=plan.quantity,
            path=list(plan.path),
            total_cost=plan.total_cost,
            total_days=plan.total_days,
            factory_id=plan.factory_id,
            warehouse_id=plan.warehouse_id,
        ),
        risk=RiskResponse(
            supplier_failure_probability=(
                risk.supplier_failure_probability
            ),
            route_failure_probability=(
                risk.route_failure_probability
            ),
            stockout_probability=(
                risk.stockout_probability
            ),
            plan_risk=risk.plan_risk,
        ),
        normalized_cost=scored_plan.normalized_cost,
        normalized_time=scored_plan.normalized_time,
        normalized_risk=scored_plan.normalized_risk,
        overall_score=scored_plan.overall_score,
        rank=scored_plan.rank,
    )


def serialize_action(
    action,
) -> RecommendationActionResponse:
    return RecommendationActionResponse(
        name=action.name,
        description=action.description,
        preconditions=list(action.preconditions),
        effects=list(action.effects),
    )


def serialize_planner_result(
    result: PlannerResult,
) -> PlannerResponse:

    recommendation = result.recommendation

    recommended_plan = serialize_scored_plan(
        recommendation.selected_plan
    )

    alternatives = [
        serialize_scored_plan(plan)
        for plan in recommendation.alternatives
    ]

    actions = [
        serialize_action(action)
        for action in recommendation.actions
    ]

    candidate_plans = [
        serialize_scored_plan(plan)
        for plan in result.candidate_plans
    ]

    scenario = ScenarioResponse(
        type=result.scenario.type,
        customer_id=result.scenario.customer_id,
        quantity=result.scenario.quantity,
        supplier_id=result.scenario.supplier_id,
        percentage=result.scenario.percentage,
    )

    return PlannerResponse(
        recommended_plan=recommended_plan,
        alternatives=alternatives,
        explanation=recommendation.explanation,
        actions=actions,
        scenario=scenario,
        candidate_plans=candidate_plans,
    )