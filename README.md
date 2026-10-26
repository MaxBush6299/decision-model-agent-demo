# Decision model + specialist agent demo

A small manufacturing demo of **Microsoft-Decision-1 working alongside
GPT-4.1-mini**. The decision model chooses an owner; the specialist drafts a
proposal; a second decision pass checks whether that proposal addresses the
original issue. Explicit review requests and approval rules can pause the
terminal for a person.

## The published site

**[Open the site](https://maxbush6299.github.io/decision-model-agent-demo/)**
is a static, read-only experience of recorded, synthetic examples. It makes no
model calls from the browser, and nothing in it is executed.

- **Home** explains what a decision model is and links to the two pages below.
- **Learn** (`#learn`) is an in-depth worked example: what a decision model
  decides, and how routing, specialist advice, validation, and human review fit
  together in one recorded shortage case.
- **Demo showcase** (`#showcase`) replays four recorded scenarios (quality hold,
  carrier delay, production resequence, order pull-forward) on one animated
  master diagram of agents working a case. Pick a scenario, then play, pause,
  step, change speed, or skip long waits. A collapsible "Live step" pane shows the
  current step, and a terminal drawer shows the recorded transcript. Outcomes are
  advisory proposals, requires-human-review, or pending validation below policy.
  Replays were selected after the fact and are not a reliability measure.

### Models

| Where | Models |
| --- | --- |
| Bounded scoring, routing, and proposal validation (both versions) | **Microsoft-Decision-1** |
| v1 CLI in this repo (`decision_demo.py`) | **GPT-4.1-mini** specialist (your own deployment) |
| Recorded v2 showcase examples | Specialist and coordinator agents used GPT-6 Luna (profile `gpt-6-luna`), per the recording metadata |

The v1 CLI default and the v2 recordings use different GPT models; don't read one
as the other. Deployment names and endpoints are not published here.

### What is in this repository

`main` holds everything: the v1 Python CLI (`decision_demo.py`), the v2
multi-agent CLI (`decision_demo_v2.py` and `decision_v2/`, built on Microsoft
Agent Framework with synthetic read-only fixture tools), the site, and the
**recordings** of v2 runs that the Demo showcase replays. The site itself runs no
model and executes nothing. v2 setup, boundaries, and results are in
[docs/v2.md](docs/v2.md). Pre-merge history of the v2 work is preserved in the tag
`v2-pre-integration-2026-10-26`.

## v1 CLI

The Python CLI makes real requests to your configured Azure resource. It
executes no plant actions and grants no real spending authority.

```text
Issue -> Decision-1 routing -> GPT specialist proposal
      -> Decision-1 proposal validation -> approval rules -> human review if needed
```

## Prerequisites

- Python **3.11+**, Azure CLI installed, and an existing Microsoft Entra sign-in.
- An Azure Foundry resource with a **Microsoft-Decision-1** deployment and a
  **GPT-4.1-mini** deployment supporting Chat Completions structured outputs.
- Existing permission to call both models and an approved network path to the
  resource. For GPT v1, Learn documents the **Cognitive Services OpenAI User**
  role. Ask your resource administrator to verify appropriate Decision-1
  data-plane permissions; this script does not grant roles or change access.
- Understand applicable usage charges and your deployment quotas.

Bring your own existing deployments. No personal endpoint or deployment is
configured by default. This repository does not provision Azure infrastructure.

## Run in PowerShell

```powershell
git clone https://github.com/MaxBush6299/decision-model-agent-demo.git
Set-Location decision-model-agent-demo
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
az login
$env:FOUNDRY_ENDPOINT = 'https://YOUR-RESOURCE.services.ai.azure.com'
$env:DECISION_DEPLOYMENT = 'YOUR-DECISION-1-DEPLOYMENT'
$env:LLM_DEPLOYMENT = 'YOUR-GPT-4.1-MINI-DEPLOYMENT'
.\.venv\Scripts\python.exe decision_demo.py --example supply-chain
```

Already signed in? Skip `az login`; the credential uses your current Azure CLI
identity. No API keys or tokens belong in the repository or configuration.
Environment values above are placeholders; replace them with your deployment
details. Configuration values are nonsecret, but keep private tenant/resource
identifiers out of public issues and screenshots.

On macOS/Linux, use `python3 -m venv .venv`, `.venv/bin/python -m pip install -r
requirements.txt`, and `.venv/bin/python decision_demo.py --example supply-chain`.
Set the same variables with `export FOUNDRY_ENDPOINT='https://...'`,
`export DECISION_DEPLOYMENT='...'`, and `export LLM_DEPLOYMENT='...'`.

CLI flags `--endpoint`, `--decision-deployment`, and `--llm-deployment` override
the environment variables. Endpoint must be an HTTPS resource root ending in
`.services.ai.azure.com` or `.openai.azure.com`, without an API path, query,
credentials, or port. Missing/invalid configuration fails before authentication.
`--help` and `--list-examples` work offline without configuration.

## Cases and human review

```powershell
.\.venv\Scripts\python.exe decision_demo.py --example supply-chain
.\.venv\Scripts\python.exe decision_demo.py --example maintenance
.\.venv\Scripts\python.exe decision_demo.py --example production
.\.venv\Scripts\python.exe decision_demo.py --example human-review
.\.venv\Scripts\python.exe decision_demo.py --text "Synthetic issue: a confirmed shipment delay."
```

| Preset | Synthetic problem |
| --- | --- |
| `supply-chain` | 480 assemblies needed, parts for 310 available; delayed shipment, $4,200 freight above a $2,500 approval limit, unapproved alternate. |
| `maintenance` | Three stops in 90 minutes, rising motor temperature, overdue bearing inspection, maintenance window 45 minutes away. |
| `production` | Quality containment: 6/80 failed samples, two lots, some parts shipped, unknown gauge calibration. |
| `human-review` | Incomplete and conflicting reports lacking measurements, quantities, lots, and safety context. |

The proposal includes an action identifier and **Assessment / Proposed steps /
Approvals / Unknowns**. Terminal output distinguishes option probabilities,
optional model-reported confidence, and client-observed HTTP round-trip times.

Human review can originate from model/evidence, an explicit specialist approval
request, or deterministic approval policy. When required, run in a real terminal
to accept for the demo, reject, or escalate. Initial review has no proposal to
accept and never overrides the route. **No preset guarantees a pause end-to-end:**
model routing, actions, and verdicts vary. Once an explicit approval action is
returned and validation succeeds, its handoff is deterministic.

## Boundaries

- At most **two Decision-1 calls and one GPT call** per invocation; no retries,
  continuous stream, rewrite loop, or hidden inference.
- Human/insufficient routing skips both downstream calls. Malformed responses
  and inference errors fail explicitly, never become acceptance.
- The **0.70 routing rule** is an illustrative application policy, not a
  calibrated guarantee. Proposal validation is not proof of real-world resolution.
- Demo acceptance does not execute actions, approve purchases, or release lots.
- Every live invocation can incur fees. Rate limits depend on your deployments;
  HTTP 429 stops without retry. The original demo was developed under 20 RPM
  Decision-1 / 10 RPM GPT limits; these are not universal service limits.
- Only send synthetic data or data you are authorized to send. The program prints
  the issue and proposal; protect your terminal logs accordingly.

## Develop and verify

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

To run the v1 and v2 tests together, install the v2 dependencies first (this
includes `requirements.txt`):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-v2.txt
.\.venv\Scripts\python.exe -m unittest
```

Tests mock credentials and HTTP, including error paths and terminal review.
They do not call Azure. The release CLI's parameterized configuration has been
verified with mocks, **not a new live smoke test**. Earlier user runs of the
private demo succeeded; that is not a guarantee for a different resource.

For the site, use Node **22**:

```powershell
Set-Location site
npm ci
npm test -- --run
npm run build
npm run dev       # local dev server (Vite prints the URL)
npm run preview   # serves the built site (after npm run build)
```

The site is deployed by `.github/workflows/pages.yml` to project GitHub Pages.
It requires no backend, Azure sign-in, or model credentials.

## Documentation

- [Behavior, API contracts, and human-review rules](docs/behavior.md)
- [v2 multi-agent examples: setup, boundaries, and recorded results](docs/v2.md)
- [Troubleshooting and exit codes](docs/troubleshooting.md)
- [Microsoft documentation and release provenance](docs/sources.md)

No license has been selected for this initial publication. Public visibility
does not itself grant an open-source license; normal copyright restrictions apply.
