"use client";

// /filter-explore — sort and filter CMS measures across all hospitals.
//
// Two modes:
//   1. Single-measure mode (?m={measure_id}) — pick one measure, see all hospitals.
//   2. Preset mode (?p={preset_id}) — pick a curated dashboard of related measures
//      (e.g., 30-day mortality across six conditions). Renders a wide table with
//      one row per hospital and one column per measure in the preset.
//
// Required disclosures (legal-compliance.md § Complete Disclosure Checklist):
//   - DisclaimerBanner — site-wide layout, always present
//   - Per-measure attribution (Template 3b) — rendered when a measure is selected
//   - SES disclosure (Template 3c) — rendered when ses_sensitivity is HIGH/MODERATE
//   - Multiple comparison disclosure (Template 3d) — rendered above table when many
//     hospitals are visible (always, since the table is the whole point)
//
// Positioning constraints (legal-compliance.md § Positioning):  // compliance-ok
//   - Never label as "ranking," "leaderboard," "top," "bottom," "best," "worst"  // compliance-ok
//   - Default sort is alphabetical by hospital name; user controls all sort/filter
//   - Per-measure context (footnotes, suppression, period, sample) renders inline
//
// URL state:
//   ?m={measure_id} XOR ?p={preset_id}, plus ?s=&t=&q= for filters and
//   ?sc=&sd= for sort. router.replace updates without navigation.

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AttributionLine } from "@/components/AttributionLine";
import { FilterExploreFilters } from "@/components/FilterExploreFilters";
import { FilterExploreTable, type SortColumn, type SortDirection } from "@/components/FilterExploreTable";
import { MeasureIndexHistogram } from "@/components/MeasureIndexHistogram";
import { MeasurePicker } from "@/components/MeasurePicker";
import { MultipleComparisonDisclosure } from "@/components/MultipleComparisonDisclosure";
import {
  PresetTable,
  mergePresetIndexes,
  type PresetMergedRow,
  type PresetSortColumn,
  type PresetSortDirection,
} from "@/components/PresetTable";
import { SESDisclosureBlock } from "@/components/SESDisclosureBlock";
import {
  FILTER_EXPLORE_COUNT_SUMMARY,
  FILTER_EXPLORE_EMPTY_RESULTS_HOSPITAL,
  FILTER_EXPLORE_EMPTY_RESULTS_NURSING_HOME,
  FILTER_EXPLORE_EMPTY_STATE_HOSPITAL,
  FILTER_EXPLORE_EMPTY_STATE_NURSING_HOME,
  FILTER_EXPLORE_HEADING_HOSPITAL,
  FILTER_EXPLORE_HEADING_NURSING_HOME,
  FILTER_EXPLORE_LOADING,
  FILTER_EXPLORE_LOAD_ERROR,
  FILTER_EXPLORE_PRESETS,
  FILTER_EXPLORE_PRESET_EMPTY_STATE,
  FILTER_EXPLORE_PRESET_LOADING,
  FILTER_EXPLORE_SUBHEADING_HOSPITAL,
  FILTER_EXPLORE_SUBHEADING_NURSING_HOME,
  MEASURE_GROUP_DISPLAY_NAMES,
  type FilterExplorePreset,
  type FilterExploreProviderType,
} from "@/lib/constants";
import {
  fetchMeasureIndex,
  fetchMeasureManifest,
  type MeasureIndexFile,
  type MeasureIndexRow,
  type MeasureManifest,
  type MeasureManifestEntry,
} from "@/lib/measure-index";
import { formatPeriodLabel } from "@/lib/utils";
import {
  measureFilterExploreSelected,
  measureFilterExploreSorted,
} from "@/lib/analytics";
import { SentryErrorBoundary } from "@/components/SentryErrorBoundary";

const PARAM_MEASURE = "m";
const PARAM_PRESET = "p";
const PARAM_STATE = "s";
const PARAM_SUBTYPE = "t";
const PARAM_NAME = "q";
const PARAM_SORT_COL = "sc";
const PARAM_SORT_DIR = "sd";

const SORT_COLS = new Set<SortColumn>(["name", "state", "value", "sample_size"]);

function isSortColumn(value: string | null): value is SortColumn {
  return value !== null && SORT_COLS.has(value as SortColumn);
}

function isSortDirection(value: string | null): value is SortDirection {
  return value === "asc" || value === "desc";
}

function manifestMatches(m: MeasureManifestEntry, providerType: FilterExploreProviderType): boolean {
  return m.applicable_provider_types.includes(providerType);
}

function findPreset(id: string | null): FilterExplorePreset | null {
  if (!id) return null;
  return FILTER_EXPLORE_PRESETS.find((p) => p.id === id) ?? null;
}

interface FilterExploreContentProps {
  providerType: FilterExploreProviderType;
}

function FilterExploreContent({ providerType }: FilterExploreContentProps): React.JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Provider-type-aware copy strings.
  const heading =
    providerType === "NURSING_HOME"
      ? FILTER_EXPLORE_HEADING_NURSING_HOME
      : FILTER_EXPLORE_HEADING_HOSPITAL;
  const subheading =
    providerType === "NURSING_HOME"
      ? FILTER_EXPLORE_SUBHEADING_NURSING_HOME
      : FILTER_EXPLORE_SUBHEADING_HOSPITAL;
  const emptyState =
    providerType === "NURSING_HOME"
      ? FILTER_EXPLORE_EMPTY_STATE_NURSING_HOME
      : FILTER_EXPLORE_EMPTY_STATE_HOSPITAL;
  const emptyResults =
    providerType === "NURSING_HOME"
      ? FILTER_EXPLORE_EMPTY_RESULTS_NURSING_HOME
      : FILTER_EXPLORE_EMPTY_RESULTS_HOSPITAL;
  const baseRoute = providerType === "NURSING_HOME" ? "/filter-explore/nursing-home/" : "/filter-explore/";

  const initialMeasureId = searchParams.get(PARAM_MEASURE);
  const initialPresetId = searchParams.get(PARAM_PRESET);
  const initialState = searchParams.get(PARAM_STATE);
  const initialSubtype = searchParams.get(PARAM_SUBTYPE);
  const initialName = searchParams.get(PARAM_NAME) ?? "";
  const rawSortCol = searchParams.get(PARAM_SORT_COL);
  const rawSortDir = searchParams.get(PARAM_SORT_DIR);

  const [manifest, setManifest] = useState<MeasureManifest | null>(null);
  const [manifestError, setManifestError] = useState<string | null>(null);

  // Selection: presetId XOR measureId. Setting one clears the other.
  const [selectedMeasureId, setSelectedMeasureId] = useState<string | null>(
    initialPresetId ? null : initialMeasureId,
  );
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(initialPresetId);

  const [indexFile, setIndexFile] = useState<MeasureIndexFile | null>(null);
  const [indexLoading, setIndexLoading] = useState(false);
  const [indexError, setIndexError] = useState<string | null>(null);

  const [presetFiles, setPresetFiles] = useState<MeasureIndexFile[] | null>(null);
  const [presetLoading, setPresetLoading] = useState(false);
  const [presetError, setPresetError] = useState<string | null>(null);

  const [stateFilter, setStateFilter] = useState<string | null>(initialState);
  const [subtypeFilter, setSubtypeFilter] = useState<string | null>(initialSubtype);
  const [nameSearch, setNameSearch] = useState<string>(initialName);
  const [sortColumn, setSortColumn] = useState<SortColumn>(
    isSortColumn(rawSortCol) ? rawSortCol : "name",
  );
  const [sortDirection, setSortDirection] = useState<SortDirection>(
    isSortDirection(rawSortDir) ? rawSortDir : "asc",
  );

  // Preset table sort state (separate from single-measure sort).
  const [presetSortColumn, setPresetSortColumn] = useState<PresetSortColumn>({ kind: "name" });
  const [presetSortDirection, setPresetSortDirection] = useState<PresetSortDirection>("asc");

  // Fetch the manifest once on mount.
  useEffect(() => {
    let cancelled = false;
    fetchMeasureManifest()
      .then((data) => {
        if (!cancelled) setManifest(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setManifestError(err instanceof Error ? err.message : FILTER_EXPLORE_LOAD_ERROR);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch the per-measure index whenever the single-measure selection changes.
  useEffect(() => {
    if (!selectedMeasureId) {
      setIndexFile(null);
      return;
    }
    let cancelled = false;
    setIndexLoading(true);
    setIndexError(null);
    setIndexFile(null);
    fetchMeasureIndex(selectedMeasureId)
      .then((data) => {
        if (!cancelled) setIndexFile(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setIndexError(err instanceof Error ? err.message : FILTER_EXPLORE_LOAD_ERROR);
        }
      })
      .finally(() => {
        if (!cancelled) setIndexLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedMeasureId]);

  // Fetch all preset measure indexes in parallel when preset selection changes.
  useEffect(() => {
    if (!selectedPresetId) {
      setPresetFiles(null);
      return;
    }
    const preset = findPreset(selectedPresetId);
    if (!preset) {
      setPresetFiles(null);
      return;
    }
    let cancelled = false;
    setPresetLoading(true);
    setPresetError(null);
    setPresetFiles(null);

    Promise.allSettled(preset.measure_ids.map((id) => fetchMeasureIndex(id)))
      .then((results) => {
        if (cancelled) return;
        const ok: MeasureIndexFile[] = [];
        for (const r of results) {
          if (r.status === "fulfilled") ok.push(r.value);
        }
        // Preserve preset-defined order.
        const order = new Map(preset.measure_ids.map((id, i) => [id, i]));
        ok.sort((a, b) => (order.get(a.measure_id) ?? 0) - (order.get(b.measure_id) ?? 0));
        setPresetFiles(ok);
        if (ok.length === 0) {
          setPresetError(FILTER_EXPLORE_PRESET_EMPTY_STATE);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setPresetError(err instanceof Error ? err.message : FILTER_EXPLORE_LOAD_ERROR);
        }
      })
      .finally(() => {
        if (!cancelled) setPresetLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPresetId]);

  // Sync URL state when filters/sort/selection change.
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedPresetId) params.set(PARAM_PRESET, selectedPresetId);
    else if (selectedMeasureId) params.set(PARAM_MEASURE, selectedMeasureId);
    if (stateFilter) params.set(PARAM_STATE, stateFilter);
    if (subtypeFilter) params.set(PARAM_SUBTYPE, subtypeFilter);
    if (nameSearch) params.set(PARAM_NAME, nameSearch);
    // Single-measure sort only — preset sort kept in component state, not URL,
    // to keep the URL simple. Linkable single-measure views remain stable.
    if (!selectedPresetId && sortColumn !== "name") params.set(PARAM_SORT_COL, sortColumn);
    if (!selectedPresetId && sortDirection !== "asc") params.set(PARAM_SORT_DIR, sortDirection);
    const search = params.toString();
    const url = search ? `${baseRoute}?${search}` : baseRoute;
    router.replace(url, { scroll: false });
  }, [
    router,
    baseRoute,
    selectedMeasureId,
    selectedPresetId,
    stateFilter,
    subtypeFilter,
    nameSearch,
    sortColumn,
    sortDirection,
  ]);

  // Filters carry across measure/preset switches — state, hospital type, and
  // name search all describe which hospitals the user wants to look at, not
  // which measure. Sort resets because it's measure-specific (a sort by a
  // measure column doesn't translate to a different measure).
  const handleSelectMeasure = useCallback((measureId: string) => {
    setSelectedMeasureId(measureId);
    setSelectedPresetId(null);
    setSortColumn("name");
    setSortDirection("asc");
    // User action: picked a measure in the left-rail MeasurePicker.
    // measure_group is logged so we can group conversion by domain
    // (mortality, infections, HCAHPS, etc.) without enumerating
    // 200+ measure_ids in the dashboard.
    const entry = manifest?.measures.find((m) => m.measure_id === measureId);
    measureFilterExploreSelected({
      measureId,
      measureGroup: entry?.measure_group ?? "UNKNOWN",
    });
  }, [manifest]);

  const handleSelectPreset = useCallback((presetId: string) => {
    setSelectedPresetId(presetId);
    setSelectedMeasureId(null);
    setPresetSortColumn({ kind: "name" });
    setPresetSortDirection("asc");
  }, []);

  const handleSort = useCallback(
    (column: SortColumn) => {
      // User action: clicked a sortable column header on the single-measure
      // results table. Compute the resulting state, apply it, and log the
      // post-click sort so the dashboard reflects what the user is now
      // looking at (not what they came from).
      let nextColumn: SortColumn;
      let nextDirection: "asc" | "desc";
      if (column === sortColumn) {
        nextColumn = column;
        nextDirection = sortDirection === "asc" ? "desc" : "asc";
        setSortDirection(nextDirection);
      } else {
        nextColumn = column;
        nextDirection = column === "value" || column === "sample_size" ? "desc" : "asc";
        setSortColumn(nextColumn);
        setSortDirection(nextDirection);
      }
      if (selectedMeasureId) {
        measureFilterExploreSorted({
          measureId: selectedMeasureId,
          sortColumn: nextColumn,
          sortDirection: nextDirection,
        });
      }
    },
    [sortColumn, sortDirection, selectedMeasureId],
  );

  const handlePresetSort = useCallback(
    (column: PresetSortColumn) => {
      const sameKind = presetSortColumn.kind === column.kind;
      const sameMeasure =
        column.kind === "measure" &&
        presetSortColumn.kind === "measure" &&
        presetSortColumn.measure_id === column.measure_id;
      if (sameKind && (column.kind !== "measure" || sameMeasure)) {
        setPresetSortDirection((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setPresetSortColumn(column);
        setPresetSortDirection(column.kind === "measure" ? "desc" : "asc");
      }
    },
    [presetSortColumn],
  );

  const handleClearFilters = useCallback(() => {
    setStateFilter(null);
    setSubtypeFilter(null);
    setNameSearch("");
  }, []);

  // Measures applicable to the active provider type (manifest contains both).
  const visibleMeasures = useMemo(() => {
    if (!manifest) return [];
    return manifest.measures.filter((m) => manifestMatches(m, providerType));
  }, [manifest, providerType]);

  // Presets for the active provider type.
  const visiblePresets = useMemo(
    () => FILTER_EXPLORE_PRESETS.filter((p) => p.provider_type === providerType),
    [providerType],
  );

  const selectedManifest = useMemo(() => {
    if (!selectedMeasureId || !manifest) return null;
    return manifest.measures.find((m) => m.measure_id === selectedMeasureId) ?? null;
  }, [selectedMeasureId, manifest]);

  const selectedPreset = useMemo(() => findPreset(selectedPresetId), [selectedPresetId]);

  // Single-measure mode: filter dropdown options + filtered rows.
  const stateOptionsSM = useMemo(() => {
    if (!indexFile) return [] as string[];
    const set = new Set<string>();
    for (const r of indexFile.rows) if (r.state) set.add(r.state);
    return Array.from(set).sort();
  }, [indexFile]);

  const subtypeOptionsSM = useMemo(() => {
    if (!indexFile) return [] as string[];
    const set = new Set<string>();
    for (const r of indexFile.rows) if (r.provider_subtype) set.add(r.provider_subtype);
    return Array.from(set).sort();
  }, [indexFile]);

  const filteredRowsSM = useMemo<MeasureIndexRow[]>(() => {
    if (!indexFile) return [];
    const normalizedName = nameSearch.trim().toLowerCase();
    return indexFile.rows.filter((r) => {
      if (stateFilter && r.state !== stateFilter) return false;
      if (subtypeFilter && r.provider_subtype !== subtypeFilter) return false;
      if (normalizedName && !r.name.toLowerCase().includes(normalizedName)) return false;
      return true;
    });
  }, [indexFile, stateFilter, subtypeFilter, nameSearch]);

  const hasActiveFilter = stateFilter !== null || subtypeFilter !== null || nameSearch !== "";

  const nationalAvgSM = useMemo<number | null>(() => {
    if (!indexFile) return null;
    for (const r of indexFile.rows) if (r.national_avg !== null) return r.national_avg;
    return null;
  }, [indexFile]);

  const dominantPeriodSM = useMemo<string | null>(() => {
    if (!indexFile) return null;
    const counts = new Map<string, number>();
    for (const r of indexFile.rows) {
      counts.set(r.period_label, (counts.get(r.period_label) ?? 0) + 1);
    }
    let best: string | null = null;
    let bestCount = 0;
    for (const [label, count] of counts) {
      if (count > bestCount) {
        best = label;
        bestCount = count;
      }
    }
    return best;
  }, [indexFile]);

  // Preset mode: merged rows, filter options, filtered rows.
  const presetMergedRows = useMemo<PresetMergedRow[]>(() => {
    if (!presetFiles) return [];
    return mergePresetIndexes(presetFiles);
  }, [presetFiles]);

  const stateOptionsP = useMemo(() => {
    const set = new Set<string>();
    for (const r of presetMergedRows) if (r.state) set.add(r.state);
    return Array.from(set).sort();
  }, [presetMergedRows]);

  const subtypeOptionsP = useMemo(() => {
    const set = new Set<string>();
    for (const r of presetMergedRows) if (r.provider_subtype) set.add(r.provider_subtype);
    return Array.from(set).sort();
  }, [presetMergedRows]);

  const filteredPresetRows = useMemo(() => {
    const normalizedName = nameSearch.trim().toLowerCase();
    return presetMergedRows.filter((r) => {
      if (stateFilter && r.state !== stateFilter) return false;
      if (subtypeFilter && r.provider_subtype !== subtypeFilter) return false;
      if (normalizedName && !r.name.toLowerCase().includes(normalizedName)) return false;
      return true;
    });
  }, [presetMergedRows, stateFilter, subtypeFilter, nameSearch]);

  // ──────────────────────────────────────────────────────────────────
  // Render branches

  if (manifestError) {
    return (
      <article>
        <ProviderTypeTabs providerType={providerType} />
        <h1 className="text-xl font-semibold text-gray-900">{heading}</h1>
        <p className="mt-2 text-sm text-gray-500">{FILTER_EXPLORE_LOAD_ERROR}</p>
      </article>
    );
  }

  if (!manifest) {
    return (
      <article>
        <ProviderTypeTabs providerType={providerType} />
        <h1 className="text-xl font-semibold text-gray-900">{heading}</h1>
        <p className="mt-2 text-sm text-gray-500">{FILTER_EXPLORE_LOADING}</p>
      </article>
    );
  }

  return (
    <article>
      <ProviderTypeTabs providerType={providerType} />
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">{heading}</h1>
        <p className="mt-1 max-w-3xl text-sm text-gray-600">{subheading}</p>
      </header>

      <div className="lg:flex lg:gap-6">
        <MeasurePicker
          measures={visibleMeasures}
          presets={visiblePresets}
          selectedMeasureId={selectedMeasureId}
          selectedPresetId={selectedPresetId}
          onSelectMeasure={handleSelectMeasure}
          onSelectPreset={handleSelectPreset}
        />

        <section className="mt-6 min-w-0 flex-1 lg:mt-0">
          {!selectedMeasureId && !selectedPresetId && (
            <div className="rounded border border-dashed border-gray-300 bg-gray-50 px-6 py-12 text-center">
              <p className="text-sm text-gray-600">{emptyState}</p>
            </div>
          )}

          {/* Single-measure mode */}
          {selectedMeasureId && indexLoading && (
            <p className="text-sm text-gray-500">{FILTER_EXPLORE_LOADING}</p>
          )}
          {selectedMeasureId && indexError && (
            <p className="text-sm text-gray-500">{FILTER_EXPLORE_LOAD_ERROR}</p>
          )}
          {selectedMeasureId && indexFile && selectedManifest && (
            <SelectedMeasurePanel
              providerType={providerType}
              emptyResultsText={emptyResults}
              indexFile={indexFile}
              manifestEntry={selectedManifest}
              filteredRows={filteredRowsSM}
              stateOptions={stateOptionsSM}
              subtypeOptions={subtypeOptionsSM}
              stateFilter={stateFilter}
              subtypeFilter={subtypeFilter}
              nameSearch={nameSearch}
              hasActiveFilter={hasActiveFilter}
              onStateChange={setStateFilter}
              onSubtypeChange={setSubtypeFilter}
              onNameChange={setNameSearch}
              onClear={handleClearFilters}
              sortColumn={sortColumn}
              sortDirection={sortDirection}
              onSort={handleSort}
              nationalAvg={nationalAvgSM}
              dominantPeriod={dominantPeriodSM}
              dataAsOf={manifest.generated_at}
            />
          )}

          {/* Preset mode */}
          {selectedPresetId && presetLoading && (
            <p className="text-sm text-gray-500">{FILTER_EXPLORE_PRESET_LOADING}</p>
          )}
          {selectedPresetId && presetError && (
            <p className="text-sm text-gray-500">{presetError}</p>
          )}
          {selectedPresetId && selectedPreset && presetFiles && presetFiles.length > 0 && (
            <PresetPanel
              providerType={providerType}
              emptyResultsText={emptyResults}
              preset={selectedPreset}
              measureFiles={presetFiles}
              filteredRows={filteredPresetRows}
              totalRows={presetMergedRows.length}
              stateOptions={stateOptionsP}
              subtypeOptions={subtypeOptionsP}
              stateFilter={stateFilter}
              subtypeFilter={subtypeFilter}
              nameSearch={nameSearch}
              hasActiveFilter={hasActiveFilter}
              onStateChange={setStateFilter}
              onSubtypeChange={setSubtypeFilter}
              onNameChange={setNameSearch}
              onClear={handleClearFilters}
              sortColumn={presetSortColumn}
              sortDirection={presetSortDirection}
              onSort={handlePresetSort}
              dataAsOf={manifest.generated_at}
            />
          )}
        </section>
      </div>
    </article>
  );
}

// ─── Single-measure panel ────────────────────────────────────────────

interface SelectedMeasurePanelProps {
  providerType: FilterExploreProviderType;
  emptyResultsText: string;
  indexFile: MeasureIndexFile;
  manifestEntry: MeasureManifestEntry;
  filteredRows: MeasureIndexRow[];
  stateOptions: string[];
  subtypeOptions: string[];
  stateFilter: string | null;
  subtypeFilter: string | null;
  nameSearch: string;
  hasActiveFilter: boolean;
  onStateChange: (s: string | null) => void;
  onSubtypeChange: (s: string | null) => void;
  onNameChange: (s: string) => void;
  onClear: () => void;
  sortColumn: SortColumn;
  sortDirection: SortDirection;
  onSort: (col: SortColumn) => void;
  nationalAvg: number | null;
  dominantPeriod: string | null;
  dataAsOf: string;
}

function SelectedMeasurePanel({
  providerType,
  emptyResultsText,
  indexFile,
  manifestEntry,
  filteredRows,
  stateOptions,
  subtypeOptions,
  stateFilter,
  subtypeFilter,
  nameSearch,
  hasActiveFilter,
  onStateChange,
  onSubtypeChange,
  onNameChange,
  onClear,
  sortColumn,
  sortDirection,
  onSort,
  nationalAvg,
  dominantPeriod,
  dataAsOf,
}: SelectedMeasurePanelProps): React.JSX.Element {
  const showSES =
    manifestEntry.ses_sensitivity === "HIGH" || manifestEntry.ses_sensitivity === "MODERATE";

  const directionPill =
    manifestEntry.direction === "LOWER_IS_BETTER"
      ? "CMS: lower is better"
      : manifestEntry.direction === "HIGHER_IS_BETTER"
        ? "CMS: higher is better"
        : null;

  const groupLabel =
    MEASURE_GROUP_DISPLAY_NAMES[manifestEntry.measure_group] ?? manifestEntry.measure_group;

  const totalReporting = indexFile.rows.length;
  const visibleCount = filteredRows.length;

  return (
    <div className="space-y-4">
      <header className="rounded border border-gray-200 bg-white px-4 py-3">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 className="text-lg font-semibold text-gray-900">
            {manifestEntry.measure_name ?? manifestEntry.measure_id}
          </h2>
          <span className="text-xs uppercase tracking-wide text-gray-400">{groupLabel}</span>
          {manifestEntry.tail_risk_flag && (
            <span className="rounded border border-gray-300 bg-gray-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-gray-600">
              Tail risk
            </span>
          )}
          {directionPill && (
            <span className="rounded border border-gray-300 bg-gray-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-gray-600">
              {directionPill}
            </span>
          )}
        </div>
        {manifestEntry.measure_plain_language && (
          <p className="mt-2 max-w-3xl text-sm text-gray-700">
            {manifestEntry.measure_plain_language}
          </p>
        )}
        {dominantPeriod && (
          <p className="mt-1 text-xs text-gray-500">
            Reporting period: {formatPeriodLabel(dominantPeriod)}
          </p>
        )}
        {manifestEntry.cms_measure_definition && (
          <details className="mt-2">
            <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-700">
              CMS measure definition
            </summary>
            <p className="mt-2 max-w-3xl whitespace-pre-line text-xs leading-relaxed text-gray-600">
              CMS defines this measure as: {manifestEntry.cms_measure_definition}
            </p>
          </details>
        )}
      </header>

      <MultipleComparisonDisclosure />
      {showSES && <SESDisclosureBlock />}

      {indexFile.unit && (
        <MeasureIndexHistogram
          rows={filteredRows}
          unit={indexFile.unit}
          nationalAvg={nationalAvg}
          providerType={providerType}
        />
      )}

      <FilterExploreFilters
        states={stateOptions}
        subtypes={subtypeOptions}
        stateValue={stateFilter}
        subtypeValue={subtypeFilter}
        nameValue={nameSearch}
        onStateChange={onStateChange}
        onSubtypeChange={onSubtypeChange}
        onNameChange={onNameChange}
        onClear={onClear}
        visibleCount={visibleCount}
        totalCount={totalReporting}
        hasActiveFilter={hasActiveFilter}
        providerType={providerType}
      />

      {filteredRows.length === 0 ? (
        <p className="rounded border border-dashed border-gray-300 bg-gray-50 px-4 py-8 text-center text-sm text-gray-500">
          {emptyResultsText}
        </p>
      ) : (
        <FilterExploreTable
          rows={filteredRows}
          unit={indexFile.unit ?? ""}
          providerType={providerType}
          sortColumn={sortColumn}
          sortDirection={sortDirection}
          onSort={onSort}
        />
      )}

      <AttributionLine
        sourceDatasetName={manifestEntry.source_dataset_name}
        periodLabel={dominantPeriod ?? ""}
        providerLastUpdated={dataAsOf}
      />
    </div>
  );
}

// ─── Preset panel ────────────────────────────────────────────────────

interface PresetPanelProps {
  providerType: FilterExploreProviderType;
  emptyResultsText: string;
  preset: FilterExplorePreset;
  measureFiles: MeasureIndexFile[];
  filteredRows: PresetMergedRow[];
  totalRows: number;
  stateOptions: string[];
  subtypeOptions: string[];
  stateFilter: string | null;
  subtypeFilter: string | null;
  nameSearch: string;
  hasActiveFilter: boolean;
  onStateChange: (s: string | null) => void;
  onSubtypeChange: (s: string | null) => void;
  onNameChange: (s: string) => void;
  onClear: () => void;
  sortColumn: PresetSortColumn;
  sortDirection: PresetSortDirection;
  onSort: (col: PresetSortColumn) => void;
  dataAsOf: string;
}

function PresetPanel({
  providerType,
  emptyResultsText,
  preset,
  measureFiles,
  filteredRows,
  totalRows,
  stateOptions,
  subtypeOptions,
  stateFilter,
  subtypeFilter,
  nameSearch,
  hasActiveFilter,
  onStateChange,
  onSubtypeChange,
  onNameChange,
  onClear,
  sortColumn,
  sortDirection,
  onSort,
  dataAsOf,
}: PresetPanelProps): React.JSX.Element {
  const showSES = measureFiles.some(
    (f) => {
      // We don't carry ses_sensitivity in MeasureIndexFile, so derive from the
      // manifest entry implicitly: any HIGH/MODERATE measure in the preset
      // should fire the disclosure. Cheaper: just always show SES on the
      // mortality and readmission presets, which are HIGH-sensitive by spec.
      const mid = f.measure_id;
      return (
        mid.startsWith("MORT_") ||
        mid.startsWith("READM_") ||
        mid.startsWith("EDAC_") ||
        mid === "PSI_90"
      );
    },
  );

  // Unique source datasets across the preset, for combined attribution.
  const datasets = useMemo(() => {
    const seen = new Map<string, { name: string; period: string }>();
    for (const f of measureFiles) {
      const sample = f.rows.find((r) => r.period_label) ?? f.rows[0];
      if (!sample) continue;
      const key = f.source_dataset_name;
      if (!seen.has(key)) {
        seen.set(key, { name: f.source_dataset_name, period: sample.period_label });
      }
    }
    return Array.from(seen.values());
  }, [measureFiles]);

  return (
    <div className="space-y-4">
      <header className="rounded border border-gray-200 bg-white px-4 py-3">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 className="text-lg font-semibold text-gray-900">{preset.label}</h2>
          <span className="text-xs uppercase tracking-wide text-gray-400">
            {preset.measure_ids.length} measures
          </span>
          {preset.tail_risk && (
            <span className="rounded border border-gray-300 bg-gray-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-gray-600">
              Tail risk
            </span>
          )}
        </div>
        <p className="mt-2 max-w-3xl text-sm text-gray-700">{preset.description}</p>
      </header>

      <MultipleComparisonDisclosure />
      {showSES && <SESDisclosureBlock />}

      <FilterExploreFilters
        states={stateOptions}
        subtypes={subtypeOptions}
        stateValue={stateFilter}
        subtypeValue={subtypeFilter}
        nameValue={nameSearch}
        onStateChange={onStateChange}
        onSubtypeChange={onSubtypeChange}
        onNameChange={onNameChange}
        onClear={onClear}
        visibleCount={filteredRows.length}
        totalCount={totalRows}
        hasActiveFilter={hasActiveFilter}
        providerType={providerType}
      />

      {filteredRows.length === 0 ? (
        <p className="rounded border border-dashed border-gray-300 bg-gray-50 px-4 py-8 text-center text-sm text-gray-500">
          {emptyResultsText}
        </p>
      ) : (
        <PresetTable
          rows={filteredRows}
          measureFiles={measureFiles}
          providerType={providerType}
          sharedSampleMeasureId={preset.shared_sample_measure_id}
          sharedSampleLabel={preset.shared_sample_label}
          sortColumn={sortColumn}
          sortDirection={sortDirection}
          onSort={onSort}
        />
      )}

      <p className="text-xs text-gray-500">
        {FILTER_EXPLORE_COUNT_SUMMARY(filteredRows.length, totalRows, providerType)} included.
      </p>

      {/* Combined attribution — one line per source dataset in the preset. */}
      <div className="border-t border-gray-200 pt-3">
        {datasets.map((d) => (
          <p key={d.name} className="text-xs text-gray-500">
            Source: CMS {d.name}, {d.period}.
          </p>
        ))}
        <p className="mt-1 text-xs text-gray-500">
          Data reflects CMS reporting as of{" "}
          {new Date(dataAsOf).toLocaleDateString("en-US", {
            year: "numeric",
            month: "long",
            day: "numeric",
          })}
          .
        </p>
      </div>
    </div>
  );
}

// ─── Provider type tabs ──────────────────────────────────────────────
//
// Two-route design: /filter-explore/ (hospitals) and
// /filter-explore/nursing-home/ (nursing homes). Tabs at the top of the page
// let users switch with a single click. URL state for filters does not carry
// across the navigation (different applicable measures, different presets).

function ProviderTypeTabs({
  providerType,
}: {
  providerType: FilterExploreProviderType;
}): React.JSX.Element {
  const baseClass =
    "inline-block rounded-t border-x border-t px-4 py-2 text-sm font-medium";
  const active = "border-gray-300 bg-white text-gray-900";
  const inactive =
    "border-transparent bg-gray-50 text-gray-500 hover:bg-gray-100 hover:text-gray-800";
  return (
    <nav
      aria-label="Provider type"
      className="mb-4 flex gap-1 border-b border-gray-300"
    >
      <a
        href="/filter-explore/"
        className={`${baseClass} ${providerType === "HOSPITAL" ? active : inactive}`}
        aria-current={providerType === "HOSPITAL" ? "page" : undefined}
      >
        Hospitals
      </a>
      <a
        href="/filter-explore/nursing-home/"
        className={`${baseClass} ${providerType === "NURSING_HOME" ? active : inactive}`}
        aria-current={providerType === "NURSING_HOME" ? "page" : undefined}
      >
        Nursing Homes
      </a>
    </nav>
  );
}

export interface FilterExploreClientProps {
  providerType: FilterExploreProviderType;
}

export function FilterExploreClient({
  providerType,
}: FilterExploreClientProps): React.JSX.Element {
  // SentryErrorBoundary captures runtime fetch and render failures —
  // /filter-explore is one of two static-export exceptions that fetches
  // CDN JSON at runtime (manifest + per-measure index files), so render-
  // time errors are real production risk.
  return (
    <SentryErrorBoundary scope="filter-explore">
      <Suspense
        fallback={
          <div className="py-12 text-center text-sm text-gray-500">
            {FILTER_EXPLORE_LOADING}
          </div>
        }
      >
        <FilterExploreContent providerType={providerType} />
      </Suspense>
    </SentryErrorBoundary>
  );
}
