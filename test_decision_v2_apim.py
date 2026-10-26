"""Offline tests for the opt-in APIM gateway profile (no network, no Azure)."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx2 as httpx

from decision_v2.cli import run_demo
from decision_v2.contracts import DemoError, SCENARIO_ID
from decision_v2.runtime import AzureRuntime, Budget, Config
from test_decision_v2 import FakeCredential, MockFoundry, MockResponsesFoundry

GATEWAY = "https://apim-example.azure-api.net"
SCOPE = "api://00000000-0000-0000-0000-000000000000/access_as_user"


class ApimConfigTests(unittest.TestCase):
    def args(self):
        return SimpleNamespace(endpoint=None, decision_deployment=None, llm_deployment=None, llm_profile=None)

    def test_default_path_unchanged_without_flag(self):
        cfg = Config("https://example.services.ai.azure.com", "decision-gate", "specialist-llm")
        self.assertFalse(cfg.apim)
        self.assertEqual(cfg.gpt_path, "/openai/v1/chat/completions")
        self.assertEqual(cfg.decision_path, "/providers/microsoft/v1/systemone")
        self.assertEqual(cfg.gpt_base_url, "https://example.services.ai.azure.com/openai/v1/")

    def test_env_flag_enables_gateway_routing(self):
        env = {"APIM_GATEWAY_URL": GATEWAY, "APIM_SCOPE": SCOPE, "DECISION_DEPLOYMENT": "decision-gate",
               "LLM_DEPLOYMENT": "specialist-llm-luna", "LLM_PROFILE": "gpt-6-luna",
               "FOUNDRY_ENDPOINT": "https://ignored.services.ai.azure.com"}
        with patch.dict("os.environ", env, clear=True):
            cfg = Config.from_args(self.args())
        self.assertEqual(cfg.endpoint, GATEWAY)
        self.assertEqual(cfg.gpt_path, "/specialist-llm-luna/v1/responses")
        self.assertEqual(cfg.gpt_base_url, GATEWAY + "/specialist-llm-luna/v1/")
        self.assertEqual(cfg.decision_path, "/decision-gate/providers/microsoft/v1/systemone")
        self.assertEqual(cfg.token_scope, SCOPE)

    def test_gateway_requires_scope_and_https_root(self):
        with patch.dict("os.environ", {"APIM_GATEWAY_URL": GATEWAY, "DECISION_DEPLOYMENT": "d",
                                       "LLM_DEPLOYMENT": "g"}, clear=True), self.assertRaises(DemoError):
            Config.from_args(self.args())
        for bad in ("http://x.azure-api.net", GATEWAY + "/api", GATEWAY + "?k=v", "https://u:p@x.azure-api.net"):
            with self.subTest(bad=bad), self.assertRaises(DemoError):
                Config(bad, "d", "g", apim_scope=SCOPE)
        with self.assertRaises(DemoError):
            Config(GATEWAY, "d", "g", apim_scope="https://cognitiveservices.azure.com/.default")

    def test_non_azure_host_still_rejected_without_flag(self):
        with self.assertRaises(DemoError):
            Config(GATEWAY, "d", "g")


class ApimRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def run_profile(self, profile, service):
        cred = FakeCredential()
        now = [0.]

        async def sleep(seconds):
            now[0] += seconds
        runtime = AzureRuntime(
            Config(GATEWAY, "decision-gate", "specialist-llm-luna" if profile == "gpt-6-luna" else "specialist-llm",
                   profile, apim_scope=SCOPE),
            Budget(clock=lambda: now[0], sleep=sleep), credential=cred, transport=httpx.MockTransport(service), scenario_id="order-pull-forward-v2")
        self.addAsyncCleanup(runtime.aclose)
        await run_demo(runtime, trace=lambda message: None)
        return runtime, cred

    async def check(self, profile, gpt_path):
        service = MockResponsesFoundry() if profile == "gpt-6-luna" else MockFoundry()
        runtime, cred = await self.run_profile(profile, service)
        self.assertTrue(service.requests)
        agents = set()
        for request, _ in service.requests:
            self.assertEqual(request.url.host, "apim-example.azure-api.net")
            expected = "/decision-gate/providers/microsoft/v1/systemone" if request.url.path.endswith("systemone") else gpt_path
            self.assertEqual(request.url.path, expected)
            self.assertEqual(request.headers["x-scenario"], "order-pull-forward-v2")
            self.assertEqual(request.headers["x-run-id"], runtime.run_id)
            agents.add(request.headers["x-agent-name"])
        self.assertIn("coordinator", agents)
        self.assertGreaterEqual(len(agents), 5)
        self.assertEqual(set(cred.scopes), {SCOPE})

    async def test_standard_profile_routes_through_gateway(self):
        await self.check("standard", "/specialist-llm/v1/chat/completions")

    async def test_luna_profile_routes_through_gateway(self):
        await self.check("gpt-6-luna", "/specialist-llm-luna/v1/responses")

    async def test_direct_profile_sends_no_custom_headers(self):
        service = MockFoundry()
        now = [0.]

        async def sleep(seconds):
            now[0] += seconds
        runtime = AzureRuntime(Config("https://example.services.ai.azure.com", "decision-deployment", "gpt-deployment"),
                               Budget(clock=lambda: now[0], sleep=sleep), credential=FakeCredential(), transport=httpx.MockTransport(service),
                               scenario_id="order-pull-forward-v2")
        self.addAsyncCleanup(runtime.aclose)
        await run_demo(runtime, trace=lambda message: None)
        for request, _ in service.requests:
            self.assertNotIn("x-run-id", request.headers)
            self.assertNotIn("x-agent-name", request.headers)


if __name__ == "__main__":
    unittest.main()
