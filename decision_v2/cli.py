import argparse
import asyncio
import logging
import os
import sys
import unicodedata

from agent_framework import AgentFrameworkException
from pydantic import ValidationError

from .agents import ExpertTeam, underlying_demo_error
from .contracts import ClarificationRequest, DemoError, FinalResult, HumanResponse, RunState
from .fixtures import ISSUE, initial_evidence
from .runtime import AzureRuntime, Budget, Config, DecisionClient
from .workflow import build_workflow


def safe_text(text: str) -> str:
    return "".join(c for c in text if c in "\n\t" or not unicodedata.category(c).startswith("C"))


def terminal_trace(message: str):
    print(safe_text(message))


async def read_terminal(request: ClarificationRequest) -> HumanResponse | None:
    if not sys.stdin.isatty():
        terminal_trace("Review pending: noninteractive stdin; no automatic continuation.")
        return None
    terminal_trace("One demo response only; clarification is unverified evidence, not approval.")
    terminal_trace("Allowed clarification keys: " + (", ".join(request.allowed_keys) or "none"))
    terminal_trace('Enter JSON: {"kind":"clarify","updates":{"recovery_capacity_assemblies":100}}')
    terminal_trace('Or {"kind":"reject"} / {"kind":"escalate"}; no accept/approve option.')
    print("> ", end="", flush=True)
    text = None
    if os.name == "nt":
        import msvcrt
        chars = []
        extended = False
        while text is None:
            if not msvcrt.kbhit():
                await asyncio.sleep(.05)
                continue
            char = msvcrt.getwch()
            if extended:
                extended = False
                continue
            if char in ("\x00", "\xe0"):
                extended = True
            elif char in ("\x03", "\x1a"):
                print()
                terminal_trace("Review pending: input ended or interrupted.")
                return None
            elif char in ("\r", "\n"):
                text = "".join(chars)
                print()
            elif char == "\b":
                if chars:
                    chars.pop()
                    print("\b \b", end="", flush=True)
            elif char.isprintable():
                chars.append(char)
                print(char, end="", flush=True)
                if len(chars) > 8192:
                    terminal_trace("\nERROR: input exceeds the bounded response size; review pending.")
                    return None
    else:
        import select
        while text is None:
            readable, _, _ = select.select([sys.stdin], [], [], 0)
            if readable:
                text = sys.stdin.readline(8193)
            else:
                await asyncio.sleep(.05)
        if not text:
            terminal_trace("Review pending: EOF.")
            return None
    if len(text) > 8192:
        terminal_trace("ERROR: input exceeds the bounded response size; review pending.")
        return None
    try:
        response = HumanResponse.model_validate_json(text)
    except ValidationError:
        terminal_trace("ERROR: invalid response JSON/schema; review pending, no reprompt.")
        return None
    if not set(response.updates).issubset(request.allowed_keys):
        terminal_trace("ERROR: clarification key is not requested; review pending.")
        return None
    return response


async def collect_events(stream):
    requests, outputs = [], []
    async for event in stream:
        if event.type == "error":
            raise DemoError("Workflow emitted an execution error; no partial success accepted.")
        if event.type == "request_info":
            if not isinstance(event.data, ClarificationRequest):
                raise DemoError("Workflow emitted an unsupported human request.")
            requests.append(event)
        if event.type == "output":
            if not isinstance(event.data, FinalResult):
                raise DemoError("Workflow emitted an unsupported final output.")
            outputs.append(event.data)
    if len(requests) + len(outputs) != 1:
        raise DemoError("Workflow did not produce exactly one final output or human request.")
    return requests, outputs


async def run_demo(runtime: AzureRuntime, response_reader=read_terminal, trace=terminal_trace) -> FinalResult:
    budget = runtime.budget
    workflow = build_workflow(ExpertTeam(runtime), DecisionClient(runtime), budget, trace)
    state = RunState(evidence=initial_evidence())
    try:
        requests, outputs = await budget.bound(
            lambda: collect_events(workflow.run(state, stream=True)), budget.remaining(),
        )
        if requests:
            request = requests[0]
            trace(f"Framework pause: request_id={request.request_id}; revision={state.revision}")
            budget.begin_human()
            try:
                async with asyncio.timeout(budget.human_remaining()):
                    response = await response_reader(request.data)
            except TimeoutError:
                trace("Review pending: human-input deadline expired.")
                response = None
            finally:
                budget.end_human()
            if response is None:
                result = FinalResult("pending", 2, request.data.reasons, state.proposal)
            elif not isinstance(response, HumanResponse):
                raise DemoError("Terminal adapter returned an invalid response type.")
            else:
                trace("Framework resume: one typed human response; same workflow/cumulative budgets")
                requests, outputs = await budget.bound(
                    lambda: collect_events(workflow.run(
                        stream=True, responses={request.request_id: response},
                    )), budget.remaining(),
                )
                if requests:
                    raise DemoError("Second human request blocked after the one continuation.")
                result = outputs[0]
        else:
            result = outputs[0]
    except AgentFrameworkException as exc:
        original = underlying_demo_error(exc)
        if original:
            raise original from exc
        raise DemoError("Framework execution failed; no partial result accepted.") from exc
    trace(f"Final advisory status: {result.status}; no actions executed or authority granted.")
    for reason in result.reasons:
        trace("Final handoff reason: " + reason)
    trace(f"Actual attempts: GPT={budget.counts['gpt']}/20 Decision-1={budget.counts['decision']}/3; "
          f"tools={sum(map(len, budget.tools.values()))}/12")
    return result


async def live_run(config):
    terminal_trace("LIVE Azure Foundry inference | SYNTHETIC fixture tools | proposals only")
    terminal_trace(ISSUE)
    terminal_trace("Hard maximum: 20 GPT + 3 Decision-1 attempts, one continuation; not expected runtime.")
    budget = Budget(terminal_trace)
    runtime = AzureRuntime(config, budget)
    try:
        return (await run_demo(runtime)).code
    finally:
        await runtime.aclose()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="V2: bounded Foundry expert-team shortage assessment.")
    parser.add_argument("--example", choices=["supply-chain"], required=True)
    parser.add_argument("--endpoint", help="Existing Azure resource root; overrides FOUNDRY_ENDPOINT")
    parser.add_argument("--decision-deployment", help="Existing Decision-1 deployment; overrides DECISION_DEPLOYMENT")
    parser.add_argument("--llm-deployment", help="Existing GPT deployment; overrides LLM_DEPLOYMENT")
    args = parser.parse_args(argv)
    # Host errors are rendered explicitly below, without SDK/workflow tracebacks.
    logging.getLogger("agent_framework").setLevel(logging.CRITICAL)
    try:
        config = Config.from_args(args)
        return asyncio.run(live_run(config))
    except DemoError as exc:
        print(f"ERROR: {safe_text(str(exc))}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        terminal_trace("Final advisory status: pending (interrupted); no actions executed.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
