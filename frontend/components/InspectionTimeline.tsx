"use client";

// InspectionTimeline — compact accordion view of inspection events.
// Each inspection is a one-line summary with expandable citation detail.
//
// Display rules (display-philosophy.md NH-8):
// - Scope/severity codes A-L with plain language and visual hierarchy
// - J/K/L (immediate jeopardy) get orange threshold treatment
// - Contested citations: show current scope as primary, original as secondary
// - DEC-028: contested citation transparency

import { useState } from "react";
import type { InspectionEvent } from "@/types/provider";
import {
  SCOPE_SEVERITY_DESCRIPTIONS,
  DEFICIENCY_CATEGORY_PLAIN,
  scopeSeverityTier,
  scopeSeveritySummary,
  type SeverityTier,
} from "@/lib/constants";

interface InspectionTimelineProps {
  inspectionEvents: InspectionEvent[];
  providerLastUpdated: string;
}

interface InspectionGroup {
  surveyDate: string;
  surveyType: string | null;
  citations: InspectionEvent[];
  hasIJ: boolean;
  ijCount: number;
  hasComplaint: boolean;
}

function groupBySurveyDate(events: InspectionEvent[]): InspectionGroup[] {
  const groups = new Map<string, InspectionGroup>();
  for (const e of events) {
    const key = e.survey_date ?? "Unknown";
    if (!groups.has(key)) {
      groups.set(key, {
        surveyDate: key,
        surveyType: e.survey_type,
        citations: [],
        hasIJ: false,
        ijCount: 0,
        hasComplaint: false,
      });
    }
    const g = groups.get(key)!;
    g.citations.push(e);
    if (e.is_immediate_jeopardy) { g.hasIJ = true; g.ijCount++; }
    if (e.is_complaint_deficiency) g.hasComplaint = true;
  }
  return Array.from(groups.values()).sort((a, b) =>
    b.surveyDate.localeCompare(a.surveyDate)
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return "Date not available";
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

const TIER_STYLES: Record<SeverityTier, string> = {
  low: "border-gray-200 bg-white",
  moderate: "border-gray-300 bg-gray-50",
  high: "border-gray-400 bg-gray-50",
  immediate_jeopardy: "border-orange-200 bg-orange-50",
};

const TIER_CODE_STYLES: Record<SeverityTier, string> = {
  low: "bg-gray-100 text-gray-500",
  moderate: "bg-gray-200 text-gray-600",
  high: "bg-gray-300 text-gray-700",
  immediate_jeopardy: "bg-orange-100 text-orange-700",
};

function CitationCard({ event }: { event: InspectionEvent }): React.JSX.Element {
  const tier = scopeSeverityTier(event.scope_severity_code);
  const summary = scopeSeveritySummary(event.scope_severity_code);
  const cmsDesc = event.scope_severity_code
    ? SCOPE_SEVERITY_DESCRIPTIONS[event.scope_severity_code.toUpperCase()]
    : null;
  const categoryPlain = event.deficiency_category
    ? DEFICIENCY_CATEGORY_PLAIN[event.deficiency_category] ?? null
    : null;

  return (
    <div className={`rounded border px-3 py-2.5 ${TIER_STYLES[tier]}`}>
      <div className="flex items-center gap-2">
        {event.scope_severity_code && (
          <span className={`inline-flex shrink-0 items-center rounded px-1.5 py-0.5 text-xs font-semibold ${TIER_CODE_STYLES[tier]}`}>
            {event.scope_severity_code}
          </span>
        )}
        {categoryPlain && (
          <span className="text-xs font-medium text-gray-600">{categoryPlain}</span>
        )}
        {event.is_complaint_deficiency && (
          <span className="rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500">Complaint</span>
        )}
        <span className="ml-auto text-[10px] text-gray-400">Tag {event.deficiency_tag}</span>
      </div>

      {summary && (
        <p className="mt-1.5 text-sm font-medium text-gray-700">{summary}</p>
      )}

      {event.deficiency_description && (
        <p className="mt-1 text-xs text-gray-500">
          <span className="font-medium text-gray-500">CMS requirement not met: </span>
          {event.deficiency_description}
        </p>
      )}

      {cmsDesc && (
        <p className="mt-1 text-[10px] text-gray-400">
          CMS classification: {cmsDesc}
        </p>
      )}

      {event.is_contested && event.originally_published_scope_severity && (
        <div className="mt-2 rounded bg-gray-50 px-2.5 py-1.5 text-xs text-gray-600">
          <p>
            Originally classified as{" "}
            <span className="font-semibold">{event.originally_published_scope_severity}</span>
            {" "}({scopeSeveritySummary(event.originally_published_scope_severity)}).
          </p>
          <p>
            Current CMS classification:{" "}
            <span className="font-semibold">{event.scope_severity_code ?? "Not available"}</span>
            {event.scope_severity_code && (
              <> ({scopeSeveritySummary(event.scope_severity_code)})</>
            )}.
          </p>
          {event.scope_severity_history?.some((h) => h.idr) && (
            <p className="mt-1 text-gray-500">Subject to Informal Dispute Resolution.</p>
          )}
        </div>
      )}

      {event.correction_date && (
        <p className="mt-1.5 text-[10px] text-gray-400">
          Corrected: {formatDate(event.correction_date)}
        </p>
      )}
    </div>
  );
}

export function InspectionTimeline({
  inspectionEvents,
  providerLastUpdated,
}: InspectionTimelineProps): React.JSX.Element {
  const groups = groupBySurveyDate(inspectionEvents);
  const [expandedDates, setExpandedDates] = useState<Set<string>>(new Set());

  const toggleDate = (date: string) => setExpandedDates((prev: Set<string>) => {
    const next = new Set(prev);
    if (next.has(date)) next.delete(date);
    else next.add(date);
    return next;
  });

  if (groups.length === 0) {
    return (
      <section aria-label="Inspection history">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Inspection Detail</h2>
        <p className="text-sm text-gray-500">
          No inspection deficiency citations in the current CMS data for this facility.
        </p>
      </section>
    );
  }

  const totalCitations = inspectionEvents.length;
  const ijTotal = inspectionEvents.filter((e) => e.is_immediate_jeopardy).length;

  return (
    <section aria-label="Inspection history">
      <h2 className="mb-2 text-lg font-semibold text-gray-900">Inspection Detail</h2>
      <p className="mb-1 text-xs text-gray-500">
        {totalCitations} citation{totalCitations !== 1 ? "s" : ""} across{" "}
        {groups.length} inspection{groups.length !== 1 ? "s" : ""}.
        {ijTotal > 0 && (
          <span className="font-medium text-orange-600"> {ijTotal} immediate jeopardy.</span>
        )}
      </p>
      <p className="mb-3 text-xs text-gray-400">
        Source: CMS Health Deficiencies dataset. Data as of {formatDate(providerLastUpdated)}.
        Expand each inspection to see individual citations.
      </p>

      <div className="space-y-1.5">
        {groups.map((group) => {
          const isExpanded = expandedDates.has(group.surveyDate);
          return (
            <div key={group.surveyDate}>
              {/* Compact one-line summary — clickable to expand */}
              <button
                type="button"
                onClick={() => toggleDate(group.surveyDate)}
                className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left transition-colors ${
                  isExpanded ? "bg-gray-100" : "bg-gray-50 hover:bg-gray-100"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-gray-800">
                    {formatDate(group.surveyDate)}
                  </span>
                  {group.surveyType && (
                    <span className="text-xs text-gray-400">{group.surveyType}</span>
                  )}
                  {group.hasComplaint && (
                    <span className="text-[10px] text-gray-400">(complaint)</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">
                    {group.citations.length} citation{group.citations.length !== 1 ? "s" : ""}
                  </span>
                  {group.hasIJ && (
                    <span className="rounded-full bg-orange-50 px-2 py-0.5 text-[10px] font-medium text-orange-700">
                      {group.ijCount} IJ
                    </span>
                  )}
                  <svg
                    className={`h-4 w-4 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>

              {/* Expanded citation detail */}
              {isExpanded && (
                <div className="ml-3 mt-1.5 space-y-2 border-l-2 border-gray-200 pl-3 pb-2">
                  {group.citations
                    .sort((a, b) => {
                      if (a.is_immediate_jeopardy !== b.is_immediate_jeopardy)
                        return a.is_immediate_jeopardy ? -1 : 1;
                      return (b.scope_severity_code ?? "").localeCompare(a.scope_severity_code ?? "");
                    })
                    .map((e, i) => (
                      <CitationCard key={`${e.deficiency_tag}-${i}`} event={e} />
                    ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
