// Obligations: see CLAUDE.md: Frontend Specification: Components: SuppressionIndicator
// Same visual footprint as a numeric value display. Never de-emphasized.

interface SuppressionIndicatorProps {
  suppression_reason: string | null;
}

export function SuppressionIndicator({
  suppression_reason,
}: SuppressionIndicatorProps): JSX.Element {
  return (
    <div className="inline-flex items-center rounded border border-gray-200 bg-gray-50 px-3 py-2">
      <span className="text-sm text-gray-500">
        {suppression_reason ?? "This value was suppressed by CMS."}
      </span>
    </div>
  );
}
