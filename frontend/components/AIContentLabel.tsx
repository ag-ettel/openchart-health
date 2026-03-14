// Wraps every SummaryBlock. Never used standalone.
// Obligations: see CLAUDE.md: Frontend Specification: Components: AIContentLabel

import { AI_LABEL_TEXT } from "@/lib/constants";

interface AIContentLabelProps {
  children: React.ReactNode;
}

export function AIContentLabel({ children }: AIContentLabelProps): JSX.Element {
  return (
    <div className="border-l-4 border-blue-200 pl-4">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
        {AI_LABEL_TEXT}
      </p>
      {children}
    </div>
  );
}
