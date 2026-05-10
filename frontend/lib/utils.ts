// Architectural contract. See CLAUDE.md: Frontend Specification: Source Files.
// No component may reimplement these functions locally.

import type { Measure, PaymentAdjustment } from "@/types/provider";

// Build the URL slug for a provider profile route. Format:
//   {kebab-name}-{kebab-city}-{state}-{ccn}
// The trailing 6-digit CCN is the canonical key — extractCcnFromSlug pulls it
// out, which means a hospital that gets renamed by CMS still resolves at the
// old URL without us having to maintain a redirect table.
export function providerSlug(
  name: string,
  city: string | null,
  state: string | null,
  ccn: string
): string {
  const parts = [name, city, state]
    .filter((p): p is string => Boolean(p))
    .map(kebabize)
    .filter((p) => p.length > 0);
  parts.push(ccn);
  return parts.join("-");
}

function kebabize(str: string): string {
  return str
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "") // strip combining diacritic marks
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

// Pulls the canonical 6-digit CCN out of a provider slug. Returns null when
// the slug doesn't end in a CCN (caller should 404).
export function extractCcnFromSlug(slug: string): string | null {
  const match = slug.match(/(?:^|-)(\d{6})$/);
  return match ? match[1] : null;
}

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

// Formats a 10-digit US phone number as (XXX) XXX-XXXX.
export function formatPhone(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  if (digits.length === 11 && digits[0] === "1") {
    return `(${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }
  return raw; // fallback to raw if unexpected format
}

/** Extract a sortable end-date key from any CMS period label format. */
export function periodEndKey(label: string): string {
  // YYYYMMDD-YYYYMMDD (NH claims)
  const m1 = label.match(/^\d{8}-(\d{8})$/);
  if (m1) return m1[1];
  // YYYY-MM to YYYY-MM (hospital)
  const m2 = label.match(/to\s+(\d{4})-(\d{2})/);
  if (m2) return `${m2[1]}${m2[2]}01`;
  // YYYYQn-YYYYQn or YYYYQn-YYYYQn_Qn (NH MDS quarterly)
  const m3 = label.match(/\d{4}Q\d-(\d{4})Q(\d)/);
  if (m3) return `${m3[1]}${String(parseInt(m3[2], 10) * 3).padStart(2, "0")}01`;
  // Single quarter YYYYQn
  const m4 = label.match(/^(\d{4})Q(\d)$/);
  if (m4) return `${m4[1]}${String(parseInt(m4[2], 10) * 3).padStart(2, "0")}01`;
  // YYYY-MM to YYYY-MM (SNF QRP)
  const m5 = label.match(/(\d{4})-(\d{2})$/);
  if (m5) return `${m5[1]}${m5[2]}01`;
  return label;
}

// Returns the most recent period label for a measure — sorts trend
// chronologically first, since the JSON trend array may be unsorted.
export function effectivePeriodLabel(m: Pick<Measure, "period_label" | "trend">): string {
  if (m.trend && m.trend.length > 0) {
    // Sort by end date to find the true latest
    const sorted = [...m.trend]
      .filter((t) => t.period_label !== "unknown")
      .sort((a, b) => periodEndKey(a.period_label).localeCompare(periodEndKey(b.period_label)));
    // Find the latest period with actual data
    for (let i = sorted.length - 1; i >= 0; i--) {
      const t = sorted[i];
      if (t.numeric_value !== null && !t.suppressed) return t.period_label;
    }
    // Fallback to last sorted period even if suppressed
    if (sorted.length > 0) return sorted[sorted.length - 1].period_label;
  }
  return m.period_label;
}

// Returns the effective numeric value for a measure — uses the latest trend
// period's value when the stored period_label is stale.
export function effectiveNumericValue(m: Pick<Measure, "numeric_value" | "period_label" | "trend">): number | null {
  if (!m.trend || m.trend.length === 0) return m.numeric_value;
  const effPeriod = effectivePeriodLabel(m);
  if (effPeriod === m.period_label) return m.numeric_value;
  // Find the value from the effective period in trend
  for (const t of m.trend) {
    if (t.period_label === effPeriod) return t.numeric_value;
  }
  return m.numeric_value;
}

// Formats a CMS period label into a human-readable date range.
// Handles all formats: hospital ("2021-04 to 2024-03"), NH claims ("20180401-20190331"),
// NH quarterly ("2024Q2-2025Q1", "2024Q2-2025Q1_Q4", "2024Q2"), SNF QRP ("2021-10 to 2022-09").
const MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
export function formatPeriodLabel(label: string): string {
  // Hospital / SNF QRP: "2021-04 to 2024-03"
  const hospMatch = label.match(/^(\d{4})-(\d{2})\s+to\s+(\d{4})-(\d{2})$/);
  if (hospMatch) {
    const [, y1, m1, y2, m2] = hospMatch;
    return `${MONTH_ABBR[parseInt(m1, 10) - 1]} ${y1} – ${MONTH_ABBR[parseInt(m2, 10) - 1]} ${y2}`;
  }

  // NH claims: "20180401-20190331" (YYYYMMDD-YYYYMMDD)
  const nhDateMatch = label.match(/^(\d{4})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})$/);
  if (nhDateMatch) {
    const [, y1, m1, , y2, m2] = nhDateMatch;
    return `${MONTH_ABBR[parseInt(m1, 10) - 1]} ${y1} – ${MONTH_ABBR[parseInt(m2, 10) - 1]} ${y2}`;
  }

  // NH quarterly range: "2024Q2-2025Q1" or "2024Q2-2025Q1_Q4"
  const nhQtrRange = label.match(/^(\d{4})Q(\d)-(\d{4})Q(\d)/);
  if (nhQtrRange) {
    const [, y1, q1, y2, q2] = nhQtrRange;
    return `Q${q1} ${y1} – Q${q2} ${y2}`;
  }

  // Single quarter: "2024Q2"
  const singleQtr = label.match(/^(\d{4})Q(\d)$/);
  if (singleQtr) {
    return `Q${singleQtr[2]} ${singleQtr[1]}`;
  }

  // Single month: "2026-02"
  const singleMonth = label.match(/^(\d{4})-(\d{2})$/);
  if (singleMonth) {
    return `${MONTH_ABBR[parseInt(singleMonth[2], 10) - 1]} ${singleMonth[1]}`;
  }

  return label; // fallback to raw
}

// Returns true when a measure has reportable data (not suppressed, not unreported,
// and has either a numeric value or a categorical score).
export function measureHasData(m: Pick<Measure, "suppressed" | "not_reported" | "numeric_value" | "score_text">): boolean {
  if (m.suppressed || m.not_reported) return false;
  return m.numeric_value !== null || m.score_text !== null;
}

// Returns true if a measure appears to be retired by CMS.
// Retired measures have "[Retired/Unknown]" in the name or their most recent data
// (from trend or period_label) is older than the cutoff year.
const RETIRED_CUTOFF_YEAR = 2022;

// Take the MAX of every 4-digit year in a period label, not the first match.
// "2021-04 to 2024-03" should yield 2024 (the period end), not 2021 (the start).
function maxYearInPeriodLabel(label: string): number {
  let best = 0;
  const re = /(\d{4})/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(label)) !== null) {
    const y = parseInt(m[1], 10);
    if (y > best) best = y;
  }
  return best;
}

export function isMeasureRetired(m: Pick<Measure, "measure_name" | "measure_id" | "period_label" | "trend">): boolean {
  // Explicitly tagged as retired
  if (m.measure_name?.startsWith("[Retired/Unknown]")) return true;
  // Find the latest year across the current period and any trend periods
  let latestYear = maxYearInPeriodLabel(m.period_label);
  if (m.trend) {
    for (const t of m.trend) {
      const y = maxYearInPeriodLabel(t.period_label);
      if (y > latestYear) latestYear = y;
    }
  }
  return latestYear > 0 && latestYear < RETIRED_CUTOFF_YEAR;
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
