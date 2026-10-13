# Sources and publication notes

Microsoft implementation guidance consulted for this demo:

- [Decision-1 quickstart](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision):
  deployment-name `model`, state and bounded named choice questions,
  provider endpoint and Cognitive Services authentication scope.
- [Azure OpenAI v1](https://learn.microsoft.com/azure/foundry/openai/api-version-lifecycle):
  resource endpoint formats, Chat Completions and Entra authentication.
- [Structured outputs](https://learn.microsoft.com/azure/foundry/openai/how-to/structured-outputs):
  JSON Schema response format, required fields, strict adherence and
  `additionalProperties: false`.
- [Foundry Entra authentication](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/configure-entra-id):
  administrator-managed access prerequisites.

The website links additional first-party model research. Distinguish vendor
benchmarks from the single recorded synthetic example and the CLI's measured
client round trips. No performance or calibration claim is established by the
small mocked test suite.

This release includes only the runnable CLI, tests, dependency file, documentation,
and static Home/Learn site. It excludes the earlier live web application,
backend, local environments, infrastructure plans, and original private history.
No Azure/model calls are made by GitHub Actions.

The CLI's only direct dependency is `azure-identity>=1.24.0,<2`; publication was
verified with Python 3.11 and azure-identity 1.26.0. Site dependencies are captured
in its lockfile. Python behavior tests use unittest and HTTP/identity mocks.

No license is included: the repository owner has not selected one. No private
resource identifiers or credentials are required to build the static website.

## Recorded evidence and sanitization

`site/src/data/supply-chain-cli-run2.json` contains three genuine historical
inference responses, not new calls or mock results. The published copy is
**sanitized**, not byte-for-byte raw provider evidence:

- The explanatory HTTP host is `example.services.ai.azure.com`.
- Deployment identifiers in strings and objects are
  `YOUR-DECISION-1-DEPLOYMENT` / `YOUR-GPT-4.1-MINI-DEPLOYMENT`.
- The specialist response ID, system fingerprint, and serving replica identifier
  are `REDACTED_RESPONSE_ID`, `REDACTED_SYSTEM_FINGERPRINT`, and
  `REDACTED_SERVING_REPLICA`.

Actual proposals, verdicts, model outputs, probabilities, confidence, usage,
model/version names, service tier, UTC dates, client timings, and stdout are
unchanged. Headers were never captured; no credentials were removed.
`sourceSha256` identifies the original CLI used for the historical capture,
not the public configurable CLI or sanitized fixture. The original private
capture is not included. Use `sha256sum` or PowerShell `Get-FileHash` on the
published fixture when you need its current asset hash.

The website's images retain embedded AI-generation provenance. They are
illustrations, not photographs of a real factory or evidence from the capture.
