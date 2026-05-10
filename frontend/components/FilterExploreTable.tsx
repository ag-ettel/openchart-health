// Sortable, virtualized table for /filter-explore.
//
// Sort rules (do not violate — see legal-compliance.md § Positioning):
//   - The user controls sort order. The default on first measure load is
//     alphabetical by hospital name.
//   - When user sorts by Value, suppressed and not-reported rows always sort
//     to the bottom regardless of direction. They are not zero or blank.
//   - Stable sort: ties stay in alphabetical order.
//
// Display rules:
//   - Suppressed → "Suppressed" with reason.
//   - Not reported → "Not reported" with reason.
//   - Footnote codes shown as inline badges.
//   - count_suppressed → sample size renders "—" with tooltip.
//   - Each hospital name links to /hospital/{slug}/ where slug ends with the
//     6-digit CCN; see providerSlug() in lib/utils.ts.
//
// Virtualization: simple windowing (only render visible rows + buffer).

"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import {
  FILTER_EXPLORE_FOOTNOTE_COUNT,
  FILTER_EXPLORE_HOSPITAL_LABEL,
  FILTER_EXPLORE_INTERVAL_LABEL,
  FILTER_EXPLORE_PERIOD_NOTE,
  FILTER_EXPLORE_SAMPLE_SIZE_LABEL,
  FILTER_EXPLORE_STATE_COL_LABEL,
  FILTER_EXPLORE_STATUS_COUNT_SUPPRESSED,
  FILTER_EXPLORE_STATUS_LABEL,
  FILTER_EXPLORE_STATUS_NOT_REPORTED,
  FILTER_EXPLORE_STATUS_SUPPRESSED,
  FILTER_EXPLORE_VALUE_LABEL,
  SMALL_SAMPLE_THRESHOLD,
} from "@/lib/constants";
import type { MeasureIndexRow } from "@/lib/measure-index";
import { rowStatus } from "@/lib/measure-index";
import { formatPeriodLabel, formatValue, providerSlug, titleCase } from "@/lib/utils";

export type SortColumn = "name" | "state" | "value" | "sample_size";
export type SortDirection = "asc" | "desc";

interface FilterExploreTableProps {
  rows: MeasureIndexRow[];
  unit: string;
  /** Drives per-row link target: "/hospital/{ccn}/" vs "/nursing-home/{ccn}/". */
  providerType?: "HOSPITAL" | "NURSING_HOME";
  sortColumn: SortColumn;
  sortDirection: SortDirection;
  onSort: (column: SortColumn) => void;
}

function rowHref(row: MeasureIndexRow, providerType: "HOSPITAL" | "NURSING_HOME"): string {
  const slug = providerSlug(row.name, row.city, row.state, row.ccn);
  return providerType === "NURSING_HOME"
    ? `/nursing-home/${slug}/`
    : `/hospital/${slug}/`;
}

const ROW_HEIGHT = 56; // px — approximate; adjusted for content
const VIEWPORT_BUFFER_ROWS = 8; // render this many extra above/below viewport

function compareNullable<T>(
  a: T | null,
  b: T | null,
  compare: (x: T, y: T) => number,
  direction: SortDirection,
): number {
  // Nulls always sort to the bottom regardless of direction.
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  const r = compare(a, b);
  return direction === "asc" ? r : -r;
}

function formatRowValue(row: MeasureIndexRow, unit: string): string {
  if (row.score_text !== null) return row.score_text;
  if (row.numeric_value === null) return "—";
  return formatValue(row.numeric_value, unit);
}

function formatRowInterval(row: MeasureIndexRow, unit: string): string | null {
  if (row.ci_lower === null || row.ci_upper === null) return null;
  return `${formatValue(row.ci_lower, unit)} – ${formatValue(row.ci_upper, unit)}`;
}

function StatusCell({ row }: { row: MeasureIndexRow }): React.JSX.Element | null {
  const status = rowStatus(row);
  const badges: React.JSX.Element[] = [];

  if (status === "suppressed") {
    badges.push(
      <span
        key="suppressed"
        className="inline-flex items-center rounded border border-gray-300 bg-gray-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-gray-600"
        title={row.suppression_reason ?? undefined}
      >
        {FILTER_EXPLORE_STATUS_SUPPRESSED}
      </span>,
    );
  } else if (status === "not_reported") {
    badges.push(
      <span
        key="not-reported"
        className="inline-flex items-center rounded border border-gray-300 bg-gray-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-gray-600"
        title={row.not_reported_reason ?? undefined}
      >
        {FILTER_EXPLORE_STATUS_NOT_REPORTED}
      </span>,
    );
  }

  if (
    row.sample_size !== null &&
    row.sample_size > 0 &&
    row.sample_size < SMALL_SAMPLE_THRESHOLD &&
    !row.suppressed &&
    !row.not_reported
  ) {
    badges.push(
      <span
        key="small-sample"
        className="inline-flex items-center rounded border border-gray-300 bg-gray-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-gray-600"
        title={`Based on ${row.sample_size} cases. With this few cases, this rate is highly uncertain.`}
      >
        Small sample
      </span>,
    );
  }

  if (row.footnote_codes && row.footnote_codes.length > 0) {
    const codes = row.footnote_codes;
    const texts = row.footnote_text ?? [];
    const tooltip = codes
      .map((c, i) => `${c}${texts[i] ? `: ${texts[i]}` : ""}`)
      .join("\n");
    badges.push(
      <span
        key="footnotes"
        className="inline-flex items-center rounded border border-gray-300 bg-gray-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-gray-600"
        title={`${FILTER_EXPLORE_FOOTNOTE_COUNT(codes.length)}\n${tooltip}`}
      >
        Footnote {codes.length === 1 ? codes[0] : `×${codes.length}`}
      </span>,
    );
  }

  if (row.count_suppressed) {
    badges.push(
      <span
        key="count-suppressed"
        className="inline-flex items-center rounded border border-gray-300 bg-gray-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-gray-600"
        title={FILTER_EXPLORE_STATUS_COUNT_SUPPRESSED}
      >
        Counts hidden
      </span>,
    );
  }

  if (badges.length === 0) return null;
  return <div className="flex flex-wrap items-center gap-1">{badges}</div>;
}

function SortHeader({
  column,
  label,
  align,
  sortColumn,
  sortDirection,
  onSort,
}: {
  column: SortColumn;
  label: string;
  align: "left" | "right";
  sortColumn: SortColumn;
  sortDirection: SortDirection;
  onSort: (col: SortColumn) => void;
}): React.JSX.Element {
  const active = sortColumn === column;
  const arrow = active ? (sortDirection === "asc" ? "▲" : "▼") : "";
  return (
    <button
      type="button"
      onClick={() => onSort(column)}
      className={`flex w-full items-center gap-1 px-3 py-2 text-xs font-semibold uppercase tracking-wide ${
        active ? "text-gray-900" : "text-gray-500"
      } ${align === "right" ? "justify-end" : "justify-start"} hover:text-gray-900`}
    >
      <span>{label}</span>
      <span className="text-[10px] text-gray-400">{arrow}</span>
    </button>
  );
}

export function sortRows(
  rows: MeasureIndexRow[],
  column: SortColumn,
  direction: SortDirection,
): MeasureIndexRow[] {
  // Always partition: rows with displayable data first, then suppressed/not-reported,
  // regardless of sort direction. Within each partition, apply the sort.
  const reportable: MeasureIndexRow[] = [];
  const unreportable: MeasureIndexRow[] = [];
  for (const r of rows) {
    if (r.suppressed || r.not_reported) {
      unreportable.push(r);
    } else {
      reportable.push(r);
    }
  }

  const numCmp = (a: number, b: number): number => a - b;
  const strCmp = (a: string, b: string): number => a.localeCompare(b);

  const compareReportable = (a: MeasureIndexRow, b: MeasureIndexRow): number => {
    let r = 0;
    switch (column) {
      case "name":
        r = compareNullable(a.name, b.name, strCmp, direction);
        break;
      case "state":
        r = compareNullable(a.state, b.state, strCmp, direction);
        break;
      case "value":
        r = compareNullable(a.numeric_value, b.numeric_value, numCmp, direction);
        if (r === 0) {
          r = compareNullable(a.score_text, b.score_text, strCmp, direction);
        }
        break;
      case "sample_size":
        r = compareNullable(a.sample_size, b.sample_size, numCmp, direction);
        break;
    }
    if (r !== 0) return r;
    // Stable tiebreak: alphabetical by name.
    return a.name.localeCompare(b.name);
  };

  // Suppressed/not-reported rows always sort alphabetically by name within their bucket
  // — they have no value, so applying a numeric sort to them is meaningless.
  const compareUnreportable = (a: MeasureIndexRow, b: MeasureIndexRow): number => {
    if (column === "name" || column === "state") return compareReportable(a, b);
    return a.name.localeCompare(b.name);
  };

  reportable.sort(compareReportable);
  unreportable.sort(compareUnreportable);
  return reportable.concat(unreportable);
}

export function FilterExploreTable({
  rows,
  unit,
  providerType = "HOSPITAL",
  sortColumn,
  sortDirection,
  onSort,
}: FilterExploreTableProps): React.JSX.Element {
  const sorted = useMemo(
    () => sortRows(rows, sortColumn, sortDirection),
    [rows, sortColumn, sortDirection],
  );

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

  return (
    <div className="rounded border border-gray-200 bg-white">
      {/* Header — sticky, outside the scroll container so it stays put */}
      <div className="grid grid-cols-[2fr_60px_1fr_1fr_80px_1fr_1.2fr] border-b border-gray-200 bg-gray-50">
        <SortHeader
          column="name"
          label={FILTER_EXPLORE_HOSPITAL_LABEL}
          align="left"
          sortColumn={sortColumn}
          sortDirection={sortDirection}
          onSort={onSort}
        />
        <SortHeader
          column="state"
          label={FILTER_EXPLORE_STATE_COL_LABEL}
          align="left"
          sortColumn={sortColumn}
          sortDirection={sortDirection}
          onSort={onSort}
        />
        <SortHeader
          column="value"
          label={FILTER_EXPLORE_VALUE_LABEL}
          align="right"
          sortColumn={sortColumn}
          sortDirection={sortDirection}
          onSort={onSort}
        />
        <div className="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
          {FILTER_EXPLORE_INTERVAL_LABEL}
        </div>
        <SortHeader
          column="sample_size"
          label={FILTER_EXPLORE_SAMPLE_SIZE_LABEL}
          align="right"
          sortColumn={sortColumn}
          sortDirection={sortDirection}
          onSort={onSort}
        />
        <div className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
          {FILTER_EXPLORE_PERIOD_NOTE}
        </div>
        <div className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
          {FILTER_EXPLORE_STATUS_LABEL}
        </div>
      </div>

      {/* Scroll container */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{ maxHeight: "min(70vh, 720px)", overflowY: "auto" }}
        role="grid"
        aria-rowcount={sorted.length}
      >
        <div style={{ height: totalHeight, position: "relative" }}>
          <div style={{ transform: `translateY(${offsetY}px)` }}>
            {visibleRows.map((row, i) => {
              const idx = startIdx + i;
              const intervalText = formatRowInterval(row, unit);
              const status = rowStatus(row);
              const valueText =
                status === "reported" || status === "no_value"
                  ? formatRowValue(row, unit)
                  : "—";
              const valueIsAvailable = status === "reported";
              const sampleText =
                row.count_suppressed
                  ? "—"
                  : row.sample_size !== null
                    ? row.sample_size.toLocaleString("en-US")
                    : "—";

              const rowStyle: CSSProperties = {
                minHeight: ROW_HEIGHT,
              };

              return (
                <div
                  key={`${row.ccn}-${idx}`}
                  className="grid grid-cols-[2fr_60px_1fr_1fr_80px_1fr_1.2fr] items-center border-b border-gray-100 px-0 py-2 text-sm hover:bg-gray-50"
                  style={rowStyle}
                  role="row"
                  aria-rowindex={idx + 2}
                >
                  <div className="px-3">
                    <a
                      href={rowHref(row, providerType)}
                      className="block font-medium text-gray-800 underline-offset-2 hover:underline"
                    >
                      {titleCase(row.name)}
                    </a>
                    {row.city && (
                      <p className="mt-0.5 text-xs text-gray-500">{titleCase(row.city)}</p>
                    )}
                  </div>
                  <div className="px-3 text-xs text-gray-600">{row.state ?? "—"}</div>
                  <div className="px-3 text-right">
                    <span
                      className={`font-semibold tabular-nums ${
                        valueIsAvailable ? "text-gray-800" : "text-gray-400"
                      }`}
                    >
                      {valueText}
                    </span>
                  </div>
                  <div className="px-3 text-right text-xs tabular-nums text-gray-500">
                    {intervalText ?? "—"}
                  </div>
                  <div className="px-3 text-right text-xs tabular-nums text-gray-600">
                    {sampleText}
                  </div>
                  <div className="px-3 text-xs text-gray-500">
                    {formatPeriodLabel(row.period_label)}
                  </div>
                  <div className="px-3">
                    <StatusCell row={row} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
