# Decision model + specialist agent demo

A small manufacturing demo of **Microsoft-Decision-1 working alongside
GPT-4.1-mini**. The decision model chooses an owner; the specialist drafts a
proposal; a second decision pass checks whether that proposal addresses the
original issue. Explicit review requests and approval rules can pause the
terminal for a person.

**[Home and Learn website](https://maxbush6299.github.io/decision-model-agent-demo/)**
is a static learning experience with recorded examples, not a hosted live
inference service. The Python CLI makes real requests to your configured Azure
resource. Neither executes plant actions or grants real spending authority.

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
npm run dev
```

The site is deployed by `.github/workflows/pages.yml` to project GitHub Pages.
It requires no backend, Azure sign-in, or model credentials.

## Documentation

- [Behavior, API contracts, and human-review rules](docs/behavior.md)
- [Troubleshooting and exit codes](docs/troubleshooting.md)
- [Microsoft documentation and release provenance](docs/sources.md)

No license has been selected for this initial publication. Public visibility
does not itself grant an open-source license; normal copyright restrictions apply.
