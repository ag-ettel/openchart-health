"use client"; // Recharts requires a client component.

// Phase 1: implement using Recharts LineChart.
// Obligations: see CLAUDE.md: Frontend Specification: Components: TrendChart

import type { TrendPeriod, MeasureDirection } from "@/types/provider";

interface TrendChartProps {
  trend:              TrendPeriod[]; // ordered chronologically, oldest first
  trend_valid:        boolean;
  trend_period_count: number;
  direction:          MeasureDirection;
  unit:               string;
}

export function TrendChart(_props: TrendChartProps): JSX.Element {
  // TODO Phase 1: implement
  //
  // trend_period_count < 3:
  //   - Render individual labeled data points as dots. No connecting line.
  //   - Render TREND_MINIMUM_PERIODS_TEXT(trend_period_count) below chart area.
  //   - No trend language ("improving", "declining", "stable") anywhere.
  //
  // trend_period_count >= 3:
  //   - Connected line chart.
  //   - At any period where methodology_change_flag is true: break the line
  //     (do not connect across the boundary). Render MethodologyChangeFlag there.
  //
  // For all cases:
  //   - Suppressed and not_reported periods: labeled gap markers, not missing points.
  //   - Color via qualityDirection() relative to national_avg where available.
  //   - Blue/orange only, consistent with BenchmarkBar color classes.
  //   - Include confidence intervals as shaded area if confidence_interval_lower and confidence_interval_upper are both non-null for that period.
  return <div data-component="TrendChart" />;
}
