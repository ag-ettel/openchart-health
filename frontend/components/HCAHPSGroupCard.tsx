"use client";

// Collapsed HCAHPS question group card.
// Shows the star rating (if available) and linear score as the headline,
// with response-level breakdown expandable.

import { useState } from "react";
import type { HCAHPSGroup } from "@/lib/measure-tags";
import { formatValue, formatPeriodLabel } from "@/lib/utils";

interface HCAHPSGroupCardProps {
  group: HCAHPSGroup;
  providerLastUpdated: string;
}

export function HCAHPSGroupCard({
  group,
  providerLastUpdated,
}: HCAHPSGroupCardProps): React.JSX.Element {
  const [expanded, setExpanded] = useState(false);

  const headline = group.starRating ?? group.linearScore ?? group.responses[0];
  const period = headline
    ? formatPeriodLabel(headline.period_label)
    : "";
  const starVal = group.starRating?.numeric_value;
  const linearVal = group.linearScore?.numeric_value;

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-5 shadow-sm">
      {/* Category badge */}
      <div className="mb-2">
        <span className="inline-block rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
          Patient Experience
        </span>
      </div>

      {/* Title */}
      <h3 className="mb-1 text-sm font-semibold text-gray-900">
        {group.label}
      </h3>
      {period && (
        <p className="mb-3 text-xs text-gray-400">
          <span className="font-medium text-gray-500">Reporting Period:</span>{" "}
          {period}
        </p>
      )}

      {/* Stat block */}
      <div className="mb-4 rounded-md border border-gray-100 bg-gray-50 px-4 py-3">
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
          {starVal !== null && starVal !== undefined && (
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-gray-400">
                Star Rating
              </div>
              <div className="mt-0.5 text-2xl font-semibold text-gray-800">
                {starVal} / 5
              </div>
            </div>
          )}
          {linearVal !== null && linearVal !== undefined && (
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-gray-400">
                Linear Score
              </div>
              <div className="mt-0.5 text-base font-medium text-gray-600">
                {formatValue(linearVal, "score")}
              </div>
            </div>
          )}
          {headline && headline.sample_size !== null && (
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-gray-400">
                Surveys
              </div>
              <div className="mt-0.5 text-base font-medium text-gray-600">
                {headline.sample_size.toLocaleString("en-US")}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Response breakdown — expandable */}
      {group.responses.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            className="flex w-full items-center justify-between text-xs font-medium text-gray-500 hover:text-gray-700"
            aria-expanded={expanded}
          >
            <span>Response breakdown ({group.responses.length} items)</span>
            <span className="ml-2 text-gray-400">{expanded ? "▲" : "▼"}</span>
          </button>
          {expanded && (
            <div className="mt-3 space-y-2">
              {group.responses.map((r) => {
                const displayName = r.measure_name ?? r.measure_id;
                const val =
                  r.numeric_value !== null
                    ? formatValue(r.numeric_value, r.unit ?? "percent")
                    : r.suppressed
                      ? "Suppressed"
                      : r.not_reported
                        ? "Not reported"
                        : "—";
                return (
                  <div
                    key={r.measure_id}
                    className="flex items-baseline justify-between border-b border-gray-50 py-1 text-xs last:border-b-0"
                  >
                    <span className="text-gray-600">{displayName}</span>
                    <span className="ml-4 shrink-0 font-medium text-gray-700">
                      {val}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Source */}
      <details className="mt-3">
        <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-600">
          Source
        </summary>
        <p className="mt-1 text-xs text-gray-400">
          Source: CMS HCAHPS Patient Survey, {period}. Data reflects CMS
          reporting as of{" "}
          {new Date(providerLastUpdated).toLocaleDateString("en-US", {
            year: "numeric",
            month: "long",
            day: "numeric",
          })}.
        </p>
      </details>
    </div>
  );
}
