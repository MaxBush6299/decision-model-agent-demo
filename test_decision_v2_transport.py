import asyncio
import json
import unittest
from unittest.mock import patch

import httpx2 as httpx

from decision_v2.contracts import DemoError
from decision_v2.runtime import AzureRuntime, Budget, Config, GuardedTransport
from test_decision_v2 import FakeCredential, responses_payload

ENDPOINT = "https://example.services.ai.azure.com"
LUNA = Config(ENDPOINT, "decision", "luna", "gpt-6-luna")
STANDARD = Config(ENDPOINT, "decision", "gpt")


def ok_luna(request):
    return httpx.Response(200, json=responses_payload({"content": "{}"}))


def ok_chat(request):
    return httpx.Response(200, json={
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "{}"}}]})


class Scripted:
    """Inner transport that plays a list of outcomes: exceptions are raised, callables are used."""

    def __init__(self, *outcomes):
        self.outcomes, self.seen = list(outcomes), []

    async def handle_async_request(self, request):
        self.seen.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome(request)

    async def aclose(self):
        pass


def connect_timeout():
    return httpx.ConnectTimeout("connect timed out")


class PostMixin:
    async def post(self, config, inner, *, kind="gpt", actor="production", budget=None):
        budget = budget or Budget()
        transport = GuardedTransport(config, budget, inner)
        path = config.gpt_path if kind == "gpt" else config.decision_path
        async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
            async with budget.stage(kind, actor, 0):
                return budget, await client.post(config.endpoint + path, json={"max_output_tokens": 100})


class DeadlinePolicyTests(PostMixin, unittest.IsolatedAsyncioTestCase):
    def test_deadlines_are_luna_only(self):
        self.assertEqual(LUNA.gpt_deadline, 120)
        self.assertEqual(STANDARD.gpt_deadline, 60)
        self.assertTrue(LUNA.transport_retry)
        self.assertFalse(STANDARD.transport_retry)

    async def observed_timeouts(self, config, kind, now=None):
        seen, real = [], asyncio.timeout
        def observe(seconds):
            seen.append(seconds)
            return real(seconds)
        inner = Scripted(ok_luna if kind == "gpt" and config.llm_profile == "gpt-6-luna" else ok_chat)
        budget = Budget(clock=lambda: now[0]) if now else None
        if now:
            now[0] = 800.
        with patch("decision_v2.runtime.asyncio.timeout", side_effect=observe):
            await self.post(config, inner, kind=kind, budget=budget)
        return seen

    async def test_per_request_deadline_by_profile_and_kind(self):
        self.assertEqual(max(await self.observed_timeouts(LUNA, "gpt")), 120)
        self.assertEqual(max(await self.observed_timeouts(STANDARD, "gpt")), 60)
        self.assertEqual(max(await self.observed_timeouts(LUNA, "decision")), 60)

    async def test_request_never_exceeds_remaining_run_time(self):
        seen = await self.observed_timeouts(LUNA, "gpt", now=[0.])
        self.assertLessEqual(max(seen), 100)

    async def test_sdk_timeout_matches_profile_and_decision_client_stays_60(self):
        for config, expected in ((LUNA, 120), (STANDARD, 60)):
            runtime = AzureRuntime(config, Budget(), credential=FakeCredential(),
                                   transport=httpx.MockTransport(ok_luna))
            self.assertEqual(runtime.sdks["production"].timeout, expected)
            self.assertEqual(runtime.http.timeout, httpx.Timeout(60))
            await runtime.aclose()


class TransportRetryTests(PostMixin, unittest.IsolatedAsyncioTestCase):
    async def test_connect_timeout_retries_once_and_counts_both_attempts(self):
        inner, trace = Scripted(connect_timeout(), ok_luna), []
        budget = Budget(trace.append)
        budget, response = await self.post(LUNA, inner, budget=budget)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(inner.seen), 2)
        self.assertEqual(budget.counts["gpt"], 2)
        self.assertEqual(len(budget.token_window), 2)
        self.assertEqual(budget.transport_retries[("production", 0)], 1)
        self.assertTrue(any("Transport retry gpt/production" in line for line in trace))
        self.assertTrue(any("attempt 2" in line for line in trace))

    async def test_second_connect_timeout_fails_with_both_attempts_reported(self):
        inner = Scripted(connect_timeout(), connect_timeout(), ok_luna)
        budget = Budget()
        with self.assertRaises(DemoError) as caught:
            await self.post(LUNA, inner, budget=budget)
        self.assertEqual(len(inner.seen), 2)
        self.assertEqual(budget.counts["gpt"], 2)
        self.assertIn("ConnectTimeout", str(caught.exception))
        self.assertIn("attempt 2 after one pre-send connect-timeout retry", str(caught.exception))

    async def test_ambiguous_and_non_connect_failures_are_never_retried(self):
        failures = (
            httpx.ReadTimeout("read"), httpx.WriteTimeout("write"), httpx.PoolTimeout("pool"),
            httpx.ConnectError("refused"), httpx.RemoteProtocolError("closed"),
        )
        for failure in failures:
            inner = Scripted(failure, ok_luna)
            with self.subTest(failure=type(failure).__name__), self.assertRaises(DemoError):
                await self.post(LUNA, inner)
            self.assertEqual(len(inner.seen), 1)

    async def test_http_status_and_model_failures_are_never_retried(self):
        outcomes = (
            lambda request: httpx.Response(429, json={}),
            lambda request: httpx.Response(500, json={}),
            lambda request: httpx.Response(401, json={}),
            lambda request: httpx.Response(200, content=b"not json"),
            lambda request: httpx.Response(200, json=responses_payload({"content": None, "refusal": "No"})),
            lambda request: httpx.Response(200, json=responses_payload({"content": "{}"}, "length")),
        )
        for outcome in outcomes:
            inner = Scripted(outcome, ok_luna)
            budget = Budget()
            try:
                await self.post(LUNA, inner, budget=budget)
            except DemoError:
                pass
            self.assertEqual(len(inner.seen), 1)
            self.assertEqual(budget.counts["gpt"], 1)

    async def test_run_deadline_exhaustion_is_never_retried(self):
        inner = Scripted(ok_luna)
        inner.handle_async_request = self.stalling(inner)
        real = asyncio.timeout
        with patch("decision_v2.runtime.asyncio.timeout", side_effect=lambda s: real(.01)):
            with self.assertRaises(DemoError):
                await self.post(LUNA, inner)
        self.assertEqual(len(inner.seen), 1)

    @staticmethod
    def stalling(inner):
        async def handle(request):
            inner.seen.append(request)
            await asyncio.sleep(10)
        return handle

    async def test_retry_is_luna_gpt_only(self):
        for config, kind in ((STANDARD, "gpt"), (LUNA, "decision"), (STANDARD, "decision")):
            inner = Scripted(connect_timeout(), ok_chat)
            with self.subTest(profile=config.llm_profile, kind=kind), self.assertRaises(DemoError):
                await self.post(config, inner, kind=kind)
            self.assertEqual(len(inner.seen), 1)

    async def test_existing_actor_cap_can_forbid_the_retry(self):
        inner = Scripted(connect_timeout(), ok_luna)
        budget = Budget()
        with self.assertRaises(DemoError) as caught:
            await self.post(LUNA, inner, actor="coordinator", budget=budget)
        self.assertEqual(len(inner.seen), 1)
        self.assertEqual(budget.counts["gpt"], 1)
        self.assertIn("not permitted by budgets", str(caught.exception))
        self.assertIn("ConnectTimeout", str(caught.exception))

    async def test_total_gpt_cap_can_forbid_the_retry(self):
        budget = Budget()
        budget.counts["gpt"] = 19
        inner = Scripted(connect_timeout(), ok_luna)
        with self.assertRaises(DemoError):
            await self.post(LUNA, inner, budget=budget)
        self.assertEqual(len(inner.seen), 1)
        self.assertEqual(budget.counts["gpt"], 20)

    async def test_retry_consumes_quota_pacing_before_second_dispatch(self):
        now, sleeps = [0.], []
        async def sleep(seconds):
            sleeps.append(seconds)
            now[0] += seconds
        budget = Budget(clock=lambda: now[0], sleep=sleep)
        budget.windows["gpt"].extend([0.] * 9)
        inner = Scripted(connect_timeout(), ok_luna)
        await self.post(LUNA, inner, budget=budget)
        self.assertEqual(sleeps, [60.])
        self.assertEqual(len(inner.seen), 2)

    async def test_retry_reuses_the_same_request_headers_and_body(self):
        inner = Scripted(connect_timeout(), ok_luna)
        await self.post(LUNA, inner)
        first, second = inner.seen
        self.assertEqual(first.content, second.content)
        self.assertEqual(dict(first.headers), dict(second.headers))


if __name__ == "__main__":
    unittest.main()
