// Displays CMS's own compared_to_national assessment as an attributed data point.
// This is CMS-published data (DEC-022), not a computed verdict.
// All states use the same neutral gray — no directional color coding (DEC-030).
//
// CMS canonical values (DEC-022): BETTER, NO_DIFFERENT, WORSE, TOO_FEW_CASES, NOT_AVAILABLE.
// Returns null when compared_to_national is null (CMS did not publish a comparison
// for this measure, e.g. HCAHPS, T&E process measures).

interface ComparisonBadgeProps {
  comparedToNational: string | null; // measure.compared_to_national
}

const CMS_COMPARISON_LABELS: Record<string, string> = {
  BETTER: "CMS rates as better than the national rate",
  NO_DIFFERENT: "CMS rates as no different from the national rate",
  WORSE: "CMS rates as worse than the national rate",
  TOO_FEW_CASES: "Too few cases for CMS to compare",
  NOT_AVAILABLE: "CMS comparison not available",
};

export function ComparisonBadge({
  comparedToNational,
}: ComparisonBadgeProps): JSX.Element | null {
  if (comparedToNational === null) {
    return null;
  }

  const label =
    CMS_COMPARISON_LABELS[comparedToNational] ??
    `CMS comparison: ${comparedToNational}`;

  return (
    <span className="inline-flex items-center rounded border border-gray-200 bg-gray-50 px-2 py-1 text-xs font-medium text-gray-700">
      {label}
    </span>
  );
}
