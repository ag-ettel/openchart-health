/**
 * Builds per-measure index JSON files from exported provider JSON files.
 *
 * Output:
 *   public/data/measure_index/_manifest.json — list of all measures with metadata
 *   public/data/measure_index/{measure_id}.json — per-measure provider rows
 *
 * Run: npx tsx scripts/build-measure-indexes.ts
 * Or:  npm run build:measure-index
 *
 * Architecture:
 *   - Reads every build/data/{ccn}.json for the requested provider type(s).
 *   - Filters out stratified rows (stratification !== null) and retired measures.
 *   - For each (measure_id, provider) pair, emits one row.
 *   - Groups rows by measure_id and writes one JSON file per measure.
 *   - Manifest drives the measure picker UI on /filter-explore.
 *
 * Designed to be provider-type extensible — currently only HOSPITAL is wired up,
 * but the partition step accepts a list of types so adding NURSING_HOME later is
 * a one-line change in main().
 */

import fs from "fs";
import path from "path";

// --- Types (mirror frontend/types/provider.ts and lib/measure-index.ts) ---

type ProviderType = "HOSPITAL" | "NURSING_HOME" | "HOME_HEALTH" | "HOSPICE";

interface RawMeasure {
  measure_id: string;
  measure_name: string | null;
  measure_plain_language: string | null;
  cms_measure_definition: string | null;
  measure_group: string;
  source_dataset_id: string | null;
  source_dataset_name: string;
  direction: "LOWER_IS_BETTER" | "HIGHER_IS_BETTER" | null;
  direction_source: string | null;
  unit: string | null;
  tail_risk_flag: boolean;
  ses_sensitivity: "HIGH" | "MODERATE" | "LOW" | "UNKNOWN";
  stratification: string | null;
  numeric_value: number | null;
  score_text: string | null;
  confidence_interval_lower: number | null;
  confidence_interval_upper: number | null;
  ci_source: string | null;
  prior_source: string | null;
  ci_level: string | null;
  overlap_flag: boolean | null;
  compared_to_national: string | null;
  suppressed: boolean;
  suppression_reason: string | null;
  not_reported: boolean;
  not_reported_reason: string | null;
  count_suppressed: boolean;
  footnote_codes: number[] | null;
  footnote_text: string[] | null;
  period_label: string;
  period_start: string | null;
  period_end: string | null;
  sample_size: number | null;
  denominator: number | null;
  reliability_flag: string | null;
  national_avg: number | null;
  state_avg: number | null;
  trend: unknown[] | null;
}

interface RawInspectionEvent {
  survey_date: string | null;
  survey_type: string | null;
  scope_severity_code: string | null;
  is_complaint_deficiency: boolean;
  is_immediate_jeopardy: boolean;
}

interface RawProvider {
  provider_id: string;
  provider_type: ProviderType;
  name: string;
  is_active: boolean;
  address: { city: string | null; state: string | null };
  provider_subtype: string | null;
  ownership_type: string | null;
  measures: RawMeasure[];
  inspection_events?: RawInspectionEvent[] | null;
}

// Row written to per-measure index file.
interface MeasureIndexRow {
  ccn: string;
  name: string;
  city: string | null;
  state: string | null;
  provider_subtype: string | null;
  ownership_type: string | null;
  numeric_value: number | null;
  score_text: string | null;
  ci_lower: number | null;
  ci_upper: number | null;
  ci_source: string | null;
  ci_level: string | null;
  sample_size: number | null;
  denominator: number | null;
  period_label: string;
  period_start: string | null;
  period_end: string | null;
  suppressed: boolean;
  suppression_reason: string | null;
  not_reported: boolean;
  not_reported_reason: string | null;
  count_suppressed: boolean;
  footnote_codes: number[] | null;
  footnote_text: string[] | null;
  compared_to_national: string | null;
  reliability_flag: string | null;
  national_avg: number | null;
  state_avg: number | null;
  overlap_flag: boolean | null;
}

interface MeasureManifestEntry {
  measure_id: string;
  measure_name: string | null;
  measure_plain_language: string | null;
  cms_measure_definition: string | null;
  measure_group: string;
  unit: string | null;
  direction: "LOWER_IS_BETTER" | "HIGHER_IS_BETTER" | null;
  direction_source: string | null;
  tail_risk_flag: boolean;
  ses_sensitivity: "HIGH" | "MODERATE" | "LOW" | "UNKNOWN";
  source_dataset_id: string | null;
  source_dataset_name: string;
  applicable_provider_types: ProviderType[];
  provider_count: number;          // total facilities with this measure (any state)
  reported_count: number;          // facilities with non-suppressed, non-not-reported value
  suppressed_count: number;
  not_reported_count: number;
}

interface MeasureIndexFile {
  measure_id: string;
  measure_name: string | null;
  measure_plain_language: string | null;
  cms_measure_definition: string | null;
  measure_group: string;
  unit: string | null;
  direction: "LOWER_IS_BETTER" | "HIGHER_IS_BETTER" | null;
  direction_source: string | null;
  tail_risk_flag: boolean;
  ses_sensitivity: "HIGH" | "MODERATE" | "LOW" | "UNKNOWN";
  source_dataset_id: string | null;
  source_dataset_name: string;
  applicable_provider_types: ProviderType[];
  rows: MeasureIndexRow[];
}

// --- Retired-measure check ---
//
// Matches the spirit of frontend/lib/utils.ts isMeasureRetired but extracts
// every 4-digit year in the label, not only the first match. The first-match
// version flags any measure whose latest period label *starts* with a year
// before the cutoff (e.g., "2021-04 to 2024-03" → start year 2021 → retired)
// even though the period clearly ends in 2024. We want the END of the latest
// period, so take the max of all matched years across period_label and trend.

const RETIRED_CUTOFF_YEAR = 2022;

function maxYear(label: string): number {
  let best = 0;
  const re = /(\d{4})/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(label)) !== null) {
    const y = parseInt(m[1], 10);
    if (y > best) best = y;
  }
  return best;
}

function isMeasureRetired(m: RawMeasure): boolean {
  if (m.measure_name?.startsWith("[Retired/Unknown]")) return true;
  let latestYear = maxYear(m.period_label);
  if (m.trend) {
    for (const t of m.trend as Array<{ period_label?: string }>) {
      if (t.period_label) {
        const y = maxYear(t.period_label);
        if (y > latestYear) latestYear = y;
      }
    }
  }
  return latestYear > 0 && latestYear < RETIRED_CUTOFF_YEAR;
}

// ─── Synthetic NH inspection-severity measures ──────────────────────────
//
// The pipeline ships two NH inspection measures (NH_INSP_TOTAL_HEALTH_DEF,
// NH_INSP_WEIGHTED_SCORE). For filter-explore we want the same severity
// breakdown the per-NH page shows (J–L, G–I, D–F, A–C). We compute it here
// from the inspection_events array using the same 120-day clustering as
// frontend/components/InspectionSummary.tsx — anchored at the most recent
// survey, including any survey within 120 days BEFORE it. Standard surveys
// and follow-up revisits within that window are treated as one event,
// matching CMS Five-Star rating-cycle weighting.
//
// Output: per-NH "most-recent inspection event" counts as synthetic measure
// rows. Hospitals are not affected (no inspection_events on hospital JSONs).

const CLUSTER_WINDOW_DAYS = 120;

type SeverityBucket = "ac" | "df" | "ghi" | "jkl";

function severityBucket(code: string | null): SeverityBucket | null {
  if (!code) return null;
  const c = code.toUpperCase();
  if ("ABC".includes(c)) return "ac";
  if ("DEF".includes(c)) return "df";
  if ("GHI".includes(c)) return "ghi";
  if ("JKL".includes(c)) return "jkl";
  return null;
}

function daysBetween(a: string, b: string): number {
  const ad = new Date(a).getTime();
  const bd = new Date(b).getTime();
  return Math.abs(ad - bd) / (1000 * 60 * 60 * 24);
}

interface MostRecentInspectionGroup {
  earliestDate: string;
  latestDate: string;
  total: number;
  ac: number;
  df: number;
  ghi: number;
  jkl: number;
  complaint: number;
}

/**
 * Cluster a provider's inspection_events into the most recent inspection
 * event using the same 120-day window as the per-NH InspectionSummary
 * component. Returns null when no events have a survey_date.
 */
function mostRecentInspectionGroup(
  events: RawInspectionEvent[] | null | undefined,
): MostRecentInspectionGroup | null {
  if (!events || events.length === 0) return null;
  // Collect events that have a survey_date, sorted newest first.
  const dated = events
    .filter((e) => e.survey_date)
    .map((e) => ({ ...e, survey_date: e.survey_date as string }))
    .sort((a, b) => b.survey_date.localeCompare(a.survey_date));
  if (dated.length === 0) return null;

  // Anchor at the most recent date; include events within CLUSTER_WINDOW_DAYS
  // BEFORE it. Anchoring at a rolling earliest date would let arbitrary chains
  // merge across many months and inflate counts vs. the per-page rollup.
  const latestDate = dated[0].survey_date;
  let earliestDate = latestDate;
  let total = 0;
  let ac = 0;
  let df = 0;
  let ghi = 0;
  let jkl = 0;
  let complaint = 0;
  for (const e of dated) {
    if (daysBetween(latestDate, e.survey_date) > CLUSTER_WINDOW_DAYS) break;
    total++;
    if (e.is_complaint_deficiency) complaint++;
    const bucket = severityBucket(e.scope_severity_code);
    if (bucket === "ac") ac++;
    else if (bucket === "df") df++;
    else if (bucket === "ghi") ghi++;
    else if (bucket === "jkl") jkl++;
    if (e.survey_date < earliestDate) earliestDate = e.survey_date;
  }

  return { earliestDate, latestDate, total, ac, df, ghi, jkl, complaint };
}

interface SyntheticMeasureSpec {
  measure_id: string;
  measure_name: string;
  measure_plain_language: string;
  measure_group: string;
  tail_risk_flag: boolean;
  pickValue: (g: MostRecentInspectionGroup) => number;
}

const NH_INSPECTION_SYNTHETIC: SyntheticMeasureSpec[] = [
  {
    measure_id: "NH_INSP_RECENT_JKL",
    measure_name: "Immediate jeopardy citations (J–L) — most recent inspection event",
    measure_plain_language:
      "Number of citations at scope and severity J, K, or L in the facility's most recent inspection event. These indicate findings that placed residents at risk of serious injury, harm, or death.",
    measure_group: "NH_INSPECTION",
    tail_risk_flag: true,
    pickValue: (g) => g.jkl,
  },
  {
    measure_id: "NH_INSP_RECENT_GHI",
    measure_name: "Actual harm citations (G–I) — most recent inspection event",
    measure_plain_language:
      "Number of citations at scope and severity G, H, or I in the facility's most recent inspection event. These indicate actual harm that does not constitute immediate jeopardy.",
    measure_group: "NH_INSPECTION",
    tail_risk_flag: true,
    pickValue: (g) => g.ghi,
  },
  {
    measure_id: "NH_INSP_RECENT_DF",
    measure_name: "Potential-harm citations (D–F) — most recent inspection event",
    measure_plain_language:
      "Number of citations at scope and severity D, E, or F in the facility's most recent inspection event. These indicate no actual harm, but potential for more than minimal harm.",
    measure_group: "NH_INSPECTION",
    tail_risk_flag: false,
    pickValue: (g) => g.df,
  },
  {
    measure_id: "NH_INSP_RECENT_AC",
    measure_name: "Low-risk citations (A–C) — most recent inspection event",
    measure_plain_language:
      "Number of citations at scope and severity A, B, or C in the facility's most recent inspection event. These indicate no actual harm and minimal potential for harm.",
    measure_group: "NH_INSPECTION",
    tail_risk_flag: false,
    pickValue: (g) => g.ac,
  },
  {
    measure_id: "NH_INSP_RECENT_TOTAL",
    measure_name: "Total citations — most recent inspection event",
    measure_plain_language:
      "Total number of citations across all severity codes in the facility's most recent inspection event (a standard survey plus any revisits or complaint investigations within 120 days).",
    measure_group: "NH_INSPECTION",
    tail_risk_flag: false,
    pickValue: (g) => g.total,
  },
  {
    measure_id: "NH_INSP_RECENT_COMPLAINT",
    measure_name: "Complaint citations — most recent inspection event",
    measure_plain_language:
      "Number of citations from complaint-driven investigations in the facility's most recent inspection event.",
    measure_group: "NH_INSPECTION",
    tail_risk_flag: false,
    pickValue: (g) => g.complaint,
  },
];

// --- Paths ---
//
// OUT_DIR is a sibling of public/data, NOT a child. scripts/sync_to_frontend.py
// mirrors build/data → public/data with robocopy /MIR, which deletes any files
// in public/data that aren't in build/data. Putting the measure index inside
// public/data would mean every sync wipes it. Sibling directory survives.

const DATA_DIR = path.join(__dirname, "..", "..", "build", "data");
const OUT_DIR = path.join(__dirname, "..", "public", "measure-index");

// --- Aggregation ---

interface MeasureAccumulator {
  manifest: MeasureManifestEntry;
  rows: MeasureIndexRow[];
}

function buildIndexes(providerTypes: ProviderType[]): void {
  if (!fs.existsSync(DATA_DIR)) {
    console.error(`Data directory not found: ${DATA_DIR}`);
    process.exit(1);
  }
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const files = fs
    .readdirSync(DATA_DIR)
    .filter(
      (f) =>
        f.endsWith(".json") &&
        f !== "search_index.json" &&
        f !== "ownership_entity_index.json"
    );

  // measure_id -> accumulator
  const accs = new Map<string, MeasureAccumulator>();
  let providersScanned = 0;

  for (const file of files) {
    const filePath = path.join(DATA_DIR, file);
    let provider: RawProvider;
    try {
      provider = JSON.parse(fs.readFileSync(filePath, "utf-8")) as RawProvider;
    } catch (err) {
      console.warn(`Skipping unreadable file ${file}: ${(err as Error).message}`);
      continue;
    }
    if (!providerTypes.includes(provider.provider_type)) continue;
    providersScanned++;

    for (const m of provider.measures) {
      if (m.stratification !== null) continue;
      if (isMeasureRetired(m)) continue;

      let acc = accs.get(m.measure_id);
      if (!acc) {
        acc = {
          manifest: {
            measure_id: m.measure_id,
            measure_name: m.measure_name,
            measure_plain_language: m.measure_plain_language,
            cms_measure_definition: m.cms_measure_definition,
            measure_group: m.measure_group,
            unit: m.unit,
            direction: m.direction,
            direction_source: m.direction_source,
            tail_risk_flag: m.tail_risk_flag,
            ses_sensitivity: m.ses_sensitivity,
            source_dataset_id: m.source_dataset_id,
            source_dataset_name: m.source_dataset_name,
            applicable_provider_types: [],
            provider_count: 0,
            reported_count: 0,
            suppressed_count: 0,
            not_reported_count: 0,
          },
          rows: [],
        };
        accs.set(m.measure_id, acc);
      }

      // Track applicable types
      if (!acc.manifest.applicable_provider_types.includes(provider.provider_type)) {
        acc.manifest.applicable_provider_types.push(provider.provider_type);
      }

      const row: MeasureIndexRow = {
        ccn: provider.provider_id,
        name: provider.name,
        city: provider.address?.city ?? null,
        state: provider.address?.state ?? null,
        provider_subtype: provider.provider_subtype,
        ownership_type: provider.ownership_type,
        numeric_value: m.numeric_value,
        score_text: m.score_text,
        ci_lower: m.confidence_interval_lower,
        ci_upper: m.confidence_interval_upper,
        ci_source: m.ci_source,
        ci_level: m.ci_level,
        sample_size: m.sample_size,
        denominator: m.denominator,
        period_label: m.period_label,
        period_start: m.period_start,
        period_end: m.period_end,
        suppressed: m.suppressed,
        suppression_reason: m.suppression_reason,
        not_reported: m.not_reported,
        not_reported_reason: m.not_reported_reason,
        count_suppressed: m.count_suppressed,
        footnote_codes: m.footnote_codes,
        footnote_text: m.footnote_text,
        compared_to_national: m.compared_to_national,
        reliability_flag: m.reliability_flag,
        national_avg: m.national_avg,
        state_avg: m.state_avg,
        overlap_flag: m.overlap_flag,
      };
      acc.rows.push(row);

      acc.manifest.provider_count++;
      if (m.suppressed) acc.manifest.suppressed_count++;
      if (m.not_reported) acc.manifest.not_reported_count++;
      if (!m.suppressed && !m.not_reported && (m.numeric_value !== null || m.score_text !== null)) {
        acc.manifest.reported_count++;
      }
    }

    // Synthetic NH inspection-severity measures — only for nursing homes that
    // expose inspection_events. Apply the same clustering as the per-NH page.
    if (provider.provider_type === "NURSING_HOME") {
      const group = mostRecentInspectionGroup(provider.inspection_events ?? null);
      const periodLabel = group
        ? group.earliestDate === group.latestDate
          ? group.latestDate
          : `${group.earliestDate} – ${group.latestDate}`
        : "";
      for (const spec of NH_INSPECTION_SYNTHETIC) {
        let synth = accs.get(spec.measure_id);
        if (!synth) {
          synth = {
            manifest: {
              measure_id: spec.measure_id,
              measure_name: spec.measure_name,
              measure_plain_language: spec.measure_plain_language,
              cms_measure_definition: null,
              measure_group: spec.measure_group,
              unit: "count",
              direction: "LOWER_IS_BETTER",
              direction_source: "CMS_DATA_DICTIONARY",
              tail_risk_flag: spec.tail_risk_flag,
              ses_sensitivity: "UNKNOWN",
              source_dataset_id: null,
              source_dataset_name: "CMS Health Deficiencies",
              applicable_provider_types: ["NURSING_HOME"],
              provider_count: 0,
              reported_count: 0,
              suppressed_count: 0,
              not_reported_count: 0,
            },
            rows: [],
          };
          accs.set(spec.measure_id, synth);
        }
        const value = group ? spec.pickValue(group) : null;
        const row: MeasureIndexRow = {
          ccn: provider.provider_id,
          name: provider.name,
          city: provider.address?.city ?? null,
          state: provider.address?.state ?? null,
          provider_subtype: provider.provider_subtype,
          ownership_type: provider.ownership_type,
          numeric_value: value,
          score_text: null,
          ci_lower: null,
          ci_upper: null,
          ci_source: null,
          ci_level: null,
          sample_size: group?.total ?? null,
          denominator: null,
          period_label: periodLabel,
          period_start: group?.earliestDate ?? null,
          period_end: group?.latestDate ?? null,
          suppressed: false,
          suppression_reason: null,
          not_reported: !group,
          not_reported_reason: group ? null : "No inspection events on file.",
          count_suppressed: false,
          footnote_codes: null,
          footnote_text: null,
          compared_to_national: null,
          reliability_flag: null,
          national_avg: null,
          state_avg: null,
          overlap_flag: null,
        };
        synth.rows.push(row);
        synth.manifest.provider_count++;
        if (group) synth.manifest.reported_count++;
        else synth.manifest.not_reported_count++;
      }
    }
  }

  // Clear out the directory before writing — drop any stale per-measure files
  // from prior runs (a measure that disappeared from the registry would otherwise
  // linger).
  for (const existing of fs.readdirSync(OUT_DIR)) {
    if (existing.endsWith(".json")) fs.unlinkSync(path.join(OUT_DIR, existing));
  }

  // Write per-measure files. Sort rows alphabetically by name as a stable default.
  for (const [measureId, acc] of accs) {
    acc.rows.sort((a, b) => a.name.localeCompare(b.name));
    const file: MeasureIndexFile = {
      measure_id: measureId,
      measure_name: acc.manifest.measure_name,
      measure_plain_language: acc.manifest.measure_plain_language,
      cms_measure_definition: acc.manifest.cms_measure_definition,
      measure_group: acc.manifest.measure_group,
      unit: acc.manifest.unit,
      direction: acc.manifest.direction,
      direction_source: acc.manifest.direction_source,
      tail_risk_flag: acc.manifest.tail_risk_flag,
      ses_sensitivity: acc.manifest.ses_sensitivity,
      source_dataset_id: acc.manifest.source_dataset_id,
      source_dataset_name: acc.manifest.source_dataset_name,
      applicable_provider_types: acc.manifest.applicable_provider_types,
      rows: acc.rows,
    };
    fs.writeFileSync(
      path.join(OUT_DIR, `${measureId}.json`),
      JSON.stringify(file),
      "utf-8"
    );
  }

  // Manifest: sorted by measure_group, then by measure_name.
  const manifestEntries = Array.from(accs.values()).map((a) => a.manifest);
  manifestEntries.sort((a, b) => {
    const g = a.measure_group.localeCompare(b.measure_group);
    if (g !== 0) return g;
    const an = a.measure_name ?? a.measure_id;
    const bn = b.measure_name ?? b.measure_id;
    return an.localeCompare(bn);
  });

  const manifest = {
    generated_at: new Date().toISOString(),
    provider_types: providerTypes,
    providers_scanned: providersScanned,
    measure_count: manifestEntries.length,
    measures: manifestEntries,
  };
  fs.writeFileSync(
    path.join(OUT_DIR, "_manifest.json"),
    JSON.stringify(manifest),
    "utf-8"
  );

  console.log(
    `Measure indexes built: ${providersScanned} providers scanned, ` +
      `${manifestEntries.length} measures → ${OUT_DIR}`
  );
}

function main(): void {
  // Both provider types share one output directory and one manifest. Measure
  // ids are exclusive between hospital and nursing-home registries (no
  // collisions), so a single flat index works. Each measure carries its
  // applicable_provider_types so the page can filter by the active type.
  const providerTypes: ProviderType[] = ["HOSPITAL", "NURSING_HOME"];
  buildIndexes(providerTypes);
}

main();
