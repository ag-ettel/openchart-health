// Phase 1: implement.
// Hospital profiles only. Reads from provider.hospital_context.
// Nursing home equivalent (NursingHomeContextPanel) deferred to NH display build phase.
// Obligations: see CLAUDE.md: Frontend Specification: Components: ProviderContextPanel

import type { HospitalContext } from "@/types/provider";

interface ProviderContextPanelProps {
  context:      HospitalContext; // provider.hospital_context; caller must guard non-null
  providerName: string;
}

export function ProviderContextPanel(_props: ProviderContextPanelProps): JSX.Element {
  // TODO Phase 1: implement
  //
  // Prominent panel, not a secondary section. Not behind a tab or expand.
  //
  // Visible on initial page load without scrolling within the panel:
  //   staffed_beds, is_critical_access, is_teaching_hospital,
  //   is_emergency_services, dsh_status, dsh_percentage,
  //   dual_eligible_proportion, urban_rural_classification.
  //
  // Secondary row in same panel (may wrap):
  //   offers_cardiac_surgery, offers_cardiac_catheterization,
  //   offers_emergency_cardiac_care, cms_certification_date.
  //
  // No field labeled or presented as a quality measure.
  // dsh_percentage and dual_eligible_proportion labeled as population context,
  // not care quality indicators.
  return <div data-component="ProviderContextPanel" />;
}
