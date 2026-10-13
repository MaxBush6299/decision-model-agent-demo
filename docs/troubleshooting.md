# Troubleshooting

| Exit code | Meaning |
| --- | --- |
| 0 | Completed demo flow or a recorded human demo choice; not proof of plant resolution. |
| 1 | Configuration/input, authentication, transport, HTTP, JSON, or model-contract failure. |
| 2 | Human review pending (EOF, interruption, invalid choice, or noninteractive input); argparse usage errors also use 2. |

## Configuration and identity

Use `--help` or `--list-examples` without any Azure configuration. For inference,
set all three variables from the README. Do not append an API route to the
resource root. Check `az account show` locally to confirm the intended identity
and subscription; do not paste identity details or tokens into public issues.
Sign in yourself with `az login` if necessary.

Authentication uses AzureCliCredential with a 15-second process timeout.
The script does not change subscriptions or sign-in state, provision resources,
assign roles, create keys, or alter network access.

## Failures

- **401:** verify the signed-in identity and the documented token audience.
- **403:** ask your administrator to check current data-plane access and approved
  network reachability. Do not broaden access just to make a demo run.
- **404:** verify the resource root, deployment identifiers, and API path.
- **429:** wait before a separate invocation; no automatic retry is performed.
- **DNS:** resolve the resource hostname on the affected machine/network.
- **TLS verification/handshake:** have your administrator inspect the approved
  trust/proxy path. Never disable certificate verification.
- **Socket errors:** numeric OS error codes distinguish refused/reset/network
  failures; check the approved network path.
- **Timeout:** the configured 60 seconds bounds each blocking HTTP operation.
  Elapsed time alone does not distinguish network delay from inference delay.
  Do not blindly raise timeouts or bypass network controls.
- **Malformed/truncated/filtered/refused model output:** the CLI fails clearly;
  it does not fabricate a proposal or acceptance.

Transport diagnostics print category/type, numeric OS/certificate codes and
elapsed time. Raw exception messages, credential-bearing proxy URLs, headers,
and tokens are withheld. HTTP statuses remain separate from transport errors.

## Why no human prompt?

Run directly in an interactive terminal, not with piped stdin. Review requires
an applicable model/evidence, specialist approval, or action-policy rule; a
positive validator with an ordinary advisory action can legitimately finish.
Try `--example supply-chain`, but do not assume the model will always choose an
approval action. No preset guarantees a prompt end-to-end.

An initial review has no proposal to accept. If you choose escalation, the
program ends: it does not gather facts, reroute, or rewrite automatically.

## Reporting

Reproduce with synthetic data. Share only the safe error category/code and
whether the run was interactive; redact resource identifiers and private issue
text. Unit tests are offline: `python -m unittest -v`. A connectivity/root HEAD
check is not an inference test, and a passing mocked test does not prove your
current Azure permissions or model behavior.
