import { useLayoutEffect, useRef, useState } from 'react';
import { decisionLearnUrl } from '../components/DecisionModelExplainer';
import { RecordedStepDiagram } from '../components/RecordedStepDiagram';
import { capture, proposalContent, routeAnswer, validationAnswer, terminalStages } from '../data/recordedCli';

const steps = ['Issue and routing request', 'Decision-1 routing response', 'Specialist proposal', 'Decision-1 validation', 'Human review'];
const stepLabels = ['The shortage', 'Choose an owner', 'Draft advice', 'Check the proposal', 'Human review'];
const stageLessons = [
  { input: '480 assemblies needed; parts for 310. Freight exceeds the approval limit; the alternate part is not approved.', output: 'The issue becomes one bounded routing question with four allowed owners.', owner: 'The application supplies the facts and defines the choices. It grants no spending permission.' },
  { input: 'The original issue and four possible owners: production, maintenance, supply-chain, or human-review.', output: 'Decision-1 chooses supply-chain. Software checks the answer before routing it.', owner: 'The model makes a judgment; software enforces the routing checks. Neither approves an action.' },
  { input: 'The same issue, supply-chain instructions, and a required two-field answer format.', output: 'The specialist proposes seeking freight approval and supplies a brief.', owner: 'The specialist writes advice. Software checks its structure; the proposal is not an executed action.' },
  { input: 'The original issue plus the actual specialist proposal, checked against three allowed verdicts.', output: 'Decision-1 returns “Addresses the issue.” Approval is still needed.', owner: 'The model judges the proposal against a rubric. Software preserves the human handoff.' },
  { input: 'The specialist’s request to seek freight approval.', output: 'Human review is pending. No acceptance or action was recorded.', owner: 'A person retains approval authority. The recording does not make that choice for them.' },
];
const decisionEnvelope = 'POST https://example.services.ai.azure.com/providers/microsoft/v1/systemone\nAuthorization: Bearer <Entra access token>\nContent-Type: application/json';

function TextPanel({ label, text }: { label: string; text: string }) {
  return <pre className="recorded-text" tabIndex={0} role="region" aria-label={label}><code>{text}</code></pre>;
}

function DecisionRequest({ index }: { index: 0 | 2 }) {
  const call = capture.calls[index];
  const question = index === 0 ? 'route' : 'validation';
  const RequestHeading = index === 0 ? 'h4' : 'h5';
  return (
    <div className="recorded-request">
      {index === 0 && <h4>What the request going to Decision-1 looked like</h4>}
      <p><strong>Decision-1 = context + a bounded question + labeled choices.</strong> This decision API uses <code>state</code> and <code>questions</code>, not chat messages.</p>
      <RequestHeading>HTTP envelope · explanatory, not captured headers</RequestHeading>
      <TextPanel label="Explanatory Decision-1 HTTP envelope" text={decisionEnvelope} />
      <p>Headers were not captured. The authorization line above contains only a literal placeholder, not a token. The CLI uses an Entra access token with scope <code>https://cognitiveservices.azure.com/.default</code>; the scope is not a JSON body field.</p>
      <RequestHeading>Full sanitized published {question === 'route' ? 'routing' : 'validation'} request · JSON formatted for reading</RequestHeading>
      <TextPanel label={`Sanitized Decision-1 ${question === 'route' ? 'routing' : 'validation'} request JSON`} text={JSON.stringify(call.requestBody, null, 2)} />
      <table className="recorded-fields">
        <caption>Decision-1 request fields</caption>
        <thead><tr><th scope="col">Field</th><th scope="col">Purpose</th></tr></thead>
        <tbody>
          <tr><th scope="row"><code>model</code></th><td>The deployment name <code>YOUR-DECISION-1-DEPLOYMENT</code>, not the underlying model name <code>Microsoft-Decision-1</code>.</td></tr>
          <tr><th scope="row"><code>state</code></th><td>Text or JSON information to evaluate: {index === 0 ? 'the original synthetic issue' : <>both <code>original_issue</code> and the actual specialist <code>proposal</code> object</>}.</td></tr>
          <tr><th scope="row"><code>questions</code></th><td>Named answers the application requests. This call names its question <code>{question}</code>.</td></tr>
          <tr><th scope="row"><code>type</code></th><td><code>choice</code> asks the model to select a labeled option.</td></tr>
          <tr><th scope="row"><code>instructions</code></th><td>Guidance for judging the supplied context against this question.</td></tr>
          <tr><th scope="row"><code>criteria</code></th><td>Output labels mapped to descriptions of what each option means. These bound the possible answers.</td></tr>
        </tbody>
      </table>
      <p><strong>Who owns the response?</strong> The CLI reads <code>answers.{question}</code>: <code>choice</code>, <code>probabilities</code>, and optional <code>confidence</code> (present in this recording). Ordinary code invokes the LLM or hands off to a person after its checks. The model never executes an action in this demo.</p>
      <p><a href={decisionLearnUrl}>Microsoft Learn: Decision-1 request and response format</a></p>
      <details>
        <summary>Sanitized recorded Decision-1 request body</summary>
        <TextPanel label="Sanitized recorded request body" text={call.requestText} />
      </details>
    </div>
  );
}

function ChoiceResult({ answer, showPercentages = false }: { answer: typeof routeAnswer; showPercentages?: boolean }) {
  return (
    <div className="recorded-result">
      <p><strong>Model choice:</strong> {answer.choice}</p>
      <dl aria-label="Exact option probabilities">
        {Object.entries(answer.probabilities).map(([option, value]) => (
          <div key={option}><dt>{option}</dt><dd>{showPercentages ? <>{(value * 100).toFixed(2)}% <span>(raw: {String(value)})</span></> : String(value)}</dd></div>
        ))}
      </dl>
      <p><strong>Separately reported confidence:</strong> {String(answer.confidence)}</p>
      <p>Option probabilities and model-reported confidence are different fields. Neither is permission to act or verified accuracy on this case.</p>
    </div>
  );
}

function RecordedCall({ index }: { index: number }) {
  const call = capture.calls[index];
  const EvidenceHeading = index === 2 ? 'h5' : 'h4';
  return (
    <div className="recorded-call">
      <p><strong>Recorded call {call.sequence} of 3:</strong> {call.label} · deployment <code>{call.deployment}</code></p>
      <p><code>{call.path}</code> · HTTP {call.httpStatus} · clientElapsedMs: <code>{String(call.clientElapsedMs)}</code></p>
      {call.kind === 'specialist' && <details>
        <summary>Sanitized request · formatted for reading</summary>
        <TextPanel label="Formatted sanitized request JSON" text={JSON.stringify(call.requestBody, null, 2)} />
      </details>}
      <details>
        <summary>Sanitized response envelope · formatted for reading</summary>
        <TextPanel label="Formatted sanitized response JSON" text={JSON.stringify(call.responseBody, null, 2)} />
      </details>
      <details>
        <summary>{call.kind === 'specialist' ? 'Sanitized recorded request and response bodies' : 'Sanitized recorded response body'}</summary>
        {call.kind === 'specialist' && <>
          <h4>Request body</h4>
          <TextPanel label="Sanitized recorded request body" text={call.requestText} />
        </>}
        <EvidenceHeading>Response body</EvidenceHeading>
        <TextPanel label="Sanitized recorded response body" text={call.responseText} />
      </details>
    </div>
  );
}

export function LearnPage() {
  const [activeIndex, setActiveIndex] = useState(0);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const panel = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const pendingOrientation = useRef(false);
  useLayoutEffect(() => {
    if (!pendingOrientation.current) return;
    pendingOrientation.current = false;
    heading.current?.focus({ preventScroll: true });
    heading.current?.scrollIntoView({ block: 'start', behavior: 'instant' });
  }, [activeIndex]);
  const selectStep = (index: number, focusTab = false) => {
    setActiveIndex(index);
    if (focusTab) tabs.current[index]?.focus();
  };
  const previewStep = (index: number) => {
    selectStep(index);
    panel.current?.focus();
  };
  const navigateStep = (index: number) => {
    pendingOrientation.current = true;
    selectStep(index);
  };

  return (
    <div className="learn-page recorded-cli">
      <header className="learn-intro">
        <div>
          <h2>Follow the recorded shortage</h2>
          <p className="learn-deck">Tomorrow needs 480 assemblies; parts for 310 are on hand. Can the team cover the gap without bypassing approval?</p>
          <p className="recorded-provenance">Recorded model calls · synthetic facts · pending human review. An in-depth look at how a decision model fits into the process, in five stages at your own pace.</p>
        </div>
      </header>

      <div className="chapter-index recorded-step-picker" role="tablist" aria-label="Recorded CLI steps">
        {steps.map((title, index) => (
          <button
            key={title}
            ref={(element) => { tabs.current[index] = element; }}
            id={`cli-step-${index}`}
            type="button"
            role="tab"
            aria-selected={index === activeIndex}
            aria-controls="cli-step-panel"
            tabIndex={index === activeIndex ? 0 : -1}
            onClick={() => selectStep(index)}
            onKeyDown={(event) => {
              let next: number | undefined;
              if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % steps.length;
              if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (index + steps.length - 1) % steps.length;
              if (event.key === 'Home') next = 0;
              if (event.key === 'End') next = steps.length - 1;
              if (next !== undefined) {
                event.preventDefault();
                selectStep(next, true);
              }
            }}
          ><span>Step {index + 1}</span>{stepLabels[index]}</button>
        ))}
      </div>

      <div ref={panel} id="cli-step-panel" className="recorded-step" role="tabpanel" aria-labelledby={`cli-step-${activeIndex}`} tabIndex={-1}>
        <p className="eyebrow">Step {activeIndex + 1} of 5</p>
        <h3 ref={heading} tabIndex={-1}>{steps[activeIndex]}</h3>
        <dl className="stage-lesson" aria-label="This stage in plain language">
          <div><dt>Input</dt><dd>{stageLessons[activeIndex].input}</dd></div>
          <div><dt>Output</dt><dd>{stageLessons[activeIndex].output}</dd></div>
          <div><dt>Who owns what</dt><dd>{stageLessons[activeIndex].owner}</dd></div>
        </dl>
        <RecordedStepDiagram step={activeIndex} />
        {activeIndex === 0 && <>
          <h4>Original synthetic issue · verbatim</h4>
          <TextPanel label="Original synthetic issue" text={capture.calls[0].requestBody.state as string} />
          <h4>Actual command</h4>
          <TextPanel label="Recorded command" text={capture.command} />
          <DecisionRequest index={0} />
          <button type="button" onClick={() => previewStep(3)}>See validation request and response</button>
        </>}
        {activeIndex === 1 && <>
          <p>The complete routing request, HTTP envelope, token scope, and field-purpose table are in Step 1.</p>
          <button type="button" onClick={() => previewStep(0)}>See routing request</button>
          <button type="button" onClick={() => previewStep(3)}>See validation request and response</button>
          <p>The recorded choice and scores are below. Decision-1 does not return a written explanation.</p>
          <h4>How to read these scores</h4>
          <p>Each <code>probabilities[label]</code> is the model-assigned probability for that option among the supplied criteria. Read the selected label, then compare it with the alternatives. Multiply a 0–1 value by 100 to read it as a percentage; percentages below are rounded, with the original values alongside.</p>
          <ChoiceResult answer={routeAnswer} showPercentages />
          <p>Here, <code>{routeAnswer.choice}</code> has {(routeAnswer.probabilities[routeAnswer.choice] * 100).toFixed(2)}%, compared with {(routeAnswer.probabilities['human-review'] * 100).toFixed(2)}% for <code>human-review</code>. That shows the model strongly favors supply-chain within these choices—not that the route is proven correct.</p>
          <p><strong>Confidence is separate.</strong> The captured <code>confidence</code> value, <code>{String(routeAnswer.confidence)}</code>, is a provider-reported confidence indicator, not the selected-option probability. The linked Microsoft Learn guidance does not define this field’s calculation or establish a conversion to real-world correctness. It is not measured accuracy, certainty, or a safety guarantee.</p>
          <p><strong>Model choice versus effective route:</strong> the CLI checks allowed choices and numeric values, complete probabilities summing to 1 within 0.001, and requires the selected expert’s probability to be at least 0.70 (70%) and strictly greater than every alternative. These are this demo’s application rules, not a confidence threshold or model guarantee. Low, missing, invalid, or tied routing evidence leads to human review rather than an automatic specialist handoff. This response passes: effective route is supply-chain.</p>
          <p>Higher scores do not authorize actions. Specialist output checks, proposal validation, and the human approval handoff still follow. <a href={decisionLearnUrl}>Microsoft Learn: choice probabilities and interpreting decisions</a></p>
          <RecordedCall index={0} />
        </>}
        {activeIndex === 2 && <>
          <p>The request uses supply-chain system instructions and a strict JSON schema requiring <code>proposed_action</code> and <code>brief</code>.</p>
          <p>The advice says expedited freight could cover the shortfall. That is the model’s wording, not independently verified feasibility or a confirmed arrival.</p>
          <h4>Exact structured response content · verbatim</h4>
          <TextPanel label="Exact specialist response content" text={proposalContent} />
          <p><strong>Next / ordinary rules:</strong> CLI parses the completed, non-refused structured answer, checks its two fields and allowed action identifier, then passes this proposal to validation. Advice authorizes no spending or actions.</p>
          <RecordedCall index={1} />
        </>}
        {activeIndex === 3 && <>
          <p className="validation-intro">Original issue + specialist proposal → validation verdict</p>
          <section className="validation-group" aria-labelledby="validation-input-heading">
            <h4 id="validation-input-heading">Input · Original issue + specialist proposal</h4>
            <p>The full request below carries both the original issue and the actual proposal together in <code>state</code>.</p>
            <div className="validation-evidence">
              <div>
                <h5>Original issue · verbatim</h5>
                <TextPanel label="Original issue beside validation" text={capture.calls[0].requestBody.state as string} />
              </div>
              <div>
                <h5>Specialist proposal · verbatim</h5>
                <TextPanel label="Actual proposal beside validation" text={proposalContent} />
              </div>
            </div>
          </section>
          <section className="validation-group" aria-labelledby="validation-rubric-heading">
            <h4 id="validation-rubric-heading">Rubric · Full validation request</h4>
            <p>The validation rubric checks relevance, quantities, approval limits, unsupported assumptions, unknowns, and consistency of the action with the brief.</p>
            <p>The three allowed verdict labels are <strong>Addresses the issue</strong>, <strong>Needs revision</strong>, and <strong>Cannot determine</strong>. Their full descriptions and judging instructions are preserved in the request below.</p>
            <DecisionRequest index={2} />
          </section>
          <section className="validation-group" aria-labelledby="validation-result-heading">
            <h4 id="validation-result-heading">Result · Validation verdict, not approval</h4>
            <p><strong>Output / model judgment:</strong> “Addresses the issue” means a judgment against the supplied rubric. It is not proof of resolution, permission, or action execution.</p>
            <ChoiceResult answer={validationAnswer} />
            <p><strong>Next / ordinary rules:</strong> CLI requires all verdict probabilities, prints the result, and checks review origins. Passing validation does not bypass the approval handoff.</p>
            <RecordedCall index={2} />
            <h5>Actual terminal output · this stage, verbatim</h5>
            <TextPanel label="Actual terminal output for this step" text={terminalStages[activeIndex]} />
          </section>
        </>}
        {activeIndex === 4 && <>
          <p><strong>Ordinary rules:</strong> the cost-limit <code>policy_reviews</code> branch runs only for <code>expedite_freight</code>. It did not fire in this run. The handoff shown here is specialist-requested, not a policy-origin review.</p>
          <p><strong>Output / human choice:</strong> Pending (noninteractive input; no automatic acceptance). Exit code {capture.exitCode}. No human accepted the proposal; no action executed.</p>
          <p>In an interactive CLI, a person could accept for the demo, reject, or escalate. This recording captured no such choice. There are no approval controls on this page, and a demo choice would not be real authorization.</p>
        </>}
        {activeIndex !== 3 && <>
          <h4>Actual terminal output · this stage, verbatim</h4>
          <TextPanel label="Actual terminal output for this step" text={terminalStages[activeIndex]} />
        </>}
      </div>

      <div className="recorded-navigation" aria-label="Step navigation">
        <button type="button" disabled={activeIndex === 0} onClick={() => navigateStep(activeIndex - 1)}>Previous step</button>
        <button type="button" disabled={activeIndex === steps.length - 1} onClick={() => navigateStep(activeIndex + 1)}>Next step</button>
        <a href="#intro">Return to Home</a>
      </div>

      <details className="recorded-archive">
        <summary>Full recorded stdout · verbatim, all reached stages</summary>
        <TextPanel label="Full recorded stdout" text={capture.stdout} />
        <p>Exit code: {capture.exitCode} · stderr: empty · Pending human review · no actions executed.</p>
      </details>
      <details className="recorded-archive">
        <summary>Recording details and interpretation</summary>
        <p><strong>2 Decision-1 calls · 1 GPT-4.1-mini call · no retries</strong></p>
        <p>UTC: <time dateTime={capture.captureStartedAtUtc}>{capture.captureStartedAtUtc}</time> through <time dateTime={capture.captureFinishedAtUtc}>{capture.captureFinishedAtUtc}</time></p>
        <p>CaptureRun {capture.captureRun}; original capture source <code>{capture.sourceFile}</code>, SHA256 <code>{capture.sourceSha256}</code>. This hash identifies the original CLI used during capture, not the public CLI or sanitized JSON asset.</p>
        <p><strong>Sanitized published capture.</strong> Deployment names are generic placeholders. The provider response ID, system fingerprint, and serving replica identifier are redacted consistently in request/response objects and strings. The explanatory resource hostname is generic.</p>
        <p>Actual model outputs, probabilities, confidence, model versions, UTC dates, timings, usage, and terminal stdout are unchanged. Formatted panels reformat the sanitized sample; modified envelopes are not byte-for-byte raw captures. Verbatim stdout labels apply only to the unchanged transcript.</p>
        <p>No HTTP headers were captured. The HTTP envelope is explanatory, with only a literal token placeholder.</p>
        <p>Client HTTP timing excludes token acquisition. Recorded round trips and provider usage do not establish general speed, quality, calibration, or readiness. This page reads saved evidence; it makes no model calls.</p>
      </details>
    </div>
  );
}
