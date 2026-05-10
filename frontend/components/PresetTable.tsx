// Multi-measure table for /filter-explore preset views.
//
// Layout:
//   Hospital | State | Measure 1 | Measure 2 | ... | Measure N
// One row per hospital. Sortable by any column. Suppressed/not-reported
// values render as a status pill, never as zero or blank. Click any
// measure column header to sort by that column; clicking a measure
// label routes to the single-measure detail view.
//
// Tradeoffs vs single-measure mode:
//   - Wide format means each cell shows only the value (no inline CI,
//     no period). The header carries the period; the row links out
//     to the per-hospital detail page for the full context.
//   - Suppressed/not-reported rows still sort to the bottom for the
//     active sort column.
//   - Virtualization here uses windowing on rows; column count is
//     bounded by the preset (≤ 13 measures so far).

"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  DIRECTION_PHRASE,
  FILTER_EXPLORE_FOOTNOTE_COUNT,
  FILTER_EXPLORE_HOSPITAL_LABEL,
  FILTER_EXPLORE_STATE_COL_LABEL,
  MEASURE_SHORT_LABEL,
  SMALL_SAMPLE_THRESHOLD,
  UNIT_DESCRIPTION,
} from "@/lib/constants";
import type { MeasureIndexFile, MeasureIndexRow } from "@/lib/measure-index";
import { rowStatus } from "@/lib/measure-index";
import { formatPeriodLabel, formatValue, providerSlug, titleCase } from "@/lib/utils";

const ROW_HEIGHT = 44;
const VIEWPORT_BUFFER_ROWS = 8;

export interface PresetMergedRow {
  ccn: string;
  name: string;
  city: string | null;
  state: string | null;
  provider_subtype: string | null;
  ownership_type: string | null;
  // measure_id → row data for this hospital, or undefined if hospital
  // doesn't appear in that measure's index file
  cells: Record<string, MeasureIndexRow | undefined>;
}

export type PresetSortColumn =
  | { kind: "name" }
  | { kind: "state" }
  | { kind: "shared_sample" }
  | { kind: "measure"; measure_id: string };

export type PresetSortDirection = "asc" | "desc";

interface PresetTableProps {
  rows: PresetMergedRow[];
  measureFiles: ReadonlyArray<MeasureIndexFile>;
  /** Drives per-row link target: "/hospital/{ccn}/" vs "/nursing-home/{ccn}/". */
  providerType?: "HOSPITAL" | "NURSING_HOME";
  /** When set, lift the sample_size from this measure's cell into a dedicated
   *  shared-sample column rendered before the measure columns. */
  sharedSampleMeasureId?: string;
  /** Header label for the shared-sample column. */
  sharedSampleLabel?: string;
  sortColumn: PresetSortColumn;
  sortDirection: PresetSortDirection;
  onSort: (col: PresetSortColumn) => void;
}

function presetRowHref(row: PresetMergedRow, providerType: "HOSPITAL" | "NURSING_HOME"): string {
  const slug = providerSlug(row.name, row.city, row.state, row.ccn);
  return providerType === "NURSING_HOME"
    ? `/nursing-home/${slug}/`
    : `/hospital/${slug}/`;
}

/**
 * Merge per-measure index files into one row per hospital. Returns rows
 * keyed by CCN, including hospitals that report at least one measure
 * in the preset. Hospitals that report none are dropped.
 */
export function mergePresetIndexes(
  measureFiles: ReadonlyArray<MeasureIndexFile>,
): PresetMergedRow[] {
  const map = new Map<string, PresetMergedRow>();
  for (const file of measureFiles) {
    for (const r of file.rows) {
      let merged = map.get(r.ccn);
      if (!merged) {
        merged = {
          ccn: r.ccn,
          name: r.name,
          city: r.city,
          state: r.state,
          provider_subtype: r.provider_subtype,
          ownership_type: r.ownership_type,
          cells: {},
        };
        map.set(r.ccn, merged);
      }
      merged.cells[file.measure_id] = r;
    }
  }
  return Array.from(map.values());
}

function compareNullable<T>(
  a: T | null | undefined,
  b: T | null | undefined,
  cmp: (x: T, y: T) => number,
  direction: PresetSortDirection,
): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1; // nulls sort to bottom regardless
  if (b == null) return -1;
  const r = cmp(a, b);
  return direction === "asc" ? r : -r;
}

function cellSortValue(row: PresetMergedRow, measure_id: string): number | null {
  const cell = row.cells[measure_id];
  if (!cell) return null;
  if (cell.suppressed || cell.not_reported) return null;
  return cell.numeric_value;
}

function sharedSampleValue(
  row: PresetMergedRow,
  measureId: string | undefined,
): number | null {
  if (!measureId) return null;
  return row.cells[measureId]?.sample_size ?? null;
}

export function sortPresetRows(
  rows: PresetMergedRow[],
  column: PresetSortColumn,
  direction: PresetSortDirection,
  sharedSampleMeasureId?: string,
): PresetMergedRow[] {
  const numCmp = (a: number, b: number): number => a - b;
  const strCmp = (a: string, b: string): number => a.localeCompare(b);

  return [...rows].sort((a, b) => {
    let r = 0;
    switch (column.kind) {
      case "name":
        r = compareNullable(a.name, b.name, strCmp, direction);
        break;
      case "state":
        r = compareNullable(a.state, b.state, strCmp, direction);
        break;
      case "shared_sample": {
        const va = sharedSampleValue(a, sharedSampleMeasureId);
        const vb = sharedSampleValue(b, sharedSampleMeasureId);
        r = compareNullable(va, vb, numCmp, direction);
        break;
      }
      case "measure": {
        const va = cellSortValue(a, column.measure_id);
        const vb = cellSortValue(b, column.measure_id);
        r = compareNullable(va, vb, numCmp, direction);
        break;
      }
    }
    if (r !== 0) return r;
    return a.name.localeCompare(b.name);
  });
}

interface CellRenderProps {
  cell: MeasureIndexRow | undefined;
  unit: string;
}

function PresetCell({ cell, unit }: CellRenderProps): React.JSX.Element {
  if (!cell) {
    return <span className="text-xs text-gray-300">·</span>;
  }
  const status = rowStatus(cell);
  if (status === "suppressed") {
    return (
      <span
        className="rounded bg-gray-100 px-1 py-0.5 text-[10px] uppercase tracking-wide text-gray-500"
        title={cell.suppression_reason ?? "Suppressed by CMS."}
      >
        S
      </span>
    );
  }
  if (status === "not_reported") {
    return (
      <span
        className="rounded bg-gray-100 px-1 py-0.5 text-[10px] uppercase tracking-wide text-gray-500"
        title={cell.not_reported_reason ?? "Not reported by hospital."}
      >
        NR
      </span>
    );
  }
  const valueText =
    cell.score_text !== null
      ? cell.score_text
      : cell.numeric_value !== null
        ? formatValue(cell.numeric_value, unit)
        : "—";

  // Compose tooltip with sample size, interval, footnotes — full context
  // is one hover away even though the cell is compact.
  const lines: string[] = [];
  if (cell.sample_size !== null && !cell.count_suppressed) {
    lines.push(`Cases: ${cell.sample_size.toLocaleString("en-US")}`);
  }
  if (cell.ci_lower !== null && cell.ci_upper !== null) {
    lines.push(
      `Interval: ${formatValue(cell.ci_lower, unit)} – ${formatValue(cell.ci_upper, unit)}`,
    );
  }
  if (cell.footnote_codes && cell.footnote_codes.length > 0) {
    const codes = cell.footnote_codes;
    const texts = cell.footnote_text ?? [];
    lines.push(FILTER_EXPLORE_FOOTNOTE_COUNT(codes.length));
    for (let i = 0; i < codes.length; i++) {
      lines.push(`  • ${codes[i]}${texts[i] ? `: ${texts[i]}` : ""}`);
    }
  }
  const isSmallSample =
    cell.sample_size !== null &&
    cell.sample_size > 0 &&
    cell.sample_size < SMALL_SAMPLE_THRESHOLD;

  const flags: string[] = [];
  if (cell.footnote_codes && cell.footnote_codes.length > 0) flags.push("ƒ");
  if (cell.count_suppressed) flags.push("·");
  if (isSmallSample) flags.push("⚠");

  return (
    <span
      className="inline-flex items-baseline gap-1 tabular-nums"
      title={lines.length > 0 ? lines.join("\n") : undefined}
    >
      <span className="font-semibold text-gray-800">{valueText}</span>
      {flags.length > 0 && <span className="text-[10px] text-gray-400">{flags.join("")}</span>}
    </span>
  );
}

function shortLabelFor(file: MeasureIndexFile): string {
  return MEASURE_SHORT_LABEL[file.measure_id] ?? file.measure_name ?? file.measure_id;
}

function buildHeaderTooltip(file: MeasureIndexFile, period: string): string {
  const lines: string[] = [];
  const short = shortLabelFor(file);
  const full = file.measure_name ?? file.measure_id;
  if (full !== short) {
    lines.push(short);
    lines.push(full);
  } else {
    lines.push(full);
  }
  if (period) lines.push(formatPeriodLabel(period));
  if (file.direction === "LOWER_IS_BETTER") lines.push(DIRECTION_PHRASE.LOWER_IS_BETTER);
  else if (file.direction === "HIGHER_IS_BETTER") lines.push(DIRECTION_PHRASE.HIGHER_IS_BETTER);
  if (file.unit) {
    const desc = UNIT_DESCRIPTION[file.unit];
    lines.push(desc ? `Scale: ${desc}` : `Scale: ${file.unit}`);
  }
  return lines.join("\n");
}

function MeasureHeader({
  file,
  active,
  direction,
  showPeriod,
  onClick,
}: {
  file: MeasureIndexFile;
  active: boolean;
  direction: PresetSortDirection;
  showPeriod: boolean;
  onClick: () => void;
}): React.JSX.Element {
  const label = shortLabelFor(file);
  const period = file.rows.find((r) => r.period_label)?.period_label ?? "";
  const arrow = active ? (direction === "asc" ? "▲" : "▼") : "";
  const tooltip = buildHeaderTooltip(file, period);
  // Tiny inline direction glyph — only when CMS publishes a direction. ↓ for
  // lower-is-better, ↑ for higher-is-better. Renders gray and small so it
  // doesn't compete with the measure label, but answers the question
  // "which way is good?" at a glance for non-obvious measures.
  const dirGlyph =
    file.direction === "LOWER_IS_BETTER"
      ? "↓"
      : file.direction === "HIGHER_IS_BETTER"
        ? "↑"
        : "";
  const dirAria =
    file.direction === "LOWER_IS_BETTER"
      ? "CMS: lower is better"
      : file.direction === "HIGHER_IS_BETTER"
        ? "CMS: higher is better"
        : "";
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full flex-col items-end justify-end px-2 py-1.5 text-right text-[11px] leading-tight ${
        active ? "bg-gray-100 text-gray-900" : "text-gray-500 hover:bg-gray-50 hover:text-gray-800"
      }`}
      title={tooltip}
    >
      <span className="flex items-baseline gap-1 font-semibold">
        <span>{label}</span>
        {dirGlyph && (
          <span
            className="text-[10px] text-gray-400"
            aria-label={dirAria}
            title={dirAria}
          >
            {dirGlyph}
          </span>
        )}
        <span className="text-[10px] text-gray-400">{arrow}</span>
      </span>
      {showPeriod && period && (
        <span className="mt-0.5 text-[10px] font-normal text-gray-400">
          {formatPeriodLabel(period)}
        </span>
      )}
    </button>
  );
}

export function PresetTable({
  rows,
  measureFiles,
  providerType = "HOSPITAL",
  sharedSampleMeasureId,
  sharedSampleLabel = "Sample",
  sortColumn,
  sortDirection,
  onSort,
}: PresetTableProps): React.JSX.Element {
  const sorted = useMemo(
    () => sortPresetRows(rows, sortColumn, sortDirection, sharedSampleMeasureId),
    [rows, sortColumn, sortDirection, sharedSampleMeasureId],
  );

  // If every measure shares the same period, render it once above the table
  // and skip per-column period subtitles. Otherwise show per-column periods.
  const periods = measureFiles.map(
    (f) => f.rows.find((r) => r.period_label)?.period_label ?? "",
  );
  const sharedPeriod =
    periods.length > 0 && periods.every((p) => p === periods[0]) ? periods[0] : null;

  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(600);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    setScrollTop(el.scrollTop);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    setViewportHeight(el.clientHeight);
    const observer = new ResizeObserver(() => setViewportHeight(el.clientHeight));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const startIdx = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - VIEWPORT_BUFFER_ROWS);
  const visibleRowCount = Math.ceil(viewportHeight / ROW_HEIGHT) + VIEWPORT_BUFFER_ROWS * 2;
  const endIdx = Math.min(sorted.length, startIdx + visibleRowCount);
  const visibleRows = sorted.slice(startIdx, endIdx);
  const totalHeight = sorted.length * ROW_HEIGHT;
  const offsetY = startIdx * ROW_HEIGHT;

  // Grid column template: hospital | state | (shared-sample) | one per measure.
  // Numeric columns get a flexible minmax — wide enough for short labels,
  // shrink-to-fit otherwise. Shared-sample column is fixed at 90px.
  const sharedSampleCol = sharedSampleMeasureId ? "90px " : "";
  const gridTemplate = `minmax(200px, 1.6fr) 50px ${sharedSampleCol}${measureFiles.map(() => "minmax(96px, 1fr)").join(" ")}`;

  const isMeasureSorted = (mid: string): boolean =>
    sortColumn.kind === "measure" && sortColumn.measure_id === mid;
  const isNameSorted = sortColumn.kind === "name";
  const isStateSorted = sortColumn.kind === "state";
  const isSharedSampleSorted = sortColumn.kind === "shared_sample";

  // Total minimum width of the grid — used to drive horizontal scroll when
  // the available container width is narrower than the sum of column minimums.
  // Hospital(200) + State(50) + (shared sample 90) + N × measure(96).
  const minTableWidth =
    200 + 50 + (sharedSampleMeasureId ? 90 : 0) + measureFiles.length * 96;

  return (
    <div className="rounded border border-gray-200 bg-white">
      {sharedPeriod && (
        <div className="border-b border-gray-200 bg-gray-50 px-3 py-1.5 text-[11px] text-gray-500">
          Reporting period: {formatPeriodLabel(sharedPeriod)}
        </div>
      )}

      {/* Combined horizontal + vertical scroll container.
          Header is sticky-top inside this container so it stays visible during
          vertical scroll, while moving with horizontal scroll alongside the body. */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{ maxHeight: "min(70vh, 720px)", overflow: "auto" }}
        role="grid"
        aria-rowcount={sorted.length}
      >
        <div style={{ minWidth: minTableWidth }}>
          {/* Sticky header */}
          <div
            className="sticky top-0 z-10 grid border-b border-gray-200 bg-gray-50"
            style={{ gridTemplateColumns: gridTemplate }}
          >
            <button
              type="button"
              onClick={() => onSort({ kind: "name" })}
              className={`sticky left-0 z-20 flex items-center gap-1 border-r border-gray-200 bg-gray-50 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide ${
                isNameSorted ? "text-gray-900" : "text-gray-500"
              } hover:text-gray-900`}
            >
              {FILTER_EXPLORE_HOSPITAL_LABEL}
              <span className="text-[10px] text-gray-400">
                {isNameSorted ? (sortDirection === "asc" ? "▲" : "▼") : ""}
              </span>
            </button>
            <button
              type="button"
              onClick={() => onSort({ kind: "state" })}
              className={`flex items-center gap-1 px-2 py-2 text-left text-xs font-semibold uppercase tracking-wide ${
                isStateSorted ? "text-gray-900" : "text-gray-500"
              } hover:text-gray-900`}
            >
              {FILTER_EXPLORE_STATE_COL_LABEL}
              <span className="text-[10px] text-gray-400">
                {isStateSorted ? (sortDirection === "asc" ? "▲" : "▼") : ""}
              </span>
            </button>
            {sharedSampleMeasureId && (
              <button
                type="button"
                onClick={() => onSort({ kind: "shared_sample" })}
                className={`flex items-center justify-end gap-1 px-2 py-2 text-right text-xs font-semibold uppercase tracking-wide ${
                  isSharedSampleSorted ? "text-gray-900" : "text-gray-500"
                } hover:text-gray-900`}
                title="Sample size shared across every column in this preset (e.g., HCAHPS surveys completed at this hospital)."
              >
                {sharedSampleLabel}
                <span className="text-[10px] text-gray-400">
                  {isSharedSampleSorted ? (sortDirection === "asc" ? "▲" : "▼") : ""}
                </span>
              </button>
            )}
            {measureFiles.map((f) => (
              <MeasureHeader
                key={f.measure_id}
                file={f}
                active={isMeasureSorted(f.measure_id)}
                direction={sortDirection}
                showPeriod={sharedPeriod === null}
                onClick={() => onSort({ kind: "measure", measure_id: f.measure_id })}
              />
            ))}
          </div>

          {/* Body — windowed render for performance. */}
          <div style={{ height: totalHeight, position: "relative" }}>
            <div style={{ transform: `translateY(${offsetY}px)` }}>
              {visibleRows.map((row, i) => {
                const idx = startIdx + i;
                return (
                  <div
                    key={`${row.ccn}-${idx}`}
                    className="group grid items-center border-b border-gray-100 px-0 py-0 text-sm"
                    style={{ gridTemplateColumns: gridTemplate, minHeight: ROW_HEIGHT }}
                    role="row"
                    aria-rowindex={idx + 2}
                  >
                    {/* Hospital name column locked to the left so it stays
                        visible during horizontal scroll. Background must be
                        opaque so scrolling content doesn't show through;
                        group-hover keeps the cell tinted alongside the row. */}
                    <div className="sticky left-0 z-10 border-r border-gray-100 bg-white px-3 py-2 group-hover:bg-gray-50">
                      <a
                        href={presetRowHref(row, providerType)}
                        className="block font-medium text-gray-800 underline-offset-2 hover:underline"
                      >
                        {titleCase(row.name)}
                      </a>
                      {row.city && (
                        <p className="text-xs text-gray-500">{titleCase(row.city)}</p>
                      )}
                    </div>
                    <div className="px-2 py-2 text-xs text-gray-600 group-hover:bg-gray-50">{row.state ?? "—"}</div>
                    {sharedSampleMeasureId && (() => {
                      // Shared-sample column: render the count from the chosen
                      // measure's cell. Use the existing small-sample threshold
                      // (⚠ at <30) for the visual flag rather than introducing a
                      // new <100 tier — the per-cell tooltip already carries the
                      // exact number.
                      const sample = sharedSampleValue(row, sharedSampleMeasureId);
                      const small =
                        sample !== null && sample > 0 && sample < SMALL_SAMPLE_THRESHOLD;
                      return (
                        <div
                          className="px-2 py-2 text-right text-sm tabular-nums text-gray-700 group-hover:bg-gray-50"
                          title={
                            sample !== null
                              ? `${sample.toLocaleString("en-US")} ${sharedSampleLabel.toLowerCase()}`
                              : "Sample not reported"
                          }
                        >
                          {sample !== null ? (
                            <span>
                              {sample.toLocaleString("en-US")}
                              {small && (
                                <span className="ml-1 text-[10px] text-gray-400" title="Small sample">⚠</span>
                              )}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400">—</span>
                          )}
                        </div>
                      );
                    })()}
                    {measureFiles.map((f) => (
                      <div key={f.measure_id} className="px-2 py-2 text-right group-hover:bg-gray-50">
                        <PresetCell cell={row.cells[f.measure_id]} unit={f.unit ?? ""} />
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Cell flag legend */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-gray-200 bg-gray-50 px-3 py-1.5 text-[11px] text-gray-500">
        <span><span className="font-semibold">S</span> = suppressed</span>
        <span><span className="font-semibold">NR</span> = not reported</span>
        <span><span className="font-semibold">ƒ</span> = footnote (hover)</span>
        <span><span className="font-semibold">⚠</span> = small sample (&lt;{SMALL_SAMPLE_THRESHOLD} cases)</span>
        <span><span className="font-semibold">·</span> = case count suppressed</span>
      </div>
    </div>
  );
}
