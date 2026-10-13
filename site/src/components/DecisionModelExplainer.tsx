import { questionCatalog } from '../contracts';

export const decisionLearnUrl = 'https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision';
export const decisionAnnouncementUrl = 'https://commandline.microsoft.com/microsoft-decision-1-model-foundry/';
export const jevContextUrl = 'https://www.theregister.com/ai-and-ml/2026/10/10/microsoft-leans-on-open-weight-model-from-chinese-ai-lab-to-challenge-jev/5302473';
const triage = questionCatalog.gates.triage;

export const mockRequest = {
  model: 'YOUR-DECISION-1-DEPLOYMENT',
  state: JSON.stringify({ eventId: 'synthetic-1', facts: { 'synthetic-1:fact': 'Line stopped' } }),
  questions: Object.fromEntries(triage.questionIds.map((id) => {
    const definition = questionCatalog.questionDefinitions[id as 'event_type' | 'urgency' | 'owning_agent'];
    return [id, {
      type: 'choice',
      instructions: [triage.instructions, definition.label, definition.instructions, '{}'].join('\n'),
      criteria: Object.fromEntries(definition.options.map((option) => [option.id, option.label])),
    }];
  })),
};

export const mockResponse = {
  results: Object.fromEntries(triage.questionIds.map((id) => {
    const options = questionCatalog.questions[id as 'event_type' | 'urgency' | 'owning_agent'];
    return [id, {
      questionId: id,
      selectedChoice: options[0],
      probabilities: Object.fromEntries(options.map((option) => [option, 1 / options.length])),
      confidence: 0.8,
      modelId: 'YOUR-DECISION-1-DEPLOYMENT',
      elapsedMs: 12,
      executionMode: 'mock',
    }];
  })),
  usage: { requestId: 'synthetic-request', inputTokens: 10, outputTokens: 5, totalTokens: 15 },
};

export function DecisionModelExplainer() {
  return (
    <section aria-labelledby="decision-explainer-title">
      <h3 id="decision-explainer-title">Why is everyone talking about decision models?</h3>
      <p>Jev is TypeSafe AI’s decision model, not a person. Reporting on Jev and rival releases
        helped put AI that returns focused, scored answers in the spotlight.{' '}
        <a href={jevContextUrl}>Jev news context [N1]</a></p>
      <p>Microsoft describes the promise as less waiting and lower cost for repeated, focused
        judgments. Microsoft reports results from its own benchmarks and internal uses—not proof
        that our demo or your work will get the same results.{' '}
        <a href={decisionAnnouncementUrl}>Microsoft’s announcement [M1]</a></p>
      <p>Microsoft Decision-1 returns numerical judgments, not written explanations.
        “Frontier” is a broader label for leading models, not a particular answer format.{' '}
        <a href={decisionLearnUrl}>Decision-1 jobs and limitations [L1]</a></p>
      <p className="beginner-authority"><strong>The useful idea is not “let AI decide everything.”</strong>{' '}
        Estimates can be wrong. Our software sets the rules; people keep approval authority
        when information is missing or consequences matter. Microsoft advises testing on your
        own examples and choosing rules around the cost of mistakes.{' '}
        <a href={decisionLearnUrl}>Validation and human responsibility [L1]</a></p>
      <details className="numbers-help">
        <summary>What does an estimated 70% mean?</summary>
        <p>A probability of 0.70 is an estimated 70% chance for that option, not guaranteed accuracy
          on this one case. If validated on similar cases, a well-calibrated model would get about
          70 out of 100 comparable predictions at that level right. Calibration means checking
          that estimates match what actually happens across many labeled examples—not trusting
          one number. It is strongest on familiar task types.{' '}
          <a href={decisionLearnUrl}>Probability and calibration guidance [L1]</a></p>
        <p>Learn preserves one recorded synthetic run, which does not establish a universal calibration
          claim. A checklist grade is not a probability, and neither is permission to act.</p>
        <p>The wording and order of possible answers can change scores. Errors, bias, and outdated
          knowledge are still possible. Choose a minimum-score rule around the cost of mistakes:
          missing a serious problem and asking for unnecessary review have different costs.
          Test on your own representative examples with answers checked by people.{' '}
          <a href={decisionLearnUrl}>Limits and choosing your rules [L1]</a></p>
        <p><code>confidence = 0.80 is a separate LOCAL MOCK-only field</code> kept in the optional
          technical examples. That mock value is not observed provider evidence, an accuracy score, or permission. Learn separately shows the actual model-reported confidence in its recorded responses.
          It must not override missing evidence or a software rule. Asking a reasoning model
          “how confident are you?” does not automatically produce a calibrated probability.</p>
      </details>
      <details>
        <summary>Developer view: mock examples + one approved body-shape sample</summary>
        <p className="note">
          The reproductions below are local mock examples. One specifically approved
          synthetic Decision-1 validation call verified request/response body shape only. That
          single body sample is not quality, calibration, performance, specialist-routing, or
          readiness evidence. The normalized response object is a local synthetic
          DecisionResultSet-shaped illustration, not observed provider JSON.
        </p>
        <h4>Observed provider response body (historical first approved synthetic sample)</h4>
        <ul>
          <li>model: <code>microsoft-decision-1</code></li>
          <li>usage: snake_case <code>input_tokens: 595</code>, <code>output_tokens: 3</code>
            (local normalized total: <code>598</code>)</li>
          <li>answers present for <code>event_type</code>, <code>urgency</code>, and <code>owning_agent</code></li>
        </ul>
        <h4>What that one sample did not establish</h4>
        <ul>
          <li>Response headers, provider request ID, and model version were not verified by that sample.</li>
          <li>That Decision-1 sample did not validate specialist inference.</li>
          <li>Home and Learn make no model calls; the web app has no Run control for now. Hosted presentation readiness remains separately blocked pending its required checks.</li>
          <li>Local normalized fields (for example <code>requestId</code>, <code>inputTokens</code>,
            <code>outputTokens</code>, <code>totalTokens</code>) are app-typed results, not direct provider
            body field names.</li>
        </ul>
        <details className="developer-json">
          <summary>Show raw developer JSON examples</summary>
          <p>These full mock examples retain the technical field names and are not provider response samples.
            Learn’s separate recorded CLI walkthrough shows three actual calls with transparently sanitized envelopes; it does not replace this historical sample.</p>
          <h4>Mock request · Gate 1 only · not yet verified</h4>
          <pre tabIndex={0} role="region" aria-label="Raw mock request JSON"><code>{JSON.stringify(mockRequest, null, 2)}</code></pre>
          <h4>Mock normalized DecisionResultSet response (local synthetic illustrative shape) · not a provider wire sample</h4>
          <pre tabIndex={0} role="region" aria-label="Raw mock normalized response JSON"><code>{JSON.stringify(mockResponse, null, 2)}</code></pre>
        </details>
        <p>These teaching examples include no credentials, hidden reasoning, live calls, or external actions.</p>
      </details>
    </section>
  );
}
