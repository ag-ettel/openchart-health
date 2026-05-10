// Filter row for /filter-explore: state, subtype, name search, clear.
// Sort controls live in the table header (clickable column headers).
//
// All copy comes from lib/constants.ts — no inline strings. Filters AND
// together. The "X of Y hospitals" count is rendered alongside.

"use client";

import {
  FILTER_EXPLORE_CLEAR_FILTERS,
  FILTER_EXPLORE_COUNT_SUMMARY,
  FILTER_EXPLORE_NAME_SEARCH_LABEL_HOSPITAL,
  FILTER_EXPLORE_NAME_SEARCH_LABEL_NURSING_HOME,
  FILTER_EXPLORE_NAME_SEARCH_PLACEHOLDER,
  FILTER_EXPLORE_STATE_ALL,
  FILTER_EXPLORE_STATE_LABEL,
  FILTER_EXPLORE_SUBTYPE_ALL,
  FILTER_EXPLORE_SUBTYPE_LABEL_HOSPITAL,
  FILTER_EXPLORE_SUBTYPE_LABEL_NURSING_HOME,
  type FilterExploreProviderType,
} from "@/lib/constants";

interface FilterExploreFiltersProps {
  states: string[];
  subtypes: string[];
  stateValue: string | null;
  subtypeValue: string | null;
  nameValue: string;
  onStateChange: (s: string | null) => void;
  onSubtypeChange: (s: string | null) => void;
  onNameChange: (s: string) => void;
  onClear: () => void;
  visibleCount: number;
  totalCount: number;
  hasActiveFilter: boolean;
  providerType?: FilterExploreProviderType;
}

export function FilterExploreFilters({
  states,
  subtypes,
  stateValue,
  subtypeValue,
  nameValue,
  onStateChange,
  onSubtypeChange,
  onNameChange,
  onClear,
  visibleCount,
  totalCount,
  hasActiveFilter,
  providerType = "HOSPITAL",
}: FilterExploreFiltersProps): React.JSX.Element {
  const subtypeLabel =
    providerType === "NURSING_HOME"
      ? FILTER_EXPLORE_SUBTYPE_LABEL_NURSING_HOME
      : FILTER_EXPLORE_SUBTYPE_LABEL_HOSPITAL;
  const nameLabel =
    providerType === "NURSING_HOME"
      ? FILTER_EXPLORE_NAME_SEARCH_LABEL_NURSING_HOME
      : FILTER_EXPLORE_NAME_SEARCH_LABEL_HOSPITAL;
  return (
    <div className="mb-3 flex flex-wrap items-end gap-3 border-b border-gray-200 pb-3">
      <div className="flex flex-col">
        <label htmlFor="filter-state" className="mb-1 text-xs font-medium text-gray-600">
          {FILTER_EXPLORE_STATE_LABEL}
        </label>
        <select
          id="filter-state"
          value={stateValue ?? ""}
          onChange={(e) => onStateChange(e.target.value || null)}
          className="rounded border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-700 focus:outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-500 focus:border-blue-500"
        >
          <option value="">{FILTER_EXPLORE_STATE_ALL}</option>
          {states.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col">
        <label htmlFor="filter-subtype" className="mb-1 text-xs font-medium text-gray-600">
          {subtypeLabel}
        </label>
        <select
          id="filter-subtype"
          value={subtypeValue ?? ""}
          onChange={(e) => onSubtypeChange(e.target.value || null)}
          className="rounded border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-700 focus:outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-500 focus:border-blue-500"
        >
          <option value="">{FILTER_EXPLORE_SUBTYPE_ALL}</option>
          {subtypes.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-1 min-w-[200px] flex-col">
        <label htmlFor="filter-name" className="mb-1 text-xs font-medium text-gray-600">
          {nameLabel}
        </label>
        <input
          id="filter-name"
          type="text"
          value={nameValue}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder={FILTER_EXPLORE_NAME_SEARCH_PLACEHOLDER}
          className="rounded border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-700 placeholder:text-gray-500 focus:outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-500 focus:border-blue-500"
        />
      </div>

      <div className="ml-auto flex items-center gap-3">
        <span className="text-xs text-gray-500">
          {FILTER_EXPLORE_COUNT_SUMMARY(visibleCount, totalCount, providerType)}
        </span>
        {hasActiveFilter && (
          <button
            type="button"
            onClick={onClear}
            className="rounded border border-gray-300 bg-white px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-50"
          >
            {FILTER_EXPLORE_CLEAR_FILTERS}
          </button>
        )}
      </div>
    </div>
  );
}
