# Decision model v2 Implementation Plan

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
- No model inference, push/merge/publication, resource/access changes, or plant writes.
- At most three specialists and one Coordinator; one initial assessment and one continuation.
- <=20 GPT, <=3 Decision-1, <=23 total attempts; failed attempts count; no retries.
- <=3 GPT attempts and <=2 unique successful tool executions per specialist invocation.
- Sequential specialists; rolling 60-second limits: 10 GPT and 20 Decision-1.
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
