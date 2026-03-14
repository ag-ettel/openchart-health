// Phase 1: implement as a CSS-based horizontal deviation bar.
// National average is the primary reference axis.
// State average renders as a secondary marker on the same bar when available.
// See .claude/rules/frontend-spec.md before implementing.

import type { MeasureDirection, ReliabilityFlag } from "@/types/provider";

interface BenchmarkBarProps {
  value:           number;
  nationalAvg:     number;
  stateAvg:        number | null;    // renders as secondary marker when non-null
  direction:       MeasureDirection;
  unit:            string;
  ciLower:         number | null;    // renders as CI range overlay on the bar
  ciUpper:         number | null;
  reliabilityFlag: ReliabilityFlag;
}

export function BenchmarkBar(_props: BenchmarkBarProps): JSX.Element {
  // TODO Phase 1: implement
  //
  // Compute national comparison:
  //   compareToAverage(value, nationalAvg, direction, ciLower, ciUpper, reliabilityFlag)
  //   Map result to color class via RESULT_CONFIG in ComparisonBadge.
  //
  // Compute state comparison when stateAvg is non-null:
  //   compareToAverage(value, stateAvg, direction, ciLower, ciUpper, reliabilityFlag)
  //   Render as a secondary tick/marker on the bar, not a second full bar.
  //   Label it clearly: "State avg" to distinguish from the national axis.
  //
  // CI range:
  //   When both ciLower and ciUpper are non-null, render as a translucent
  //   horizontal span overlaid on the bar. This makes visual the uncertainty
  //   range that informs the comparison result.
  //
  // Labels:
  //   Both hospital value and national average labeled with formatValue(value, unit).
  //   Bar must be readable without tooltip interaction.
  //   State average tick labeled with formatValue(stateAvg, unit) when present.
  //
  // Guard at call site (MeasureCard): do not render when:
  //   - nationalAvg is null
  //   - suppressed is true
  //   - not_reported is true
  //   - reliabilityFlag is LIMITED_SAMPLE without SMALL_SAMPLE_CAVEAT also rendering
  return <div data-component="BenchmarkBar" />;
}
