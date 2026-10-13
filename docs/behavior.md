# Behavior and contracts

## Model boundaries

Decision-1 selects among fixed criteria and returns numerical scores, not a
generated explanation. The specialist GPT supplies the text proposal.

Routing uses `POST /providers/microsoft/v1/systemone`, a configured deployment
in `model`, issue text in `state`, and the named `route` choice question. Four
criteria: production (including quality containment), maintenance, supply-chain,
human-review. Azure CLI tokens use `https://cognitiveservices.azure.com/.default`.

An eligible specialist requires a complete finite probability distribution,
selected expert probability >= 0.70, and a unique highest score. Explicit human
review is honored even if another option scores higher. Never reconstruct missing
probabilities from confidence.

GPT uses `POST /openai/v1/chat/completions`, the configured GPT deployment,
selected-role system instructions, and the actual issue as user data. Its token
scope is `https://ai.azure.com/.default`. Strict structured output contains
exactly `proposed_action` (a constrained identifier) and `brief` (text).

Validation sends the **original issue and actual proposal object** to Decision-1
with one named `validation` choice question:

| Verdict | Fixed criterion |
| --- | --- |
| Addresses the issue | Relevant, actionable, supported by supplied facts. |
| Needs revision | Misses part of the issue, vague, or makes unsupported assumptions. |
| Cannot determine | Insufficient evidence to assess adequacy. |

It checks facts, quantities, approval limits, uncertainties, and action/text
consistency, not persuasiveness. Fixed criterion text is application-defined,
not model reasoning. The verdict ends inference; no automatic revision follows.

The output keeps probabilities and optional model-reported confidence distinct.
Confidence is not substituted for a selected-option probability or interpreted
as a safety guarantee. Timings use a monotonic clock around each HTTP request
and response read; they include network time and exclude token acquisition.

## Human-review origins

| Origin | Trigger |
| --- | --- |
| Model/evidence | Initial human route, insufficient routing evidence, or validation Needs revision / Cannot determine. |
| Specialist-requested approval handoff | Selected `seek_freight_approval` or `engineering_review`, even with positive validation. |
| Policy-required | Selected `expedite_freight` exceeds fixed case approval authority, or cost/limit is unknown. |

For the synthetic shortage, parts for 480 - 310 = **170 assemblies** are missing.
Selected freight costs $4,200 against a $2,500 approval limit. Mentioning freight
as an unselected alternative does not trigger the rule: it checks the action ID,
not a text substring. The action ID is still model output, and validation checks
that it agrees with the recommendation.

`maintenance_review` means diagnostic/inspection planning; `quality_containment`,
`resequence_build`, and `gather_information` are advisory recommendations, not
unconditional approval requests. They can still hand off through the validation
rules. Custom freight proposals lack verified synthetic metadata and require
review rather than interpreting arbitrary numbers from text.

When a proposal exists, one TTY prompt allows **a** (accept for demo), **r**
(reject), or **e** (escalate / ask for information). Initial routing review
allows only **r/e**, before the specialist, with no route override.
All choices print a final demo summary. No further inference or plant operation
follows. EOF, Ctrl+C during the prompt, invalid input, and noninteractive stdin
leave review pending; there is no auto-acceptance.

No preset forces a deterministic model response. The human-review case
encourages abstention; the shortage encourages approval handling. Once the
model output meets an explicit review rule, the terminal behavior is deterministic.

## Recorded website versus live CLI

The static site contains a recorded synthetic example, explicitly labeled.
Visitors cannot use it to invoke Azure. Recorded scores, outputs, and timings
are historical evidence for one example, not promises of quality or performance.
The runnable CLI instead calls the user's configured resource, with no mock
results disguised as live output.
