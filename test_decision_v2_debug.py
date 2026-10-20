import io
import json
import unittest

from decision_v2 import debug
from decision_v2.cli import run_demo
from decision_v2.contracts import DemoError
from test_decision_v2 import FrameworkAgentTests


class BrokenStream:
    def write(self, text):
        raise OSError("closed")

    def flush(self):
        pass


class DebugSinkTests(unittest.TestCase):
    def tearDown(self):
        debug.disable()

    def test_off_by_default_and_emit_is_noop(self):
        debug.disable()
        self.assertFalse(debug.enabled())
        debug.emit("anything", value="x")

    def test_flag_and_env_enable(self):
        self.assertFalse(debug.configure(False, {}))
        self.assertTrue(debug.configure(False, {"DECISION_DEBUG": "1"}))
        debug.disable()
        self.assertTrue(debug.configure(True, {}))
        debug.disable()
        self.assertFalse(debug.configure(False, {"DECISION_DEBUG": "0"}))

    def test_events_are_json_lines_and_redacted(self):
        stream = io.StringIO()
        debug.enable(stream)
        jwt = "eyJhbGciOi.eyJzdWIiOiIx.c2lnbmF0dXJl"
        debug.emit("probe", note=f"Authorization: Bearer abc123 {jwt} https://example.test/x",
                   headers={"Authorization": "Bearer secret"}, big="z" * 1000)
        record = json.loads(stream.getvalue().strip())
        text = stream.getvalue()
        for secret in ("abc123", jwt, "example.test", "Bearer secret"):
            self.assertNotIn(secret, text)
        self.assertEqual(record["event"], "probe")
        self.assertLess(len(record["big"]), 260)

    def test_sink_failure_is_explicit(self):
        debug.enable(BrokenStream())
        with self.assertRaisesRegex(DemoError, "Debug trace sink failed"):
            debug.emit("x")

    def test_usage_keeps_only_integers(self):
        self.assertEqual(debug.usage_of({"usage": {"input_tokens": 3, "x": "y", "ok": True}}),
                         {"input_tokens": 3})
        self.assertIsNone(debug.usage_of({}))


class DebugOutputIdentityTests(unittest.IsolatedAsyncioTestCase):
    make_runtime = FrameworkAgentTests.make_runtime

    async def run_once(self):
        lines = []
        runtime = self.make_runtime(None, scenario_id="order-pull-forward-v2")

        async def no_input(_):
            return None

        result = await run_demo(runtime, no_input, lines.append)
        return lines, result

    def scrub(self, lines):
        import re
        return [re.sub(r"\d+\.\d+ms", "Nms", re.sub(r"request_id=\S+", "request_id=X", line)) for line in lines]

    async def test_stdout_identical_with_debug_on_and_trace_emitted(self):
        debug.disable()
        off_lines, off_result = await self.run_once()
        stream = io.StringIO()
        debug.enable(stream)
        try:
            on_lines, on_result = await self.run_once()
        finally:
            debug.disable()
        self.assertEqual(self.scrub(off_lines), self.scrub(on_lines))
        self.assertEqual((off_result.status, off_result.code), (on_result.status, on_result.code))
        events = [json.loads(line)["event"] for line in stream.getvalue().splitlines()]
        for expected in ("request.start", "request.end", "budget.dispatch", "decision.response",
                         "routing.host", "actor.start", "actor.end", "run.end"):
            self.assertIn(expected, events)
        self.assertNotIn("Bearer", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
