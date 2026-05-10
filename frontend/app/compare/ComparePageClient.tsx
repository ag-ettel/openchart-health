"use client";

// Compare page — side-by-side comparison of two providers.
// The only route that fetches data at runtime (client-side).
// See .claude/rules/frontend-spec.md, ses-context.md, legal-compliance.md.
//
// URL: /compare?a={ccn}&b={ccn}
//
// Architecture:
//   - Fetches two provider JSONs from CDN
//   - Pairs measures by measure_id (union of both providers' measures)
//   - Single shared CategoryNav drives filtering for both providers
//   - Side-by-side on desktop (lg+), stacked on mobile
//   - All required legal disclosures rendered per legal-compliance.md checklist
//
// Mobile strategy: stacked layout (not tabs). Both providers' data is always
// visible. This is antifragile — no hidden state, no JS-dependent tab toggling,
// both values always in the DOM for comparison. The stacked layout degrades
// gracefully and maintains the "non-disclosure is presence" philosophy.

import { Suspense, useState, useMemo, useCallback, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import type { Provider, Measure, ProviderType } from "@/types/provider";
import { titleCase, hasSESSensitivity, measureHasData, formatPeriodLabel, isMeasureRetired } from "@/lib/utils";
import {
  POPULATION_CONTEXT_WARNING,
} from "@/lib/constants";
import {
  getTagsForMeasure,
  getTagsForNHMeasure,
  isHCAHPS,
  isRetiredHCAHPS,
  hcahpsBase,
  groupHCAHPS,
  HCAHPS_GROUPS,
  MEASURE_TAGS,
  NH_MEASURE_TAGS,
  type HCAHPSGroup,
  type MeasureTag,
} from "@/lib/measure-tags";
import { SetCompareTarget } from "@/components/CompareContext";
import { CompareHeader } from "@/components/CompareHeader";
import { CompareMeasureRow } from "@/components/CompareMeasureRow";
import { SESDisclosureBlock } from "@/components/SESDisclosureBlock";
import { MultipleComparisonDisclosure } from "@/components/MultipleComparisonDisclosure";
import { CompareIntervalPlot } from "@/components/CompareIntervalPlot";
import { CompareDistributionHistogram } from "@/components/CompareDistributionHistogram";
import { CompareTrendChart } from "@/components/CompareTrendChart";
import { useDistribution } from "@/lib/use-distributions";
import { CompareFiveStar } from "@/components/CompareFiveStar";
import { CompareStaffing } from "@/components/CompareStaffing";
import { CompareInspectionSummary } from "@/components/CompareInspectionSummary";
import { CompareFacilityTimeline } from "@/components/CompareFacilityTimeline";
import { CompareOwnership } from "@/components/CompareOwnership";
import { NHGuideLink } from "@/components/NHGuideLink";
import { SentryErrorBoundary } from "@/components/SentryErrorBoundary";
import { compareStarted } from "@/lib/analytics";

// --- Data fetching ---

const CDN_BASE = process.env.NEXT_PUBLIC_CDN_BASE ?? "/data";

async function fetchProvider(ccn: string): Promise<Provider> {
  const resp = await fetch(`${CDN_BASE}/${ccn}.json`);
  if (!resp.ok) throw new Error(`Failed to load provider ${ccn}: ${resp.status}`);
  return resp.json() as Promise<Provider>;
}

// --- Section ordering (provider-type-aware) ---

// Hospital condition / domain rendering order (mirrors hospital MeasuresSection).
const HOSPITAL_SECTION_RENDER_ORDER: { id: string; label: string }[] = [
  { id: "heart", label: "Heart & Cardiac" },
  { id: "lung", label: "Lung & Respiratory" },
  { id: "stroke", label: "Stroke" },
  { id: "sepsis", label: "Sepsis" },
  { id: "vte", label: "Blood Clots (VTE)" },
  { id: "orthopedic", label: "Hip & Knee" },
  { id: "infections", label: "Healthcare-Associated Infections" },
  { id: "opioid", label: "Opioid Safety" },
  { id: "cancer", label: "Cancer & Chemotherapy" },
  { id: "colonoscopy", label: "Colonoscopy & Colon" },
  { id: "cataract", label: "Cataract Surgery" },
  { id: "mortality", label: "Mortality" },
  { id: "complications", label: "Complications & Safety" },
  { id: "readmissions", label: "Unplanned Hospital Visits" },
  { id: "timely_emergency", label: "Timely & Emergency Care" },
  { id: "surgical", label: "Surgical & Procedural" },
  { id: "imaging", label: "Imaging Efficiency" },
  { id: "spending", label: "Medicare Spending" },
  { id: "other", label: "Other Measures" },
];

const HOSPITAL_CONDITION_TAGS = new Set([
  "heart", "lung", "stroke", "sepsis", "vte", "orthopedic",
  "opioid", "colonoscopy", "cataract", "cancer",
]);

function assignHospitalSection(tags: string[]): string {
  if (tags.includes("infections")) return "infections";
  for (const t of tags) {
    if (HOSPITAL_CONDITION_TAGS.has(t)) return t;
  }
  const domains = [
    "mortality", "complications", "readmissions",
    "timely_emergency", "surgical", "imaging", "spending",
  ];
  for (const d of domains) {
    if (tags.includes(d)) return d;
  }
  return "other";
}

const HOSPITAL_PAGE_ORDER_SECTIONS: { label: string; tagIds: string[] }[] = [
  { label: "Patient Experience", tagIds: ["patient_experience"] },
  {
    label: "By Condition",
    tagIds: ["heart", "lung", "stroke", "orthopedic", "colonoscopy", "cataract",
             "cancer", "sepsis", "vte", "opioid"],
  },
  { label: "Safety & Outcomes", tagIds: ["mortality", "infections", "complications", "readmissions"] },
  { label: "Process & Timely Care", tagIds: ["timely_emergency", "surgical"] },
  { label: "Utilization & Cost", tagIds: ["imaging", "spending"] },
  { label: "Status", tagIds: ["not_reported"] },
];

// Nursing home rendering order — mirrors NHMeasuresSection. Section assignment
// is by measure_group so we route a Measure directly rather than via tag set.
const NH_SECTION_RENDER_ORDER: { id: string; label: string }[] = [
  { id: "long_stay_outcomes", label: "Long-Stay Resident Outcomes" },
  { id: "short_stay_outcomes", label: "Short-Stay Resident Outcomes" },
  { id: "claims_quality", label: "Claims-Based Quality" },
  { id: "snf_qrp", label: "SNF Quality Reporting" },
  { id: "spending", label: "Medicare Spending" },
  { id: "other", label: "Other Measures" },
];

function assignNHSection(m: Measure): string {
  switch (m.measure_group) {
    case "NH_QUALITY_LONG_STAY": return "long_stay_outcomes";
    case "NH_QUALITY_SHORT_STAY": return "short_stay_outcomes";
    case "NH_QUALITY_CLAIMS": return "claims_quality";
    case "NH_SNF_QRP": return "snf_qrp";
    case "SPENDING": return "spending";
    default: return "other";
  }
}

const NH_PAGE_ORDER_SECTIONS: { label: string; tagIds: string[] }[] = [
  { label: "Safety & Inspections", tagIds: ["critical_safety"] },
  { label: "Quality Domains", tagIds: ["nh_long_stay", "nh_short_stay", "nh_claims", "nh_snf_qrp"] },
  { label: "Utilization & Cost", tagIds: ["spending"] },
  { label: "Status", tagIds: ["not_reported"] },
];

// Measures that the NH dashboard already shows in topline cards — exclude from
// the paired measure detail section to avoid duplication.
const NH_TOPLINE_MEASURE_IDS = new Set<string>([
  "NH_STAFF_TOTAL_TURNOVER",
  "NH_STAFF_REPORTED_RN_HPRD",
  "NH_STAFF_REPORTED_TOTAL_HPRD",
  "NH_INSP_WEIGHTED_SCORE",
]);

function CompareNav({
  activeTag,
  onTagChange,
  tagCounts,
  kind,
}: {
  activeTag: string | null;
  onTagChange: (tag: string | null) => void;
  tagCounts: Record<string, number>;
  kind: ProviderType;
}): React.JSX.Element {
  const tags: MeasureTag[] = kind === "NURSING_HOME" ? NH_MEASURE_TAGS : MEASURE_TAGS;
  const sectionList = kind === "NURSING_HOME" ? NH_PAGE_ORDER_SECTIONS : HOSPITAL_PAGE_ORDER_SECTIONS;
  const tagById = new Map(tags.map((t) => [t.id, t]));

  const allTags = sectionList
    .flatMap((s) => s.tagIds)
    .map((id) => tagById.get(id))
    .filter((t): t is NonNullable<typeof t> => t !== undefined && (tagCounts[t.id] ?? 0) > 0);

  return (
    <>
      {/* Desktop sidebar */}
      <nav aria-label="Measure categories" className="hidden lg:block lg:w-48 lg:shrink-0">
        <div className="sticky top-16 max-h-[calc(100vh-5rem)] overflow-y-auto space-y-0.5 pb-8">
          <button
            type="button"
            onClick={() => onTagChange(null)}
            className={`flex w-full items-center justify-between rounded px-3 py-1.5 text-left text-xs transition-colors ${
              activeTag === null
                ? "bg-blue-50 font-semibold text-blue-700"
                : "text-gray-500 hover:bg-gray-50 hover:text-gray-700"
            }`}
          >
            <span>All Measures</span>
          </button>

          {sectionList.map((section) => {
            const sectionTags = section.tagIds
              .map((id) => tagById.get(id))
              .filter((t): t is NonNullable<typeof t> => t !== undefined && (tagCounts[t.id] ?? 0) > 0);
            if (sectionTags.length === 0) return null;

            return (
              <div key={section.label}>
                <p className="mb-1 mt-3 px-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
                  {section.label}
                </p>
                {sectionTags.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => onTagChange(activeTag === t.id ? null : t.id)}
                    className={`flex w-full items-center justify-between rounded px-3 py-1.5 text-left text-xs transition-colors ${
                      activeTag === t.id
                        ? "bg-blue-50 font-semibold text-blue-700"
                        : "text-gray-500 hover:bg-gray-50 hover:text-gray-700"
                    }`}
                  >
                    <span>{t.label}</span>
                    <span className={`text-xs ${activeTag === t.id ? "text-blue-400" : "text-gray-300"}`}>
                      {tagCounts[t.id] ?? 0}
                    </span>
                  </button>
                ))}
              </div>
            );
          })}
        </div>
      </nav>

      {/* Mobile filter bar */}
      <div className="sticky top-12 z-20 -mx-6 mb-6 flex gap-1.5 overflow-x-auto border-b border-gray-200 bg-white px-6 py-2 lg:hidden">
        <button
          type="button"
          onClick={() => onTagChange(null)}
          className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            activeTag === null ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-500"
          }`}
        >
          All
        </button>
        {allTags.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onTagChange(activeTag === t.id ? null : t.id)}
            className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              activeTag === t.id ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-500"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
    </>
  );
}

// --- Collapsible section ---

function CollapsibleSection({
  label,
  count,
  children,
}: {
  label: string;
  count: number;
  children: React.ReactNode;
}): React.JSX.Element {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [inView, setInView] = useState(false);

  const handleToggle = useCallback(() => {
    const el = detailsRef.current;
    if (!el) return;
    setIsOpen(el.open);
    if (!el.open) {
      // Section was just collapsed — scroll it into view
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, []);

  useEffect(() => {
    const el = detailsRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => setInView(entry.isIntersecting),
      { threshold: 0 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // After collapsing via the floating bar, return focus to the originating
  // <summary> so AT users land at a known landmark instead of having focus
  // disappear with the floating bar. (Audit C7.)
  const summaryRef = useRef<HTMLElement>(null);

  return (
    <>
      <details ref={detailsRef} className="mb-6 group/section" onToggle={handleToggle}>
        <summary
          ref={summaryRef}
          className="mb-3 flex cursor-pointer items-center justify-between rounded-md border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm font-semibold text-gray-700 shadow-sm hover:bg-blue-50 hover:text-blue-700"
        >
          <span>
            {label}
            <span className="ml-2 text-xs font-normal text-gray-400">
              ({count} {count === 1 ? "measure" : "measures"})
            </span>
          </span>
          <svg className="h-4 w-4 shrink-0 text-gray-400 transition-transform group-open/section:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true" focusable="false">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </summary>
        <div className="space-y-4 pt-2">{children}</div>
      </details>

      {/* Sticky bottom collapse bar — visible when section is open and in view */}
      {isOpen && inView && (
        <div className="fixed inset-x-0 bottom-12 z-30 border-t border-gray-200 bg-white/95 px-4 py-2 backdrop-blur-sm">
          <button
            type="button"
            onClick={() => {
              const el = detailsRef.current;
              if (el) {
                el.open = false;
                setIsOpen(false);
                el.scrollIntoView({ behavior: "smooth", block: "nearest" });
                // Return keyboard focus to the originating summary — without this
                // AT users lose their place when the floating bar disappears.
                summaryRef.current?.focus();
              }
            }}
            className="mx-auto block max-w-xl rounded border border-gray-200 bg-gray-50 px-6 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1"
            aria-label={`Collapse ${label} section`}
          >
            Collapse {label}
          </button>
        </div>
      )}
    </>
  );
}

// --- Compact paired HCAHPS display ---

/** Categorize HCAHPS responses into labeled slices. */
interface ResponseSlice {
  measure: Measure;
  label: string;
  color: string;
  isPrimary: boolean;
}

function categorizeHCAHPSResponses(responses: Measure[]): ResponseSlice[] {
  const slices: ResponseSlice[] = [];
  for (const m of responses) {
    const id = m.measure_id;
    if (id.endsWith("_A_P")) slices.push({ measure: m, label: "Always", color: "#2563eb", isPrimary: true });
    else if (id.endsWith("_U_P")) slices.push({ measure: m, label: "Usually", color: "#93c5fd", isPrimary: false });
    else if (id.endsWith("_SN_P")) slices.push({ measure: m, label: "Sometimes/Never", color: "#e5e7eb", isPrimary: false });
    else if (id.endsWith("_DY")) slices.push({ measure: m, label: "Definitely Yes", color: "#2563eb", isPrimary: true });
    else if (id.endsWith("_PY")) slices.push({ measure: m, label: "Probably Yes", color: "#93c5fd", isPrimary: false });
    else if (id.endsWith("_DN")) slices.push({ measure: m, label: "Probably/Definitely No", color: "#e5e7eb", isPrimary: false });
    else if (id.endsWith("_Y_P")) slices.push({ measure: m, label: "Yes", color: "#2563eb", isPrimary: true });
    else if (id.endsWith("_N_P")) slices.push({ measure: m, label: "No", color: "#e5e7eb", isPrimary: false });
    else if (id.endsWith("_9_10")) slices.push({ measure: m, label: "9-10 (High)", color: "#2563eb", isPrimary: true });
    else if (id.endsWith("_7_8")) slices.push({ measure: m, label: "7-8 (Medium)", color: "#93c5fd", isPrimary: false });
    else if (id.endsWith("_0_6")) slices.push({ measure: m, label: "6 or lower", color: "#e5e7eb", isPrimary: false });
  }
  return slices.sort((a, b) => {
    if (a.isPrimary && !b.isPrimary) return -1;
    if (!a.isPrimary && b.isPrimary) return 1;
    return (b.measure.numeric_value ?? 0) - (a.measure.numeric_value ?? 0);
  });
}

/** Compact HCAHPS side — headline value + stacked bar. */
function CompactHCAHPSSide({ group }: {
  group: HCAHPSGroup | null;
}): React.JSX.Element {
  if (!group) {
    return (
      <div className="flex-1 min-w-0 rounded border border-gray-100 bg-gray-50 px-3 py-2">
        <p className="text-xs text-gray-400">Not reported at this facility.</p>
      </div>
    );
  }

  const slices = categorizeHCAHPSResponses(group.responses);
  const primary = slices.find((s) => s.isPrimary);
  const total = slices.reduce((sum, s) => sum + (s.measure.numeric_value ?? 0), 0);
  const surveyCount = group.starRating?.sample_size ?? primary?.measure.sample_size ?? null;

  if (total === 0) {
    return (
      <div className="flex-1 min-w-0 rounded border border-gray-100 bg-gray-50 px-3 py-2">
        <p className="text-sm text-gray-400">No response data</p>
      </div>
    );
  }

  // The headline top-response value and the side-by-side comparison both
  // appear in the CompareIntervalPlot below this row, so we don't repeat
  // them here — the per-side block's job is to show the response
  // distribution (top/middle/bottom slices) that the interval plot can't.
  return (
    <div className="flex-1 min-w-0">
      <div className="flex h-4 overflow-hidden rounded-full">
        {slices
          .filter((s) => (s.measure.numeric_value ?? 0) > 0)
          .map((s) => (
            <div
              key={s.measure.measure_id}
              style={{ width: `${((s.measure.numeric_value ?? 0) / total) * 100}%`, backgroundColor: s.color }}
              title={`${s.label}: ${s.measure.numeric_value}%`}
            />
          ))}
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-gray-500">
        {slices
          .filter((s) => (s.measure.numeric_value ?? 0) > 0)
          .map((s) => (
            <span key={s.measure.measure_id} className="flex items-center gap-1 whitespace-nowrap">
              <span className="inline-block h-2 w-2 rounded-sm" style={{ backgroundColor: s.color }} />
              <span className="font-medium tabular-nums text-gray-700">{s.measure.numeric_value}%</span>
              <span className="text-gray-500">{s.label}</span>
            </span>
          ))}
        {surveyCount !== null && (
          <span className="text-gray-400">· {surveyCount.toLocaleString("en-US")} surveys</span>
        )}
      </div>
    </div>
  );
}

function CompareHCAHPSGroup({
  groupBase,
  groupLabel,
  providerA,
  providerB,
}: {
  groupBase: string;
  groupLabel: string;
  providerA: Provider;
  providerB: Provider;
}): React.JSX.Element {
  const groupsA = groupHCAHPS(providerA.measures.filter((m) => measureHasData(m)));
  const groupsB = groupHCAHPS(providerB.measures.filter((m) => measureHasData(m)));
  const groupA = groupsA.find((g) => g.groupBase === groupBase) ?? null;
  const groupB = groupsB.find((g) => g.groupBase === groupBase) ?? null;

  // Period from either side
  const anyMeasure = groupA?.responses[0] ?? groupB?.responses[0] ?? null;
  const period = anyMeasure ? formatPeriodLabel(anyMeasure.period_label) : "";

  // Trend data for expandable detail
  const primaryA = groupA ? categorizeHCAHPSResponses(groupA.responses).find((s) => s.isPrimary)?.measure ?? null : null;
  const primaryB = groupB ? categorizeHCAHPSResponses(groupB.responses).find((s) => s.isPrimary)?.measure ?? null : null;
  const hasTrendA = primaryA?.trend !== null && (primaryA?.trend?.length ?? 0) > 0;
  const hasTrendB = primaryB?.trend !== null && (primaryB?.trend?.length ?? 0) > 0;
  const hasTrend = hasTrendA || hasTrendB;
  const nameA = titleCase(providerA.name);
  const nameB = titleCase(providerB.name);

  // National-distribution lookup for the primary top-box response. Hooks
  // must be called unconditionally — empty strings produce a null lookup
  // and the bar-chart fallback renders.
  const primaryMeasureId = primaryA?.measure_id ?? primaryB?.measure_id ?? "";
  const primaryPeriod = primaryA?.period_label ?? primaryB?.period_label ?? "";
  const distribution = useDistribution(primaryMeasureId, primaryPeriod);

  return (
    <div className="rounded-lg border border-gray-200 border-l-4 border-l-blue-400 bg-white px-5 py-4 shadow-sm">
      {/* Header — full width */}
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-blue-800">{groupLabel}</h3>
        {period && <p className="mt-0.5 text-xs text-gray-400">{period}</p>}
      </div>

      {/* Plain language description */}
      {(primaryA?.measure_plain_language ?? primaryB?.measure_plain_language) && (
        <p className="mb-3 text-sm font-semibold leading-snug text-gray-800">
          {primaryA?.measure_plain_language ?? primaryB?.measure_plain_language}
        </p>
      )}

      {/* Side-by-side compact values */}
      <div className="flex flex-col gap-4 lg:flex-row lg:gap-6">
        <div className="lg:hidden text-xs font-bold text-blue-700 border-b border-blue-100 pb-1">{nameA}</div>
        <CompactHCAHPSSide group={groupA} />
        <div className="lg:hidden text-xs font-bold text-gray-800 border-b border-gray-200 pb-1">{nameB}</div>
        <CompactHCAHPSSide group={groupB} />
      </div>

      {/* National-distribution histogram with both providers' top-box
          response marked, falling back to the paired bar chart when no
          distribution is available for this measure/period. */}
      {(primaryA?.numeric_value !== null || primaryB?.numeric_value !== null) && (
        distribution !== null ? (
          <CompareDistributionHistogram
            measureId={primaryMeasureId}
            periodLabel={primaryPeriod}
            providerA={primaryA && primaryA.numeric_value !== null ? {
              value: primaryA.numeric_value,
              ciLower: primaryA.confidence_interval_lower,
              ciUpper: primaryA.confidence_interval_upper,
              label: nameA,
            } : null}
            providerB={primaryB && primaryB.numeric_value !== null ? {
              value: primaryB.numeric_value,
              ciLower: primaryB.confidence_interval_lower,
              ciUpper: primaryB.confidence_interval_upper,
              label: nameB,
            } : null}
            nationalAvg={primaryA?.national_avg ?? primaryB?.national_avg ?? null}
            direction={primaryA?.direction ?? primaryB?.direction ?? null}
            unit="percent"
          />
        ) : (
          <CompareIntervalPlot
            providerA={primaryA && primaryA.numeric_value !== null ? {
              value: primaryA.numeric_value,
              ciLower: primaryA.confidence_interval_lower,
              ciUpper: primaryA.confidence_interval_upper,
              label: nameA,
              sampleSize: primaryA.sample_size ?? primaryA.denominator ?? null,
              sampleLabel: "Surveys",
            } : null}
            providerB={primaryB && primaryB.numeric_value !== null ? {
              value: primaryB.numeric_value,
              ciLower: primaryB.confidence_interval_lower,
              ciUpper: primaryB.confidence_interval_upper,
              label: nameB,
              sampleSize: primaryB.sample_size ?? primaryB.denominator ?? null,
              sampleLabel: "Surveys",
            } : null}
            nationalAvg={primaryA?.national_avg ?? primaryB?.national_avg ?? null}
            unit="percent"
          />
        )
      )}

      {/* Trend chart — overlaid on single axis */}
      {hasTrend && (
        <details className="mt-3 border-t border-gray-100 pt-3" open>
          <summary className="cursor-pointer text-xs font-semibold text-blue-600 hover:text-blue-800">
            Trend over time
          </summary>
          <CompareTrendChart
            trendA={primaryA?.trend ?? null}
            trendB={primaryB?.trend ?? null}
            trendValidA={primaryA?.trend_valid ?? false}
            trendValidB={primaryB?.trend_valid ?? false}
            trendPeriodCountA={primaryA?.trend_period_count ?? 0}
            trendPeriodCountB={primaryB?.trend_period_count ?? 0}
            unit="percent"
            nationalAvg={primaryA?.national_avg ?? primaryB?.national_avg ?? null}
            nameA={nameA}
            nameB={nameB}
            yAxisLabel="Top Response %"
          />
        </details>
      )}

      {/* Source */}
      <details className="mt-3">
        <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-600">Source</summary>
        <p className="mt-1 text-xs text-gray-400">Source: CMS HCAHPS Patient Survey, {period}.</p>
      </details>
    </div>
  );
}

// --- Main compare content ---

interface SearchEntry {
  provider_id: string;
  name: string;
  city: string | null;
  state: string | null;
  provider_type: string;
}

function providerToSearchEntry(p: Provider): SearchEntry {
  return {
    provider_id: p.provider_id,
    name: p.name,
    city: p.address.city,
    state: p.address.state,
    provider_type: p.provider_type,
  };
}

function providerTypeLabel(t: string | null, plural: boolean): string {
  if (t === "NURSING_HOME") return plural ? "nursing homes" : "nursing home";
  if (t === "HOSPITAL") return plural ? "hospitals" : "hospital";
  return plural ? "providers" : "provider";
}

function CompareSearchPicker({ lockedA }: { lockedA: Provider | null }): React.JSX.Element {
  const [index, setIndex] = useState<SearchEntry[]>([]);
  const [pickedA, setPickedA] = useState<SearchEntry | null>(null);
  const [pickedB, setPickedB] = useState<SearchEntry | null>(null);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch("/search_index.json")
      .then((res) => res.json())
      .then((data: SearchEntry[]) => setIndex(data))
      .catch(() => {/* search index not available; results stay empty */});
  }, []);

  const slotA: SearchEntry | null = lockedA ? providerToSearchEntry(lockedA) : pickedA;
  const slotB: SearchEntry | null = pickedB;
  const selectingSlot: "a" | "b" = slotA === null ? "a" : "b";
  const constrainType: string | null = slotA?.provider_type ?? null;

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];
    return index
      .filter((entry) => {
        if (constrainType && entry.provider_type !== constrainType) return false;
        if (slotA && entry.provider_id === slotA.provider_id) return false;
        if (slotB && entry.provider_id === slotB.provider_id) return false;
        return (
          entry.name.toLowerCase().includes(q) ||
          entry.provider_id.includes(q) ||
          (entry.city !== null && entry.city.toLowerCase().includes(q)) ||
          (entry.state !== null && entry.state.toLowerCase().includes(q))
        );
      })
      .slice(0, 30);
  }, [query, index, constrainType, slotA, slotB]);

  // Auto-navigation removed — keyboard users tabbing past a freshly filled slot
  // could trigger an unintended redirect. The explicit Compare button below
  // requires deliberate activation. (Audit C10.)

  const handleSelect = (entry: SearchEntry) => {
    if (selectingSlot === "a") setPickedA(entry);
    else setPickedB(entry);
    setQuery("");
    inputRef.current?.focus();
  };

  const compareHref = slotA && slotB
    ? `/compare?a=${encodeURIComponent(slotA.provider_id)}&b=${encodeURIComponent(slotB.provider_id)}`
    : null;

  const placeholder = constrainType
    ? `Search ${providerTypeLabel(constrainType, true)} by name, city, state, or CCN…`
    : "Search hospitals and nursing homes by name, city, state, or CCN…";

  return (
    <div className="mx-auto max-w-2xl py-10">
      <h1 className="mb-2 text-center text-2xl font-bold text-gray-900">Compare Providers</h1>
      <p className="mb-6 text-center text-sm text-gray-600">
        Search for two providers to compare side by side.
      </p>

      {/* Slot pills */}
      <div className="mb-4 flex gap-2">
        {([
          { slot: "a" as const, entry: slotA, locked: lockedA !== null, clear: () => setPickedA(null) },
          { slot: "b" as const, entry: slotB, locked: false, clear: () => setPickedB(null) },
        ]).map(({ slot, entry, locked, clear }) => {
          const isActive = selectingSlot === slot;
          const label = slot === "a" ? "Provider A" : "Provider B";
          if (!entry) {
            return (
              <div
                key={slot}
                className={`flex-1 min-w-0 rounded-lg border-2 border-dashed px-3 py-2.5 text-left transition-colors ${
                  isActive ? "border-blue-300 bg-blue-50" : "border-gray-200 bg-gray-50"
                }`}
              >
                <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">{label}</p>
                <p className="mt-0.5 text-xs text-gray-400">
                  {isActive ? "Pick from results below…" : "Select first"}
                </p>
              </div>
            );
          }
          return (
            <div
              key={slot}
              className={`flex-1 min-w-0 rounded-lg border-2 px-3 py-2.5 transition-colors ${
                isActive ? "border-blue-400 bg-blue-50" : "border-gray-200 bg-white"
              }`}
            >
              <div className="flex items-start justify-between gap-1">
                <div className="min-w-0">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">{label}</p>
                  <p className="mt-0.5 truncate text-sm font-medium text-gray-900">{titleCase(entry.name)}</p>
                  <p className="truncate text-xs text-gray-500">
                    {[entry.city ? titleCase(entry.city) : null, entry.state].filter(Boolean).join(", ")}
                    {" · "}
                    {entry.provider_id}
                  </p>
                </div>
                {!locked && (
                  <button
                    type="button"
                    onClick={clear}
                    className="mt-1 shrink-0 rounded p-0.5 text-gray-300 hover:text-gray-500 hover:bg-gray-100"
                    aria-label={`Clear ${label}`}
                    title="Clear"
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Explicit Compare button — only when both slots are filled. Keyboard
          users activate intentionally rather than triggering a side-effect
          redirect on every selection. */}
      {compareHref && (
        <a
          href={compareHref}
          className="mb-4 flex w-full items-center justify-center gap-1.5 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 transition-colors"
        >
          Compare these providers
        </a>
      )}

      {/* Constraint hint */}
      {constrainType && selectingSlot === "b" && (
        <p className="mb-2 text-xs text-gray-500">
          Showing {providerTypeLabel(constrainType, true)} only — providers must be the same type to compare.
        </p>
      )}

      {/* Search input */}
      <div className="relative">
        <svg
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-md border border-gray-300 py-2 pl-9 pr-3 text-sm text-gray-900 placeholder:text-gray-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 focus:border-blue-500"
        />
      </div>

      {/* Results */}
      {query.trim().length >= 2 && (
        <div className="mt-3 overflow-hidden rounded-md border border-gray-200">
          {results.length === 0 ? (
            <p className="px-4 py-3 text-sm text-gray-500">No matching providers found.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {results.map((entry) => (
                <li key={entry.provider_id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(entry)}
                    className="block w-full px-4 py-2.5 text-left transition-colors hover:bg-blue-50"
                  >
                    <p className="text-sm font-medium text-gray-900">{titleCase(entry.name)}</p>
                    <p className="mt-0.5 text-xs text-gray-500">
                      {[entry.city ? titleCase(entry.city) : null, entry.state].filter(Boolean).join(", ")}
                      {" · "}
                      {entry.provider_id}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function CompareContent(): React.JSX.Element {
  const searchParams = useSearchParams();
  const ccnA = searchParams.get("a");
  const ccnB = searchParams.get("b");

  const [providerA, setProviderA] = useState<Provider | null>(null);
  const [providerB, setProviderB] = useState<Provider | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTag, setActiveTag] = useState<string | null>(null);

  useEffect(() => {
    if (!ccnA || !ccnB) {
      // If only one CCN, load that provider to show its name in the picker
      if (ccnA && !ccnB) {
        fetchProvider(ccnA)
          .then((a) => setProviderA(a))
          .catch(() => {/* handled in full compare */});
      }
      return;
    }
    if (ccnA === ccnB) {
      setError("Please select two different providers to compare.");
      return;
    }

    setLoading(true);
    setError(null);
    Promise.all([fetchProvider(ccnA), fetchProvider(ccnB)])
      .then(([a, b]) => {
        setProviderA(a);
        setProviderB(b);
        // User action: opened /compare?a=…&b=… and both provider JSONs
        // resolved successfully. Fires once per successful load. Provider
        // type is logged so we can distinguish hospital vs nursing-home
        // compare engagement; CCNs are public CMS identifiers.
        if (a.provider_type === b.provider_type) {
          compareStarted({
            ccnA: a.provider_id,
            ccnB: b.provider_id,
            providerType: a.provider_type === "NURSING_HOME"
              ? "NURSING_HOME"
              : "HOSPITAL",
          });
        }
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load provider data.");
      })
      .finally(() => setLoading(false));
  }, [ccnA, ccnB]);

  // --- Empty / loading / error states ---

  if (!ccnA && !ccnB) {
    return <CompareSearchPicker lockedA={null} />;
  }

  // One CCN provided (e.g. from "Compare" button on hospital page) — prompt for second
  if (ccnA && !ccnB) {
    if (!providerA) {
      return <div className="py-12 text-center text-sm text-gray-500">Loading…</div>;
    }
    return <CompareSearchPicker lockedA={providerA} />;
  }

  if (!ccnB) return <></>;  // unreachable, satisfies TS

  if (loading) {
    return (
      <div className="py-12 text-center" role="status" aria-live="polite">
        <p className="text-sm text-gray-500">Loading provider data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl py-12 text-center">
        <h1 className="mb-4 text-2xl font-bold text-gray-900">Compare Providers</h1>
        <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800" role="alert" aria-live="assertive">
          {error}
        </div>
      </div>
    );
  }

  if (!providerA || !providerB) return <></>;

  // Same-type enforcement — measures, disclosures, and the SES frame don't
  // carry across provider types. A hospital cannot be meaningfully compared
  // to a nursing home on the same axes.
  if (providerA.provider_type !== providerB.provider_type) {
    const fmt = (t: string) => t.replace(/_/g, " ").toLowerCase();
    return (
      <article className="mx-auto max-w-2xl py-12">
        <h1 className="mb-4 text-2xl font-bold text-gray-900 text-center">Compare Providers</h1>
        <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <p className="font-medium">These providers are different types and cannot be compared on the same axes.</p>
          <p className="mt-2">
            <span className="font-semibold">{titleCase(providerA.name)}</span> is a {fmt(providerA.provider_type)}.
            <br />
            <span className="font-semibold">{titleCase(providerB.name)}</span> is a {fmt(providerB.provider_type)}.
          </p>
          <p className="mt-2 text-xs text-amber-700">
            Hospital and nursing home quality measures, regulatory frames, and population contexts are not directly comparable. Choose two providers of the same type.
          </p>
        </div>
      </article>
    );
  }

  return (
    <CompareLoaded
      providerA={providerA}
      providerB={providerB}
      activeTag={activeTag}
      setActiveTag={setActiveTag}
    />
  );
}

function CompareLoaded({
  providerA,
  providerB,
  activeTag,
  setActiveTag,
}: {
  providerA: Provider;
  providerB: Provider;
  activeTag: string | null;
  setActiveTag: (tag: string | null) => void;
}): React.JSX.Element {
  // Both providers are guaranteed same type by the same-type guard upstream.
  const kind = providerA.provider_type;
  const isNH = kind === "NURSING_HOME";
  const isHospital = kind === "HOSPITAL";

  // Register compare context so nav bar shows the drawer instead of plain link
  const compareTarget = useMemo(() => ({
    ccn: providerA.provider_id,
    name: providerA.name,
    providerType: providerA.provider_type,
  }), [providerA.provider_id, providerA.name, providerA.provider_type]);

  const nameA = titleCase(providerA.name);
  const nameB = titleCase(providerB.name);
  const [showAllPE, setShowAllPE] = useState(false);
  const [peInView, setPeInView] = useState(false);
  const peRef = useRef<HTMLDivElement>(null);

  // Track whether the PE section is visible — hides the fixed collapse bar when not
  useEffect(() => {
    const el = peRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => setPeInView(entry.isIntersecting),
      { threshold: 0 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Build primary measure maps for both providers. Exclude retired/unknown
  // measures (matches NHMeasuresSection on the profile page). For NH, also
  // exclude topline measures that render in the dashboard above the grid.
  const primaryA = useMemo(
    () => providerA.measures.filter(
      (m) => m.stratification === null
        && !isMeasureRetired(m)
        && (!isNH || !NH_TOPLINE_MEASURE_IDS.has(m.measure_id))
    ),
    [providerA.measures, isNH]
  );
  const primaryB = useMemo(
    () => providerB.measures.filter(
      (m) => m.stratification === null
        && !isMeasureRetired(m)
        && (!isNH || !NH_TOPLINE_MEASURE_IDS.has(m.measure_id))
    ),
    [providerB.measures, isNH]
  );

  const measureMapA = useMemo(() => {
    const map = new Map<string, Measure>();
    for (const m of primaryA) map.set(m.measure_id, m);
    return map;
  }, [primaryA]);

  const measureMapB = useMemo(() => {
    const map = new Map<string, Measure>();
    for (const m of primaryB) map.set(m.measure_id, m);
    return map;
  }, [primaryB]);

  // Union of all measure IDs (both providers)
  const allMeasureIds = useMemo(() => {
    const ids = new Set<string>();
    for (const m of primaryA) ids.add(m.measure_id);
    for (const m of primaryB) ids.add(m.measure_id);
    return ids;
  }, [primaryA, primaryB]);

  // Tags derived from the union of both providers' measures
  const measureTags = useMemo(() => {
    const map = new Map<string, string[]>();
    const tagFn = isNH ? getTagsForNHMeasure : getTagsForMeasure;
    for (const id of allMeasureIds) {
      const m = measureMapA.get(id) ?? measureMapB.get(id);
      if (m) map.set(id, tagFn(m));
    }
    return map;
  }, [allMeasureIds, measureMapA, measureMapB, isNH]);

  // Tag counts for the sidebar — count HCAHPS by group, not individual responses
  const tagCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    const seenHcahpsGroups = new Set<string>();

    for (const id of allMeasureIds) {
      const m = measureMapA.get(id) ?? measureMapB.get(id);
      if (!m) continue;
      if (isRetiredHCAHPS(m)) continue;

      const tags = measureTags.get(id) ?? [];

      if (isHCAHPS(m)) {
        const base = hcahpsBase(m.measure_id);
        if (!base) continue;
        const groupKey = tags.join("|") + "|" + base;
        if (seenHcahpsGroups.has(groupKey)) continue;
        seenHcahpsGroups.add(groupKey);
      }

      for (const t of tags) {
        counts[t] = (counts[t] ?? 0) + 1;
      }
    }
    return counts;
  }, [allMeasureIds, measureMapA, measureMapB, measureTags]);

  // Filter measure IDs by active tag
  const filteredIds = useMemo(() => {
    if (activeTag === null) return allMeasureIds;
    const filtered = new Set<string>();
    for (const id of allMeasureIds) {
      const tags = measureTags.get(id) ?? [];
      if (tags.includes(activeTag)) filtered.add(id);
    }
    return filtered;
  }, [allMeasureIds, activeTag, measureTags]);

  // Separate HCAHPS and non-HCAHPS measures
  const nonHcahpsIds = useMemo(() => {
    const ids: string[] = [];
    for (const id of filteredIds) {
      const m = measureMapA.get(id) ?? measureMapB.get(id);
      if (!m) continue;
      if (isHCAHPS(m) || isRetiredHCAHPS(m)) continue;
      if (!measureHasData(m) && !(measureMapB.get(id) && measureHasData(measureMapB.get(id)!)) &&
          !(measureMapA.get(id) && measureHasData(measureMapA.get(id)!))) continue;
      ids.push(id);
    }
    return ids;
  }, [filteredIds, measureMapA, measureMapB]);

  // HCAHPS groups from the union
  const hcahpsGroupBases = useMemo(() => {
    const bases = new Set<string>();
    for (const id of filteredIds) {
      const m = measureMapA.get(id) ?? measureMapB.get(id);
      if (!m || !isHCAHPS(m) || isRetiredHCAHPS(m)) continue;
      const base = hcahpsBase(id);
      if (base) bases.add(base);
    }
    // Sort by the canonical HCAHPS group order
    const ORDER = [
      "H_HSP_RATING", "H_RECMND",
      "H_COMP_1", "H_NURSE_LISTEN", "H_NURSE_RESPECT", "H_NURSE_EXPLAIN",
      "H_COMP_2", "H_DOCTOR_LISTEN", "H_DOCTOR_RESPECT", "H_DOCTOR_EXPLAIN",
      "H_COMP_5", "H_MED_FOR", "H_SIDE_EFFECTS",
      "H_COMP_6", "H_DISCH_HELP", "H_SYMPTOMS",
      "H_CLEAN_HSP", "H_CLEAN", "H_QUIET_HSP", "H_QUIET",
    ];
    return Array.from(bases).sort((a, b) => {
      const ai = ORDER.indexOf(a);
      const bi = ORDER.indexOf(b);
      return (ai >= 0 ? ai : 999) - (bi >= 0 ? bi : 999);
    });
  }, [filteredIds, measureMapA, measureMapB]);

  // Group non-HCAHPS into sections
  const sections = useMemo(() => {
    const sectionMap = new Map<string, string[]>();
    for (const id of nonHcahpsIds) {
      const m = measureMapA.get(id) ?? measureMapB.get(id);
      if (!m) continue;
      const tags = measureTags.get(id) ?? [];
      const section = isNH ? assignNHSection(m) : assignHospitalSection(tags);
      if (!sectionMap.has(section)) sectionMap.set(section, []);
      sectionMap.get(section)!.push(id);
    }

    // Sort within section: tail_risk first, then alphabetical
    for (const [, ids] of sectionMap) {
      ids.sort((a, b) => {
        const ma = measureMapA.get(a) ?? measureMapB.get(a);
        const mb = measureMapA.get(b) ?? measureMapB.get(b);
        if (!ma || !mb) return 0;
        if (ma.tail_risk_flag && !mb.tail_risk_flag) return -1;
        if (!ma.tail_risk_flag && mb.tail_risk_flag) return 1;
        const aName = ma.measure_plain_language ?? ma.measure_name ?? "";
        const bName = mb.measure_plain_language ?? mb.measure_name ?? "";
        return aName.localeCompare(bName);
      });
    }

    const order = isNH ? NH_SECTION_RENDER_ORDER : HOSPITAL_SECTION_RENDER_ORDER;
    return order
      .filter((s) => sectionMap.has(s.id))
      .map((s) => ({
        ...s,
        measureIds: sectionMap.get(s.id)!,
      }));
  }, [nonHcahpsIds, measureMapA, measureMapB, measureTags, isNH]);

  // SES sensitivity check across both providers' filtered measures
  const showSES = useMemo(() => {
    const allFiltered: Measure[] = [];
    for (const id of filteredIds) {
      const a = measureMapA.get(id);
      const b = measureMapB.get(id);
      if (a) allFiltered.push(a);
      if (b) allFiltered.push(b);
    }
    return hasSESSensitivity(allFiltered);
  }, [filteredIds, measureMapA, measureMapB]);

  // Not-reported measures (in at least one provider)
  const notReportedIds = useMemo(() => {
    const ids: string[] = [];
    for (const id of filteredIds) {
      const a = measureMapA.get(id);
      const b = measureMapB.get(id);
      // Include if both sides lack data
      const aHasData = a ? measureHasData(a) : false;
      const bHasData = b ? measureHasData(b) : false;
      if (!aHasData && !bHasData && !isHCAHPS(a ?? b!)) {
        ids.push(id);
      }
    }
    return ids;
  }, [filteredIds, measureMapA, measureMapB]);

  const isFiltered = activeTag !== null;
  const isNotReportedFilter = activeTag === "not_reported";

  return (
    <article>
      <SetCompareTarget
        ccn={compareTarget.ccn}
        name={compareTarget.name}
        providerType={compareTarget.providerType}
      />
      {/* Header — both providers side by side */}
      <CompareHeader providerA={providerA} providerB={providerB} />

      {/* Sticky provider name labels — desktop only, visible during scroll */}
      <div className="hidden lg:flex sticky top-12 z-20 mt-4 mb-2 gap-8">
        <div className="w-48 shrink-0" /> {/* sidebar spacer */}
        <div className="flex flex-1 gap-6">
          <div className="flex-1 rounded-md border-2 border-blue-300 bg-blue-50 px-3 py-2 text-center text-sm font-bold text-blue-700 shadow-sm">
            <span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-blue-600" />
            {nameA}
          </div>
          <div className="flex-1 rounded-md border-2 border-gray-400 bg-gray-50 px-3 py-2 text-center text-sm font-bold text-gray-700 shadow-sm">
            <span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-gray-700" />
            {nameB}
          </div>
        </div>
      </div>

      {/* CMS reference — Medicare.gov NH publication (NH only) compliance-ok */}
      {isNH && (
        <div className="mt-4">
          <NHGuideLink />
        </div>
      )}

      {/* Template 3f: Population context warning — fires unconditionally (deferred fields) */}
      <div className="mt-4 rounded border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-relaxed text-gray-700">
        <p>{POPULATION_CONTEXT_WARNING}</p>
      </div>

      {/* Grounder text */}
      <p className="mt-4 mb-1 text-sm text-gray-500">
        All data sourced from CMS. Use the filters to explore by condition or category.
      </p>

      {/* Nursing-home-only summary blocks — render between header and measures.
          For hospitals, the existing header + HCAHPS section already covers
          headline data. */}
      {isNH && (
        <div className="mt-6 space-y-4">
          <CompareFiveStar
            measuresA={providerA.measures}
            measuresB={providerB.measures}
            nameA={nameA}
            nameB={nameB}
          />
          <CompareStaffing
            measuresA={providerA.measures}
            measuresB={providerB.measures}
            ctxA={providerA.nursing_home_context}
            ctxB={providerB.nursing_home_context}
            nameA={nameA}
            nameB={nameB}
          />
          <CompareFacilityTimeline providerA={providerA} providerB={providerB} />
          <CompareInspectionSummary
            eventsA={providerA.inspection_events ?? []}
            eventsB={providerB.inspection_events ?? []}
            nameA={nameA}
            nameB={nameB}
            stateA={providerA.address.state}
            stateB={providerB.address.state}
          />
          <CompareOwnership providerA={providerA} providerB={providerB} />
        </div>
      )}

      {/* Main layout: sidebar + measures */}
      <div className="relative mt-6 lg:flex lg:gap-8">
        <CompareNav
          activeTag={activeTag}
          onTagChange={setActiveTag}
          tagCounts={tagCounts}
          kind={kind}
        />

        <div className="min-w-0 flex-1">
          {/* Active filter label */}
          {isFiltered && (
            <div className="mb-4 flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">
                Showing: {activeTag!.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </span>
              <button
                type="button"
                onClick={() => setActiveTag(null)}
                className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500 hover:bg-gray-200"
              >
                Clear
              </button>
            </div>
          )}

          {!isNotReportedFilter && (
            <>
              {/* Patient Experience — hospital HCAHPS only */}
              {isHospital && hcahpsGroupBases.length > 0 && (() => {
                const peCards = hcahpsGroupBases.map((base) => (
                  <CompareHCAHPSGroup
                    key={base}
                    groupBase={base}
                    groupLabel={HCAHPS_GROUPS[base] ?? base}
                    providerA={providerA}
                    providerB={providerB}
                  />
                ));
                const firstCard = peCards[0];
                const restCards = peCards.slice(1);
                const restCount = restCards.length;

                return (
                  <div ref={peRef} className="mb-8">
                    <h2 className="mb-3 text-lg font-semibold text-gray-900">Patient Experience</h2>
                    <div className="space-y-4">
                      {firstCard}
                    </div>
                    {restCount > 0 && !showAllPE && (
                      <button
                        type="button"
                        onClick={() => setShowAllPE(true)}
                        className="mt-4 w-full rounded border border-gray-200 bg-gray-50 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 hover:text-blue-700"
                      >
                        Show all {restCount + 1} patient experience measures
                      </button>
                    )}
                    {showAllPE && (
                      <>
                        <div className="mt-4 space-y-4">
                          {restCards}
                        </div>
                        <div className="mt-4">
                          <button
                            type="button"
                            onClick={() => setShowAllPE(false)}
                            className="w-full rounded border border-gray-200 bg-gray-50 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100"
                          >
                            Collapse patient experience
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                );
              })()}

              {/* Disclosures */}
              <div className="mb-6">
                <MultipleComparisonDisclosure />
              </div>
              {showSES && (
                <div className="mb-4">
                  <SESDisclosureBlock />
                </div>
              )}

              {/* Quality measures — grouped by condition (hospital) or domain (NH) */}
              {sections.length > 0 && (
                <div>
                  {!isFiltered && (
                    <h2 className="mb-4 text-lg font-semibold text-gray-900">
                      Quality Measures by {isNH ? "Domain" : "Condition"}
                    </h2>
                  )}
                  {isFiltered && (
                    <h2 className="mb-4 text-lg font-semibold text-gray-900">
                      Quality Measures
                    </h2>
                  )}

                  {sections.map((section) => (
                    <CollapsibleSection
                      key={section.id}
                      label={section.label}
                      count={section.measureIds.length}
                    >
                      {section.measureIds.map((id) => (
                        <CompareMeasureRow
                          key={id}
                          measureA={measureMapA.get(id) ?? null}
                          measureB={measureMapB.get(id) ?? null}
                          providerNameA={nameA}
                          providerNameB={nameB}
                        />
                      ))}
                    </CollapsibleSection>
                  ))}
                </div>
              )}
            </>
          )}

          {/* Not reported section */}
          {notReportedIds.length > 0 && !isNotReportedFilter && (
            <CollapsibleSection label="Not Reported (Both)" count={notReportedIds.length}>
              {notReportedIds.map((id) => {
                const m = measureMapA.get(id) ?? measureMapB.get(id);
                return m ? (
                  <div key={id} className="rounded border border-gray-200 bg-gray-50 px-4 py-2 text-xs text-gray-500">
                    {m.measure_name ?? m.measure_id}
                    {m.not_reported_reason && <span className="ml-2 text-gray-400">— {m.not_reported_reason}</span>}
                  </div>
                ) : null;
              })}
            </CollapsibleSection>
          )}
          {notReportedIds.length > 0 && isNotReportedFilter && (
            <div className="space-y-1.5">
              {notReportedIds.map((id) => {
                const m = measureMapA.get(id) ?? measureMapB.get(id);
                return m ? (
                  <div key={id} className="rounded border border-gray-200 bg-gray-50 px-4 py-2 text-xs text-gray-500">
                    {m.measure_name ?? m.measure_id}
                    {m.not_reported_reason && <span className="ml-2 text-gray-400">— {m.not_reported_reason}</span>}
                  </div>
                ) : null;
              })}
            </div>
          )}

          {/* Empty state */}
          {nonHcahpsIds.length === 0 && hcahpsGroupBases.length === 0 && notReportedIds.length === 0 && (
            <p className="text-sm text-gray-500">No measures match the selected filter.</p>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-8 border-t border-gray-200 pt-4 text-xs text-gray-500">
        <p>
          Data reflects CMS reporting as of{" "}
          {new Date(providerA.last_updated).toLocaleDateString("en-US", {
            year: "numeric",
            month: "long",
            day: "numeric",
          })}.
        </p>
        <p className="mt-1">
          Comparing: {providerA.provider_id} and {providerB.provider_id}
        </p>
      </footer>

      {/* Fixed bottom collapse bar for Patient Experience — only while PE section is in view */}
      {showAllPE && peInView && (
        <div className="fixed inset-x-0 bottom-12 z-30 border-t border-gray-200 bg-white/95 px-4 py-2 backdrop-blur-sm">
          <button
            type="button"
            onClick={() => setShowAllPE(false)}
            className="mx-auto block max-w-xl rounded border border-gray-200 bg-gray-50 px-6 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100"
          >
            Collapse patient experience
          </button>
        </div>
      )}
    </article>
  );
}

// Wrap in Suspense because useSearchParams requires it in Next.js App Router.
// SentryErrorBoundary captures runtime fetch and render failures — /compare
// is one of two static-export exceptions that fetches CDN JSON at runtime,
// so render-time errors are real production risk.
export function ComparePageClient(): React.JSX.Element {
  return (
    <SentryErrorBoundary scope="compare-page">
      <Suspense fallback={<div className="py-12 text-center text-sm text-gray-500" role="status" aria-live="polite">Loading...</div>}>
        <CompareContent />
      </Suspense>
    </SentryErrorBoundary>
  );
}
