// Always rendered inside AIContentLabel. Never standalone.
// Obligations: see CLAUDE.md: Frontend Specification: Components: SummaryBlock

import type { Summary } from "@/types/provider";

interface SummaryBlockProps {
  summary: Summary;
}

export function SummaryBlock({ summary }: SummaryBlockProps): JSX.Element {
  // No visual distinction between fallback_used true/false.
  // Fallback text is validated safe for display as-is.
  return (
    <p className="text-base leading-relaxed text-gray-900">
      {summary.summary_text}
    </p>
  );
}
