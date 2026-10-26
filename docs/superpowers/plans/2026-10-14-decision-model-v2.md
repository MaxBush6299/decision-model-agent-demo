# Decision model v2 Implementation Plan

**Revision note:** The original plan below records the shortage implementation
committed as `ee7d404`. The user then approved the researched quality-hold case
on 2026-10-14 ("Lets try this now"); the current specification supersedes the
old scenario/human contracts while keeping framework/auth/budgets unchanged.
The quality-hold execution record is at the end of this plan.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved terminal expert-team shortage workflow with real
Microsoft Agent Framework agents, fixture tools, and one clarification resume.

**Architecture:** Strict application records define the evidence and outputs.
A bounded transport under real framework agents counts every HTTP attempt and
tool-result model turn; custom framework executors own selection, synthesis,
validation, policy, and HITL. A thin terminal adapter handles events and one
typed human response without live plant operations.

**Tech Stack:** Python 3.11+, unittest, Pydantic 2, Azure Identity,
agent-framework-core 1.21.0, agent-framework-openai 1.15.0 (user-approved
configured-feed adjustment), OpenAI AsyncOpenAI,
HTTPX2 2.13.1 fake transports (OpenAI SDK 3.26.0) for offline integration tests.

## Global Constraints

- Approved specification: `docs\superpowers\specs\2026-10-14-decision-model-v2-design.md`, commit `a6036a3`.
- Leave v1 CLI/tests/requirements/contracts, site, and GitHub Actions untouched.
- No push/merge/publication, resource/access changes, or plant writes.
  User15 October exception: four initial live cases plus at most two corrective
  runs against the existing deployments only. All six were used; no further run
  is authorized by that bounded permission.
- At most three specialists and one Coordinator; one initial assessment and one continuation.
- <=20 GPT, <=4 Decision-1, <=24 total attempts; failed attempts count; no retries.
- <=3 GPT attempts and <=2 unique successful tool executions per specialist invocation.
- Sequential specialists; rolling60s limits10 GPT/20 Decision-1 plus conservative
  local10,000-token GPT estimate, as observed in the existing deployment.
- Deadlines: request 60s, credential 15s, tool 2s, active 900s, human 300s, wall 1200s.
- Human assertions never change immutable facts, approvals, tools, rubric, or budgets.

## File map

Create `requirements-v2.txt`, `decision_demo_v2.py`, `decision_v2\__init__.py`,
`decision_v2\contracts.py`, `decision_v2\fixtures.py`, `decision_v2\runtime.py`,
`decision_v2\agents.py`, `decision_v2\workflow.py`, `decision_v2\cli.py`,
`test_decision_v2.py`, and `docs\v2.md`. Fixture records live in `fixtures.py`:
one scenario, no general fixture loader or additional input domains.
Do not change v1 configuration helpers; reproduce its small validation contract
in the isolated v2 runtime and compare outcomes with existing regression tests.

### Task 1: Pinned runtime and compatibility boundary

**Files:** Create `requirements-v2.txt`, `decision_v2\__init__.py`.
**Interfaces:** The worktree's ignored `.venv` provides the real framework imports.

- [x] Write the v2 manifest:

```text
-r requirements.txt
agent-framework-core==1.21.0
agent-framework-openai==1.15.0
```

- [x] Use the existing isolated `.venv`, then run
  `.\.venv\Scripts\python.exe -m pip install -r requirements-v2.txt`.
  No TLS bypass, alternate untrusted package source, or repository execution.
- [x] Inspect `Agent`, `OpenAIChatCompletionClient`, `WorkflowBuilder`,
  `WorkflowContext.request_info`, `FunctionInvocationConfiguration`, middleware,
  and `AsyncOpenAI` signatures/source with the installed interpreter.
  Confirm injected SDK client, strict output value, real tool errors, and
  capped transport can enforce this spec. Surface load-bearing incompatibility
  before changing the design.
- [x] Commit only the plan/manifest/package marker with required session trailers.

### Task 2: Strict evidence and deterministic policy

**Files:** Create `decision_v2\contracts.py`, `decision_v2\fixtures.py`;
create/extend `test_decision_v2.py`.
**Interfaces:** `ChoiceAnswer`, `ExpertFinding`, `CoordinatedProposal`,
`HumanResponse`, `ClarificationRequest`, `RunState`; `fixture_records()`;
`parse_choices(payload, names, options)`; `affected_agents(response, active,
uncertain)`; `policy_requirements(proposal, fixture)`.

- [x] Add failing unittest assertions for independent selections:

```python
def test_selection_uncertainty(self):
    answer = ChoiceAnswer(selected="needed",
        probabilities={"needed": .5, "not_needed": .4, "cannot_determine": .1})
    self.assertEqual(answer.effective, "cannot_determine")
```

- [x] Define strict models (`ConfigDict(extra="forbid", strict=True)`),
  frozen envelopes, enum/literal identifiers, bounded lists/text, evidence IDs,
  fixed authoritative shortage records, and record-level reference validation.
  Probability validation rejects bool/nonfinite/missing/extra options or
  distributions outside sum tolerance .001; .70 is a policy threshold.
- [x] Implement affected-key map and human overlay rules: mapped activation
  during initial selection uncertainty, replacement of affected findings,
  preservation of unaffected findings/uncertainty, contradictions retained.
  Compute mandatory freight/engineering/customer review from typed action and
  immutable data, preserving expert requests.
- [x] Run `.\.venv\Scripts\python.exe -m unittest test_decision_v2 -v`;
  cover strict coercion, immutable values, unknown versus failure, and explicit
  approval handoffs. Include this boundary in the reviewed implementation commit.

### Task 3: Actual agent/tool dispatch and inference ceilings

**Files:** Create `decision_v2\runtime.py`, `decision_v2\agents.py`;
extend `test_decision_v2.py`.
**Interfaces:** `Config`, `Budget`, `GuardedTransport`, `DecisionClient`,
`ExpertTeam.assess(agent_id, state) -> ExpertFinding`,
`ExpertTeam.coordinate(state) -> CoordinatedProposal`.

- [x] Add a fake HTTPX transport assertion:

```python
async def test_specialist_fourth_attempt_blocked(self):
    budget = Budget()
    for _ in range(3):
        await budget.reserve("gpt", "supply-chain", 0)
    with self.assertRaises(DemoError):
        await budget.reserve("gpt", "supply-chain", 0)
```

- [x] Implement explicit config validation, existing Entra audiences, guarded
  HTTPX transport with actual pre-send counters and rolling-window pacing,
  fake-clock injection, request/deadline caps, sanitized errors, no redirects,
  and `AsyncOpenAI(max_retries=0, ...)` injection.
  A budget reservation includes revision+agent and cannot reset at resume.
  Decision-1 sends actual named systemone choice requests with typed response
  validation. Credential acquisition must not block the event loop indefinitely.
- [x] Create real Agents with isolated invocations and annotated allowlisted
  fixture functions. Use `response_format` models; reject refusals/truncation,
  absent values, unknown citations/identities, and error content.
  Tool guards are authoritative before execution; middleware fails host/tool
  errors before another model turn, even if framework would normally repair.
  Coordinator preserves active references and unresolved unions.
- [x] Run real-framework fake-transport tests including actual function-call
  turns, exact URL/audience, every attempt, fourth dispatch, tool duplicates/
  batch excess, coordinator extra requests, deadlines, and cleanup.
  Include the agent/runtime boundary in the reviewed commit without live inference.

### Task 4: Executor orchestration, terminal adapter, and documentation

**Files:** Create `decision_v2\workflow.py`, `decision_v2\cli.py`,
`decision_demo_v2.py`, `docs\v2.md`; extend `test_decision_v2.py`.
**Interfaces:** `build_workflow(team, decision, budget, trace)`;
`run_demo(runtime, response_reader, ...) -> FinalResult`; `main(argv=None) -> int`.

- [x] Write failing request/resume test using actual WorkflowBuilder:

```python
async def test_framework_resume_once(self):
    events = [event async for event in workflow.run(initial_state, stream=True)]
    request = next(e for e in events if e.type == "request_info")
    resumed = [event async for event in workflow.run(
        stream=True, responses={request.request_id: clarification})]
    self.assertFalse(any(e.type == "request_info" for e in resumed))
```

- [x] Implement bounded executors: selection -> sequential specialists/join ->
  coordinator -> validation -> deterministic review/output. A typed response
  handler consumes the single continuation, refreshes the mapped experts,
  reuses other findings, synthesizes/validates, and yields final status.
  Failures never become skipped agents or successful partial results.
- [x] Implement one terminal event adapter, bounded typed field input,
  non-TTY/EOF/interrupt/invalid handling, request/human/overall deadlines,
  offline help, explicit exit codes, and sanitized readable trace.
  `decision_demo_v2.py` only imports/calls `cli.main`.
- [x] Document exact PowerShell setup/run, unchanged config variables,
  synthetic-only scope, mocked versus live status, costs/caps, clarification
  schema, approvals, error/exit behavior, and separate smoke authorization.
- [x] Run all v2 mocked tests; include CLI/workflow/docs in the reviewed commit.

### Task 5: Integration verification and focused review

**Files:** Extend `test_decision_v2.py`; fix only v2 files as evidence requires.
**Interfaces:** Complete working CLI and reproducible offline unittest command.

- [x] Run `.\.venv\Scripts\python.exe -m unittest -v` for v1+v2 and
  `.\.venv\Scripts\python.exe decision_demo_v2.py --help`.
  Test selection zero/one/two/three/uncertain, typed citations/conflicts,
  positive/negative/low/tied validation, actual tool turns, immutable policy,
  initial-pause and post-proposal continuation, request binding, and reused
  findings. Cover non-TTY/EOF/interrupt/invalid input, rate/call/tool caps,
  timeouts/refusals/429/errors/no retries, credentials, and client cleanup.
- [x] Run focused read-only code review of the substantial v2 diff; resolve
  correctness issues and re-run affected tests. No security-vulnerability
  audit or unrelated refactor.
- [x] Inspect `git diff --check` and changed paths; confirm only v2 files,
  approved spec/plan, and related docs. Commit fixes with required trailers.
- [x] Report ready command and existing config, actual framework/mocked
  coverage, remaining runtime uncertainty, and no live inference performed.

## Plan self-review and execution

Each spec section maps to Tasks 1-5: pinned API/auth (1/3), strict fixtures and
human provenance/policy (2), actual attempts/tool budgets (3), bounded framework
HITL/terminal deadlines/trace (4), mocked acceptance and v1 isolation (5).
No task adds an approval agent, frontend, general planner, hosting, or live test.
Execute inline using `executing-plans` under the user's already-approved local
implementation request; no additional conceptual approval gate.

Completed locally: 78 offline tests (34 unchanged v1, 44 v2), CLI help, and
dependency consistency passed. Focused review found a refresh could discard
a previous unknown; refresh now requires relevant cited clarification or retains
that unknown. A deadline regression also ensures human waiting is not shortened
by the remaining active clock. Both fixes have real-framework offline coverage.
Implementation boundaries are grouped in one reviewed commit rather than
separate interim boundary commits. Branch/worktree remain local and preserved;
live Azure inference is untested and still requires separately bounded approval.

## User-directed quality-hold revision

- [x] Replace shortage records with the dated incident/lot/ASN, released versus
  held stock, replacement quote, customer schedule and approval/contact policy.
  Derive arithmetic/unknowns from canonical fixtures; do not extrapolate sample
  failures or permit held-stock use.
- [x] Add typed quantity/window/reference customer clarification; refresh
  Production and Commercial, reuse Supply-chain, preserve Quality containment,
  pending contact/disposition and conditional freight authority.
- [x] Render six readable business sections, natural non-JSON input, compact
  probability/confidence, complete verbose diagnostics and always-visible
  quota/errors/attempt totals. Update docs/spec; keep the old startup alias.
- [x] Run actual-framework fake-transport regressions and full v1/v2 suite,
  inspect the offline terminal flow, complete focused read-only review and
  commit locally. No live inference or push/merge/Azure/site changes.

Verification: 88 offline tests (34 unchanged v1, 54 v2), CLI help and dependency
consistency pass. Focused review found no significant issues. A typed freight
dependency flag also protects combined containment/recovery recommendations
from losing spending review merely because their main action is not "freight".
Live behavior remains untested; start with `--example quality-hold` (or the
preserved `--example supply-chain` alias), optionally `--verbose`.

## User-directed recommendation-led review revision

- [x] Start human review with customer-contact rationale from canonical delivery
  quantities. Preserve actual model findings/proposal; distinguish the templated
  host suggestion unless the Coordinator explicitly requests a customer-window review.
- [x] Offer two choices: record an unverified customer response after contact,
  collecting quantity/time/reference, or reject and request leadership escalation.
  Keep one shared human deadline, one typed response and one framework resume.
  Escalation performs no contact, refresh or further inference and retains
  unresolved evidence and mandatory owner handoffs in the final output.
- [x] Cover real-framework offline recommendation/response/escalation paths,
  input termination, bounded references and whole-collection timeout. Update
  the spec and startup guide without altering agents, tools, limits or v1/site.

Verification: 94 offline tests (34 unchanged v1, 60 v2), CLI help, dependency
consistency and diff checks pass. No live inference, external contact, push or
merge performed. The branch and native worktree remain local.

## User-directed three additional cases

- [x] Add immutable carrier-delay, production-resequence and order-pull-forward
  records with coherent quantity/material/rate/cutoff/arrival/customer-reference
  checks. Preserve the quality-hold dataset and supply-chain alias.
- [x] Bind scenario identity through CLI, actual agents/tools, transport,
  Decision-1 context, policy and presentation. Reuse the existing no-review
  completion branch; remove quality-only requirements from healthy cases,
  not model-generated uncertainty or mandatory policy handoffs.
- [x] Preserve typed carrier/cell/pull-forward/overtime/displacement dependencies.
  Generic review offers pending/escalation rather than accepting inappropriate
  quality-window evidence. All runtime quotas, retries, auth and tools retained.
- [x] Exercise actual framework with fake provider for positive no-review,
  selective dispatch, negative/uncertain/low-probability scoring, canonical
  unsupported evidence/policy, model unknowns/conflicts/approvals, dependency
  loss and cross-scenario rejection. Update startup documentation.

No-review success existed before this change; the new canonical evidence and
scenario-scoped policies allow it without forcing success. No live model run,
real operational/customer write, dependency/feed change, v1/site edit or
push/merge is authorized by this revision.

Verification: 110 offline tests (34 unchanged v1, 76 v2) pass, including full CLI
execution for every new selector with real framework and fake Azure transport.
Positive supported cases emit no request_info; policy/unknown/conflict/negative
paths pause, and generic customer-window updates are rejected without calls.
Selective Production-only synthesis can cite canonical policy supplied in its
ledger without an extra tool/model call. Offline terminal preview, help,
dependency consistency and diff checks pass. Live behavior remains untested.

## Carrier routing diagnosis and scoped clarification

- [x] Trace the actual selection payload and strict routing gate. All carrier
  records were already supplied; weak selected not_needed scores become
  uncertain and block all specialist dispatch. No evidence omission or
  quality-case handoff was found.
- [x] Clarify additional-case role criteria and supply derived canonical
  position/check/applicability data, not role assignments. Keep genuinely
  missing applicable evidence and all probability/dispatch guards unchanged.
- [x] Distinguish raw model choice/chosen-option probability from effective
  routing, and pre-dispatch uncertainty from a business evidence/plan failure.
- [x] Verify reported rounded chosen scores with explicitly synthetic residual
  probabilities, one Decision-1/no GPT/tool attempts, actual request grounding,
  applicable missing qualification and chosen-not-maximum probability display.

Verification:116 offline tests (34 unchanged v1,82 v2), CLI help and diff checks
pass. The same reported scores still pause under the preserved routing policy;
grounding fixes are not a promise of different live scores. The full live score
vectors were not provided and were not invented as observed evidence.
No live inference, push/merge or auth/budget/dependency/cloud/site change.
Consulting routing-uncertain specialists instead of pausing remains a separate
user decision, not an implemented fix.

## User-directed two-stage routing and bounded live validation (15 October)

Supersedes the previous routing gate following explicit user approval:
"it should first decide if it needs further assesment, if yes it decides which
specialists, if no it goes straight through."

- [x] Add independent typed overall assessment decision and canonical guarded
  direct no-assessment disposition; distinguish this from a validated plan.
- [x] Add second role-relevance decision; conservatively consult weak/uncertain
  roles instead of escalating routing questions. Overall uncertainty assesses.
  All confidently skipped roles use canonical Coordinator-only assessment,
  citations/unknown guards and ordinary proposal validation/policy.
- [x] Preserve three-role/one-resume/read-only/Foundry-only boundaries. Increase
  D1 ceiling3->4 and total23->24; GPT20/tools12/deadlines unchanged. Generic
  business review offers pending or escalation, not a lone "choose2".
- [x] Run four authorized live cases, then two permitted corrective quality
  runs. Fix concrete truncation with concise output guidance, not more output
  tokens/repair calls. Inspect existing deployment read-only:10GPT RPM and10k
  GPT TPM. Add conservative local TPM pacing and explicit429 reporting; no
  cloud quota/deployment change or automatic retry.
- [x] Critically review live numbers, source citations, flags and handoffs.
  Healthy cases each chose direct no-assessment. Last quality run completed
  one simulated human continuation,12GPT+4D1,10 tools,377.6s, unresolved handoff.
  Earlier quality attempts stopped on malformed/truncated output and token429.
  No stock, shipment, customer or spending action performed.
- [x] Add explicit derived provisional-window context after observing stale
  refreshed prose. Offline coverage confirms baseline240/provisional0 and
  Saturday08:00 without changing canonical Friday schedule or stock. This
  final grounding/notification wording change was not rerun live: all six
  authorized runs are exhausted, and model prose reliability is not calibrated.

Complete sanitized wire/trace/metadata files remain in private session storage.
Public startup guidance records outcomes/limitations without provider IDs/host.
Local commit only; no push/merge, v1/site/dependency/auth/cloud changes.

Final offline verification:128 tests (34 unchanged v1,94 v2) pass, including
actual framework two-stage/direct/conservative/all-skip/quality-policy branches,
the reported carrier scores, no retries and revised caps, token pacing, generic
pending/escalation and provisional-window context. CLI help, pip consistency
and diff checks pass. Live test ceiling respected: four initial plus two
corrective runs, with complete private captures and explicit failed-run results.

## User-directed expected 0 / 1 / 3 scenario revision

The user selected live-model expectations rather than fixed routing presets.

- [x] Preserve resolved carrier and advanced quality fixtures/alias. Replace
  Production's single answer with qualified P2/P3 setup/runtime/readiness choices.
  Replace Pull-forward's single answer with evidenced full400/overnight1800 versus
  split160+240/standing-route0 choices, protecting SO-6702's200 materials,
  17:00-19:00 capacity and Friday14:00 delivery.
- [x] Use the existing four tools with bounded immutable option/leg/customer
  records. Omit single-option reference projections from model inputs; retain
  neutral arithmetic for every option without a host-selected preferred answer.
  Add Coordinator selected_option_id, explicit unknown-ID failure and missing-
  selection business review. Check all selected legs and aggregate freight.
- [x] Keep two-stage Decision-1 decisions, thresholds, conservative consultation,
  Coordinator-only fallback and all auth/call/tool/deadline guards. Render
  expected-versus-actual routes without expected counts in model prompts.
- [x] Verify actual-framework fake-provider option/citation/policy paths plus
  unchanged v1 regression suite:135 tests pass before the new live batch.
- [x] Run one authorized Production and one Pull-forward live case; critically
  inspect routes, findings, option arithmetic, reservations, authority and final
  review. At most2 corrective reruns only for concrete bugs, never count-fishing.
  Production completed1-role/P2/positive validation,3D1+4GPT/2tools in136.9s.
  Pull-forward invoked all3,2D1+7GPT/6tools in240.1s, then validation auth failed:
  AzureCliCredential "Azure CLI not found on path". Stop without credential/PATH
  workaround or further inference;2 of4 run slots used.
- [x] Fix observed alternative contamination with option-scoped finding/
  synthesis dependencies and approvals; preserve global unknowns/conflicts/
  containment/notification. Explicitly review canonical selected-option
  overtime/freight/displacement contradictions instead of rewriting model output.
  Restore the missing shared planner limit in option-case issue context, so
  Supply-chain/Production need no extra policy-tool access. Commercial already
  had policy, so missing context is not the sole explanation of model conservatism.
- [x] Record actual versus expected counts, including all conservative
  consultations after weak raw not_needed scores. Mark final corrections
  offline-only; live final-code validation remains blocked by authentication.
- [x] Verify final scoped changes and commit locally without push, cloud,
  dependency, v1 or site edits.

Final offline acceptance:140 tests (34 unchanged v1,106 v2), CLI help, dependency
consistency and diff checks pass. Customer full/split records include independent
window starts as well as due times; shifted carrier windows cannot authorize an
early delivery. No additional live runs occurred after the authentication stop.
Final-code live validation remains explicitly blocked, not marked successful.

## User-directed routing evidence/question framing

- [x] Add a canonical per-case decision_status/objective, observed record summary,
  calculated feasibility and unresolved preference framing. Keep complete
  supporting records, authority, safety constraints and source references.
  Use the same formatter for overall assessment and role selection; no extra
  model summary, fixture changes or preferred answer.
- [x] Ask independent role questions about material contribution to choosing
  alternatives, even with complete evidence. Preserve actual choices,
  thresholds, conservative consultation and no-assessment/quality semantics.
- [x] Exercise emitted assessment/selection payloads, full/split quantities/
  costs/preferences, missing-versus-nonapplicable evidence and all-case branches.
  Offline preflight:143 tests (34 v1,109 v2) pass.
- [x] Run Pull-forward once and Production once as a focused routing regression,
  within the two-run authorization. Record raw/effective routing separately
  from GPT numerical/dependency/approval quality; never rerun to chase counts.
  Pull-forward: all3 raw needed98.4/72.5/99.2%, not conservative fallbacks;
 3D1+7GPT/6tools,192.9s, full-early selected, pending after Needs revision58.2%
  and model-requested freight review. Production: Production needed99.4%,
  other roles confidently skipped; P2 selected, validation96.3%, advisory
  complete,3D1+3GPT/2tools,121.1s.
- [x] Preserve and report independent GPT issues: false/contradictory overtime
  in the Pull-forward Production finding and freight authority requests despite
  1800<2500. No automatic flag normalization, prompt retuning or extra live run.
  Production's "optimal"/margin-risk prose is stronger than a proved optimum.
- [x] Record actual live outcomes/limitations, final143-test acceptance,
  CLI/dependency/diff checks and local commit. Only routing context/questions,
  tests and directly related docs change; fixtures/thresholds/model choices,
  v1/site/dependencies/Azure remain untouched.
