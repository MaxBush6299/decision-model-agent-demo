import {
  decisionAnnouncementUrl,
  decisionLearnUrl,
  jevContextUrl,
} from '../components/DecisionModelExplainer';

export function IntroPage() {
  return (
    <div className="learn-page intro-page">
      <header className="home-hero">
        <div className="home-hero-art" aria-hidden="true">
          <img className="home-hero-image" src={`${import.meta.env.BASE_URL}home/decision-switchboard.png`} alt="" width="896" height="1120" fetchPriority="high" />
        </div>
        <div className="home-hero-copy">
          <h2 id="intro-title">Explore how decision models work</h2>
          <p className="learn-deck">Some AI writes an answer. A decision model helps choose among known answers. Start with what that means, then follow how a decision model, a language model, software rules, and a person work together.</p>
                    <p className="home-hero-cta"><a className="home-start" href="#showcase">Open the Demo showcase</a></p>
                  </div>
      </header>

      <section className="intro-basics intro-what" aria-labelledby="basics-what-title">
        <div className="home-teaching-panel home-panel-basics">
          <h3 id="basics-what-title">What is a decision model?</h3>
          <p>A decision model is AI built for focused judgments: which team should handle a ticket, which item is urgent, or whether a proposal meets a checklist. You supply context, a bounded question, and allowed answers. For a choice question, it returns a structured choice and probabilities for the options—not a written explanation.</p>
          <p>Think of a sorting clerk at a mailroom. The clerk puts a package in one of a few bins rather than writing a letter about it. The bins are your choices; the package is your context. You still decide what happens after sorting.</p>
          <p><a href={decisionLearnUrl}>Microsoft Learn: Decision-1 jobs and answer formats [L1]</a></p>
        </div>
        <img className="home-photo" src={`${import.meta.env.BASE_URL}home/branching-tracks.png`} alt="" width="1024" height="1024" loading="lazy" />
      </section>

      <section className="intro-basics intro-how" aria-labelledby="basics-how-title">
        <h3 id="basics-how-title">Context in. A bounded answer out.</h3>
        <ol className="intro-steps">
          <li><strong>Describe the situation.</strong> Supply the relevant facts, not just a question without context.</li>
          <li><strong>Ask a focused question.</strong> For example, “Which team should handle this ticket?” Define the allowed choices and what each means; include a way to say there is not enough information.</li>
          <li><strong>Read the structured result.</strong> A choice answer identifies an option and gives a probability for each option. Software can use those numbers for ranking or a minimum-probability rule.</li>
          <li><strong>Apply your rules.</strong> Check the answer shape, allowed choice, and required evidence before routing work or asking a person to review.</li>
        </ol>
        <p>A probability of 0.70 is an estimated 70% chance, not guaranteed accuracy on one case. Calibration means checking that estimates match outcomes across many comparable, labeled examples. Optional reported <code>confidence</code> is a separate field, not the selected-choice probability or permission to act. <a href={decisionLearnUrl}>Probabilities and validation [L1]</a></p>
      </section>

      <section className="intro-basics intro-difference home-teaching-panel home-panel-complement" aria-labelledby="basics-diff-title">
        <h3 id="basics-diff-title">Different jobs, useful together</h3>
        <div className="beginner-jobs">
          <article>
            <h4>Generative language model</h4>
            <p>A large language model (LLM) can draft, summarize, rewrite, or explain content. Use it when you need language or a proposal, not just a selection from known options. LLMs can also return structured answers; structure alone does not make a probability calibrated.</p>
          </article>
          <article>
            <h4>Decision model</h4>
            <p>Use a focused choice or numerical judgment when the question and criteria are already defined. Decision-1 does not write a prose rationale. Its scores are estimates to test, not proof that its choice is right.</p>
          </article>
        </div>
        <p>This is a difference in job and answer format, not a claim that one replaces the other. A decision model can route an alert; a language model can draft advice for the selected specialist. A further decision-model check can assess that proposal against a supplied rubric. <a href={decisionLearnUrl}>Supported tasks and limitations [L1]</a></p>
      </section>

      <section className="intro-basics intro-how" aria-labelledby="basics-agent-title">
        <h3 id="basics-agent-title">Where it fits in an agent</h3>
        <ol className="intro-steps">
          <li><strong>Routing:</strong> the decision model suggests who should handle the issue. Ordinary application code validates the result and decides which specialist to invoke.</li>
          <li><strong>Drafting:</strong> a generative LLM proposes an approach using the supplied issue and instructions.</li>
          <li><strong>Validation:</strong> a decision model judges the proposal against explicit criteria. Passing that check is not proof of resolution or approval.</li>
          <li><strong>Human review:</strong> software applies review and approval rules. A person retains approval authority; a model score cannot grant it.</li>
        </ol>
        <p>The model supplies a judgment; the application owns the workflow. Missing evidence, invalid output, or an ambiguous answer should lead to a safe fallback or review—not an automatic action.</p>
      </section>

      <section className="intro-basics intro-applications home-teaching-panel home-panel-rules" aria-labelledby="basics-limits-title">
        <h3 id="basics-limits-title">Useful estimates, not guarantees</h3>
        <div>
          <p>Routing tickets, prioritizing alerts, and checking a report against a rubric are focused uses. Open-ended writing belongs with a generative model. High-consequence decisions still need appropriate safeguards and human responsibility.</p>
          <p>Errors, bias, outdated knowledge, and sensitivity to the wording or order of choices are still possible. Test on representative examples with answers checked by people. Choose thresholds around the cost of mistakes, and measure review needs as well as correct answers. A single synthetic case proves no general quality, calibration, speed, or cost advantage. <a href={decisionLearnUrl}>Limitations and workload validation [L1]</a></p>
        </div>
      </section>

      <section className="home-launchpad" aria-labelledby="home-paths-title">
        <h3 id="home-paths-title">Now follow a recorded decision</h3>
        <div className="home-path-cards">
          <article className="home-path-card">
            <h4>Follow the recorded shortage</h4>
            <p>Five steps through one factory shortage: the issue, routing, specialist advice, validation, and human review.</p>
            <a className="home-start" href="#learn">Follow the recorded shortage</a>
            <small>One recorded case with synthetic facts.</small>
          </article>
          <article className="home-path-card">
            <h4>Demo showcase</h4>
            <p>Replay four recorded scenarios on one diagram of agents working a case, from Decision-1 routing to the final check.</p>
            <a className="home-start home-start-secondary" href="#showcase">Open the Demo showcase</a>
            <small>Replays were selected after the fact; not a reliability measure.</small>
          </article>
        </div>
        <p className="home-provenance">Recorded runs of synthetic cases. Nothing is executed, and opening these makes no new model calls.</p>
      </section>

      <details className="home-support">
        <summary>Sources and context</summary>
        <section className="learn-sources" aria-labelledby="learn-sources-title">
          <h3 id="learn-sources-title">Sources and what they support</h3>
          <p>The walkthrough preserves three recorded model calls and their terminal output. One synthetic case cannot establish general quality, speed, cost, or readiness for your workload.</p>
          <ul>
            <li>
              <a href={decisionLearnUrl}>L1 · Microsoft Learn: Decision-1 guidance</a>
              <span>Primary source for supported jobs, probabilities, limitations, validation, and human responsibility.</span>
            </li>
            <li>
              <a href={decisionAnnouncementUrl}>M1 · Microsoft’s Decision-1 announcement</a>
              <span>Vendor motivation and vendor-reported results—not a test of this case.</span>
            </li>
            <li>
              <a href={jevContextUrl}>N1 · The Register: Jev and rival decision models</a>
              <span>Independent reporting and market context, not Microsoft product guidance.</span>
            </li>
          </ul>
          <p>To evaluate a model for your work, use representative examples with answers checked by people. Compare mistakes, review needs, full waiting time, and cost—not just whether an answer came back.</p>
          <p>The switchboard and branching tracks are original AI-generated illustrations, created with MAI-Image-2.5 on 13 October 2026. They are visual metaphors, not model outputs or measured evidence.</p>
        </section>
      </details>
    </div>
  );
}
