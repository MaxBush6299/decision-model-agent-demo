import contextlib
import io
import json
import os
import socket
import ssl
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

import decision_demo as demo
from azure.core.exceptions import ClientAuthenticationError

ENDPOINT = "https://example.services.ai.azure.com"

def response(choice="maintenance", probabilities=None, confidence=0.83):
    answer = {
        "type": "choice",
        "choice": choice,
        "probabilities": probabilities or {
            "production": 0.05, "maintenance": 0.85,
            "supply-chain": 0.05, "human-review": 0.05,
        },
    }
    if confidence is not None:
        answer["confidence"] = confidence
    return {"answers": {"route": answer}}


PROPOSAL = {
    "proposed_action": "maintenance_review",
    "brief": (
        "Assessment: The observations need qualified maintenance assessment; a cause is unproven.\n"
        "Proposed steps: Escalate the readings and stop history for qualified inspection planning.\n"
        "Approvals: Authorized staff must decide operating status and any schedule change.\n"
        "Unknowns: Temperature limits, inspection findings, and safety assessment."
    ),
}


def llm_response(action="maintenance_review", brief=PROPOSAL["brief"]):
    return {"choices": [{
        "finish_reason": "stop",
        "message": {"content": json.dumps({"proposed_action": action, "brief": brief})},
    }]}


LLM = llm_response()


def validation_response(choice="Addresses the issue", confidence=0.61):
    scores = dict.fromkeys(
        ["Addresses the issue", "Needs revision", "Cannot determine"], 0.05
    )
    scores[choice] = 0.9
    answer = {"type": "choice", "choice": choice, "probabilities": scores}
    if confidence is not None:
        answer["confidence"] = confidence
    return {"answers": {"validation": answer}}


class DemoTests(unittest.TestCase):
    def setUp(self):
        patch.dict(os.environ, {
            "FOUNDRY_ENDPOINT": ENDPOINT,
            "DECISION_DEPLOYMENT": "decision-gate",
            "LLM_DEPLOYMENT": "specialist-llm",
        }).start()
        self.credentials = patch.object(demo, "AzureCliCredential").start()
        self.credentials.return_value.get_token.return_value.token = "TEST_TOKEN"
        self.http = patch.object(demo.urllib.request, "urlopen").start()
        self.tty = patch.object(demo.sys.stdin, "isatty", return_value=True).start()
        self.prompt = patch("builtins.input", return_value="e").start()
        self.addCleanup(patch.stopall)

    def wire(self, *payloads):
        handles = []
        for payload in payloads:
            handle = MagicMock()
            handle.__enter__.return_value.read.return_value = (
                payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            )
            handles.append(handle)
        self.http.side_effect = handles

    def run_cli(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = demo.main(list(args))
        return result, output.getvalue(), errors.getvalue()

    def test_http_contract_and_specialist_only(self):
        self.wire(response(), LLM, validation_response())
        result, output, errors = self.run_cli("--example", "maintenance")
        self.assertEqual((result, errors), (0, ""))
        first, second, third = [c.args[0] for c in self.http.call_args_list]
        self.assertEqual(first.full_url, ENDPOINT + "/providers/microsoft/v1/systemone")
        body = json.loads(first.data)
        self.assertEqual(body["model"], "decision-gate")
        self.assertEqual(body["state"], demo.EXAMPLES["maintenance"])
        self.assertEqual(body["questions"]["route"]["criteria"], demo.ROUTES)
        self.assertEqual(second.full_url, ENDPOINT + "/openai/v1/chat/completions")
        body = json.loads(second.data)
        self.assertEqual(body["model"], "specialist-llm")
        self.assertIn(demo.SPECIALISTS["maintenance"], body["messages"][0]["content"])
        self.assertNotIn(demo.SPECIALISTS["production"], body["messages"][0]["content"])
        self.assertEqual(body["messages"][1]["content"], demo.EXAMPLES["maintenance"])
        for section in ("Assessment", "Proposed steps", "Approvals", "Unknowns"):
            self.assertIn(section, body["messages"][0]["content"])
        self.assertEqual(body["max_completion_tokens"], 600)
        schema = body["response_format"]
        self.assertEqual(schema["type"], "json_schema")
        self.assertTrue(schema["json_schema"]["strict"])
        fields = schema["json_schema"]["schema"]
        self.assertEqual(fields["required"], ["proposed_action", "brief"])
        self.assertFalse(fields["additionalProperties"])
        self.assertEqual(fields["properties"]["proposed_action"]["enum"], list(demo.ACTIONS))
        self.assertEqual(third.full_url, first.full_url)
        body = json.loads(third.data)
        self.assertEqual(body["model"], "decision-gate")
        self.assertEqual(body["state"], {
            "original_issue": demo.EXAMPLES["maintenance"],
            "proposal": PROPOSAL,
        })
        self.assertEqual(body["questions"]["validation"]["type"], "choice")
        self.assertEqual(body["questions"]["validation"]["criteria"], demo.VERDICTS)
        self.assertIn("constraints", body["questions"]["validation"]["instructions"])
        self.assertIn("unsupported", body["questions"]["validation"]["instructions"])
        self.assertEqual(first.get_header("Authorization"), "Bearer TEST_TOKEN")
        for call in self.http.call_args_list:
            self.assertEqual(call.kwargs["timeout"], 60)
        scopes = [c.args[0] for c in self.credentials.return_value.get_token.call_args_list]
        self.assertEqual(scopes, [demo.DECISION_SCOPE, demo.LLM_SCOPE, demo.DECISION_SCOPE])
        self.assertIn("maintenance: 0.850000", output)
        self.assertIn("Model-reported confidence: 0.830000", output)
        self.assertIn("Client-observed Decision-1 round trip:", output)
        self.assertIn("Client-observed GPT-4.1-mini round trip:", output)
        self.assertIn("Client-observed Decision-1 validation round trip:", output)
        self.assertIn("Model-reported confidence: 0.610000", output)
        self.assertIn("Addresses the issue: 0.900000", output)
        self.assertIn("not proof of real-world resolution", output)
        self.assertNotIn("TEST_TOKEN", output)

    def test_each_expert_route(self):
        for route in demo.SPECIALISTS:
            with self.subTest(route=route):
                self.http.reset_mock()
                probs = {key: 0.1 for key in demo.ROUTES}
                probs[route] = 0.7
                self.wire(response(route, probs), LLM, validation_response())
                result, output, _ = self.run_cli("--example", route)
                self.assertEqual(result, 0)
                self.assertIn(f"Effective route: {route}", output)
                self.assertEqual(self.http.call_count, 3)
                self.assertIn("Synthetic case brief (illustrative, not live plant data):", output)
                self.assertLess(output.index("Synthetic case brief"), output.index("Model-selected route"))
                self.assertLess(output.index("Model-selected route"), output.index("Proposal (advisory"))
                body = json.loads(self.http.call_args_list[-1].args[0].data)
                self.assertEqual(body["state"]["original_issue"], demo.EXAMPLES[route])

    def test_scenario_facts_and_constraints(self):
        facts = {
            "supply-chain": (
                "480 assemblies", "310", "$4,200", "$2,500",
                "not engineering-approved", "delayed",
            ),
            "maintenance": (
                "three station stops", "90 minutes", "rising motor temperature",
                "overdue bearing inspection", "45 minutes", "wants to continue",
            ),
            "production": (
                "6 of 80", "two lots", "already shipped", "gauge calibration is unknown",
            ),
            "human-review": (
                "station", "quantities", "measurements", "lots", "safety",
            ),
        }
        for route, snippets in facts.items():
            for snippet in snippets:
                with self.subTest(route=route, snippet=snippet):
                    self.assertIn(snippet, demo.EXAMPLES[route])
        self.assertIn("quality containment", demo.ROUTES["production"])
        self.assertIn("quality containment", demo.SPECIALISTS["production"])
        self.assertIn("release", demo.SPECIALISTS["production"])
        self.assertIn("suspected", demo.SPECIALISTS["maintenance"])
        self.assertIn("safe-to-operate", demo.SPECIALISTS["maintenance"])
        self.assertIn("approval", demo.SPECIALISTS["supply-chain"])

    def test_custom_text(self):
        self.wire(response(), LLM, validation_response())
        self.assertEqual(self.run_cli("--text", "A synthetic motor vibrates.")[0], 0)
        body = json.loads(self.http.call_args_list[0].args[0].data)
        self.assertEqual(body["state"], "A synthetic motor vibrates.")
        validation = json.loads(self.http.call_args_list[2].args[0].data)
        self.assertEqual(validation["state"]["original_issue"], "A synthetic motor vibrates.")
        _, output, _ = self.run_cli("--list-examples")
        self.assertIn("gauge calibration is unknown", output)

    def test_timings_measure_each_round_trip(self):
        self.wire(response(), LLM, validation_response())
        with patch.object(demo, "perf_counter", side_effect=[1, 1.25, 2, 2.5, 3, 3.75]):
            result, output, _ = self.run_cli("--example", "maintenance")
        self.assertEqual(result, 0)
        self.assertIn("Decision-1 round trip: 250.0 ms", output)
        self.assertIn("GPT-4.1-mini round trip: 500.0 ms", output)
        self.assertIn("Decision-1 validation round trip: 750.0 ms", output)

    def test_explicit_review_never_calls_llm(self):
        self.wire(response("human-review"))
        result, output, _ = self.run_cli("--example", "human-review")
        self.assertEqual(result, 0)
        self.assertEqual(self.http.call_count, 1)
        self.assertIn("Effective route: human-review", output)
        self.assertIn("LLM skipped", output)
        self.assertIn("validation skipped", output)
        self.assertIn("Model/evidence review", output)
        self.assertIn("Escalated", output)
        prompt = self.prompt.call_args.args[0]
        self.assertNotIn("[a]", prompt)

    def test_insufficient_evidence_never_calls_llm(self):
        cases = [
            {"production": 0.1, "maintenance": 0.699999,
             "supply-chain": 0.1, "human-review": 0.100001},
            {"production": 0.45, "maintenance": 0.45,
             "supply-chain": 0.05, "human-review": 0.05},
            {"production": 0.8, "maintenance": 0.1,
             "supply-chain": 0.05, "human-review": 0.05},
            {"maintenance": 0.9},
        ]
        for probs in cases:
            with self.subTest(probs=probs):
                self.http.reset_mock()
                self.wire(response(probabilities=probs))
                result, output, _ = self.run_cli("--example", "maintenance")
                self.assertEqual(result, 0)
                self.assertEqual(self.http.call_count, 1)
                self.assertIn("Effective route: human-review", output)
                self.assertIn("validation skipped", output)

    def test_each_validation_verdict_finishes_without_rewriting(self):
        for verdict in ("Addresses the issue", "Needs revision", "Cannot determine"):
            with self.subTest(verdict=verdict):
                self.http.reset_mock()
                self.wire(response(), LLM, validation_response(verdict))
                result, output, errors = self.run_cli("--example", "maintenance")
                self.assertEqual((result, errors), (0, ""))
                self.assertEqual(self.http.call_count, 3)
                self.assertIn(f"Proposal validation verdict (model judgment): {verdict}", output)
                self.assertIn(demo.VERDICTS[verdict], output)
                self.assertEqual(output.count("Proposal (advisory"), 1)
                if verdict != "Addresses the issue":
                    self.assertIn("Model/evidence review", output)
                    self.assertIn("Escalated", output)

    def test_selected_freight_triggers_policy_but_alternative_does_not(self):
        for action, expected in (("expedite_freight", True), ("resequence_build", False)):
            with self.subTest(action=action):
                self.http.reset_mock()
                self.prompt.reset_mock()
                self.wire(response("supply-chain", {
                    "production": 0.05, "maintenance": 0.05,
                    "supply-chain": 0.85, "human-review": 0.05,
                }), llm_response(action, "Consider $4,200 freight only as an alternative."),
                    validation_response())
                result, output, errors = self.run_cli("--example", "supply-chain")
                self.assertEqual((result, errors), (0, ""))
                self.assertEqual(self.http.call_count, 3)
                self.assertEqual(self.prompt.call_count, int(expected))
                if expected:
                    self.assertIn("Policy-required review", output)
                    self.assertIn("$4,200", output)
                    self.assertIn("$2,500", output)
                    self.assertIn("Escalated", output)
                else:
                    self.assertIn("no human review required by demo rules", output)

    def test_both_review_origins_and_every_proposal_choice(self):
        for choice, expected in (
            ("a", "Accepted for this demo"), ("r", "Rejected for this demo"),
            ("e", "Escalated"),
        ):
            with self.subTest(choice=choice):
                self.http.reset_mock()
                self.prompt.reset_mock()
                self.prompt.return_value = choice
                self.wire(response(), llm_response("expedite_freight"),
                          validation_response("Needs revision"))
                result, output, _ = self.run_cli("--example", "supply-chain")
                self.assertEqual(result, 0)
                self.assertEqual(self.http.call_count, 3)
                self.assertEqual(self.prompt.call_count, 1)
                self.assertIn("Model/evidence review", output)
                self.assertIn("Policy-required review", output)
                self.assertIn(expected, output)
                self.assertIn("no plant actions or real authorization", output)

    def test_custom_freight_without_metadata_requires_review(self):
        self.wire(response(), llm_response("expedite_freight"), validation_response())
        result, output, _ = self.run_cli("--text", "A synthetic delayed shipment.")
        self.assertEqual(result, 0)
        self.assertIn("Policy-required review", output)
        self.assertIn("cost or approval limit is unknown", output)
        self.assertEqual(self.http.call_count, 3)

    def test_freight_policy_threshold_and_approval_request(self):
        for cost, expected in ((2500, False), (2501, True)):
            with self.subTest(cost=cost), patch.dict(demo.FREIGHT_POLICY, {"supply-chain": (cost, 2500)}):
                reviews = demo.policy_reviews({"proposed_action": "expedite_freight"}, "supply-chain")
                self.assertEqual(bool(reviews), expected)
        reviews = demo.policy_reviews({
            "proposed_action": "seek_freight_approval", "brief": "Seek approval for $4,200 freight.",
        }, "supply-chain")
        self.assertEqual(reviews, [])

    def test_specialist_requested_approval_pauses_despite_positive_validation(self):
        for action in ("seek_freight_approval", "engineering_review"):
            with self.subTest(action=action):
                self.http.reset_mock()
                self.prompt.reset_mock()
                self.wire(response("supply-chain", {
                    "production": 0.05, "maintenance": 0.05,
                    "supply-chain": 0.85, "human-review": 0.05,
                }), llm_response(action), validation_response())
                result, output, errors = self.run_cli("--example", "supply-chain")
                self.assertEqual((result, errors), (0, ""))
                self.assertEqual(self.http.call_count, 3)
                self.assertEqual(self.prompt.call_count, 1)
                self.assertIn("Specialist-requested approval handoff", output)
                self.assertIn(action, output)
                self.assertIn("Escalated", output)
                self.assertNotIn("Policy-required review:", output)
                self.assertNotIn("Model/evidence review:", output)

    def test_approval_request_noninteractive_stays_pending(self):
        self.tty.return_value = False
        self.wire(response(), llm_response("seek_freight_approval"), validation_response())
        result, output, _ = self.run_cli("--example", "supply-chain")
        self.assertEqual(result, 2)
        self.prompt.assert_not_called()
        self.assertEqual(self.http.call_count, 3)
        self.assertIn("Specialist-requested approval handoff", output)
        self.assertIn("Pending", output)

    def test_initial_review_cannot_accept_nonexistent_proposal(self):
        for choice, code in (("a", 2), ("e", 0), ("r", 0)):
            with self.subTest(choice=choice):
                self.http.reset_mock()
                self.prompt.reset_mock()
                self.prompt.return_value = choice
                self.wire(response("human-review"))
                result, output, _ = self.run_cli("--example", "human-review")
                self.assertEqual(result, code)
                self.assertEqual(self.http.call_count, 1)
                self.assertEqual(self.prompt.call_count, 1)
                self.assertNotIn("Accepted", output)
                self.assertNotIn("Proposal (advisory", output)
                self.assertNotIn("[a]", self.prompt.call_args.args[0])

    def test_noninteractive_input_never_prompts_or_accepts(self):
        self.tty.return_value = False
        for proposal_exists in (False, True):
            with self.subTest(proposal_exists=proposal_exists):
                self.http.reset_mock()
                if proposal_exists:
                    self.wire(response(), LLM, validation_response("Cannot determine"))
                else:
                    self.wire(response("human-review"))
                result, output, _ = self.run_cli("--example", "maintenance")
                self.assertEqual(result, 2)
                self.prompt.assert_not_called()
                self.assertIn("Pending", output)
                self.assertIn("noninteractive", output)
                self.assertNotIn("Accepted", output)
                self.assertEqual(self.http.call_count, 3 if proposal_exists else 1)

    def test_interrupted_or_invalid_review_stays_pending_without_inference(self):
        for value in (EOFError(), KeyboardInterrupt(), "invalid"):
            with self.subTest(value=value):
                self.http.reset_mock()
                self.prompt.reset_mock()
                self.prompt.side_effect = value if isinstance(value, BaseException) else None
                self.prompt.return_value = value
                self.wire(response(), LLM, validation_response("Needs revision"))
                result, output, _ = self.run_cli("--example", "maintenance")
                self.assertEqual(result, 2)
                self.assertIn("Pending", output)
                self.assertNotIn("Accepted", output)
                self.assertEqual(self.http.call_count, 3)
                self.assertEqual(self.prompt.call_count, 1)

    def test_bad_structured_proposal_stops_before_validation(self):
        for content in (
            "not JSON", "null", "[]", "{}",
            json.dumps({"proposed_action": "unknown", "brief": "text"}),
            json.dumps({"proposed_action": "maintenance_review", "brief": ""}),
            json.dumps({"proposed_action": "maintenance_review", "brief": 1}),
            json.dumps({"proposed_action": "maintenance_review", "brief": "text", "extra": True}),
        ):
            with self.subTest(content=content):
                self.http.reset_mock()
                self.prompt.reset_mock()
                llm = {"choices": [{
                    "finish_reason": "stop", "message": {"content": content},
                }]}
                self.wire(response(), llm)
                result, output, errors = self.run_cli("--example", "maintenance")
                self.assertEqual(result, 1)
                self.assertIn("GPT-4.1-mini", errors)
                self.assertEqual(self.http.call_count, 2)
                self.prompt.assert_not_called()
                self.assertNotIn("Proposal validation verdict", output)

    def test_missing_validation_confidence_not_fabricated(self):
        self.wire(response(), LLM, validation_response(confidence=None))
        result, output, errors = self.run_cli("--example", "maintenance")
        self.assertEqual((result, errors), (0, ""))
        self.assertIn("Model-reported confidence: not reported", output)

    def test_invalid_validation_response_never_accepts(self):
        cases = [None, {}, {"answers": {"validation": {"type": "score"}}}]
        bad = validation_response()
        bad["answers"]["validation"]["choice"] = "unknown"
        cases.append(bad)
        for scores in (
            None, {}, {"Addresses the issue": 1.0}, [],
            {"Addresses the issue": 1.0, "unknown": 0.0},
            dict.fromkeys(["Addresses the issue", "Needs revision", "Cannot determine"], 0.9),
        ):
            bad = validation_response()
            bad["answers"]["validation"]["probabilities"] = scores
            cases.append(bad)
        for value in (float("nan"), float("inf"), -1, 2, True, "0.9"):
            bad = validation_response()
            bad["answers"]["validation"]["probabilities"]["Addresses the issue"] = value
            cases.append(bad)
        bad = validation_response()
        bad["answers"]["validation"]["confidence"] = 2
        cases.append(bad)
        cases.append(b"not JSON")
        for payload in cases:
            with self.subTest(payload=payload):
                self.http.reset_mock()
                self.wire(response(), LLM, payload)
                result, output, errors = self.run_cli("--example", "maintenance")
                self.assertEqual(result, 1)
                self.assertEqual(self.http.call_count, 3)
                self.assertIn("validation", errors)
                self.assertNotIn("Proposal validation verdict", output)
                self.assertIn("Proposal (advisory", output)

    def test_validation_http_failures_never_accept_or_retry(self):
        for error in (
            urllib.error.HTTPError(ENDPOINT, 429, "limited", {}, None),
            urllib.error.HTTPError(ENDPOINT, 401, "unauthorized", {}, None),
            urllib.error.URLError("unreachable"), TimeoutError(),
        ):
            with self.subTest(error=error):
                self.http.reset_mock()
                self.wire(response(), LLM)
                self.http.side_effect = [*self.http.side_effect, error]
                result, output, errors = self.run_cli("--example", "maintenance")
                self.assertEqual(result, 1)
                self.assertEqual(self.http.call_count, 3)
                self.assertIn("Decision-1 validation", errors)
                self.assertNotIn("Proposal validation verdict", output)

    def test_validation_auth_failure_is_explicit(self):
        self.wire(response(), LLM)
        token = MagicMock(token="TEST_TOKEN")
        self.credentials.return_value.get_token.side_effect = [
            token, token, ClientAuthenticationError(message="TEST_SECRET"),
        ]
        result, output, errors = self.run_cli("--example", "maintenance")
        self.assertEqual(result, 1)
        self.assertEqual(self.http.call_count, 2)
        self.assertIn("Decision-1 validation authentication failed", errors)
        self.assertNotIn("TEST_SECRET", errors)
        self.assertNotIn("Proposal validation verdict", output)

    def test_missing_scores_and_confidence_not_fabricated(self):
        payload = response(confidence=None)
        del payload["answers"]["route"]["probabilities"]
        self.wire(payload)
        result, output, _ = self.run_cli("--example", "maintenance")
        self.assertEqual(result, 0)
        self.assertIn("maintenance: not reported", output)
        self.assertIn("Model-reported confidence: not reported", output)
        self.assertEqual(self.http.call_count, 1)

    def test_bad_decision_schema(self):
        cases = [None, {}, {"answers": []}, response("alien")]
        bad = response()
        bad["answers"]["route"]["type"] = "score"
        cases.append(bad)
        for value in (float("nan"), float("inf"), -0.1, 1.1, True, "0.9"):
            bad = response()
            bad["answers"]["route"]["probabilities"]["maintenance"] = value
            cases.append(bad)
        bad = response()
        bad["answers"]["route"]["probabilities"]["alien"] = 0.1
        cases.append(bad)
        bad = response()
        bad["answers"]["route"]["probabilities"] = []
        cases.append(bad)
        cases.append(response(confidence=2))
        cases.append(response(probabilities=dict.fromkeys(demo.ROUTES, 0.8)))
        for payload in cases:
            with self.subTest(payload=payload):
                self.http.reset_mock()
                self.wire(payload)
                result, _, errors = self.run_cli("--example", "production")
                self.assertEqual(result, 1)
                self.assertIn("ERROR:", errors)
                self.assertEqual(self.http.call_count, 1)

    def test_http_errors_no_retry(self):
        for code in (401, 403, 404, 429, 500):
            with self.subTest(code=code):
                self.http.reset_mock()
                self.http.side_effect = urllib.error.HTTPError(
                    ENDPOINT, code, "failed", {"Retry-After": "60"}, None
                )
                result, _, errors = self.run_cli("--example", "maintenance")
                self.assertEqual(result, 1)
                self.assertIn(f"HTTP {code}", errors)
                self.assertEqual(self.http.call_count, 1)

    def test_network_timeout_and_invalid_json(self):
        for error in (urllib.error.URLError("unreachable"), TimeoutError()):
            self.http.side_effect = error
            self.assertEqual(self.run_cli("--example", "maintenance")[0], 1)
        for raw in (b"not JSON", b"\xff"):
            self.wire(raw)
            self.assertIn("invalid JSON", self.run_cli("--example", "maintenance")[2])

    def test_transport_errors_preserve_safe_categories_without_credentials(self):
        certificate = ssl.SSLCertVerificationError(1, "TEST_SECRET")
        certificate.verify_code = 20
        cases = (
            (socket.gaierror(11001, "TEST_SECRET"), "DNS resolution failed", "errno=11001"),
            (certificate, "TLS certificate verification failed", "verify_code=20"),
            (ssl.SSLError(1, "TEST_SECRET"), "TLS handshake failed", "SSLError"),
            (TimeoutError("TEST_SECRET"), "connection or response timed out", "TimeoutError"),
            (ConnectionResetError(10054, "TEST_SECRET"), "socket connection failed", "errno=10054"),
            (OSError(10051, "TEST_SECRET"), "network I/O failed", "errno=10051"),
            ("https://user:TEST_SECRET@proxy.example.invalid", "transport failed", "URLError"),
        )
        for reason, category, detail in cases:
            for wrapped in (True, False) if isinstance(reason, OSError) else (True,):
                with self.subTest(reason=type(reason).__name__, wrapped=wrapped):
                    self.http.reset_mock()
                    self.http.side_effect = urllib.error.URLError(reason) if wrapped else reason
                    with patch.object(demo, "perf_counter", side_effect=[10, 12.5]):
                        result, _, errors = self.run_cli("--example", "supply-chain")
                    self.assertEqual(result, 1)
                    self.assertIn(category, errors)
                    self.assertIn(detail, errors)
                    self.assertIn("after 2.5 s", errors)
                    self.assertIn("60 s request timeout", errors)
                    self.assertIn("no retry was made", errors)
                    self.assertNotIn("TEST_SECRET", errors)
                    self.assertNotIn("TEST_TOKEN", errors)
                    self.assertNotIn("proxy.example.invalid", errors)
                    self.assertEqual(self.http.call_count, 1)

    def test_auth_failure_no_http(self):
        self.credentials.return_value.get_token.side_effect = ClientAuthenticationError(
            message="TEST_SECRET"
        )
        result, _, errors = self.run_cli("--example", "maintenance")
        self.assertEqual(result, 1)
        self.assertIn("az login", errors)
        self.assertNotIn("TEST_SECRET", errors)
        self.http.assert_not_called()

    def test_invalid_llm_response_is_not_success(self):
        for payload in ({}, {"choices": []},
                        {"choices": [{"finish_reason": "length", "message": {"content": "partial"}}]},
                        {"choices": [{"finish_reason": "content_filter", "message": {"content": ""}}]},
                        {"choices": [{"finish_reason": "stop", "message": {"content": None}}]}):
            with self.subTest(payload=payload):
                self.wire(response(), payload)
                result, output, errors = self.run_cli("--example", "maintenance")
                self.assertEqual(result, 1)
                self.assertIn("GPT-4.1-mini", errors)
                self.assertNotIn("Proposal (advisory", output)
                self.assertNotIn("Proposal validation verdict", output)

    def test_llm_failure_retains_route_output(self):
        handle = MagicMock()
        handle.__enter__.return_value.read.return_value = json.dumps(response()).encode()
        self.http.side_effect = [handle, urllib.error.URLError("unreachable")]
        result, output, errors = self.run_cli("--example", "maintenance")
        self.assertEqual(result, 1)
        self.assertIn("Effective route: maintenance", output)
        self.assertIn("GPT-4.1-mini", errors)

    def test_input_validation_and_listing_are_offline(self):
        self.assertEqual(self.run_cli("--text", " ")[0], 1)
        self.assertEqual(self.run_cli("--list-examples")[0], 0)
        self.credentials.assert_not_called()
        self.http.assert_not_called()
        for args in ([], ["--example", "unknown"],
                     ["--example", "production", "--text", "conflict"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                demo.main(args)

    def test_missing_configuration_stops_before_auth(self):
        with patch.dict(os.environ, {}, clear=True):
            result, _, errors = self.run_cli("--example", "supply-chain")
            self.assertEqual(result, 1)
            self.assertIn("Missing configuration", errors)
            self.assertEqual(self.run_cli("--list-examples")[0], 0)
        self.credentials.assert_not_called()
        self.http.assert_not_called()

    def test_cli_configuration_overrides_environment(self):
        self.wire(response(), LLM, validation_response())
        result, _, errors = self.run_cli(
            "--example", "maintenance", "--endpoint", "https://other.services.ai.azure.com/",
            "--decision-deployment", "router", "--llm-deployment", "writer",
        )
        self.assertEqual((result, errors), (0, ""))
        self.assertEqual(self.http.call_args_list[0].args[0].full_url,
                         "https://other.services.ai.azure.com/providers/microsoft/v1/systemone")
        self.assertEqual(json.loads(self.http.call_args_list[0].args[0].data)["model"], "router")
        self.assertEqual(json.loads(self.http.call_args_list[1].args[0].data)["model"], "writer")

    def test_invalid_endpoint_never_sends_token(self):
        for endpoint in (
            "http://example.services.ai.azure.com", "https://example.invalid",
            "https://example.services.ai.azure.com@evil.invalid", ENDPOINT + "/api",
            ENDPOINT + "?key=SECRET", "https://user:SECRET@example.services.ai.azure.com",
        ):
            with self.subTest(endpoint=endpoint):
                result, _, errors = self.run_cli("--example", "maintenance", "--endpoint", endpoint)
                self.assertEqual(result, 1)
                self.assertNotIn("SECRET", errors)
        self.credentials.assert_not_called()
        self.http.assert_not_called()


if __name__ == "__main__":
    unittest.main()
