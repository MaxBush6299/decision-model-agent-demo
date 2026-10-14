import math
from datetime import datetime
from dataclasses import dataclass, field
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AGENTS = ("supply-chain", "production", "commercial")
SELECTION_OPTIONS = ("needed", "not_needed", "cannot_determine")
VALIDATION_OPTIONS = ("Addresses the issue", "Needs revision", "Cannot determine")
SCENARIO_ID = "quality-hold-v2"
ISSUE_ID = "issue:quality-hold-v2"
THRESHOLD = .70
AgentId = Literal["supply-chain", "production", "commercial"]
Action = Literal[
    "seek_freight_approval", "expedite_freight", "resequence_build",
    "contain_and_recover", "request_customer_window", "gather_information",
]
Approval = Literal["freight_authority", "quality_containment", "customer_notification", "customer_commitment"]
UnknownKey = Literal[
    "shipment_arrival", "incoming_acceptance", "customer_disposition",
    "customer_delivery_change", "proposal_feedback",
]
Text = Annotated[str, Field(min_length=1, max_length=2000)]
EvidenceId = Annotated[str, Field(min_length=1, max_length=120)]


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
        if keys not in (set(SELECTION_OPTIONS), set(VALIDATION_OPTIONS)):
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
    description: str = Field(min_length=1, max_length=500)


class FindingRef(StrictModel):
    agent_id: AgentId
    revision: Literal[0, 1]

    @field_validator("revision", mode="before")
    @classmethod
    def integer_revision(cls, value):
        if type(value) is not int:
            raise ValueError("Revision must be an integer, not a boolean.")
        return value


class ExpertFinding(StrictModel):
    agent_id: AgentId
    revision: Literal[0, 1]
    assessment: Annotated[str, Field(min_length=1, max_length=500)]
    implication: Annotated[str, Field(min_length=1, max_length=500)]
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


class CoordinatedProposal(StrictModel):
    revision: Literal[0, 1]
    recommended_action: Action
    uses_held_stock: bool
    uses_expedited_freight: bool
    containment_required: bool
    changes_customer_commitment: bool
    brief: Annotated[str, Field(min_length=1, max_length=1000)]
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


@dataclass(frozen=True)
class FinalResult:
    status: str
    code: int
    reasons: tuple[str, ...]
    proposal: CoordinatedProposal | None


@dataclass
class RunState:
    revision: int = 0
    selections: dict[str, ChoiceAnswer] = field(default_factory=dict)
    active: list[str] = field(default_factory=list)
    uncertain: list[str] = field(default_factory=list)
    findings: dict[str, ExpertFinding] = field(default_factory=dict)
    overlays: list[HumanEvidence] = field(default_factory=list)
    proposal: CoordinatedProposal | None = None
    validation: ChoiceAnswer | None = None
    policies: list[str] = field(default_factory=list)
    evidence: dict[str, dict] = field(default_factory=dict)
    continuation_used: bool = False
    refresh: list[str] = field(default_factory=list)


def affected_agents(response: HumanResponse, active: list[str], uncertain: list[str]) -> list[str]:
    selected = set()
    for key in response.updates:
        selected.update(active or uncertain if key == "proposal_feedback" else AFFECTED[key])
    return [agent for agent in AGENTS if agent in selected]


def validate_references(output: ExpertFinding | CoordinatedProposal, allowed: set[str]) -> None:
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
    if proposal.uses_held_stock or not proposal.containment_required:
        raise DemoError("Coordinator cannot release held stock or omit shipped-lot containment.")
    for field_name in ("containment_required", "uses_expedited_freight", "changes_customer_commitment"):
        if any(getattr(f, field_name) for f in findings) and not getattr(proposal, field_name):
            raise DemoError(f"Coordinator omitted a material {field_name} requirement.")
    for field_name in ("unknown_keys", "approval_requests"):
        required = {v for f in findings for v in getattr(f, field_name)}
        if not required.issubset(getattr(proposal, field_name)):
            raise DemoError(f"Coordinator omitted unresolved {field_name}.")
    conflicts = {c.model_dump_json() for f in findings for c in f.conflicts}
    if not conflicts.issubset({c.model_dump_json() for c in proposal.conflicts}):
        raise DemoError("Coordinator omitted or rewrote an unresolved conflict.")
