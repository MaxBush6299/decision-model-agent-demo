import { useId } from 'react';
import { routeAnswer, validationAnswer } from '../data/recordedCli';

type Icon = 'facts' | 'choices' | 'decision' | 'rules' | 'draft' | 'human';
type Node = { icon: Icon; owner: string; label: string; detail: string; inactive?: boolean };

const icons: Record<Icon, string> = {
  facts: 'M18 12h23l7 7v33H18z M41 12v9h7 M25 29h16 M25 37h16 M25 45h10 M12 19v38h29',
  choices: 'M12 32h15 M27 16v32 M27 16h12 M27 32h12 M27 48h12 M45 10h9v12h-9z M45 26h9v12h-9z M45 42h9v12h-9z',
  decision: 'M32 10l22 22-22 22L10 32z M22 32h20 M35 25l7 7-7 7',
  rules: 'M13 13h38v38H13z M22 23l4 4 8-8 M22 40h20 M39 20h5 M22 46h12',
  draft: 'M13 12h28v12 M13 12v40h34V39 M28 37l-2 9 9-2 20-20-7-7z M44 21l7 7 M20 23h12 M20 30h7',
  human: 'M24 23a8 8 0 1 0 16 0a8 8 0 1 0-16 0 M16 51v-5a16 16 0 0 1 32 0v5 M10 12h12 M16 6v12 M48 12h6 M51 9v6',
};

function DiagramIcon({ icon }: { icon: Icon }) {
  return <svg viewBox="0 0 64 64" width="64" height="64" aria-hidden="true" focusable="false">
    <path d={icons[icon]} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>;
}

function FlowNode({ node }: { node: Node }) {
  return <div className={`recorded-flow-node${node.inactive ? ' recorded-flow-inactive' : ''}`} role="listitem">
    <DiagramIcon icon={node.icon} />
    <div>
      <span className="recorded-flow-owner">{node.owner}</span>
      <strong>{node.label}</strong>
      <span className="recorded-flow-detail">{node.detail}</span>
    </div>
  </div>;
}

function Connector() {
  return <svg className="recorded-flow-connector" viewBox="0 0 32 32" width="32" height="32" aria-hidden="true" focusable="false">
    <path d="M3 16h25 M20 8l8 8-8 8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>;
}

const maps: { title: string; inputs?: Node[]; nodes: Node[] }[] = [
  {
    title: 'Build one bounded routing question',
    inputs: [
      { icon: 'facts', owner: 'Supplied context', label: 'Original issue', detail: 'The synthetic shortage goes in state.' },
      { icon: 'choices', owner: 'Supplied rubric', label: 'One question, four owners', detail: 'production / maintenance / supply-chain / human-review' },
    ],
    nodes: [{ icon: 'decision', owner: 'Model judgment', label: 'Decision-1', detail: 'Choose from the supplied owners.' }],
  },
  {
    title: 'A routing choice is checked before handoff',
    nodes: [
      { icon: 'decision', owner: 'Model judgment', label: routeAnswer.choice, detail: 'The recorded routing choice.' },
      { icon: 'rules', owner: 'Ordinary CLI rules', label: 'Check the answer', detail: 'Allowed choice, probabilities, routing threshold.' },
      { icon: 'draft', owner: 'Specialist handoff', label: 'Supply-chain specialist', detail: 'Only the selected specialist is called here.' },
    ],
  },
  {
    title: 'The specialist drafts advice, not an action',
    nodes: [
      { icon: 'facts', owner: 'Ordinary CLI input', label: 'Issue + role instructions', detail: 'The same shortage, with a strict answer schema.' },
      { icon: 'draft', owner: 'Model judgment', label: 'GPT-4.1-mini', detail: 'Draft a proposed_action and brief.' },
      { icon: 'rules', owner: 'Ordinary CLI output check', label: 'Structured proposal', detail: 'Parse and check before validation.' },
    ],
  },
  {
    title: 'Validate the proposal against the original issue',
    inputs: [
      { icon: 'facts', owner: 'Supplied context', label: 'original_issue', detail: 'The original shortage, not a summary.' },
      { icon: 'draft', owner: 'Specialist output', label: 'Actual proposal', detail: 'The captured proposed_action + brief.' },
    ],
    nodes: [
      { icon: 'decision', owner: 'Model judgment', label: 'Decision-1 validation', detail: validationAnswer.choice },
      { icon: 'human', owner: 'Approval boundary', label: 'Still needs review', detail: 'A verdict is not permission to execute.' },
    ],
  },
  {
    title: 'Review origins stay distinct at the human checkpoint',
    inputs: [
      { icon: 'decision', owner: 'Model-origin review', label: 'Not triggered', detail: 'The route was supply-chain.', inactive: true },
      { icon: 'rules', owner: 'Policy-origin review', label: 'Not triggered', detail: 'The expedite_freight cost branch did not fire.', inactive: true },
      { icon: 'draft', owner: 'Specialist-requested review', label: 'Triggered in this recording', detail: 'seek_freight_approval requests a person.' },
    ],
    nodes: [{ icon: 'human', owner: 'Human choice', label: 'Pending', detail: 'No acceptance recorded; no action executed.' }],
  },
];

export function RecordedStepDiagram({ step }: { step: number }) {
  const titleId = useId();
  const map = maps[step];
  return <figure className="recorded-flow" aria-labelledby={titleId}>
    <figcaption id={titleId}><span>Stage map</span>{map.title}</figcaption>
    <div className="recorded-flow-track" role="list" aria-label="Responsibilities and handoffs">
      {map.inputs && <>
        <div className="recorded-flow-inputs" role="presentation">
          {map.inputs.map((node) => <FlowNode key={node.label + node.owner} node={node} />)}
        </div>
        <Connector />
      </>}
      {map.nodes.map((node, index) => <div key={node.label} className="recorded-flow-segment" role="presentation">
        {index > 0 && <Connector />}
        <FlowNode node={node} />
      </div>)}
    </div>
  </figure>;
}
