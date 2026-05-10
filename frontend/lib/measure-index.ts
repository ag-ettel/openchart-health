// Types and fetch helpers for /filter-explore.
//
// The pipeline → frontend handshake is:
//   build/data/{ccn}.json — per-provider exports (canonical schema in provider.ts)
//   frontend/public/data/measure_index/_manifest.json — measure list (this file)
//   frontend/public/data/measure_index/{measure_id}.json — per-measure rows
//
// Generator: frontend/scripts/build-measure-indexes.ts
// Schema is internal to the frontend (not part of the JSON export contract).

import type {
  MeasureDirection,
  ProviderType,
  SesSensitivity,
  ReliabilityFlag,
  DirectionSource,
} from "@/types/provider";

export interface MeasureIndexRow {
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
  reliability_flag: ReliabilityFlag | null;
  national_avg: number | null;
  state_avg: number | null;
  overlap_flag: boolean | null;
}

export interface MeasureManifestEntry {
  measure_id: string;
  measure_name: string | null;
  measure_plain_language: string | null;
  cms_measure_definition: string | null;
  measure_group: string;
  unit: string | null;
  direction: MeasureDirection | null;
  direction_source: DirectionSource | null;
  tail_risk_flag: boolean;
  ses_sensitivity: SesSensitivity;
  source_dataset_id: string | null;
  source_dataset_name: string;
  applicable_provider_types: ProviderType[];
  provider_count: number;
  reported_count: number;
  suppressed_count: number;
  not_reported_count: number;
}

export interface MeasureManifest {
  generated_at: string;
  provider_types: ProviderType[];
  providers_scanned: number;
  measure_count: number;
  measures: MeasureManifestEntry[];
}

export interface MeasureIndexFile {
  measure_id: string;
  measure_name: string | null;
  measure_plain_language: string | null;
  cms_measure_definition: string | null;
  measure_group: string;
  unit: string | null;
  direction: MeasureDirection | null;
  direction_source: DirectionSource | null;
  tail_risk_flag: boolean;
  ses_sensitivity: SesSensitivity;
  source_dataset_id: string | null;
  source_dataset_name: string;
  applicable_provider_types: ProviderType[];
  rows: MeasureIndexRow[];
}

// Sibling of /data/ rather than a child — keeps the index out of the path
// that scripts/sync_to_frontend.py mirrors and would otherwise wipe.
const INDEX_BASE = "/measure-index";

export async function fetchMeasureManifest(): Promise<MeasureManifest> {
  const resp = await fetch(`${INDEX_BASE}/_manifest.json`);
  if (!resp.ok) {
    throw new Error(`Failed to load measure manifest: ${resp.status}`);
  }
  return resp.json() as Promise<MeasureManifest>;
}

export async function fetchMeasureIndex(measureId: string): Promise<MeasureIndexFile> {
  const resp = await fetch(`${INDEX_BASE}/${encodeURIComponent(measureId)}.json`);
  if (!resp.ok) {
    throw new Error(`Failed to load measure index for ${measureId}: ${resp.status}`);
  }
  return resp.json() as Promise<MeasureIndexFile>;
}

/** A row is "reportable" when it carries a numeric value or categorical score. */
export function rowHasData(row: MeasureIndexRow): boolean {
  if (row.suppressed || row.not_reported) return false;
  return row.numeric_value !== null || row.score_text !== null;
}

/** Status enum used by the table for visual hierarchy. */
export type RowStatus = "reported" | "suppressed" | "not_reported" | "no_value";

export function rowStatus(row: MeasureIndexRow): RowStatus {
  if (row.not_reported) return "not_reported";
  if (row.suppressed) return "suppressed";
  if (row.numeric_value === null && row.score_text === null) return "no_value";
  return "reported";
}
