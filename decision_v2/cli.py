import argparse
import asyncio
import logging
import os
import sys
import unicodedata
from datetime import datetime, timedelta, timezone

from agent_framework import AgentFrameworkException
from pydantic import ValidationError

from .agents import ExpertTeam, underlying_demo_error
from .contracts import ClarificationRequest, CustomerDeliveryChange, DemoError, FinalResult, HumanResponse, RunState
from .fixtures import initial_evidence, validate_delivery_change
from .presentation import Presenter
from .runtime import AzureRuntime, Budget, Config, DecisionClient
from .workflow import build_workflow


def safe_text(text: str) -> str:
    return "".join(c for c in text if c in "\n\t" or not unicodedata.category(c).startswith("C"))


def terminal_trace(message: str):
    print(safe_text(message))


def parse_terminal_response(text: str, request: ClarificationRequest) -> HumanResponse:
    text = text.strip()
    if text.lower() in ("reject", "escalate"):
        return HumanResponse(kind=text.lower())
    if "customer_delivery_change" not in request.allowed_keys:
        raise DemoError("No customer-delivery clarification was requested; reject or escalate instead.")
    if text.lower() == "no":
        change = CustomerDeliveryChange(
            customer_agreed=False, quantity=0, revised_delivery_at=None,
            reference="Terminal operator reports no customer-agreed revised window.",
        )
    else:
        fields = [field.strip() for field in text.split("|")]
        if len(fields) != 3 or not fields[0].isdigit():
            raise DemoError("Use quantity | YYYY-MM-DD HH:MM | customer-planner reference, or no/reject/escalate.")
        at = datetime.strptime(fields[1], "%Y-%m-%d %H:%M").replace(
            tzinfo=timezone(timedelta(hours=-5)),
        )
        change = CustomerDeliveryChange(
            customer_agreed=True, quantity=int(fields[0]), revised_delivery_at=at, reference=fields[2],
        )
    validate_delivery_change(change)
    return HumanResponse(kind="clarify", updates={"customer_delivery_change": change})


async def read_terminal(request: ClarificationRequest) -> HumanResponse | None:
    if not sys.stdin.isatty():
        terminal_trace("Review pending: noninteractive stdin; no automatic continuation.")
        return None
    if "customer_delivery_change" in request.allowed_keys:
        terminal_trace("Has the customer agreed to move tomorrow's second delivery?")
        terminal_trace("If so, what quantity and revised delivery time? First 180 at Friday 10:00 stays unchanged.")
        terminal_trace("Enter quantity | YYYY-MM-DD HH:MM | planner/reference (snapshot timezone UTC-05:00).")
        terminal_trace("Example: 240 | 2026-10-17 08:00 | customer planner phone note")
        terminal_trace("Or type no, reject, or escalate. A reported agreement is unverified evidence, not approval.")
    else:
        terminal_trace("This pause needs responsible-owner evidence, not a customer-window clarification.")
        terminal_trace("Type reject or escalate; this demo cannot grant approval or release stock.")
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
        response = parse_terminal_response(text, request)
    except (ValidationError, ValueError, DemoError):
        terminal_trace("ERROR: invalid response quantity/window/reference; review pending, no reprompt.")
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


async def run_demo(runtime: AzureRuntime, response_reader=read_terminal, trace=terminal_trace, *, verbose=False) -> FinalResult:
    budget = runtime.budget
    presenter = Presenter(trace, verbose)
    presenter.case()
    workflow = build_workflow(ExpertTeam(runtime), DecisionClient(runtime), budget, trace, presenter=presenter)
    state = RunState(evidence=initial_evidence())
    try:
        requests, outputs = await budget.bound(
            lambda: collect_events(workflow.run(state, stream=True)), budget.remaining(),
        )
        if requests:
            request = requests[0]
            presenter.diagnostic(f"Framework pause: request_id={request.request_id}; revision={state.revision}")
            budget.begin_human()
            try:
                async with asyncio.timeout(budget.human_remaining()):
                    response = await response_reader(request.data)
            except TimeoutError:
                presenter.line("Review pending: human-input deadline expired.")
                response = None
            finally:
                budget.end_human()
            if response is None:
                result = FinalResult("pending", 2, request.data.reasons, state.proposal)
            elif not isinstance(response, HumanResponse):
                raise DemoError("Terminal adapter returned an invalid response type.")
            else:
                presenter.diagnostic("Framework resume: one typed human response; same workflow/cumulative budgets")
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
        presenter.attempts(budget)
        original = underlying_demo_error(exc)
        if original:
            raise original from exc
        raise DemoError("Framework execution failed; no partial result accepted.") from exc
    except DemoError:
        presenter.attempts(budget)
        raise
    except asyncio.CancelledError:
        presenter.attempts(budget)
        raise
    presenter.finish(result, budget)
    return result


async def live_run(config, verbose=False):
    terminal_trace("LIVE Azure Foundry inference | SYNTHETIC fixture tools | proposals only")
    terminal_trace("One clarification; hard maximum 20 GPT +3 Decision-1 attempts, not expected runtime.")
    budget = Budget(terminal_trace)
    runtime = AzureRuntime(config, budget)
    try:
        return (await run_demo(runtime, verbose=verbose)).code
    finally:
        await runtime.aclose()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="V2: quality-hold containment and customer-delivery recovery.")
    parser.add_argument("--example", choices=["quality-hold", "supply-chain"], required=True,
                        help="Quality-hold preset; supply-chain is its backward-compatible alias")
    parser.add_argument("--verbose", action="store_true", help="Include complete model scores, tool/call diagnostics and provenance")
    parser.add_argument("--endpoint", help="Existing Azure resource root; overrides FOUNDRY_ENDPOINT")
    parser.add_argument("--decision-deployment", help="Existing Decision-1 deployment; overrides DECISION_DEPLOYMENT")
    parser.add_argument("--llm-deployment", help="Existing GPT deployment; overrides LLM_DEPLOYMENT")
    args = parser.parse_args(argv)
    # Host errors are rendered explicitly below, without SDK/workflow tracebacks.
    logging.getLogger("agent_framework").setLevel(logging.CRITICAL)
    try:
        config = Config.from_args(args)
        return asyncio.run(live_run(config, verbose=args.verbose))
    except DemoError as exc:
        print(f"ERROR: {safe_text(str(exc))}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        terminal_trace("Final advisory status: pending (interrupted); no actions executed.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
