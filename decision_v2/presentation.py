import json
import textwrap
from datetime import datetime

from .fixtures import SNAPSHOT, delivery_position, fixture_records

LABELS = {
    "shipment_arrival": "replacement arrival unconfirmed",
    "incoming_acceptance": "replacement incoming acceptance pending",
    "customer_disposition": "customer disposition of shipped suspect stock unknown",
    "customer_delivery_change": "customer flexibility for the second delivery unknown",
    "proposal_feedback": "proposal needs review",
    "freight_authority": "Operations manager freight approval",
    "quality_containment": "Quality-owned hold, inspection and shipped-lot containment",
    "customer_notification": "responsible Quality/customer contact notification",
    "customer_commitment": "formal customer delivery-window review",
}
ACTION_LABELS = {
    "seek_freight_approval": "seek freight authority",
    "expedite_freight": "consider dedicated collection, subject to authority and acceptance",
    "resequence_build": "revise the delivery/replenishment schedule",
    "contain_and_recover": "contain exposure and evaluate delivery recovery separately",
    "request_customer_window": "request a customer delivery-window review",
    "gather_information": "establish missing evidence before committing",
}
SOURCE_LABELS = {
    "read_inventory": "inventory and Quality hold",
    "read_shipment": "replacement offer and shipped ASN",
    "read_build": "customer delivery schedule",
    "read_approval_policy": "authority and contact policy",
}


def display_time(value):
    at = datetime.fromisoformat(value)
    offset = at.strftime("%z")
    return at.strftime("%a %d %b %Y %H:%M") + f" UTC{offset[:3]}:{offset[3:]}"


class Presenter:
    def __init__(self, output, verbose=False):
        self.output, self.verbose = output, verbose
        self.sections = set()

    def line(self, text):
        for paragraph in str(text).splitlines() or [""]:
            indent = len(paragraph) - len(paragraph.lstrip())
            for line in textwrap.wrap(
                paragraph, width=94, break_long_words=False, break_on_hyphens=False,
                subsequent_indent=" " * indent,
            ) or [""]:
                self.output(line)

    def section(self, title):
        if title not in self.sections:
            self.output("")
            self.output(f"=== {title} ===")
            self.sections.add(title)

    def diagnostic(self, message):
        if self.verbose or message.startswith(("Quota pacing:", "ERROR:")):
            self.line(message)

    def record(self, label, value):
        if self.verbose:
            self.output(f"[diagnostic] {label}: {value.model_dump_json()}")

    def case(self):
        records = fixture_records()
        stock, shipment, build = records["read_inventory"], records["read_shipment"], records["read_build"]
        lot, position = stock.incident, delivery_position()
        self.section("CASE")
        self.line(f"SYNTHETIC planning case | snapshot {display_time(SNAPSHOT)}")
        self.line(f"{build.customer} | order {build.order_id}")
        self.line(f"Incident {lot.incident_id}, {lot.part_id}, lot {lot.lot_id}: "
                  f"{lot.total_units} total = {lot.held_onsite_units} Quality-held onsite + "
                  f"{lot.already_shipped_units} already shipped ({shipment.shipment_id}, {shipment.asn_id}).")
        self.line(f"Measured sample: {lot.measured_failures} failures in {lot.inspected_units} checked. "
                  "Total nonconforming quantity is unknown; do not extrapolate the sample.")
        self.line(f"Usable stock: {stock.released_units} from independently released lot {stock.released_lot_id}. "
                  "Held stock is excluded; this demo cannot lift the hold.")
        for delivery in build.deliveries:
            self.line(f"Scheduled delivery: {delivery.quantity} units at {display_time(delivery.due_at)}.")
        self.line(f"{position.total_demand} scheduled / {position.released_units} usable: first delivery "
                  f"covered by {position.first_covered}; original second-window shortfall {position.baseline_gap}.")
        self.line(f"Separate-lot offer: {shipment.replacement_units} from {shipment.replacement_lot_id}; "
                  "collection possible, arrival and incoming acceptance unconfirmed.")
        self.line(f"Dedicated quote ${shipment.freight_cost_usd:,}; planner limit "
                  f"${records['read_approval_policy'].planner_limit_usd:,}. "
                  "No approved concession. Notification and customer disposition remain pending.")
        self.line("Model results are advisory. Synthetic evidence is not a live ERP/QA/customer record.")

    def choice(self, label, answer, selection=False):
        if selection:
            self.section("TEAM")
        effective = answer.effective if selection else (
            answer.selected if answer.satisfactory else f"{answer.selected} (below routing policy)"
        )
        confidence = "not reported" if answer.confidence is None else f"{answer.confidence:.0%}"
        self.line(f"{label}: {effective.replace('_', ' ')} | chosen-option probability "
                  f"{answer.probabilities[answer.selected]:.1%} | model-reported confidence {confidence}.")
        if selection and answer.effective != answer.selected:
            self.line(f"  Model selected {answer.selected.replace('_', ' ')}; effective selection is uncertain.")
        if self.verbose:
            self.output("[diagnostic] complete option probabilities (not confidence): " +
                        json.dumps(answer.probabilities))

    def finding(self, finding):
        if finding.revision == 0:
            self.section("FINDINGS")
        self.line(f"{finding.agent_id.title()} (assessment {finding.revision + 1})")
        self.line("  Evidence: " + finding.assessment)
        self.line("  Implication: " + finding.implication)
        sources = {record.evidence_id: SOURCE_LABELS[name]
                   for name, record in fixture_records().items()}
        sources["issue:quality-hold-v2"] = "synthetic incident"
        self.line("  Sources: " + ", ".join(
            "unverified customer-planner assertion" if key.startswith("human:") else sources[key]
            for key in finding.evidence_ids
        ))
        self.line("  Recommended next step: " + ACTION_LABELS[finding.recommended_action])
        if finding.unknown_keys:
            self.line("  Still missing: " + "; ".join(LABELS[k] for k in finding.unknown_keys))
        self.record("complete finding/provenance", finding)

    def proposal(self, state):
        if state.revision == 0:
            self.section("INITIAL PLAN")
        self.line(("Updated" if state.revision else "Initial") + " coordinator proposal: " + state.proposal.brief)
        self.line("Next step: " + ACTION_LABELS[state.proposal.recommended_action])
        if state.proposal.unknown_keys:
            self.line("Missing evidence: " + "; ".join(LABELS[k] for k in state.proposal.unknown_keys))
        for conflict in state.proposal.conflicts:
            self.line("Preserved disagreement: " + conflict.description)
        self.record("complete proposal/provenance", state.proposal)

    def review(self, state, reasons, request):
        if state.proposal is None:
            self.section("INITIAL PLAN")
            self.line("Assessment paused before expert dispatch; selection evidence is unresolved.")
        if state.policies:
            self.line("Required owner handoffs: " + "; ".join(LABELS[k] for k in state.policies))
        self.section("HUMAN CLARIFICATION")
        if "customer_delivery_change" in request.allowed_keys:
            first, second = fixture_records()["read_build"].deliveries
            supported = state.proposal is not None and state.proposal.recommended_action == "request_customer_window"
            label = ("Recommended follow-up to the coordinator proposal" if supported else
                     "Host-suggested review step (not a model recommendation)")
            self.line(f"{label}: Contact the customer planner about rescheduling the second "
                      f"{second.quantity} units due {display_time(second.due_at)}. "
                      f"Keep the first {first.quantity} at {display_time(first.due_at)} unchanged.")
            position = delivery_position()
            self.line(f"Rationale: released stock covers the first {position.first_covered} units; "
                      f"the original second-window shortfall is {position.baseline_gap}.")
            if state.proposal is not None:
                self.line("Review the actual findings and coordinator proposal above before contacting the customer.")
            else:
                self.line("Expert selection remains unresolved; customer timing alone cannot resolve it.")
        self.line("Planning update only; quality release, containment and required approvals remain separate.")
        for reason in reasons:
            self.diagnostic("Human review: " + reason)

    def resumed(self, state):
        self.section("UPDATED HANDOFF")
        position = delivery_position(state.overlays)
        self.line(f"Original second-window uncovered demand: {position.baseline_gap} -> "
                  f"{position.provisional_gap}, provisionally under the operator's unverified assertion.")
        if position.moved_units:
            self.line(f"Reported move: {position.moved_units} units to {display_time(position.revised_delivery_at)}. "
                      "The first delivery is unchanged. Formal customer-window review is still required.")
        else:
            self.line("No customer-agreed move was reported; original demand remains.")
        self.line(f"Usable inventory is still {position.released_units}; moved demand is not replenished stock.")
        self.line("Refresh: " + ", ".join(a.title() for a in state.refresh) + ". Reuse: " +
                  (", ".join(a.title() for a in state.active if a not in state.refresh) or "none") + ".")

    def finish(self, result, budget):
        self.section("UPDATED HANDOFF")
        self.line(f"Final advisory status: {result.status.replace('_', ' ')}. "
                  "No stock released, notification sent, customer commitment made or spending authorized.")
        for reason in result.reasons:
            if reason.startswith("Leadership escalation requested"):
                self.line(reason)
            elif reason.startswith("Mandatory approval handoff: "):
                keys = reason.removeprefix("Mandatory approval handoff: ").split(", ")
                self.line("Required owner actions: " + "; ".join(LABELS[k] for k in keys))
            elif reason.startswith("Unknown domain evidence: "):
                keys = reason.removeprefix("Unknown domain evidence: ").split(", ")
                self.line("Unresolved evidence: " + "; ".join(LABELS[k] for k in keys))
            else:
                self.line("Unresolved: " + reason)
        self.line("Quality retains the held lot and owns shipped-suspect containment/disposition. "
                  "Delivery relief never closes the quality incident.")
        self.attempts(budget)

    def attempts(self, budget):
        self.line(f"Actual model attempts: GPT {budget.counts['gpt']}/20; Decision-1 "
                  f"{budget.counts['decision']}/3; fixture tools {sum(map(len, budget.tools.values()))}/12.")
