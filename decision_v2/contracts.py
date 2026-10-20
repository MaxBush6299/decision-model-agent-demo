import math
from datetime import datetime
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

AGENTS = ("supply-chain", "production", "commercial")
SELECTION_OPTIONS = ("needed", "not_needed", "cannot_determine")
ASSESSMENT_OPTIONS = ("assessment_needed", "no_further_assessment", "cannot_determine")
VALIDATION_OPTIONS = ("Addresses the issue", "Needs revision", "Cannot determine")
SCENARIO_ID = "quality-hold-v2"
ScenarioId = Literal["quality-hold-v2", "carrier-delay-v2", "production-resequence-v2", "order-pull-forward-v2"]
SCENARIO_IDS = ("quality-hold-v2", "carrier-delay-v2", "production-resequence-v2", "order-pull-forward-v2")
ISSUE_ID = "issue:quality-hold-v2"
THRESHOLD = .70
AgentId = Literal["supply-chain", "production", "commercial"]
Action = Literal[
    "seek_freight_approval", "expedite_freight", "resequence_build",
    "contain_and_recover", "request_customer_window", "gather_information",
    "switch_approved_carrier", "use_qualified_cell", "accept_requested_window",
]
Approval = Literal["freight_authority", "quality_containment", "customer_notification", "customer_commitment", "production_authority"]
UnknownKey = Literal[
    "shipment_arrival", "incoming_acceptance", "customer_disposition",
    "customer_delivery_change", "proposal_feedback",
    "carrier_confirmation", "delivery_window", "production_capacity", "qualified_cell",
    "material_allocation", "customer_request", "other_order_impact",
]
SCOPED_UNKNOWN_OWNERS = MappingProxyType({
    "shipment_arrival": "supply-chain",
    "incoming_acceptance": "supply-chain",
    "carrier_confirmation": "supply-chain",
    "delivery_window": "supply-chain",
    "material_allocation": "supply-chain",
    "production_capacity": "production",
    "qualified_cell": "production",
    "other_order_impact": "production",
    "customer_disposition": "commercial",
    "customer_delivery_change": "commercial",
    "customer_request": "commercial",
    "proposal_feedback": "coordinator",
})
Text = Annotated[str, Field(min_length=1, max_length=2000)]
EvidenceId = Annotated[str, Field(min_length=1, max_length=120)]


def owned_scoped_unknowns(actor: str) -> set[str]:
    return {key for key, owner in SCOPED_UNKNOWN_OWNERS.items() if owner == actor}


class DemoError(RuntimeError):
    """Explicit execution or model-contract failure; never acceptance."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    @field_validator("*")
    @classmethod
    def nonempty_text(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("Text must not be blank.")
        return value


class ChoiceAnswer(StrictModel):
    selected: str
    probabilities: dict[str, float]
    confidence: float | None = None

    @field_validator("probabilities", mode="before")
    @classmethod
    def check_scores(cls, value):
        if not isinstance(value, dict) or any(
            isinstance(v, bool) or not isinstance(v, (int, float))
            or not math.isfinite(v) or not 0 <= v <= 1 for v in value.values()
        ):
            raise ValueError("Probabilities must be finite numbers in [0,1].")
        return value

    @field_validator("confidence", mode="before")
    @classmethod
    def check_confidence(cls, value):
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not 0 <= value <= 1
        ):
            raise ValueError("Confidence must be a finite number in [0,1].")
        return value

    @model_validator(mode="after")
    def check_distribution(self):
        keys = set(self.probabilities)
        if keys not in (set(SELECTION_OPTIONS), set(VALIDATION_OPTIONS), set(ASSESSMENT_OPTIONS)):
            raise ValueError("Complete known option distribution required.")
        if self.selected not in keys or not math.isclose(
            sum(self.probabilities.values()), 1, abs_tol=.001,
        ):
            raise ValueError("Selected option or probability sum invalid.")
        return self

    @property
    def satisfactory(self) -> bool:
        score = self.probabilities[self.selected]
        return score >= THRESHOLD and all(
            score > value for key, value in self.probabilities.items() if key != self.selected
        )

    @property
    def effective(self) -> str:
        return self.selected if self.satisfactory else "cannot_determine"


def parse_choices(payload: object, names: list[str], options: tuple[str, ...]) -> dict[str, ChoiceAnswer]:
    from pydantic import ValidationError
    answers = payload.get("answers") if isinstance(payload, dict) else None
    if not isinstance(answers, dict) or set(answers) != set(names):
        raise DemoError("Decision-1 did not return exactly the requested answers.")
    result = {}
    for name in names:
        answer = answers[name]
        if not isinstance(answer, dict) or answer.get("type") != "choice":
            raise DemoError(f"Decision-1 answer {name} is not a choice.")
        try:
            parsed = ChoiceAnswer(
                selected=answer.get("choice"), probabilities=answer.get("probabilities"),
                confidence=answer.get("confidence"),
            )
        except ValidationError as exc:
            raise DemoError(f"Decision-1 answer {name} violates its probability contract.") from exc
        if set(parsed.probabilities) != set(options):
            raise DemoError(f"Decision-1 answer {name} has the wrong options.")
        result[name] = parsed
    return result


class Conflict(StrictModel):
    subject_key: UnknownKey
    evidence_ids: list[EvidenceId] = Field(min_length=1, max_length=12)
    description: str = Field(min_length=1)


class FindingRef(StrictModel):
    agent_id: AgentId
    revision: Literal[0, 1]

    @field_validator("revision", mode="before")
    @classmethod
    def integer_revision(cls, value):
        if type(value) is not int:
            raise ValueError("Revision must be an integer, not a boolean.")
        return value


class PlanDependencies(StrictModel):
    uses_alternative_carrier: bool = False
    uses_alternative_cell: bool = False
    pulls_order_forward: bool = False
    requires_overtime: bool = False
    displaces_other_orders: bool = False


class ExpertFinding(PlanDependencies):
    agent_id: AgentId
    revision: Literal[0, 1]
    selected_option_id: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    assessment: Annotated[str, Field(min_length=1)]
    implication: Annotated[str, Field(min_length=1)]
    recommended_action: Action
    uses_held_stock: bool
    uses_expedited_freight: bool
    containment_required: bool
    changes_customer_commitment: bool
    evidence_ids: list[EvidenceId] = Field(min_length=1, max_length=12)
    unknown_keys: list[UnknownKey] = Field(max_length=12)
    approval_requests: list[Approval] = Field(max_length=12)
    conflicts: list[Conflict] = Field(max_length=6)

    @field_validator("revision", mode="before")
    @classmethod
    def integer_revision(cls, value):
        return FindingRef.integer_revision(value)


class OptionEvidence(StrictModel):
    option_id: Annotated[str, Field(min_length=1, max_length=64)]
    assessment: Annotated[str, Field(min_length=1)]
    evidence_ids: list[EvidenceId] = Field(min_length=1, max_length=12)


class SupplyOptionAssessment(OptionEvidence):
    freight_total_usd: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None
    uses_alternative_carrier: bool | None
    uses_expedited_freight: bool | None


class ProductionOptionAssessment(OptionEvidence):
    required_cell_minutes: Annotated[int, Field(ge=0)] | None
    available_cell_minutes: Annotated[int, Field(ge=0)] | None
    packing_minutes: Annotated[int, Field(ge=0)] | None
    ready_at: AwareDatetime | None
    uses_alternative_cell: bool | None
    requires_overtime: bool | None
    displaces_other_orders: bool | None


class CommercialOptionAssessment(OptionEvidence):
    pulls_order_forward: bool | None
    changes_customer_commitment: bool | None


class ScopedFindingBase(StrictModel):
    revision: Literal[0, 1]
    assessment: Annotated[str, Field(min_length=1)]
    implication: Annotated[str, Field(min_length=1)]
    preferred_option_id: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    uses_held_stock: bool
    containment_required: bool
    safety_approval_requests: list[Literal["quality_containment", "customer_notification"]] = Field(max_length=2)
    evidence_ids: list[EvidenceId] = Field(min_length=1, max_length=12)
    unknown_keys: list[UnknownKey] = Field(max_length=12)
    conflicts: list[Conflict] = Field(max_length=6)

    @field_validator("revision", mode="before")
    @classmethod
    def integer_revision(cls, value):
        return FindingRef.integer_revision(value)

    @classmethod
    def model_json_schema(cls, *args, **kwargs):
        schema = super().model_json_schema(*args, **kwargs)
        # Foundry's wire-schema subset differs from local Pydantic validation.
        unsupported = {
            "minLength", "maxLength", "pattern", "format", "minimum", "maximum", "multipleOf",
            "patternProperties", "unevaluatedProperties", "propertyNames", "minProperties", "maxProperties",
            "unevaluatedItems", "contains", "minContains", "maxContains", "minItems", "maxItems", "uniqueItems",
        }
        def restrict(node):
            for key in unsupported:
                node.pop(key, None)
            for group in ("properties", "$defs"):
                for child in node.get(group, {}).values():
                    restrict(child)
            if isinstance(node.get("items"), dict):
                restrict(node["items"])
            for group in ("anyOf", "allOf", "oneOf"):
                for child in node.get(group, []):
                    restrict(child)
        restrict(schema)
        return schema


class SupplyFinding(ScopedFindingBase):
    agent_id: Literal["supply-chain"]
    option_assessments: list[SupplyOptionAssessment] = Field(min_length=2, max_length=2)


class ProductionFinding(ScopedFindingBase):
    agent_id: Literal["production"]
    option_assessments: list[ProductionOptionAssessment] = Field(min_length=2, max_length=2)


class CommercialFinding(ScopedFindingBase):
    agent_id: Literal["commercial"]
    option_assessments: list[CommercialOptionAssessment] = Field(min_length=2, max_length=2)


OptionAssessment = SupplyOptionAssessment | ProductionOptionAssessment | CommercialOptionAssessment
ScopedFinding = SupplyFinding | ProductionFinding | CommercialFinding
Finding = ExpertFinding | ScopedFinding


def validate_option_finding(finding: ScopedFinding, option_ids: set[str], allowed: set[str]) -> None:
    foreign = set(finding.unknown_keys) - owned_scoped_unknowns(finding.agent_id)
    if foreign:
        details = ", ".join(f"{key} (owner: {SCOPED_UNKNOWN_OWNERS[key]})" for key in sorted(foreign))
        raise DemoError(f"{finding.agent_id} raised foreign-domain unknown_keys: {details}; no repair was made.")
    ids = [assessment.option_id for assessment in finding.option_assessments]
    if len(ids) != len(set(ids)) or set(ids) != option_ids:
        raise DemoError("Specialist must assess each supplied planning option exactly once.")
    if finding.preferred_option_id is not None and finding.preferred_option_id not in option_ids:
        raise DemoError("Specialist preference is absent from supplied planning options.")
    validate_references(finding, allowed)
    for assessment in finding.option_assessments:
        if not set(assessment.evidence_ids).issubset(allowed):
            raise DemoError("Option assessment cites evidence absent from its supplied ledger.")


def option_assessment(finding: ScopedFinding, option_id: str) -> OptionAssessment:
    for assessment in finding.option_assessments:
        if assessment.option_id == option_id:
            return assessment
    raise DemoError("Specialist omitted the selected planning option.")


def dependency_claims(assessment: OptionAssessment) -> dict[str, bool | None]:
    if isinstance(assessment, SupplyOptionAssessment):
        names = ("uses_alternative_carrier", "uses_expedited_freight")
    elif isinstance(assessment, ProductionOptionAssessment):
        names = ("uses_alternative_cell", "requires_overtime", "displaces_other_orders")
    else:
        names = ("pulls_order_forward", "changes_customer_commitment")
    return {name: getattr(assessment, name) for name in names}


class CoordinatedProposal(PlanDependencies):
    revision: Literal[0, 1]
    selected_option_id: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    recommended_action: Action
    uses_held_stock: bool
    uses_expedited_freight: bool
    containment_required: bool
    changes_customer_commitment: bool
    brief: Annotated[str, Field(min_length=1)]
    finding_refs: list[FindingRef] = Field(max_length=3)
    evidence_ids: list[EvidenceId] = Field(max_length=12)
    unknown_keys: list[UnknownKey] = Field(max_length=12)
    approval_requests: list[Approval] = Field(max_length=12)
    conflicts: list[Conflict] = Field(max_length=6)

    @field_validator("revision", mode="before")
    @classmethod
    def integer_revision(cls, value):
        return FindingRef.integer_revision(value)


AFFECTED = {
    "customer_delivery_change": ("production", "commercial"),
}


class CustomerDeliveryChange(StrictModel):
    customer_agreed: bool
    quantity: int = Field(ge=0)
    revised_delivery_at: datetime | None
    reference: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def check_window(self):
        if not self.customer_agreed:
            if self.quantity != 0 or self.revised_delivery_at is not None:
                raise ValueError("No agreement cannot move any delivery.")
        elif (
            self.quantity <= 0 or self.revised_delivery_at is None
            or self.revised_delivery_at.utcoffset() is None
        ):
            raise ValueError("Reported agreement requires positive quantity and an offset-aware delivery time.")
        return self


class HumanResponse(StrictModel):
    kind: Literal["clarify", "reject", "escalate"]
    updates: dict[str, CustomerDeliveryChange] = Field(default_factory=dict, max_length=1)

    @model_validator(mode="after")
    def check_updates(self):
        if self.kind != "clarify":
            if self.updates:
                raise ValueError("Only clarification can carry updates.")
            return self
        if not self.updates:
            raise ValueError("Clarification requires evidence.")
        for key, value in self.updates.items():
            if key not in AFFECTED:
                raise ValueError("Unsupported clarification key.")
        return self


class HumanEvidence(StrictModel):
    evidence_id: EvidenceId
    key: str
    value: CustomerDeliveryChange
    source: Literal["human_clarification"] = "human_clarification"
    request_id: str
    revision: Literal[1] = 1


@dataclass(frozen=True)
class ClarificationRequest:
    revision: int
    allowed_keys: tuple[str, ...]
    uncertain_agents: tuple[str, ...]
    reasons: tuple[str, ...]
    proposal: CoordinatedProposal | None
    request_id: str = ""
    scenario_id: ScenarioId = SCENARIO_ID


PROSE_REVIEW_PREFIX = "Prose review required: "


@dataclass(frozen=True)
class FinalResult:
    status: str
    code: int
    reasons: tuple[str, ...]
    proposal: CoordinatedProposal | None
    warnings: tuple["ProseWarning", ...] = ()


@dataclass(frozen=True)
class ProseWarning:
    """Host-owned, non-authoritative flag for a prose claim the narrow checks could not verify."""
    actor: str
    field: str
    claim: str
    rule_id: str
    expected: str


@dataclass
class RunState:
    revision: int = 0
    prose_warnings: dict[str, tuple[ProseWarning, ...]] = field(default_factory=dict)
    selections: dict[str, ChoiceAnswer] = field(default_factory=dict)
    active: list[str] = field(default_factory=list)
    uncertain: list[str] = field(default_factory=list)
    findings: dict[str, Finding] = field(default_factory=dict)
    overlays: list[HumanEvidence] = field(default_factory=list)
    proposal: CoordinatedProposal | None = None
    validation: ChoiceAnswer | None = None
    policies: list[str] = field(default_factory=list)
    evidence: dict[str, dict] = field(default_factory=dict)
    continuation_used: bool = False
    refresh: list[str] = field(default_factory=list)
    scenario_id: ScenarioId = SCENARIO_ID
    assessment: ChoiceAnswer | None = None
    assessment_required: bool = True


def affected_agents(response: HumanResponse, active: list[str], uncertain: list[str]) -> list[str]:
    selected = set()
    for key in response.updates:
        selected.update(active or uncertain if key == "proposal_feedback" else AFFECTED[key])
    return [agent for agent in AGENTS if agent in selected]


def validate_references(output: Finding | CoordinatedProposal, allowed: set[str]) -> None:
    citations = set(output.evidence_ids)
    for conflict in output.conflicts:
        citations.update(conflict.evidence_ids)
    if not citations.issubset(allowed):
        raise DemoError("Agent returned evidence IDs absent from the supplied evidence ledger.")


def validate_proposal(proposal: CoordinatedProposal, state: RunState) -> None:
    if proposal.revision != state.revision:
        raise DemoError("Coordinator returned the wrong revision.")
    refs = [(ref.agent_id, ref.revision) for ref in proposal.finding_refs]
    expected = [(a, state.findings[a].revision) for a in state.active]
    if len(refs) != len(expected) or set(refs) != set(expected):
        raise DemoError("Coordinator omitted or duplicated a participating finding.")
    validate_references(proposal, set(state.evidence))
    findings = [state.findings[a] for a in state.active]
    legacy = [f for f in findings if isinstance(f, ExpertFinding)]
    scoped = [f for f in findings if isinstance(f, ScopedFinding)]
    applicable = [f for f in legacy if proposal.selected_option_id is None
                  or f.selected_option_id in (None, proposal.selected_option_id)]
    if proposal.uses_held_stock or (state.scenario_id == SCENARIO_ID and not proposal.containment_required):
        raise DemoError("Coordinator cannot release held stock or omit shipped-lot containment.")
    for field_name in (
        "containment_required", "uses_expedited_freight", "changes_customer_commitment",
        *PlanDependencies.model_fields,
    ):
        relevant = findings if field_name == "containment_required" else applicable
        if any(getattr(f, field_name) for f in relevant) and not getattr(proposal, field_name):
            raise DemoError(f"Coordinator omitted a material {field_name} requirement.")
    selected = [option_assessment(f, proposal.selected_option_id) for f in scoped
                if proposal.selected_option_id is not None]
    for assessment in selected:
        for name, value in dependency_claims(assessment).items():
            if value is True and not getattr(proposal, name):
                raise DemoError(f"Coordinator omitted a material {name} requirement.")
    for field_name in ("unknown_keys", "approval_requests"):
        relevant = findings if field_name == "unknown_keys" else applicable
        required = {v for f in relevant for v in getattr(f, field_name)}
        if field_name == "approval_requests":
            required.update(v for f in legacy for v in f.approval_requests
                            if v in ("quality_containment", "customer_notification"))
            required.update(value for finding in scoped for value in finding.safety_approval_requests)
        if not required.issubset(getattr(proposal, field_name)):
            raise DemoError(f"Coordinator omitted unresolved {field_name}.")
    conflicts = {c.model_dump_json() for f in findings for c in f.conflicts}
    if not conflicts.issubset({c.model_dump_json() for c in proposal.conflicts}):
        raise DemoError("Coordinator omitted or rewrote an unresolved conflict.")
