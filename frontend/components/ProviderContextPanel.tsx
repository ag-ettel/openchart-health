// Hospital context panel — interpretive context fields, not quality measures.
// Star rating removed — displayed alongside other CMS ratings in the measures section.
// Deferred fields removed from consumer display (documented in ses-context.md).

import type { HospitalContext } from "@/types/provider";

interface ProviderContextPanelProps {
  context: HospitalContext;
  providerName: string;
}

function ContextRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <div className="flex items-baseline justify-between border-b border-gray-100 py-2 text-sm last:border-b-0">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-700">{children}</span>
    </div>
  );
}

function formatBool(val: boolean | null, trueLabel: string, falseLabel: string): string {
  if (val === null) return "Not available";
  return val ? trueLabel : falseLabel;
}

export function ProviderContextPanel({
  context,
  providerName,
}: ProviderContextPanelProps): React.JSX.Element {
  return (
    <div className="rounded border border-gray-200 bg-white px-4 py-4">
      <h2 className="mb-1 text-sm font-semibold text-gray-900">
        Hospital Context
      </h2>
      <p className="mb-3 text-xs text-gray-500">
        These fields are interpretive context, not quality measures.
      </p>

      <div>
        <ContextRow label="Critical Access Hospital">
          {formatBool(context.is_critical_access, "Yes", "No")}
        </ContextRow>
        <ContextRow label="Emergency Services">
          {formatBool(context.is_emergency_services, "Yes", "No")}
        </ContextRow>
        <ContextRow label="Birthing Friendly Designation">
          {formatBool(context.birthing_friendly_designation, "Yes", "No")}
        </ContextRow>
      </div>
    </div>
  );
}
