import { humanize } from "../format";
import type { ClaimState } from "../types";

const CLASSES: Record<ClaimState, string> = {
  waiting: "chip chip-waiting",
  "in progress": "chip chip-progress",
  "waiting for sign-off": "chip chip-sign-off",
  decided: "chip chip-decided",
};

export function StateChip({ state }: { readonly state: ClaimState }) {
  return <span className={CLASSES[state]}>{humanize(state)}</span>;
}
