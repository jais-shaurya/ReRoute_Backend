from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.graph import build_supply_chain_graph
from app.database.models import (
    AppUser,
    Customer,
    Factory,
    Organization,
    OrganizationEntityAccess,
    PlanningRun,
    PlanningScenario,
    Route,
    Supplier,
    Warehouse,
)
from app.services.planner import PlannerService


class BusinessService:
    def __init__(self, db: Session):
        self.db = db

    def _to_jsonable(self, value):
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, dict):
            return {key: self._to_jsonable(val) for key, val in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._to_jsonable(item) for item in value]
        return value

    def _entity_scope_ids(self, entity_type: str, organization_id: int) -> list[int]:
        return [
            item.entity_id
            for item in self.db.query(OrganizationEntityAccess)
            .filter_by(organization_id=organization_id, entity_type=entity_type)
            .all()
        ]

    def _scoped_entities(self, model, entity_type: str, current_user: AppUser):
        entity_ids = self._entity_scope_ids(entity_type, current_user.organization_id)
        if not entity_ids:
            return self.db.query(model).filter(False)
        return self.db.query(model).filter(model.id.in_(entity_ids))

    def _grant_entity_scope(self, entity_type: str, entity_id: int, organization_id: int) -> None:
        existing = (
            self.db.query(OrganizationEntityAccess)
            .filter_by(organization_id=organization_id, entity_type=entity_type, entity_id=entity_id)
            .first()
        )
        if existing is None:
            self.db.add(
                OrganizationEntityAccess(
                    organization_id=organization_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            )

    def _require_scoped_entity(self, model, entity_type: str, entity_id: int, current_user: AppUser):
        entity = self._scoped_entities(model, entity_type, current_user).filter_by(id=entity_id).first()
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_type.title()} not found.",
            )
        return entity

    def _validate_route_endpoints(self, payload, current_user: AppUser) -> None:
        self._require_scoped_entity(
            {"supplier": Supplier, "factory": Factory, "warehouse": Warehouse}[payload.source_type],
            payload.source_type,
            payload.source_id,
            current_user,
        )
        self._require_scoped_entity(
            {"factory": Factory, "warehouse": Warehouse, "customer": Customer}[payload.destination_type],
            payload.destination_type,
            payload.destination_id,
            current_user,
        )

    def _organization_graph(self, planner: PlannerService, current_user: AppUser):
        graph = planner.build_graph()
        scoped_node_types = {
            "supplier": set(self._entity_scope_ids("supplier", current_user.organization_id)),
            "customer": set(self._entity_scope_ids("customer", current_user.organization_id)),
            "warehouse": set(self._entity_scope_ids("warehouse", current_user.organization_id)),
            "factory": set(self._entity_scope_ids("factory", current_user.organization_id)),
        }
        for node, attributes in list(graph.nodes(data=True)):
            entity_type = attributes.get("node_type")
            entity_id = attributes.get("database_id")
            if entity_id not in scoped_node_types.get(entity_type, set()):
                graph.remove_node(node)

        allowed_routes = set(self._entity_scope_ids("route", current_user.organization_id))
        for source, destination, attributes in list(graph.edges(data=True)):
            if attributes.get("route_id") not in allowed_routes:
                graph.remove_edge(source, destination)
        return graph

    def _ensure_organization(self, organization_id: int) -> Organization:
        organization = self.db.query(Organization).filter_by(id=organization_id).first()
        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )
        return organization

    def _ensure_user_scope(self, current_user: AppUser, organization_id: int) -> None:
        if current_user.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization mismatch. You cannot access another organization's data.",
            )

    def list_suppliers(self, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        return self._scoped_entities(Supplier, "supplier", current_user).all()

    def create_supplier(self, payload, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        existing = self.db.query(Supplier).filter_by(supplier_code=payload.supplier_code).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Supplier code already exists.",
            )
        supplier = Supplier(**payload.model_dump())
        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        self._grant_entity_scope("supplier", supplier.id, current_user.organization_id)
        self.db.commit()
        return supplier

    def get_supplier(self, supplier_id: int, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        supplier = self._scoped_entities(Supplier, "supplier", current_user).filter_by(id=supplier_id).first()
        if supplier is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
        return supplier

    def update_supplier(self, supplier_id: int, payload, current_user: AppUser):
        supplier = self.get_supplier(supplier_id, current_user)
        for field, value in payload.model_dump().items():
            setattr(supplier, field, value)
        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def delete_supplier(self, supplier_id: int, current_user: AppUser):
        supplier = self.get_supplier(supplier_id, current_user)
        self.db.delete(supplier)
        self.db.commit()
        return {"deleted": True, "supplier_id": supplier_id}

    def list_customers(self, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        return self._scoped_entities(Customer, "customer", current_user).all()

    def create_customer(self, payload, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        existing = self.db.query(Customer).filter_by(customer_code=payload.customer_code).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Customer code already exists.")
        customer = Customer(**payload.model_dump())
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        self._grant_entity_scope("customer", customer.id, current_user.organization_id)
        self.db.commit()
        return customer

    def get_customer(self, customer_id: int, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        customer = self._scoped_entities(Customer, "customer", current_user).filter_by(id=customer_id).first()
        if customer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
        return customer

    def update_customer(self, customer_id: int, payload, current_user: AppUser):
        customer = self.get_customer(customer_id, current_user)
        for field, value in payload.model_dump().items():
            setattr(customer, field, value)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def delete_customer(self, customer_id: int, current_user: AppUser):
        customer = self.get_customer(customer_id, current_user)
        self.db.delete(customer)
        self.db.commit()
        return {"deleted": True, "customer_id": customer_id}

    def list_warehouses(self, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        return self._scoped_entities(Warehouse, "warehouse", current_user).all()

    def create_warehouse(self, payload, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        existing = self.db.query(Warehouse).filter_by(warehouse_code=payload.warehouse_code).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Warehouse code already exists.")
        warehouse = Warehouse(**payload.model_dump())
        self.db.add(warehouse)
        self.db.commit()
        self.db.refresh(warehouse)
        self._grant_entity_scope("warehouse", warehouse.id, current_user.organization_id)
        self.db.commit()
        return warehouse

    def get_warehouse(self, warehouse_id: int, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        warehouse = self._scoped_entities(Warehouse, "warehouse", current_user).filter_by(id=warehouse_id).first()
        if warehouse is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found.")
        return warehouse

    def update_warehouse(self, warehouse_id: int, payload, current_user: AppUser):
        warehouse = self.get_warehouse(warehouse_id, current_user)
        for field, value in payload.model_dump().items():
            setattr(warehouse, field, value)
        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def delete_warehouse(self, warehouse_id: int, current_user: AppUser):
        warehouse = self.get_warehouse(warehouse_id, current_user)
        self.db.delete(warehouse)
        self.db.commit()
        return {"deleted": True, "warehouse_id": warehouse_id}

    def list_factories(self, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        return self._scoped_entities(Factory, "factory", current_user).all()

    def create_factory(self, payload, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        existing = self.db.query(Factory).filter_by(factory_code=payload.factory_code).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Factory code already exists.")
        factory = Factory(**payload.model_dump())
        self.db.add(factory)
        self.db.commit()
        self.db.refresh(factory)
        self._grant_entity_scope("factory", factory.id, current_user.organization_id)
        self.db.commit()
        return factory

    def get_factory(self, factory_id: int, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        factory = self._scoped_entities(Factory, "factory", current_user).filter_by(id=factory_id).first()
        if factory is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factory not found.")
        return factory

    def update_factory(self, factory_id: int, payload, current_user: AppUser):
        factory = self.get_factory(factory_id, current_user)
        for field, value in payload.model_dump().items():
            setattr(factory, field, value)
        self.db.commit()
        self.db.refresh(factory)
        return factory

    def delete_factory(self, factory_id: int, current_user: AppUser):
        factory = self.get_factory(factory_id, current_user)
        self.db.delete(factory)
        self.db.commit()
        return {"deleted": True, "factory_id": factory_id}

    def list_routes(self, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        return self._scoped_entities(Route, "route", current_user).all()

    def create_route(self, payload, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        self._validate_route_endpoints(payload, current_user)
        existing = self.db.query(Route).filter_by(route_code=payload.route_code).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Route code already exists.")
        route = Route(**payload.model_dump())
        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)
        self._grant_entity_scope("route", route.id, current_user.organization_id)
        self.db.commit()
        return route

    def get_route(self, route_id: int, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        route = self._scoped_entities(Route, "route", current_user).filter_by(id=route_id).first()
        if route is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found.")
        return route

    def update_route(self, route_id: int, payload, current_user: AppUser):
        route = self.get_route(route_id, current_user)
        self._validate_route_endpoints(payload, current_user)
        for field, value in payload.model_dump().items():
            setattr(route, field, value)
        self.db.commit()
        self.db.refresh(route)
        return route

    def delete_route(self, route_id: int, current_user: AppUser):
        route = self.get_route(route_id, current_user)
        self.db.delete(route)
        self.db.commit()
        return {"deleted": True, "route_id": route_id}

    def list_scenarios(self, current_user: AppUser):
        return self.db.query(PlanningScenario).filter_by(organization_id=current_user.organization_id).order_by(PlanningScenario.created_at.desc()).all()

    def create_scenario(self, payload, current_user: AppUser):
        self._ensure_organization(current_user.organization_id)
        self._require_scoped_entity(Customer, "customer", payload.customer_id, current_user)
        if payload.supplier_id is not None:
            self._require_scoped_entity(Supplier, "supplier", payload.supplier_id, current_user)
        for route_id in payload.route_ids + payload.simultaneous_route_ids:
            self._require_scoped_entity(Route, "route", route_id, current_user)
        scenario = PlanningScenario(
            organization_id=current_user.organization_id,
            created_by_id=current_user.id,
            name=payload.name,
            scenario_type=payload.scenario_type,
            customer_id=payload.customer_id,
            quantity=payload.quantity,
            supplier_id=payload.supplier_id,
            route_ids=payload.route_ids,
            simultaneous_route_ids=payload.simultaneous_route_ids,
            demand_spike_percentage=payload.demand_spike_percentage,
            notes=payload.notes,
        )
        self.db.add(scenario)
        self.db.commit()
        self.db.refresh(scenario)
        return scenario

    def get_scenario(self, scenario_id: int, current_user: AppUser):
        scenario = self.db.query(PlanningScenario).filter_by(id=scenario_id, organization_id=current_user.organization_id).first()
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found.")
        return scenario

    def execute_scenario(self, scenario_id: int, current_user: AppUser):
        scenario = self.get_scenario(scenario_id, current_user)
        planner = PlannerService(self.db)
        self._require_scoped_entity(Customer, "customer", scenario.customer_id, current_user)
        if scenario.supplier_id is not None:
            self._require_scoped_entity(Supplier, "supplier", scenario.supplier_id, current_user)
        graph = self._organization_graph(planner, current_user)

        for route_id in scenario.route_ids or []:
            route = self._require_scoped_entity(Route, "route", route_id, current_user)
            source_node = f"{route.source_type}:{route.source_id}"
            destination_node = f"{route.destination_type}:{route.destination_id}"
            if graph.has_edge(source_node, destination_node):
                graph.remove_edge(source_node, destination_node)

        for route_id in scenario.simultaneous_route_ids or []:
            route = self._require_scoped_entity(Route, "route", route_id, current_user)
            source_node = f"{route.source_type}:{route.source_id}"
            destination_node = f"{route.destination_type}:{route.destination_id}"
            if graph.has_edge(source_node, destination_node):
                graph.remove_edge(source_node, destination_node)

        if scenario.supplier_id is not None:
            graph = planner.apply_supplier_failure(graph, scenario.supplier_id)

        if scenario.scenario_type == "demand_spike" and scenario.demand_spike_percentage is not None:
            graph = planner.apply_demand_spike(graph, scenario.customer_id, scenario.demand_spike_percentage)

        disruption_type = None if scenario.scenario_type == "none" else scenario.scenario_type
        kwargs = {
            "customer_id": scenario.customer_id,
            "quantity": scenario.quantity,
            "disruption_type": disruption_type,
            "supplier_id": scenario.supplier_id,
            "disruption_customer_id": scenario.customer_id,
            "demand_spike_percentage": scenario.demand_spike_percentage,
            "weights": None,
            "max_alternatives": 3,
            "base_graph": graph,
        }
        if scenario.scenario_type == "simultaneous":
            kwargs["disruption_type"] = "supplier_failure"
            kwargs["supplier_id"] = scenario.supplier_id or 1

        result = planner.recommend(**kwargs)

        run = PlanningRun(
            organization_id=current_user.organization_id,
            created_by_id=current_user.id,
            scenario_id=scenario.id,
            status="completed",
            requested_customer_id=scenario.customer_id,
            requested_quantity=scenario.quantity,
            disruption_type=kwargs["disruption_type"] or "none",
            supplier_id=scenario.supplier_id,
            demand_spike_percentage=scenario.demand_spike_percentage,
            recommendation=result.recommendation.selected_plan.plan.path[-1] if result.recommendation.selected_plan else None,
            explanation=result.recommendation.explanation,
            result_payload={
                "recommended_plan": self._to_jsonable(result.recommendation.selected_plan),
                "alternatives": [self._to_jsonable(plan) for plan in result.recommendation.alternatives],
                "candidate_plans": [self._to_jsonable(plan) for plan in result.candidate_plans],
                "scenario": {
                    "type": result.scenario.type,
                    "customer_id": result.scenario.customer_id,
                    "quantity": result.scenario.quantity,
                    "supplier_id": result.scenario.supplier_id,
                    "percentage": result.scenario.percentage,
                },
            },
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def list_runs(self, current_user: AppUser):
        return self.db.query(PlanningRun).filter_by(organization_id=current_user.organization_id).order_by(PlanningRun.created_at.desc()).all()

    def get_run(self, run_id: int, current_user: AppUser):
        run = self.db.query(PlanningRun).filter_by(id=run_id, organization_id=current_user.organization_id).first()
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning run not found.")
        return run

    def get_run_comparison(self, run_id: int, current_user: AppUser):
        run = self.get_run(run_id, current_user)
        payload = run.result_payload or {}
        recommended = payload.get("recommended_plan", {})
        alternatives = payload.get("alternatives", [])
        explanation = payload.get("explanation") or run.explanation or ""
        actions = payload.get("actions", [])
        return {
            "selected_plan": recommended,
            "alternatives": alternatives,
            "explanation": explanation,
            "actions": actions,
        }

    def get_run_explanation(self, run_id: int, current_user: AppUser):
        run = self.get_run(run_id, current_user)
        payload = run.result_payload or {}
        explanation = payload.get("scenario", {})
        risk_summary = {
            "status": run.status,
            "disruption_type": run.disruption_type,
            "requested_quantity": run.requested_quantity,
        }
        feasibility = {
            "feasible": run.status == "completed",
            "recommendation": run.recommendation,
        }
        return {
            "explanation": run.explanation or payload.get("recommended_plan", {}).get("path") or "No explanation available.",
            "risk_summary": risk_summary,
            "feasibility": feasibility,
        }

    def get_organization_users(self, organization_id: int, current_user: AppUser):
        self._ensure_user_scope(current_user, organization_id)
        return self.db.query(AppUser).filter_by(organization_id=organization_id).all()

    def create_organization(self, payload):
        existing = self.db.query(Organization).filter_by(slug=payload.slug.lower()).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization slug already exists.")
        organization = Organization(name=payload.name, slug=payload.slug.lower())
        self.db.add(organization)
        self.db.commit()
        self.db.refresh(organization)
        return organization

    def create_user(self, organization_id: int, payload, current_user: AppUser):
        self._ensure_user_scope(current_user, organization_id)
        if current_user.role not in {"admin", "planner"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to create team members.")
        existing = self.db.query(AppUser).filter_by(email=payload.email.lower()).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists.")
        user = AppUser(
            email=payload.email.lower(),
            full_name=payload.full_name,
            role=payload.role,
            organization_id=organization_id,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
