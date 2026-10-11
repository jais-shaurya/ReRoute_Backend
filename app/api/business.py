from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database.connection import get_db
from app.database.models import AppUser, Organization
from app.schemas.business import (
    CustomerCreateRequest,
    CustomerResponse,
    CustomerUpdateRequest,
    FactoryCreateRequest,
    FactoryResponse,
    FactoryUpdateRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
    PlanningRunResponse,
    RecommendationComparisonResponse,
    RiskExplanationResponse,
    RouteCreateRequest,
    RouteResponse,
    RouteUpdateRequest,
    ScenarioCreateRequest,
    ScenarioResponse,
    SupplierCreateRequest,
    SupplierResponse,
    SupplierUpdateRequest,
    UserCreateRequest,
    UserResponse,
    WarehouseCreateRequest,
    WarehouseResponse,
    WarehouseUpdateRequest,
)
from app.security.auth import get_current_user, require_role, require_tenant_scope
from app.services.planner import InfeasiblePlanningError
from app.services.business import BusinessService

router = APIRouter(prefix="/api/business", tags=["Business"])


def _serialize_supplier(supplier):
    return SupplierResponse(
        id=supplier.id,
        supplier_code=supplier.supplier_code,
        name=supplier.name,
        capacity=supplier.capacity,
        unit_cost=supplier.unit_cost,
        reliability=supplier.reliability,
        available=supplier.available,
    )


def _serialize_customer(customer):
    return CustomerResponse(
        id=customer.id,
        customer_code=customer.customer_code,
        name=customer.name,
        demand=customer.demand,
        deadline_days=customer.deadline_days,
    )


def _serialize_customer_list(customers):
    return [_serialize_customer(item) for item in customers]


def _serialize_warehouse(warehouse):
    return WarehouseResponse(
        id=warehouse.id,
        warehouse_code=warehouse.warehouse_code,
        name=warehouse.name,
        capacity=warehouse.capacity,
        inventory=warehouse.inventory,
    )


def _serialize_factory(factory):
    return FactoryResponse(
        id=factory.id,
        factory_code=factory.factory_code,
        name=factory.name,
        capacity=factory.capacity,
        available=factory.available,
    )


def _serialize_route(route):
    return RouteResponse(
        id=route.id,
        route_code=route.route_code,
        source_type=route.source_type,
        source_id=route.source_id,
        destination_type=route.destination_type,
        destination_id=route.destination_id,
        transportation_cost=route.transportation_cost,
        delivery_time_days=route.delivery_time_days,
        capacity=route.capacity,
        available=route.available,
    )


def _serialize_scenario(scenario):
    return ScenarioResponse(
        id=scenario.id,
        organization_id=scenario.organization_id,
        created_by_id=scenario.created_by_id,
        name=scenario.name,
        scenario_type=scenario.scenario_type,
        customer_id=scenario.customer_id,
        quantity=scenario.quantity,
        supplier_id=scenario.supplier_id,
        route_ids=scenario.route_ids or [],
        simultaneous_route_ids=scenario.simultaneous_route_ids or [],
        demand_spike_percentage=scenario.demand_spike_percentage,
        notes=scenario.notes,
        created_at=scenario.created_at.isoformat(),
    )


def _serialize_run(run):
    return PlanningRunResponse(
        id=run.id,
        organization_id=run.organization_id,
        created_by_id=run.created_by_id,
        scenario_id=run.scenario_id,
        status=run.status,
        requested_customer_id=run.requested_customer_id,
        requested_quantity=run.requested_quantity,
        disruption_type=run.disruption_type,
        supplier_id=run.supplier_id,
        demand_spike_percentage=run.demand_spike_percentage,
        recommendation=run.recommendation,
        explanation=run.explanation,
        result_payload=run.result_payload,
        created_at=run.created_at.isoformat(),
    )


@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin")),
):
    service = BusinessService(db)
    org = service.create_organization(payload)
    return OrganizationResponse(id=org.id, name=org.name, slug=org.slug)


@router.post("/organizations/{organization_id}/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_organization_user(
    organization_id: int,
    payload: UserCreateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    user = service.create_user(organization_id, payload, current_user)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        organization_id=user.organization_id,
        is_active=user.is_active,
    )


@router.get("/organizations/{organization_id}/users", response_model=list[UserResponse])
def list_organization_users(
    organization_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    require_tenant_scope(organization_id, current_user)
    service = BusinessService(db)
    users = service.get_organization_users(organization_id, current_user)
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            organization_id=user.organization_id,
            is_active=user.is_active,
        )
        for user in users
    ]


@router.get("/suppliers", response_model=list[SupplierResponse])
def list_suppliers(
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    items = service.list_suppliers(current_user)
    return [_serialize_supplier(item) for item in items]


@router.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    supplier = service.create_supplier(payload, current_user)
    return _serialize_supplier(supplier)


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    supplier = service.get_supplier(supplier_id, current_user)
    return _serialize_supplier(supplier)


@router.put("/suppliers/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    supplier = service.update_supplier(supplier_id, payload, current_user)
    return _serialize_supplier(supplier)


@router.delete("/suppliers/{supplier_id}")
def delete_supplier(
    supplier_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin")),
):
    service = BusinessService(db)
    return service.delete_supplier(supplier_id, current_user)


@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return _serialize_customer_list(service.list_customers(current_user))


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    customer = service.create_customer(payload, current_user)
    return _serialize_customer(customer)


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return _serialize_customer(service.get_customer(customer_id, current_user))


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    payload: CustomerUpdateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    return _serialize_customer(service.update_customer(customer_id, payload, current_user))


@router.delete("/customers/{customer_id}")
def delete_customer(
    customer_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin")),
):
    service = BusinessService(db)
    return service.delete_customer(customer_id, current_user)


@router.get("/warehouses", response_model=list[WarehouseResponse])
def list_warehouses(
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return [_serialize_warehouse(item) for item in service.list_warehouses(current_user)]


@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    payload: WarehouseCreateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    warehouse = service.create_warehouse(payload, current_user)
    return _serialize_warehouse(warehouse)


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def get_warehouse(
    warehouse_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return _serialize_warehouse(service.get_warehouse(warehouse_id, current_user))


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(
    warehouse_id: int,
    payload: WarehouseUpdateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    return _serialize_warehouse(service.update_warehouse(warehouse_id, payload, current_user))


@router.delete("/warehouses/{warehouse_id}")
def delete_warehouse(
    warehouse_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin")),
):
    service = BusinessService(db)
    return service.delete_warehouse(warehouse_id, current_user)


@router.get("/factories", response_model=list[FactoryResponse])
def list_factories(
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return [_serialize_factory(item) for item in service.list_factories(current_user)]


@router.post("/factories", response_model=FactoryResponse, status_code=status.HTTP_201_CREATED)
def create_factory(
    payload: FactoryCreateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    factory = service.create_factory(payload, current_user)
    return _serialize_factory(factory)


@router.get("/factories/{factory_id}", response_model=FactoryResponse)
def get_factory(
    factory_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return _serialize_factory(service.get_factory(factory_id, current_user))


@router.put("/factories/{factory_id}", response_model=FactoryResponse)
def update_factory(
    factory_id: int,
    payload: FactoryUpdateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    return _serialize_factory(service.update_factory(factory_id, payload, current_user))


@router.delete("/factories/{factory_id}")
def delete_factory(
    factory_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin")),
):
    service = BusinessService(db)
    return service.delete_factory(factory_id, current_user)


@router.get("/routes", response_model=list[RouteResponse])
def list_routes(
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return [_serialize_route(item) for item in service.list_routes(current_user)]


@router.post("/routes", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
def create_route(
    payload: RouteCreateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    route = service.create_route(payload, current_user)
    return _serialize_route(route)


@router.get("/routes/{route_id}", response_model=RouteResponse)
def get_route(
    route_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return _serialize_route(service.get_route(route_id, current_user))


@router.put("/routes/{route_id}", response_model=RouteResponse)
def update_route(
    route_id: int,
    payload: RouteUpdateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    return _serialize_route(service.update_route(route_id, payload, current_user))


@router.delete("/routes/{route_id}")
def delete_route(
    route_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin")),
):
    service = BusinessService(db)
    return service.delete_route(route_id, current_user)


@router.get("/scenarios", response_model=list[ScenarioResponse])
def list_scenarios(
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return [_serialize_scenario(item) for item in service.list_scenarios(current_user)]


@router.post("/scenarios", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def create_scenario(
    payload: ScenarioCreateRequest,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    scenario = service.create_scenario(payload, current_user)
    return _serialize_scenario(scenario)


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return _serialize_scenario(service.get_scenario(scenario_id, current_user))


@router.post("/scenarios/{scenario_id}/execute", response_model=PlanningRunResponse)
def execute_scenario(
    scenario_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(require_role("admin", "planner")),
):
    service = BusinessService(db)
    try:
        run = service.execute_scenario(scenario_id, current_user)
    except InfeasiblePlanningError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_run(run)


@router.get("/planning-runs", response_model=list[PlanningRunResponse])
def list_runs(
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return [_serialize_run(item) for item in service.list_runs(current_user)]


@router.get("/planning-runs/{run_id}", response_model=PlanningRunResponse)
def get_run(
    run_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return _serialize_run(service.get_run(run_id, current_user))


@router.get("/planning-runs/{run_id}/comparison", response_model=RecommendationComparisonResponse)
def get_run_comparison(
    run_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return service.get_run_comparison(run_id, current_user)


@router.get("/planning-runs/{run_id}/explanation", response_model=RiskExplanationResponse)
def get_run_explanation(
    run_id: int,
    db=Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    service = BusinessService(db)
    return service.get_run_explanation(run_id, current_user)
