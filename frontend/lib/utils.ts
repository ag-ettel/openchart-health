// Architectural contract. See CLAUDE.md: Frontend Specification: Source Files.
// No component may reimplement these functions locally.

import type { Measure, PaymentAdjustment } from "@/types/provider";

// Title-case a string: "SOUTHEAST HEALTH MEDICAL CENTER" → "Southeast Health Medical Center"
// Preserves short words (of, and, the, for, in, at) as lowercase unless first word.
const LOWERCASE_WORDS = new Set(["of", "and", "the", "for", "in", "at", "or", "to", "a", "an"]);
export function titleCase(str: string): string {
  return str
    .toLowerCase()
    .split(" ")
    .map((word, i) => {
      if (i === 0 || !LOWERCASE_WORDS.has(word)) {
        return word.charAt(0).toUpperCase() + word.slice(1);
      }
      return word;
    })
    .join(" ");
}

// Formats a numeric_value for display.
// numeric_value is stored as Decimal(12,4) in the database and parsed to JS number
// in the JSON export. Use toFixed(), never toPrecision().
export function formatValue(value: number, unit: string): string {
  switch (unit) {
    case "percent":
      return `${value.toFixed(1)}%`;
    case "ratio":
      return value.toFixed(2);
    case "minutes":
      return `${Math.round(value)} min`;
    case "count":
      return value.toLocaleString("en-US");
    case "score":
      return value.toFixed(1);
    default:
      return value.toFixed(2);
  }
}

// Formats the per-measure CMS attribution line required by the Legal Compliance
// section. Call at render time inside AttributionLine. Do not inline this logic.
// providerLastUpdated is provider.last_updated (ISO8601).
export function formatAttribution(
  sourceDatasetName: string,
  periodLabel: string,
  providerLastUpdated: string
): string {
  const [year, month, day] = providerLastUpdated.slice(0, 10).split("-").map(Number);
  const formatted = new Date(year, month - 1, day).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  return (
    `Source: CMS ${sourceDatasetName}, ${periodLabel}. ` +
    `Data reflects CMS reporting as of ${formatted}.`
  );
}

// Returns true when any measure in the array warrants the SES disclosure block.
export function hasSESSensitivity(
  measures: Pick<Measure, "ses_sensitivity">[]
): boolean {
  return measures.some(
    (m) => m.ses_sensitivity === "HIGH" || m.ses_sensitivity === "MODERATE"
  );
}

// Groups a flat measures array by measure_id.
// The entry with stratification === null is the primary measure for that ID.
// Entries with stratification !== null are stratified sub-measures, rendered
// as a grouped sub-table beneath the primary in MeasureCard.
// A group may have sub-measures but no primary (primary: null) if the
// non-stratified row was suppressed at the dataset level.
// Handle that case in MeasureCard without crashing.
export function groupByMeasureId(
  measures: Measure[]
): Map<string, { primary: Measure | null; stratified: Measure[] }> {
  const groups = new Map<string, { primary: Measure | null; stratified: Measure[] }>();
  for (const m of measures) {
    if (!groups.has(m.measure_id)) {
      groups.set(m.measure_id, { primary: null, stratified: [] });
    }
    const group = groups.get(m.measure_id)!;
    if (m.stratification === null) {
      group.primary = m;
    } else {
      group.stratified.push(m);
    }
  }
  return groups;
}

// Formats a CMS period label like "2021-04 to 2024-03" into "Apr 2021 – Mar 2024".
const MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
export function formatPeriodLabel(label: string): string {
  const match = label.match(/^(\d{4})-(\d{2})\s+to\s+(\d{4})-(\d{2})$/);
  if (!match) return label; // fallback to raw label
  const [, y1, m1, y2, m2] = match;
  return `${MONTH_ABBR[parseInt(m1, 10) - 1]} ${y1} – ${MONTH_ABBR[parseInt(m2, 10) - 1]} ${y2}`;
}

// Returns true when a measure has reportable data (not suppressed, not unreported,
// and has either a numeric value or a categorical score).
export function measureHasData(m: Pick<Measure, "suppressed" | "not_reported" | "numeric_value" | "score_text">): boolean {
  if (m.suppressed || m.not_reported) return false;
  return m.numeric_value !== null || m.score_text !== null;
}

// Detects consecutive penalty years for a given payment program.
// Returns the count of consecutive recent penalty years, or 0 if < 2 consecutive.
// Used by both PatientSafetyRecord and PaymentAdjustmentHistory.
export function consecutivePenalties(
  adjustments: PaymentAdjustment[],
  program: string
): number {
  const penaltyYears = adjustments
    .filter((a) => a.program === program && a.penalty_flag === true)
    .map((a) => a.program_year)
    .sort((a, b) => b - a); // newest first

  if (penaltyYears.length < 2) return 0;

  let count = 1;
  for (let i = 1; i < penaltyYears.length; i++) {
    if (penaltyYears[i] === penaltyYears[i - 1] - 1) {
      count++;
    } else {
      break;
    }
  }
  return count >= 2 ? count : 0;
}
