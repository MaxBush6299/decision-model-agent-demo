from types import MappingProxyType
from typing import Literal

from pydantic import Field

from .contracts import CoordinatedProposal, StrictModel, ISSUE_ID

ISSUE = (
    "Synthetic parts shortage. Tomorrow requires 480 assemblies; material for 310 "
    "is available (shortfall 170). Remaining shipment is delayed without confirmed "
    "arrival. Freight costs $4,200 versus planner authority $2,500. An alternate "
    "is not engineering-approved. Recovery capacity and customer commitment are "
    "unknown. Compare feasible next steps; never authorize freight, substitute "
    "unapproved parts, claim safety, or invent facts."
)
ALLOWLIST = {
    "supply-chain": ("read_inventory", "read_shipment"),
    "production": ("read_inventory", "read_build"),
    "commercial": ("read_shipment", "read_approval_policy"),
}
DOMAIN_UNKNOWNS = {
    "supply-chain": ("shipment_arrival",),
    "production": ("shipment_arrival", "recovery_capacity_assemblies"),
    "commercial": ("customer_commitment",),
}


class FixtureRecord(StrictModel):
    scenario_id: Literal["parts-shortage-v2"] = "parts-shortage-v2"
    source: Literal["synthetic_fixture"] = "synthetic_fixture"
    evidence_id: str


class Inventory(FixtureRecord):
    required_assemblies: Literal[480] = 480
    available_assemblies: Literal[310] = 310
    shortfall_assemblies: Literal[170] = 170
    alternate_engineering_approved: Literal[False] = False


class Shipment(FixtureRecord):
    status: Literal["delayed"] = "delayed"
    confirmed_arrival: str | None = None
    freight_cost_usd: int | None = Field(default=4200, ge=0)


class Build(FixtureRecord):
    build_window: Literal["tomorrow"] = "tomorrow"
    required_assemblies: Literal[480] = 480
    recovery_capacity_assemblies: int | None = Field(default=None, ge=0)


class ApprovalPolicy(FixtureRecord):
    planner_limit_usd: int | None = Field(default=2500, ge=0)
    freight_approval_required_above_limit: Literal[True] = True
    alternate_requires_engineering_approval: Literal[True] = True
    customer_commitment: str | None = None


def fixture_records():
    return MappingProxyType({
        "read_inventory": Inventory(evidence_id="fixture:inventory:v1"),
        "read_shipment": Shipment(evidence_id="fixture:shipment:v1"),
        "read_build": Build(evidence_id="fixture:build:v1"),
        "read_approval_policy": ApprovalPolicy(evidence_id="fixture:policy:v1"),
    })


def initial_evidence() -> dict[str, dict]:
    return {ISSUE_ID: {"evidence_id": ISSUE_ID, "source": "synthetic_issue", "text": ISSUE}}


def policy_requirements(proposal: CoordinatedProposal, records, customer_changed=False) -> list[str]:
    required = set(proposal.approval_requests)
    if proposal.recommended_action in ("expedite_freight", "seek_freight_approval"):
        cost = records["read_shipment"].freight_cost_usd
        limit = records["read_approval_policy"].planner_limit_usd
        if cost is None or limit is None or cost > limit:
            required.add("freight_authority")
    if proposal.recommended_action == "engineering_review" or proposal.uses_alternate:
        required.add("engineering")
    if customer_changed or proposal.changes_customer_commitment:
        required.add("customer_commitment")
    return sorted(required)
