from uuid import uuid4

from agent_framework import (
    Executor, WorkflowBuilder, WorkflowContext, handler, response_handler,
)

from .agents import ExpertTeam
from .contracts import (
    AGENTS, AFFECTED, ClarificationRequest, DemoError, FinalResult, HumanEvidence,
    HumanResponse, RunState, affected_agents,
)
from .fixtures import fixture_records, policy_requirements, validate_delivery_change
from .presentation import Presenter
from .runtime import Budget, DecisionClient


class SelectionExecutor(Executor):
    def __init__(self, decision, presenter):
        super().__init__(id="selection")
        self.decision, self.presenter = decision, presenter

    @handler
    async def select(self, state: RunState, ctx: WorkflowContext[RunState]):
        state.selections = await self.decision.select(state)
        for actor in AGENTS:
            answer = state.selections[actor]
            self.presenter.choice(actor.title(), answer, selection=True)
            if answer.effective == "needed":
                state.active.append(actor)
            elif answer.effective == "cannot_determine":
                state.uncertain.append(actor)
            else:
                self.presenter.diagnostic(f"Skipped specialist: {actor}")
        state.refresh = list(state.active)
        await ctx.send_message(state)


class ExpertsExecutor(Executor):
    def __init__(self, team, presenter):
        super().__init__(id="experts")
        self.team, self.presenter = team, presenter

    @handler
    async def assess(self, state: RunState, ctx: WorkflowContext[RunState]):
        if not state.active or len(state.active) > 3 or not set(state.refresh).issubset(state.active):
            raise DemoError("Invalid expert selection/refresh boundary.")
        for actor in state.active:
            if actor in state.refresh:
                state.findings[actor] = await self.team.assess(actor, state)
                self.presenter.finding(state.findings[actor])
            elif actor in state.findings:
                self.presenter.line(f"{actor.title()}: reused previous finding; evidence unchanged.")
            else:
                raise DemoError("Join lacks an unaffected specialist finding.")
        await ctx.send_message(state)


class CoordinatorExecutor(Executor):
    def __init__(self, team, presenter):
        super().__init__(id="coordinator")
        self.team, self.presenter = team, presenter

    @handler
    async def coordinate(self, state: RunState, ctx: WorkflowContext[RunState]):
        state.proposal = await self.team.coordinate(state)
        self.presenter.proposal(state)
        await ctx.send_message(state)


class ValidationExecutor(Executor):
    def __init__(self, decision, presenter):
        super().__init__(id="validation")
        self.decision, self.presenter = decision, presenter

    @handler
    async def validate(self, state: RunState, ctx: WorkflowContext[RunState]):
        state.validation = await self.decision.validate(state)
        self.presenter.choice("Decision-1 proposal validation (not execution)", state.validation)
        state.policies = policy_requirements(
            state.proposal, fixture_records(),
            customer_changed=any(e.value.customer_agreed for e in state.overlays),
        )
        await ctx.send_message(state)


def review_reasons(state: RunState) -> list[str]:
    reasons = []
    if state.uncertain:
        reasons.append("Selection uncertainty: " + ", ".join(state.uncertain))
    if state.validation and (
        state.validation.selected != "Addresses the issue" or not state.validation.satisfactory
    ):
        reasons.append("Validation unresolved: " + state.validation.selected)
    if state.proposal:
        if state.proposal.unknown_keys:
            reasons.append("Unknown domain evidence: " + ", ".join(state.proposal.unknown_keys))
        if state.proposal.conflicts:
            reasons.append("Conflicting/unverified evidence remains.")
    if state.policies:
        reasons.append("Mandatory approval handoff: " + ", ".join(state.policies))
    return reasons


class ReviewExecutor(Executor):
    def __init__(self, budget, presenter):
        super().__init__(id="review")
        self.budget, self.presenter = budget, presenter
        self.pending_state = None
        self.pending_request = None

    @handler
    async def review(self, state: RunState, ctx: WorkflowContext[RunState, FinalResult]):
        self.budget.remaining()
        reasons = review_reasons(state)
        if not state.active and not state.uncertain:
            await ctx.yield_output(FinalResult("handoff", 2, ("No specialist selected; human ownership needed.",), None))
            return
        if not reasons:
            if state.proposal is None or state.validation is None:
                raise DemoError("Incomplete assessment cannot finish successfully.")
            await ctx.yield_output(FinalResult("advisory_complete", 0, (), state.proposal))
            return
        if state.continuation_used:
            await ctx.yield_output(FinalResult("handoff", 2, tuple(reasons), state.proposal))
            return
        allowed = set(state.proposal.unknown_keys if state.proposal else ()) & set(AFFECTED)
        for actor in state.uncertain:
            allowed.update(k for k, actors in AFFECTED.items() if actor in actors)
        request = ClarificationRequest(
            revision=state.revision, allowed_keys=tuple(sorted(allowed)),
            uncertain_agents=tuple(state.uncertain), reasons=tuple(reasons),
            proposal=state.proposal, request_id="clarify-" + uuid4().hex,
        )
        self.pending_state, self.pending_request = state, request
        self.presenter.review(state, reasons, request)
        await ctx.request_info(request_data=request, response_type=HumanResponse, request_id=request.request_id)

    @response_handler
    async def resume(
        self, original_request: ClarificationRequest, response: HumanResponse,
        ctx: WorkflowContext[RunState, FinalResult],
    ):
        state = self.pending_state
        if (
            state is None or original_request != self.pending_request
            or state.continuation_used or state.revision != 0
        ):
            raise DemoError("Unbound or repeated human continuation blocked.")
        self.pending_state, self.pending_request = None, None
        if response.kind != "clarify":
            await ctx.yield_output(FinalResult(
                "rejected" if response.kind == "reject" else "escalated", 0,
                ("Leadership escalation requested; no notification or external contact performed."
                 if response.kind == "escalate" else
                 "Human stopped this advisory demo; no actions or authority granted.",
                 *original_request.reasons), state.proposal,
            ))
            return
        if not set(response.updates).issubset(original_request.allowed_keys):
            await ctx.yield_output(FinalResult(
                "pending", 2, ("Invalid clarification keys; no continuation executed.",), state.proposal,
            ))
            return
        affected = affected_agents(response, state.active, state.uncertain)
        if not affected:
            raise DemoError("Clarification maps to no specialist.")
        for change in response.updates.values():
            validate_delivery_change(change)
        state.continuation_used = True
        state.revision = 1
        for key, value in response.updates.items():
            evidence = HumanEvidence(
                evidence_id=f"human:{original_request.request_id}:{key}", key=key, value=value,
                request_id=original_request.request_id,
            )
            state.overlays.append(evidence)
            state.evidence[evidence.evidence_id] = evidence.model_dump(mode="json")
            self.presenter.diagnostic(
                f"Unverified human_clarification evidence {evidence.evidence_id}: {key}={value.model_dump_json()}"
            )
        state.active = [a for a in AGENTS if a in set(state.active) | set(affected)]
        state.uncertain = [a for a in state.uncertain if a not in affected]
        state.refresh = affected if state.findings else list(state.active)
        state.proposal, state.validation, state.policies = None, None, []
        self.presenter.resumed(state)
        self.presenter.diagnostic(f"One continuation: affected={affected}; active={state.active}; "
                                  "activation source=deterministic clarification map, not new model probabilities")
        await ctx.send_message(state)


def build_workflow(team: ExpertTeam, decision: DecisionClient, budget: Budget, trace, *, presenter=None):
    presenter = presenter or Presenter(trace)
    budget.trace = presenter.diagnostic
    select = SelectionExecutor(decision, presenter)
    experts = ExpertsExecutor(team, presenter)
    coordinator = CoordinatorExecutor(team, presenter)
    validate = ValidationExecutor(decision, presenter)
    review = ReviewExecutor(budget, presenter)
    builder = WorkflowBuilder(start_executor=select, max_iterations=12, output_from=[review])
    builder.add_edge(select, experts, condition=lambda state: bool(state.active) and not state.uncertain)
    builder.add_edge(select, review, condition=lambda state: not state.active or bool(state.uncertain))
    builder.add_edge(experts, coordinator)
    builder.add_edge(coordinator, validate)
    builder.add_edge(validate, review)
    builder.add_edge(review, experts)
    return builder.build()
