import pytest
from pydantic import ValidationError

from app.schemas.planner import (
    DemandSpikeRequest,
    PlannerRequest,
    ScoringWeightsRequest,
    SupplierFailureRequest,
)


def test_valid_normal_request():
    request = PlannerRequest(
        customer_id=1,
        quantity=42,
    )

    assert request.customer_id == 1
    assert request.quantity == 42
    assert request.disruption_type == "none"


def test_valid_supplier_failure_request():
    request = PlannerRequest(
        customer_id=1,
        quantity=42,
        disruption_type="supplier_failure",
        supplier_id=1,
    )

    assert request.disruption_type == "supplier_failure"
    assert request.supplier_id == 1


def test_valid_demand_spike_request():
    request = PlannerRequest(
        customer_id=1,
        quantity=42,
        disruption_type="demand_spike",
        disruption_customer_id=1,
        demand_spike_percentage=20,
    )

    assert request.disruption_type == "demand_spike"
    assert request.demand_spike_percentage == 20


def test_default_weights():
    request = PlannerRequest(
        customer_id=1,
        quantity=42,
    )

    assert request.weights.cost == 0.4
    assert request.weights.time == 0.3
    assert request.weights.risk == 0.3


def test_invalid_quantity():
    with pytest.raises(ValidationError):
        PlannerRequest(
            customer_id=1,
            quantity=0,
        )


def test_invalid_weights():
    with pytest.raises(ValidationError):
        ScoringWeightsRequest(
            cost=0.5,
            time=0.5,
            risk=0.5,
        )


def test_supplier_failure_requires_supplier():
    with pytest.raises(ValidationError):
        PlannerRequest(
            customer_id=1,
            quantity=42,
            disruption_type="supplier_failure",
        )


def test_demand_spike_requires_percentage():
    with pytest.raises(ValidationError):
        PlannerRequest(
            customer_id=1,
            quantity=42,
            disruption_type="demand_spike",
        )


def test_supplier_failure_schema():
    request = SupplierFailureRequest(
        type="supplier_failure",
        supplier_id=1,
    )

    assert request.supplier_id == 1


def test_demand_spike_schema():
    request = DemandSpikeRequest(
        type="demand_spike",
        customer_id=1,
        percentage=20,
    )

    assert request.percentage == 20