from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil
from types import MappingProxyType
from typing import Literal
from collections.abc import Iterable

from pydantic import Field, model_validator

from .contracts import (
    CoordinatedProposal, CustomerDeliveryChange, DemoError, HumanEvidence,
    StrictModel, SCENARIO_ID, SCENARIO_IDS, ScenarioId,
    ScopedFinding, SupplyOptionAssessment, ProductionOptionAssessment,
    dependency_claims, option_assessment,
)

SNAPSHOT = "2026-10-15T14:00:00-05:00"
ALLOWLIST = {
    "supply-chain": ("read_inventory", "read_shipment"),
    "production": ("read_inventory", "read_build"),
    "commercial": ("read_shipment", "read_approval_policy"),
}
EXAMPLES: dict[str, ScenarioId] = {
    "quality-hold": SCENARIO_ID, "supply-chain": SCENARIO_ID,
    "carrier-delay": "carrier-delay-v2",
    "production-resequence": "production-resequence-v2",
    "order-pull-forward": "order-pull-forward-v2",
}


class FixtureRecord(StrictModel):
    scenario_id: ScenarioId = SCENARIO_ID
    source: Literal["synthetic_fixture"] = "synthetic_fixture"
    as_of: str = SNAPSHOT
    evidence_id: str


class IncidentLot(StrictModel):
    incident_id: str = "QI-2026-1042"
    lot_id: str = "L-1042"
    part_id: str = "MB-217 stamped mounting bracket"
    total_units: int = 960
    held_onsite_units: int = 720
    already_shipped_units: int = 240
    inspected_units: int = 80
    measured_failures: int = 6
    hold_status: Literal["Quality-held"] = "Quality-held"
    quality_owner: str = "Supplier Quality lead"
    total_nonconforming_units: None = None

    @model_validator(mode="after")
    def check_counts(self):
        if (
            self.held_onsite_units + self.already_shipped_units != self.total_units
            or not 0 <= self.measured_failures <= self.inspected_units <= self.total_units
        ):
            raise ValueError("Incident counts do not reconcile.")
        return self


class Inventory(FixtureRecord):
    incident: IncidentLot = IncidentLot()
    released_lot_id: str = "L-1038"
    released_units: int = 180
    released_status: Literal["independently Quality-released"] = "independently Quality-released"
    held_stock_usable: Literal[False] = False


class Shipment(FixtureRecord):
    suspect_lot_id: str
    suspect_units: int
    shipment_id: str = "SH-882"
    asn_id: str = "ASN-019443"
    shipped_at: str = "2026-10-15T09:00:00-05:00"
    customer_disposition: str | None = None
    notification_status: Literal["pending responsible Quality contact"] = "pending responsible Quality contact"
    replacement_lot_id: str = "L-1058"
    replacement_offer_id: str = "SUP-OFFER-300"
    replacement_units: int = 300
    collection_possible: Literal[True] = True
    confirmed_arrival: str | None = None
    incoming_accepted: Literal[False] = False
    quote_id: str = "DQ-3600"
    freight_cost_usd: int = Field(default=3600, ge=0)


class Delivery(StrictModel):
    order_line: str
    quantity: int = Field(gt=0)
    due_at: str


class Build(FixtureRecord):
    customer: str = "Fictional Tier-1 customer"
    order_id: str = "SO-4821"
    deliveries: tuple[Delivery, ...] = (
        Delivery(order_line="10", quantity=180, due_at="2026-10-16T10:00:00-05:00"),
        Delivery(order_line="20", quantity=240, due_at="2026-10-16T16:00:00-05:00"),
    )
    replenishment_rule: str = "Only independently released stock; replacements need receipt and incoming acceptance."


class ApprovalPolicy(FixtureRecord):
    planner_limit_usd: int = Field(default=2500, ge=0)
    freight_approval_owner: str = "Operations manager"
    quality_owner: str = "Supplier Quality lead"
    customer_contact_owner: str = "Account lead with responsible Quality contact"
    approved_concession: Literal[False] = False
    customer_flexibility: None = None
    customer_window_change_requires_review: Literal[True] = True
    notification_rule: str = "Escalate shipped suspect exposure to responsible Quality contact now; no automated notification."


def fixture_records(scenario_id: ScenarioId = SCENARIO_ID):
    if scenario_id not in SCENARIO_IDS:
        raise DemoError("Unsupported synthetic scenario.")
    if scenario_id != SCENARIO_ID:
        return operational_records(scenario_id)
    inventory = Inventory(evidence_id="fixture:inventory:quality-v2")
    return MappingProxyType({
        "read_inventory": inventory,
        "read_shipment": Shipment(
            evidence_id="fixture:shipment:quality-v2",
            suspect_lot_id=inventory.incident.lot_id,
            suspect_units=inventory.incident.already_shipped_units,
        ),
        "read_build": Build(evidence_id="fixture:build:quality-v2"),
        "read_approval_policy": ApprovalPolicy(evidence_id="fixture:policy:quality-v2"),
    })


def domain_unknowns(actor: str, scenario_id: ScenarioId = SCENARIO_ID) -> set[str]:
    records = fixture_records(scenario_id)
    if scenario_id != SCENARIO_ID:
        if actor == "coordinator":
            return set()
        checks = operational_checks(records)
        domains = {
            "supply-chain": {"carrier_confirmation", "delivery_window", "material_allocation"},
            "production": {"production_capacity", "qualified_cell", "material_allocation", "other_order_impact"},
            "commercial": {"carrier_confirmation", "delivery_window", "customer_request", "other_order_impact"},
        }
        return {key for key in domains[actor] if not checks[key]}
    shipment, policy = records["read_shipment"], records["read_approval_policy"]
    missing = set()
    if actor in ("supply-chain", "production"):
        if shipment.confirmed_arrival is None:
            missing.add("shipment_arrival")
        if not shipment.incoming_accepted:
            missing.add("incoming_acceptance")
    if actor == "commercial" and shipment.customer_disposition is None:
        missing.add("customer_disposition")
    if actor in ("production", "commercial") and policy.customer_flexibility is None:
        missing.add("customer_delivery_change")
    return missing


def validate_delivery_change(change: CustomerDeliveryChange):
    second = fixture_records()["read_build"].deliveries[1]
    if change.customer_agreed and (
        change.quantity > second.quantity
        or change.revised_delivery_at <= datetime.fromisoformat(second.due_at)
    ):
        raise DemoError("Reported change must move at most the second delivery quantity to a later window.")


@dataclass(frozen=True)
class DeliveryPosition:
    total_demand: int
    released_units: int
    first_covered: int
    baseline_gap: int
    provisional_gap: int
    moved_units: int
    revised_delivery_at: str | None


def delivery_position(overlays: Iterable[HumanEvidence] = ()) -> DeliveryPosition:
    records = fixture_records()
    inventory, build = records["read_inventory"], records["read_build"]
    demand = sum(d.quantity for d in build.deliveries)
    released = inventory.released_units
    change = next((e.value for e in overlays if e.key == "customer_delivery_change"), None)
    moved, revised = 0, None
    if change is not None:
        validate_delivery_change(change)
        if change.customer_agreed:
            moved = change.quantity
            revised = change.revised_delivery_at.isoformat()
    baseline = max(0, demand - released)
    return DeliveryPosition(
        demand, released, min(released, build.deliveries[0].quantity),
        baseline, max(0, baseline - moved), moved, revised,
    )


def authoritative_constraints(scenario_id: ScenarioId = SCENARIO_ID) -> dict:
    records = fixture_records(scenario_id)
    if scenario_id != SCENARIO_ID:
        return {
            "checks": operational_checks(records),
            "unselected_options": operational_options(records),
            "position": None if records["read_build"].options else operational_position(records),
            "no_execution_authority": True,
        }
    position = delivery_position()
    return {
        "incident": records["read_inventory"].incident.model_dump(mode="json"),
        "released_stock_units": position.released_units,
        "deliveries": records["read_build"].model_dump(mode="json"),
        "baseline_delivery_shortfall": position.baseline_gap,
        "shipment": records["read_shipment"].model_dump(mode="json"),
        "policy": records["read_approval_policy"].model_dump(mode="json"),
        "hold_cannot_be_lifted_by_demo": True,
        "sample_is_not_total_lot_defect_count": True,
    }


ISSUE = (
    f"SYNTHETIC Tier-2 to Tier-1 quality incident, snapshot {SNAPSHOT}. "
    "QI-2026-1042: stamped mounting-bracket lot L-1042 totals 960; 720 are already "
    "Quality-held onsite and 240 shipped on SH-882 / ASN-019443. Six of 80 measured "
    "parts failed; total nonconforming quantity is unknown, not an extrapolated rate. "
    "A different independently released lot has 180 usable units. Friday deliveries "
    "are 180 at 10:00 and 240 at 16:00 (420 total): first covered, second short 240. "
    "Supplier offers 300 from separate lot L-1058, collection possible, but arrival "
    "and incoming acceptance are unconfirmed. Dedicated courier quote $3,600 exceeds "
    "$2,500 planner authority. Customer flexibility and shipped-lot disposition are "
    "unknown; responsible Quality notification is pending. Separate containment from "
    "delivery recovery. No approved concession; never release held stock, perform "
    "notification, authorize spending, or treat human assertions as approvals."
)


def issue_id(scenario_id: ScenarioId = SCENARIO_ID) -> str:
    return f"issue:{scenario_id}"


def issue_text(scenario_id: ScenarioId = SCENARIO_ID) -> str:
    if scenario_id == SCENARIO_ID:
        return ISSUE
    records = fixture_records(scenario_id)
    build, shipment = records["read_build"], records["read_shipment"]
    position = operational_position(records)
    if build.options:
        return (
            f"SYNTHETIC {build.title}, snapshot {SNAPSHOT}. {build.context} "
            f"Order {build.order_id}: {position['demand_units']} units, "
            f"{position['available_stock_units']} independently released finished units, "
            f"{position['available_material_units']} unreserved released materials. "
            f"Existing planner authority ${records['read_approval_policy'].planner_limit_usd:,}; "
            "this planning limit does not authorize execution. "
            "Compare the explicitly unselected options; no recommended option is supplied. "
            "All evidence is fictional and read-only; no quality incident exists. "
            "Preserve documented customer alternatives, other-order reservations and existing authority."
        )
    return (
        f"SYNTHETIC {build.title}, snapshot {SNAPSHOT}. {build.context} "
        f"Order {build.order_id}: {position['demand_units']} units, "
        f"{position['available_stock_units']} independently released finished units and "
        f"{build.production_units} planned new units; available released materials "
        f"{position['available_material_units']}. Ready plan {position['ready_at']}. "
        f"Carrier {shipment.carrier}, quote ${shipment.freight_cost_usd}, planner authority "
        f"${records['read_approval_policy'].planner_limit_usd}; booking cutoff {shipment.booking_cutoff}, "
        f"pickup {shipment.pickup_at}, transit {shipment.transit_minutes} minutes, "
        f"customer window {shipment.window_start} to {shipment.window_end}, "
        f"schedule reference {shipment.commitment_reference}. "
        f"All evidence is fictional, immutable and read-only. No hold or shipped-suspect incident exists. "
        "Check qualified capacity, material allocation, carrier/customer records, cutoffs and other "
        "committed orders. Do not invent missing approvals or guarantee execution/safety."
    )


def initial_evidence(scenario_id: ScenarioId = SCENARIO_ID) -> dict[str, dict]:
    identifier = issue_id(scenario_id)
    return {identifier: {"evidence_id": identifier, "source": "synthetic_issue", "text": issue_text(scenario_id)}}


def assessment_blockers(scenario_id: ScenarioId) -> list[str]:
    records = fixture_records(scenario_id)
    missing = sorted(set().union(*(domain_unknowns(actor, scenario_id) for actor in ALLOWLIST)))
    reasons = ["Missing canonical evidence: " + ", ".join(missing)] if missing else []
    shipment, policy = records["read_shipment"], records["read_approval_policy"]
    if scenario_id == SCENARIO_ID:
        reasons.append("Quality containment and responsible customer notification remain required.")
    else:
        options = operational_options(records)
        authorized = (any(option["freight_total_usd"] <= policy.planner_limit_usd and option["approved_carriers"]
                          for option in options.values()) if options else
                      shipment.freight_cost_usd <= policy.planner_limit_usd and shipment.approved_carrier)
        if not authorized:
            reasons.append("Carrier/freight authority requires owner review.")
    return reasons


def policy_requirements(proposal: CoordinatedProposal, records, customer_changed=False) -> list[str]:
    if records["read_inventory"].scenario_id != SCENARIO_ID:
        return operational_policy(proposal, records)
    if proposal.uses_held_stock or not proposal.containment_required:
        raise DemoError("Quality hold and shipped-lot containment cannot be bypassed.")
    required = set(proposal.approval_requests)
    required.add("quality_containment")
    if records["read_shipment"].notification_status.startswith("pending"):
        required.add("customer_notification")
    if proposal.uses_expedited_freight or proposal.recommended_action in ("expedite_freight", "seek_freight_approval"):
        if records["read_shipment"].freight_cost_usd > records["read_approval_policy"].planner_limit_usd:
            required.add("freight_authority")
    if customer_changed or proposal.changes_customer_commitment:
        required.add("customer_commitment")
    return sorted(required)


class ReleasedInventory(FixtureRecord):
    part_id: str = "MB-217 mounting bracket"
    released_lot_id: str
    released_units: int = Field(ge=0)
    allocated_finished_units: int = Field(default=0, ge=0)
    released_material_units: int = Field(default=0, ge=0)
    materials_reserved_other_orders: int = Field(default=0, ge=0)
    release_reference: str
    held_units: Literal[0] = 0


class QualifiedCell(StrictModel):
    cell_id: str
    qualification_reference: str | None
    available_from: str
    available_until: str
    staffed_shift_end: str
    setup_minutes: int = Field(ge=0)
    units_per_hour: int = Field(gt=0)
    reserved_minutes_other_orders: int = Field(default=0, ge=0)


class CommittedOrder(StrictModel):
    order_id: str
    quantity: int = Field(gt=0)
    production_from: str
    production_until: str
    delivery_at: str
    material_reserved_units: int = Field(ge=0)


class BuildOption(StrictModel):
    option_id: str = Field(min_length=1, max_length=64)
    cell: QualifiedCell
    production_units: int = Field(ge=0)
    packing_minutes: int = Field(ge=0)
    deliveries: tuple[Delivery, ...] = Field(min_length=1, max_length=2)


class OperationalBuild(FixtureRecord):
    title: str
    context: str
    customer: str = "Fictional Tier-1 customer"
    order_id: str
    deliveries: tuple[Delivery, ...]
    production_units: int = Field(ge=0)
    finished_ready_at: str | None
    machine_unavailable: str | None = None
    cell: QualifiedCell | None = None
    packing_minutes: int = Field(default=0, ge=0)
    packing_station_confirmed: bool = True
    other_orders: tuple[CommittedOrder, ...] = ()
    options: tuple[BuildOption, ...] = Field(default=(), max_length=2)


class CarrierService(StrictModel):
    shipment_id: str
    carrier: str
    service_kind: Literal["standard", "approved_alternative"] = "standard"
    approved_carrier: bool = True
    slot_confirmed: bool = True
    confirmation_reference: str | None
    original_carrier_arrival: str | None = None
    booking_cutoff: str
    pickup_at: str
    transit_minutes: int = Field(gt=0)
    window_start: str
    window_end: str
    commitment_reference: str | None
    freight_cost_usd: int = Field(ge=0)
    cost_basis: Literal["incremental_to_standing_route"] = "incremental_to_standing_route"
    expedited: bool = False


class DispatchLeg(CarrierService):
    quantity: int = Field(gt=0)


class ShipmentOption(StrictModel):
    option_id: str = Field(min_length=1, max_length=64)
    legs: tuple[DispatchLeg, ...] = Field(min_length=1, max_length=2)


class CarrierPlan(FixtureRecord, CarrierService):
    options: tuple[ShipmentOption, ...] = Field(default=(), max_length=2)


class CustomerDelivery(Delivery):
    window_start: str


class CustomerDeliveryOption(StrictModel):
    option_id: str = Field(min_length=1, max_length=64)
    reference: str = Field(min_length=1)
    deliveries: tuple[CustomerDelivery, ...] = Field(min_length=1, max_length=2)


class OperatingPolicy(FixtureRecord):
    planner_limit_usd: int = Field(default=2500, ge=0)
    carrier_roster_reference: str = "CARRIER-ROSTER-2026-10"
    overtime_approved: Literal[False] = False
    new_qualification_approved: Literal[False] = False
    customer_request_reference: str | None = None
    customer_request_quantity: int = Field(default=0, ge=0)
    customer_request_due_at: str | None = None
    customer_delivery_options: tuple[CustomerDeliveryOption, ...] = Field(default=(), max_length=2)
    execution_rule: str = "Planning only. Responsible owners execute; models perform no shipment, production or customer writes."


def operational_records(scenario_id: ScenarioId):
    suffix = scenario_id.removesuffix("-v2")
    def metadata(kind):
        return {"scenario_id": scenario_id, "evidence_id": f"fixture:{kind}:{suffix}-v2"}
    common = dict(
        confirmation_reference=f"DISPATCH-{suffix}-CONFIRMED",
        booking_cutoff="2026-10-15T16:00:00-05:00",
        pickup_at="2026-10-16T05:30:00-05:00", transit_minutes=240,
        window_start="2026-10-16T09:00:00-05:00", window_end="2026-10-16T11:00:00-05:00",
        commitment_reference="EDI-SCHEDULE-6102", freight_cost_usd=0,
    )
    if scenario_id == "carrier-delay-v2":
        inventory = ReleasedInventory(**metadata("inventory"), released_lot_id="L-1061",
                                      released_units=600, release_reference="QA-REL-1061")
        build = OperationalBuild(
            **metadata("build"), title="Carrier delay within existing authority", order_id="SO-6101",
            context="Primary carrier breakdown projects Friday 12:30, after the 09:00-11:00 window. "
                    "All 600 units are released, packed and staged. An approved alternate carrier offers a documented slot.",
            deliveries=(Delivery(order_line="10", quantity=600, due_at="2026-10-16T11:00:00-05:00"),),
            production_units=0, finished_ready_at="2026-10-15T13:30:00-05:00",
        )
        shipment = CarrierPlan(
            **metadata("shipment"), shipment_id="SH-901", carrier="Fictional approved regional carrier B",
            service_kind="approved_alternative",
            **{**common, "booking_cutoff": "2026-10-15T14:30:00-05:00",
               "pickup_at": "2026-10-15T15:00:00-05:00", "transit_minutes": 1110,
               "commitment_reference": "EDI-SCHEDULE-6101", "freight_cost_usd": 900},
            original_carrier_arrival="2026-10-16T12:30:00-05:00",
        )
        policy = OperatingPolicy(**metadata("policy"))
    elif scenario_id == "production-resequence-v2":
        inventory = ReleasedInventory(**metadata("inventory"), released_lot_id="L-1062",
                                      released_units=100, released_material_units=440,
                                      release_reference="QA-REL-FG1062-MAT4062")
        build = OperationalBuild(
            **metadata("build"), title="Choose a qualified replacement cell", order_id="SO-6102",
            context="Press P1 is unavailable until Friday 12:00. No replacement cell has been chosen. "
                    "Compare P2 (30-minute setup, 160/hour) with P3 (10-minute setup, 100/hour): "
                    "different setup effort, cell occupancy and completion margins. Both are qualified "
                    "with documented staffed slots. Stock/material allocation, the contracted pickup, "
                    "customer window and zero incremental freight are fixed for either choice.",
            deliveries=(Delivery(order_line="10", quantity=500, due_at=common["window_end"]),),
            production_units=400, finished_ready_at=None, machine_unavailable="Press P1, maintenance MT-441",
            cell=QualifiedCell(cell_id="P2", qualification_reference="PQ-MB217-P2-REV4",
                available_from="2026-10-15T14:30:00-05:00", available_until="2026-10-15T18:30:00-05:00",
                staffed_shift_end="2026-10-15T20:00:00-05:00", setup_minutes=30, units_per_hour=160),
            packing_minutes=60,
        )
        shipment = CarrierPlan(**metadata("shipment"), shipment_id="SH-902",
                               carrier="Fictional standard contracted carrier", **common)
        policy = OperatingPolicy(**metadata("policy"))
    elif scenario_id == "order-pull-forward-v2":
        inventory = ReleasedInventory(**metadata("inventory"), released_lot_id="L-1063",
                                      released_units=160, released_material_units=600,
                                      materials_reserved_other_orders=200,
                                      release_reference="QA-REL-FG1063-MAT4063")
        build = OperationalBuild(
            **metadata("build"), title="Customer-requested order pull-forward", order_id="SO-6701",
            context="Customer planning record CR-6701 asks to compare full 400 units Friday 09:00-10:00 "
                    "with a split 160 in that window and 240 Friday 14:00-16:00. Customer prefers full "
                    "early supply to avoid a second lineside receipt but explicitly permits either option "
                    "for planning; no option or dispatch has been accepted. Full early requires an $1800 "
                    "approved overnight service; split uses two standing routes at zero incremental charge. "
                    "160 finished plus 240 new units are needed. C4's setup/run must finish before the "
                    "17:00-19:00 reservation for SO-6702 (200 units, Friday 14:00 delivery); its materials "
                    "and capacity cannot be borrowed. Compare delivery benefit, capacity margin and cost.",
            deliveries=(Delivery(order_line="10", quantity=400, due_at="2026-10-16T16:00:00-05:00"),),
            production_units=240, finished_ready_at=None,
            cell=QualifiedCell(cell_id="C4", qualification_reference="PQ-MB217-C4-REV2",
                available_from="2026-10-15T14:30:00-05:00", available_until="2026-10-15T19:30:00-05:00",
                staffed_shift_end="2026-10-15T20:00:00-05:00", setup_minutes=30, units_per_hour=120,
                reserved_minutes_other_orders=120),
            packing_minutes=60,
            other_orders=(CommittedOrder(order_id="SO-6702", quantity=200,
                production_from="2026-10-15T17:00:00-05:00", production_until="2026-10-15T19:00:00-05:00",
                delivery_at="2026-10-16T14:00:00-05:00", material_reserved_units=200),),
        )
        shipment = CarrierPlan(**metadata("shipment"), shipment_id="SH-903",
            carrier="Fictional approved overnight carrier", service_kind="approved_alternative",
            **{**common, "booking_cutoff": "2026-10-15T16:30:00-05:00",
               "pickup_at": "2026-10-15T18:30:00-05:00", "transit_minutes": 900,
               "window_start": "2026-10-16T09:00:00-05:00", "window_end": "2026-10-16T10:00:00-05:00",
               "freight_cost_usd": 1800, "expedited": True, "commitment_reference": "EDI-AMENDMENT-CR-6701"})
        policy = OperatingPolicy(**metadata("policy"), customer_request_reference="EDI-AMENDMENT-CR-6701",
                                 customer_request_quantity=400, customer_request_due_at=shipment.window_end)
    else:
        raise DemoError("Unsupported operational fixture.")
    if scenario_id == "production-resequence-v2":
        cells = (
            ("cell-p2", build.cell),
            ("cell-p3", QualifiedCell(cell_id="P3", qualification_reference="PQ-MB217-P3-REV3",
                available_from="2026-10-15T14:15:00-05:00", available_until="2026-10-15T19:15:00-05:00",
                staffed_shift_end="2026-10-15T20:00:00-05:00", setup_minutes=10, units_per_hour=100)),
        )
        build = build.model_copy(update={"options": tuple(BuildOption(
            option_id=key, cell=cell, production_units=400, packing_minutes=60, deliveries=build.deliveries,
        ) for key, cell in cells)})
        service = shipment.model_dump(exclude={"scenario_id", "source", "as_of", "evidence_id", "options"})
        shipment = shipment.model_copy(update={"options": tuple(ShipmentOption(
            option_id=key, legs=(DispatchLeg(**service, quantity=500),),
        ) for key, _ in cells)})
    elif scenario_id == "order-pull-forward-v2":
        full = (Delivery(order_line="10", quantity=400, due_at="2026-10-16T10:00:00-05:00"),)
        split = (Delivery(order_line="10a", quantity=160, due_at="2026-10-16T10:00:00-05:00"),
                 Delivery(order_line="10b", quantity=240, due_at="2026-10-16T16:00:00-05:00"))
        build = build.model_copy(update={"options": tuple(BuildOption(
            option_id=key, cell=build.cell, production_units=240, packing_minutes=60, deliveries=deliveries,
        ) for key, deliveries in (("full-early", full), ("split-standard", split)))})
        service = shipment.model_dump(exclude={"scenario_id", "source", "as_of", "evidence_id", "options"})
        standard = {**service, "carrier": "Fictional standard contracted carrier", "service_kind": "standard",
                    "freight_cost_usd": 0, "transit_minutes": 240, "expedited": False}
        shipment = shipment.model_copy(update={"options": (
            ShipmentOption(option_id="full-early", legs=(DispatchLeg(**service, quantity=400),)),
            ShipmentOption(option_id="split-standard", legs=(
                DispatchLeg(**{**standard, "shipment_id": "SH-903-S1",
                    "booking_cutoff": "2026-10-15T16:00:00-05:00", "pickup_at": "2026-10-16T05:30:00-05:00"},
                    quantity=160),
                DispatchLeg(**{**standard, "shipment_id": "SH-903-S2",
                    "booking_cutoff": "2026-10-16T09:00:00-05:00", "pickup_at": "2026-10-16T10:00:00-05:00",
                    "window_start": "2026-10-16T14:00:00-05:00", "window_end": "2026-10-16T16:00:00-05:00"},
                    quantity=240),
            )),
        )})
        policy = policy.model_copy(update={"customer_delivery_options": tuple(CustomerDeliveryOption(
            option_id=key, reference="EDI-AMENDMENT-CR-6701", deliveries=tuple(
                CustomerDelivery(**delivery.model_dump(), window_start=(
                    "2026-10-16T09:00:00-05:00" if index == 0 else "2026-10-16T14:00:00-05:00"
                )) for index, delivery in enumerate(deliveries)
            ),
        ) for key, deliveries in (("full-early", full), ("split-standard", split)))})
    return MappingProxyType({
        "read_inventory": inventory, "read_shipment": shipment,
        "read_build": build, "read_approval_policy": policy,
    })


def fixture_payload(record):
    data = record.model_dump(mode="json")
    if isinstance(record, OperationalBuild) and record.options:
        for key in ("cell", "production_units", "packing_minutes", "deliveries"):
            data.pop(key)
    elif isinstance(record, CarrierPlan) and record.options:
        for key in CarrierService.model_fields:
            data.pop(key)
    elif isinstance(record, OperatingPolicy) and record.customer_delivery_options:
        data.pop("customer_request_due_at")
    return data


def operational_position(records):
    stock, build, shipment = (records[name] for name in ("read_inventory", "read_build", "read_shipment"))
    cell = build.cell
    minutes = ceil(build.production_units * 60 / cell.units_per_hour) + cell.setup_minutes if cell else 0
    ready = (datetime.fromisoformat(cell.available_from) + timedelta(minutes=minutes + build.packing_minutes)
             if cell else datetime.fromisoformat(build.finished_ready_at) if build.finished_ready_at else None)
    available = ((min(datetime.fromisoformat(cell.available_until), datetime.fromisoformat(cell.staffed_shift_end))
                  - datetime.fromisoformat(cell.available_from)).total_seconds() / 60
                 - cell.reserved_minutes_other_orders if cell else 0)
    return {
        "demand_units": sum(d.quantity for d in build.deliveries),
        "available_stock_units": stock.released_units - stock.allocated_finished_units,
        "available_material_units": stock.released_material_units - stock.materials_reserved_other_orders,
        "production_minutes": minutes, "available_cell_minutes": available,
        "ready_at": ready.isoformat() if ready else None,
        "arrival_at": (datetime.fromisoformat(shipment.pickup_at) + timedelta(minutes=shipment.transit_minutes)).isoformat(),
    }


def routing_context(scenario_id: ScenarioId):
    records = fixture_records(scenario_id)
    policy = records["read_approval_policy"]
    context = {
        "source": "derived_synthetic_fixture",
        "decision_status": {},
        "observed_records": {
            "evidence_ids": [record.evidence_id for record in records.values()],
            "planner_limit_usd": policy.planner_limit_usd,
            "source": "synthetic_fixture",
        },
        "unresolved_preferences": {},
        "known_unknowns_by_role": {
            actor: sorted(domain_unknowns(actor, scenario_id)) for actor in ALLOWLIST
        },
        "no_execution_authority": True,
    }
    if scenario_id == SCENARIO_ID:
        position = delivery_position()
        context["decision_status"] = {
            "state": "business_questions_open", "selected_option_id": None, "alternative_ids": [],
            "objective": "Assess shipped-lot containment and delivery recovery separately; business questions remain open.",
        }
        context["observed_records"]["hold_cannot_be_lifted_by_demo"] = True
        context["calculated_feasibility"] = {
            "baseline_delivery_shortfall": position.baseline_gap,
            "scheduled_units": position.total_demand, "released_units": position.released_units,
        }
        return context
    build = records["read_build"]
    checks = operational_checks(records)
    context["applicability"] = {
        "qualified_cell": build.production_units > 0,
        "customer_pull_forward_request": scenario_id == "order-pull-forward-v2",
    }
    context["calculated_feasibility"] = {"checks": checks}
    if build.options:
        context["calculated_feasibility"]["unselected_options"] = operational_options(records)
        context["decision_status"] = {
            "state": "choice_required", "selected_option_id": None,
            "alternative_ids": [option.option_id for option in build.options],
            "objective": "Choose between qualified cells: compare setup effort, processing time and readiness margin. "
                         "Material allocation, transport and customer windows are fixed for either choice.",
        }
        if scenario_id == "order-pull-forward-v2":
            context["decision_status"]["objective"] = (
                "Choose full-early versus split-standard; neither has been selected. Balance customer receipt "
                "preference, incremental freight and shared production/readiness/other-order reservations. "
                "Feasibility being established does not make this tradeoff decision complete."
            )
            context["observed_records"]["customer_planning_permission"] = {
                "reference": policy.customer_request_reference,
                "permitted_option_ids": [option.option_id for option in policy.customer_delivery_options],
                "stated_preference": "Full early supply to avoid a second lineside receipt; split is permitted for planning.",
            }
            context["unresolved_preferences"] = {
                "second_receipt_monetary_value_usd": None,
                "decision_question": "How to weigh the recorded receipt preference against incremental freight.",
                "not_a_mandatory_missing_approval": True,
            }
    else:
        shipment = records["read_shipment"]
        resolved = all(checks.values()) and shipment.approved_carrier and shipment.freight_cost_usd <= policy.planner_limit_usd
        context["calculated_feasibility"]["position"] = operational_position(records)
        context["decision_status"] = {
            "state": "resolved_record" if resolved else "business_questions_open",
            "selected_option_id": None, "alternative_ids": [],
            "objective": ("Review established recovery facts; no outstanding alternative choice is supplied."
                          if resolved else "Assess unsupported recovery evidence and required owner handoffs."),
        }
    return context


def operational_options(records):
    build, shipment, policy = (records[name] for name in ("read_build", "read_shipment", "read_approval_policy"))
    builds = {option.option_id: option for option in build.options}
    shipments = {option.option_id: option for option in shipment.options}
    if len(builds) != len(build.options) or len(shipments) != len(shipment.options) or set(builds) != set(shipments):
        raise DemoError("Planning options must have unique matching build/shipment identifiers.")
    output = {}
    for key, option in builds.items():
        legs = shipments[key].legs
        if not legs or len(legs) != len(option.deliveries):
            raise DemoError("Every planning delivery must have exactly one matching shipment leg.")
        projected_build = build.model_copy(update={
            "cell": option.cell, "production_units": option.production_units,
            "packing_minutes": option.packing_minutes, "deliveries": option.deliveries, "options": (),
        })
        checks, positions = [], []
        customer = next((c for c in policy.customer_delivery_options if c.option_id == key), None)
        for index, (leg, delivery) in enumerate(zip(legs, option.deliveries)):
            projected_shipment = shipment.model_copy(update={**leg.model_dump(exclude={"quantity"}), "options": ()})
            projected_policy = policy.model_copy(update={
                "customer_request_due_at": delivery.due_at,
            })
            projected = {**records, "read_build": projected_build, "read_shipment": projected_shipment,
                         "read_approval_policy": projected_policy}
            position = operational_position(projected)
            check = _single_operational_checks(projected)
            check["delivery_window"] &= leg.quantity == delivery.quantity
            if records["read_inventory"].scenario_id == "order-pull-forward-v2":
                documented = customer.deliveries if customer else ()
                check["customer_request"] &= (
                    customer is not None and customer.reference == leg.commitment_reference
                    and len(documented) == len(option.deliveries)
                    and all(c.model_dump(exclude={"window_start"}) == d.model_dump()
                            for c, d in zip(documented, option.deliveries))
                )
                check["delivery_window"] &= index < len(documented) and (
                    datetime.fromisoformat(documented[index].window_start)
                    <= datetime.fromisoformat(position["arrival_at"])
                    <= datetime.fromisoformat(documented[index].due_at)
                )
            checks.append(check)
            positions.append(position)
        output[key] = {
            "position": positions[0],
            "checks": {name: all(check[name] for check in checks) for name in checks[0]},
            "leg_quantities": [leg.quantity for leg in legs],
            "arrivals": [position["arrival_at"] for position in positions],
            "freight_total_usd": sum(leg.freight_cost_usd for leg in legs),
            "approved_carriers": all(leg.approved_carrier for leg in legs),
            "service_kinds": [leg.service_kind for leg in legs],
            "dependencies": {
                "uses_alternative_carrier": any(leg.service_kind == "approved_alternative" for leg in legs),
                "uses_expedited_freight": any(leg.expedited for leg in legs),
                "uses_alternative_cell": bool(build.machine_unavailable),
                "pulls_order_forward": bool(policy.customer_request_reference),
                "requires_overtime": datetime.fromisoformat(positions[0]["ready_at"])
                                     > datetime.fromisoformat(option.cell.staffed_shift_end),
                "displaces_other_orders": not all(check["other_order_impact"] for check in checks),
            },
        }
    return output


def option_disagreements(proposal, records):
    selected = operational_options(records).get(proposal.selected_option_id)
    if selected is None:
        return []
    return [f"Selected-option contradiction: {key}={getattr(proposal, key)}; "
            f"canonical {proposal.selected_option_id} records support {value}."
            for key, value in selected["dependencies"].items() if getattr(proposal, key) != value]


def scoped_option_disagreements(finding: ScopedFinding, records, option_id: str) -> list[str]:
    assessment = option_assessment(finding, option_id)
    selected = operational_options(records)[option_id]
    expected = dict(selected["dependencies"])
    if selected["checks"]["customer_request"] and selected["checks"]["delivery_window"]:
        expected["changes_customer_commitment"] = False
    measurements = {}
    if isinstance(assessment, SupplyOptionAssessment):
        measurements["freight_total_usd"] = selected["freight_total_usd"]
    elif isinstance(assessment, ProductionOptionAssessment):
        build = next(option for option in records["read_build"].options if option.option_id == option_id)
        measurements.update(
            required_cell_minutes=selected["position"]["production_minutes"],
            available_cell_minutes=selected["position"]["available_cell_minutes"],
            packing_minutes=build.packing_minutes,
            ready_at=datetime.fromisoformat(selected["position"]["ready_at"]),
        )
    reasons = []
    values = {**dependency_claims(assessment), **{key: getattr(assessment, key) for key in measurements}}
    for key, value in values.items():
        label = f"{finding.agent_id}/{option_id} {key}"
        if value is None:
            reasons.append(f"Scoped evidence unknown: {label}.")
        else:
            canonical = measurements.get(key, expected.get(key))
            if canonical is not None and value != canonical:
                reasons.append(f"Scoped evidence contradiction: {label}={value}; canonical records support {canonical}.")
    return reasons


def operational_checks(records, option_id=None):
    if records["read_build"].options:
        options = operational_options(records)
        if option_id is not None:
            if option_id not in options:
                raise DemoError("Proposal selected a planning option absent from canonical evidence.")
            return options[option_id]["checks"]
        feasible = [option for option in options.values() if all(option["checks"].values())]
        return {key: bool(feasible) or all(option["checks"][key] for option in options.values())
                for key in next(iter(options.values()))["checks"]}
    if option_id is not None:
        raise DemoError("This case has no selectable planning options.")
    return _single_operational_checks(records)


def _single_operational_checks(records):
    stock, build, shipment, policy = (records[name] for name in
                                     ("read_inventory", "read_build", "read_shipment", "read_approval_policy"))
    position, cell = operational_position(records), build.cell
    ready = datetime.fromisoformat(position["ready_at"]) if position["ready_at"] else None
    arrival = datetime.fromisoformat(position["arrival_at"])
    other_ok = not build.other_orders or bool(cell) and (
        sum(o.material_reserved_units for o in build.other_orders) == stock.materials_reserved_other_orders
        and sum((datetime.fromisoformat(o.production_until) - datetime.fromisoformat(o.production_from)).total_seconds() / 60
                for o in build.other_orders) == cell.reserved_minutes_other_orders
        and all(datetime.fromisoformat(cell.available_from) + timedelta(minutes=position["production_minutes"])
                <= datetime.fromisoformat(o.production_from) < datetime.fromisoformat(o.production_until)
                <= datetime.fromisoformat(cell.available_until)
                and o.material_reserved_units >= o.quantity
                and (datetime.fromisoformat(o.production_until) - datetime.fromisoformat(o.production_from)).total_seconds() / 60
                    >= ceil(o.quantity * 60 / cell.units_per_hour)
                and datetime.fromisoformat(o.production_until) < datetime.fromisoformat(o.delivery_at)
                for o in build.other_orders)
    )
    return {
        "carrier_confirmation": shipment.slot_confirmed and bool(shipment.confirmation_reference),
        "delivery_window": bool(shipment.commitment_reference) and ready is not None
            and datetime.fromisoformat(SNAPSHOT) <= datetime.fromisoformat(shipment.booking_cutoff)
            < datetime.fromisoformat(shipment.pickup_at)
            and ready <= datetime.fromisoformat(shipment.pickup_at)
            and datetime.fromisoformat(shipment.window_start) <= arrival <= datetime.fromisoformat(shipment.window_end)
            and datetime.fromisoformat(shipment.window_end) <= datetime.fromisoformat(
                policy.customer_request_due_at if policy.customer_request_due_at else build.deliveries[0].due_at),
        "qualified_cell": not build.production_units or cell is not None and bool(cell.qualification_reference),
        "production_capacity": position["available_stock_units"] + build.production_units >= position["demand_units"]
            and build.packing_station_confirmed and ready is not None
            and (not build.production_units or cell is not None
                 and position["production_minutes"] <= position["available_cell_minutes"]
                 and datetime.fromisoformat(cell.available_from) >= datetime.fromisoformat(SNAPSHOT)
                 and ready <= datetime.fromisoformat(cell.staffed_shift_end)),
        "material_allocation": position["available_stock_units"] >= 0
            and position["available_material_units"] >= build.production_units,
        "customer_request": stock.scenario_id != "order-pull-forward-v2" or
            bool(policy.customer_request_reference) and policy.customer_request_reference == shipment.commitment_reference
            and policy.customer_request_quantity == position["demand_units"]
            and policy.customer_request_due_at == shipment.window_end,
        "other_order_impact": bool(other_ok),
    }


def operational_policy(proposal, records):
    if proposal.uses_held_stock:
        raise DemoError("Held stock cannot be used by any scenario.")
    required = set(proposal.approval_requests)
    checks = operational_checks(records, proposal.selected_option_id)
    shipment, policy = records["read_shipment"], records["read_approval_policy"]
    options = operational_options(records)
    selected = options.get(proposal.selected_option_id)
    cost = selected["freight_total_usd"] if selected else shipment.freight_cost_usd
    approved = selected["approved_carriers"] if selected else shipment.approved_carrier
    standard = all(kind == "standard" for kind in selected["service_kinds"]) if selected else shipment.service_kind == "standard"
    if cost > policy.planner_limit_usd or not approved or not checks["carrier_confirmation"]:
        required.add("freight_authority")
    if standard and (
        proposal.uses_expedited_freight or proposal.uses_alternative_carrier
        or proposal.recommended_action in ("expedite_freight", "switch_approved_carrier")
    ):
        required.add("freight_authority")
    if proposal.recommended_action == "seek_freight_approval":
        required.add("freight_authority")
    if (
        not checks["delivery_window"] or not checks["customer_request"]
        or proposal.changes_customer_commitment or proposal.displaces_other_orders
        or proposal.recommended_action == "request_customer_window"
    ):
        required.add("customer_commitment")
    if not all(checks[key] for key in ("production_capacity", "qualified_cell", "material_allocation", "other_order_impact")) or proposal.requires_overtime:
        required.add("production_authority")
    cell = next((option.cell for option in records["read_build"].options
                 if option.option_id == proposal.selected_option_id), records["read_build"].cell)
    if (proposal.uses_alternative_cell or proposal.recommended_action == "use_qualified_cell") and (
        cell is None or not cell.qualification_reference
    ):
        required.add("production_authority")
    if (proposal.pulls_order_forward or proposal.recommended_action == "accept_requested_window") and not policy.customer_request_reference:
        required.add("customer_commitment")
    if proposal.containment_required:
        required.add("quality_containment")
    return sorted(required)
