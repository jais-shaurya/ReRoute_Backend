from dataclasses import dataclass

import networkx as nx
from sqlalchemy.orm import Session

from app.ai.astar import find_lowest_cost_path
from app.ai.bayesian_risk import (
    BayesianRiskResult,
    estimate_plan_risk,
)
from app.ai.csp import (
    CandidatePlan,
    generate_feasible_plans,
)
from app.ai.disruption import (
    simulate_demand_spike,
    simulate_supplier_failure,
)
from app.ai.graph import build_supply_chain_graph
from app.ai.recommendation import (
    RecommendationResult,
    recommend_plan,
)
from app.ai.scoring import (
    ScoredPlan,
    ScoringWeights,
    score_plans,
)


@dataclass(frozen=True)
class PlannerScenario:
    """
    Describes the scenario actually used by the planner.
    """

    type: str
    customer_id: int
    quantity: int

    supplier_id: int | None = None
    percentage: float | None = None


@dataclass(frozen=True)
class PlannerResult:
    """
    Complete result produced by the planner service.

    The API layer will later convert this into
    Pydantic response models.
    """

    recommendation: RecommendationResult
    scenario: PlannerScenario
    candidate_plans: tuple[ScoredPlan, ...]


class PlannerService:
    """
    Orchestrates the existing ReRoute AI pipeline.

    This service does not implement A*, CSP, Bayesian risk,
    scoring, or recommendation logic itself.

    It only coordinates the existing modules.
    """

    def __init__(self, session: Session):
        self.session = session

    # ========================================================
    # Graph
    # ========================================================

    def build_graph(self) -> nx.DiGraph:
        """
        Build a fresh supply-chain graph from the database.
        """

        return build_supply_chain_graph(self.session)

    # ========================================================
    # Scenario
    # ========================================================

    def apply_supplier_failure(
        self,
        graph: nx.DiGraph,
        supplier_id: int,
    ) -> nx.DiGraph:
        """
        Apply a supplier-failure scenario to a copy
        of the current graph.
        """

        return simulate_supplier_failure(
            graph,
            supplier_id,
        )

    def apply_demand_spike(
        self,
        graph: nx.DiGraph,
        customer_id: int,
        percentage: float,
    ) -> nx.DiGraph:
        """
        Apply a demand-spike scenario to a copy
        of the current graph.
        """

        return simulate_demand_spike(
            graph,
            customer_id,
            percentage,
        )

    # ========================================================
    # Candidate generation
    # ========================================================

    def generate_candidates(
        self,
        graph: nx.DiGraph,
        customer_id: int,
        quantity: int,
    ) -> list[CandidatePlan]:
        """
        Generate CSP-feasible recovery plans.

        The existing CSP module internally:
            supplier candidates
                ↓
            A*
                ↓
            CandidatePlan
                ↓
            CSP validation
        """

        return generate_feasible_plans(
            graph,
            customer_id,
            quantity,
        )

    # ========================================================
    # Risk
    # ========================================================

    def calculate_risks(
        self,
        graph: nx.DiGraph,
        plans: list[CandidatePlan],
    ) -> list[BayesianRiskResult]:
        """
        Calculate Bayesian risk for every feasible plan.
        """

        return [
            estimate_plan_risk(
                graph,
                plan,
            )
            for plan in plans
        ]

    # ========================================================
    # Scoring
    # ========================================================

    def score_candidates(
        self,
        plans: list[CandidatePlan],
        risks: list[BayesianRiskResult],
        weights: ScoringWeights,
    ) -> list[ScoredPlan]:
        """
        Score and rank feasible plans.
        """

        return score_plans(
            plans,
            risks,
            weights,
        )

    # ========================================================
    # Recommendation
    # ========================================================

    def generate_recommendation(
        self,
        ranked_plans: list[ScoredPlan],
        max_alternatives: int = 3,
    ) -> RecommendationResult:
        """
        Select the best plan and generate explanation/actions.
        """

        return recommend_plan(
            ranked_plans,
            max_alternatives=max_alternatives,
        )

    # ========================================================
    # Complete pipeline
    # ========================================================

    def recommend(
        self,
        customer_id: int,
        quantity: int,
        disruption_type: str | None = None,
        supplier_id: int | None = None,
        disruption_customer_id: int | None = None,
        demand_spike_percentage: float | None = None,
        weights: ScoringWeights | None = None,
        max_alternatives: int = 3,
    ) -> PlannerResult:
        """
        Execute the complete ReRoute planning pipeline.

        Pipeline:

            Database
                ↓
            Graph
                ↓
            Disruption
                ↓
            A*
                ↓
            CSP
                ↓
            Bayesian Risk
                ↓
            Multi-objective Scoring
                ↓
            Recommendation
        """

        # ----------------------------------------------------
        # Basic service-level validation
        # ----------------------------------------------------

        if customer_id <= 0:
            raise ValueError(
                "Customer ID must be greater than zero."
            )

        if quantity <= 0:
            raise ValueError(
                "Planning quantity must be greater than zero."
            )

        if max_alternatives < 0:
            raise ValueError(
                "max_alternatives cannot be negative."
            )

        # ----------------------------------------------------
        # Build base graph
        # ----------------------------------------------------

        graph = self.build_graph()

        # ----------------------------------------------------
        # Validate selected customer
        # ----------------------------------------------------

        customer_node = f"customer:{customer_id}"

        if customer_node not in graph:
            raise ValueError(
                f"Customer with ID {customer_id} does not exist."
            )

        # ----------------------------------------------------
        # Validate quantity against current demand
        # ----------------------------------------------------

        current_demand = graph.nodes[
            customer_node
        ].get("demand")

        if current_demand is None:
            raise ValueError(
                f"Customer {customer_id} has no demand value."
            )

        # ----------------------------------------------------
        # Apply disruption
        # ----------------------------------------------------

        scenario_quantity = quantity

        if disruption_type is None:
            scenario_graph = graph

            scenario = PlannerScenario(
                type="none",
                customer_id=customer_id,
                quantity=quantity,
            )

        elif disruption_type == "supplier_failure":

            if supplier_id is None:
                raise ValueError(
                    "supplier_id is required for "
                    "supplier_failure."
                )

            scenario_graph = self.apply_supplier_failure(
                graph,
                supplier_id,
            )

            scenario = PlannerScenario(
                type="supplier_failure",
                customer_id=customer_id,
                quantity=quantity,
                supplier_id=supplier_id,
            )

        elif disruption_type == "demand_spike":

            if disruption_customer_id is None:
                disruption_customer_id = customer_id

            if disruption_customer_id != customer_id:
                raise ValueError(
                    "Demand spike customer_id must match "
                    "the planner customer_id."
                )

            if demand_spike_percentage is None:
                raise ValueError(
                    "percentage is required for "
                    "demand_spike."
                )

            scenario_graph = self.apply_demand_spike(
                graph,
                customer_id,
                demand_spike_percentage,
            )

            updated_demand = scenario_graph.nodes[
                customer_node
            ].get("demand")

            if updated_demand is None:
                raise ValueError(
                    f"Customer {customer_id} has no demand "
                    "value after demand spike."
                )

            scenario_quantity = int(updated_demand)

            if scenario_quantity <= 0:
                raise ValueError(
                    "Demand spike produced an invalid "
                    "planning quantity."
                )

            scenario = PlannerScenario(
                type="demand_spike",
                customer_id=customer_id,
                quantity=scenario_quantity,
                percentage=demand_spike_percentage,
            )

        else:
            raise ValueError(
                f"Unsupported disruption type: "
                f"{disruption_type}."
            )

        # ----------------------------------------------------
        # CSP candidate generation
        # ----------------------------------------------------

        plans = self.generate_candidates(
            scenario_graph,
            customer_id,
            scenario_quantity,
        )

        if not plans:
            raise ValueError(
                "No feasible recovery plans exist "
                "for the requested scenario."
            )

        # ----------------------------------------------------
        # Bayesian risk
        # ----------------------------------------------------

        risks = self.calculate_risks(
            scenario_graph,
            plans,
        )

        # ----------------------------------------------------
        # Multi-objective scoring
        # ----------------------------------------------------

        if weights is None:
            weights = ScoringWeights()

        ranked_plans = self.score_candidates(
            plans,
            risks,
            weights,
        )

        if not ranked_plans:
            raise ValueError(
                "No plans were produced by the scoring layer."
            )

        # ----------------------------------------------------
        # Recommendation
        # ----------------------------------------------------

        recommendation = self.generate_recommendation(
            ranked_plans,
            max_alternatives=max_alternatives,
        )

        return PlannerResult(
            recommendation=recommendation,
            scenario=scenario,
            candidate_plans=tuple(ranked_plans),
        )