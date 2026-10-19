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
from .contracts import SCENARIO_ID, ClarificationRequest, CustomerDeliveryChange, DemoError, FinalResult, HumanResponse, RunState
from .fixtures import EXAMPLES, fixture_records, initial_evidence, validate_delivery_change
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
    if request.scenario_id != SCENARIO_ID or "customer_delivery_change" not in request.allowed_keys:
        raise DemoError("No customer-delivery clarification was requested; reject or escalate instead.")
    if text.lower() == "no":
        change = CustomerDeliveryChange(
            customer_agreed=False, quantity=0, revised_delivery_at=None,
            reference="Terminal operator reports no customer-agreed revised window.",
        )
    else:
        fields = [field.strip() for field in text.split("|", 2)]
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


async def read_terminal_line(prompt: str) -> str | None:
    print(prompt, end="", flush=True)
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
    return text.strip()


async def read_terminal(request: ClarificationRequest) -> HumanResponse | None:
    if not sys.stdin.isatty():
        terminal_trace("Review pending: noninteractive stdin; no automatic continuation.")
        return None
    can_record = request.scenario_id == SCENARIO_ID and "customer_delivery_change" in request.allowed_keys
    if can_record:
        terminal_trace("1. Record customer response after contact: customer will move the second delivery.")
    else:
        terminal_trace("1. Leave review pending for responsible-owner evidence.")
    terminal_trace("2. Reject the recommendation and request leadership escalation." if can_record else
                   "2. Request leadership escalation for unresolved review.")
    choice = await read_terminal_line("Choose 1 or 2: ")
    if choice is None:
        return None
    if choice.lower() in ("2", "reject", "escalate"):
        return HumanResponse(kind="escalate")
    if not can_record and choice.lower() in ("1", "pending"):
        terminal_trace("Review remains pending; no action or further inference performed.")
        return None
    if choice != "1" or not can_record:
        terminal_trace("ERROR: invalid review choice; review pending, no reprompt.")
        return None
    terminal_trace("Record a response received after contact, not an intention to reach out.")
    terminal_trace("The response remains an unverified user report. Type escalate at any field to stop.")
    second = fixture_records()["read_build"].deliveries[1]
    fields = []
    for prompt in (
        f"Quantity customer reportedly agreed to move (1-{second.quantity}): ",
        "Revised delivery time (YYYY-MM-DD HH:MM, UTC-05:00): ",
        "Customer-planner response reference (1-200 characters): ",
    ):
        value = await read_terminal_line(prompt)
        if value is None:
            return None
        if value.lower() in ("reject", "escalate"):
            return HumanResponse(kind="escalate")
        fields.append(value)
    try:
        response = parse_terminal_response(" | ".join(fields), request)
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
    presenter = Presenter(trace, verbose, scenario_id=runtime.scenario_id)
    presenter.case()
    workflow = build_workflow(ExpertTeam(runtime), DecisionClient(runtime), budget, trace, presenter=presenter)
    state = RunState(scenario_id=runtime.scenario_id, evidence=initial_evidence(runtime.scenario_id))
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


async def live_run(config, verbose=False, scenario_id=SCENARIO_ID):
    terminal_trace("LIVE Azure Foundry inference | SYNTHETIC fixture tools | proposals only")
    terminal_trace(f"GPT deployment={config.llm_deployment}; profile={config.llm_profile}; "
                   f"local pacing=10 RPM/10,000 estimated TPM; output allowance={config.gpt_output_tokens:,} tokens.")
    terminal_trace("At most one clarification; hard maximum 20 GPT +4 Decision-1 attempts, not expected runtime.")
    budget = Budget(terminal_trace)
    runtime = AzureRuntime(config, budget, scenario_id=scenario_id)
    try:
        return (await run_demo(runtime, verbose=verbose)).code
    finally:
        await runtime.aclose()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="V2: bounded expert-team planning with synthetic operational cases.")
    parser.add_argument("--example", choices=list(EXAMPLES), required=True,
                        help="Select a synthetic case; supply-chain remains an alias for quality-hold")
    parser.add_argument("--verbose", action="store_true", help="Include complete model scores, tool/call diagnostics and provenance")
    parser.add_argument("--endpoint", help="Existing Azure resource root; overrides FOUNDRY_ENDPOINT")
    parser.add_argument("--decision-deployment", help="Existing Decision-1 deployment; overrides DECISION_DEPLOYMENT")
    parser.add_argument("--llm-deployment", help="Existing GPT deployment; overrides LLM_DEPLOYMENT")
    parser.add_argument("--llm-profile", choices=("standard", "gpt-6-luna"),
                        help="GPT request profile; overrides LLM_PROFILE (default: standard)")
    args = parser.parse_args(argv)
    # Host errors are rendered explicitly below, without SDK/workflow tracebacks.
    logging.getLogger("agent_framework").setLevel(logging.CRITICAL)
    try:
        config = Config.from_args(args)
        return asyncio.run(live_run(config, verbose=args.verbose, scenario_id=EXAMPLES[args.example]))
    except DemoError as exc:
        print(f"ERROR: {safe_text(str(exc))}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        terminal_trace("Final advisory status: pending (interrupted); no actions executed.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
