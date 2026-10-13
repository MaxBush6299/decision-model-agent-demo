import capture from './supply-chain-cli-run2.json' with { type: 'json' };

type ChoiceAnswer = { choice: string; confidence: number; probabilities: Record<string, number> };
export { capture };
export const routeAnswer: ChoiceAnswer = JSON.parse(capture.calls[0].responseText).answers.route;
export const validationAnswer: ChoiceAnswer = JSON.parse(capture.calls[2].responseText).answers.validation;
export const proposalContent: string = JSON.parse(capture.calls[1].responseText).choices[0].message.content;

const boundaries = [
  0,
  ...capture.calls.slice(1).map((call) => call.stdoutOffsetBeforeCall),
  capture.stdout.indexOf('Human review required:'),
  capture.stdout.length,
];
boundaries.splice(1, 0, capture.calls[0].stdoutOffsetBeforeCall);
export const terminalStages = boundaries.slice(0, -1).map((start, index) => capture.stdout.slice(start, boundaries[index + 1]));
