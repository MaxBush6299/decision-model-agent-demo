from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Literal
from collections.abc import Iterable

from pydantic import Field, model_validator

from .contracts import (
    CoordinatedProposal, CustomerDeliveryChange, DemoError, HumanEvidence,
    StrictModel, ISSUE_ID,
)

SNAPSHOT = "2026-10-15T14:00:00-05:00"
ALLOWLIST = {
    "supply-chain": ("read_inventory", "read_shipment"),
    "production": ("read_inventory", "read_build"),
    "commercial": ("read_shipment", "read_approval_policy"),
}


class FixtureRecord(StrictModel):
    scenario_id: Literal["quality-hold-v2"] = "quality-hold-v2"
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


def fixture_records():
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


def domain_unknowns(actor: str) -> set[str]:
    records = fixture_records()
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


def authoritative_constraints() -> dict:
    records = fixture_records()
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


def initial_evidence() -> dict[str, dict]:
    return {ISSUE_ID: {"evidence_id": ISSUE_ID, "source": "synthetic_issue", "text": ISSUE}}


def policy_requirements(proposal: CoordinatedProposal, records, customer_changed=False) -> list[str]:
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
