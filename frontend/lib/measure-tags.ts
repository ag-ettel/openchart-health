// Measure tagging system for consumer-facing category navigation.
//
// Each measure can have multiple tags. The sidebar filters by tag — selecting
// a tag shows all measures with that tag. Measures appear once on the page;
// the filter controls visibility.
//
// Tags are derived from measure_id patterns and tail_risk_flag. This keeps
// the mapping in the frontend (display concern) rather than the pipeline.

import type { Measure } from "@/types/provider";

export interface MeasureTag {
  id: string;
  label: string;
  /** Display order in the sidebar */
  order: number;
}

// Canonical tag definitions in display order.
// Order reflects consumer priority: safety-critical first, conditions grouped,
// process measures after, utilization/cost last, status at the end.
export const MEASURE_TAGS: MeasureTag[] = [
  // Safety & outcomes — what can seriously harm you
  { id: "critical_safety",    label: "Critical Safety Indicators", order: 0 },
  { id: "mortality",          label: "Mortality",                   order: 1 },
  { id: "infections",         label: "Infections",                 order: 2 },
  { id: "complications",      label: "Complications & Safety",     order: 3 },
  { id: "readmissions",       label: "Readmissions",               order: 4 },
  // Conditions — grouped by body system / procedure
  { id: "heart",              label: "Heart & Cardiac",            order: 10 },
  { id: "lung",               label: "Lung & Respiratory",         order: 11 },
  { id: "stroke",             label: "Stroke",                     order: 12 },
  { id: "orthopedic",         label: "Hip & Knee",                 order: 13 },
  { id: "colonoscopy",        label: "Colonoscopy & Colon",        order: 14 },
  { id: "cataract",           label: "Cataract Surgery",           order: 15 },
  { id: "cancer",             label: "Cancer & Chemotherapy",      order: 16 },
  { id: "sepsis",             label: "Sepsis",                     order: 17 },
  { id: "vte",                label: "Blood Clots (VTE)",          order: 18 },
  { id: "opioid",             label: "Opioid Safety",              order: 19 },
  // Process & experience measures
  { id: "timely_emergency",   label: "Timely & Emergency Care",    order: 20 },
  { id: "surgical",           label: "Surgical & Procedural",      order: 21 },
  { id: "patient_experience", label: "Patient Experience",         order: 22 },
  // Utilization & cost
  { id: "imaging",            label: "Imaging Efficiency",         order: 30 },
  { id: "spending",           label: "Spending",                   order: 31 },
  // Status
  { id: "not_reported",       label: "Not Reported",               order: 90 },
];

// Tag groups for sidebar sections
export const SAFETY_TAGS = MEASURE_TAGS.filter((t) => t.order >= 0 && t.order < 10);
export const CONDITION_TAGS = MEASURE_TAGS.filter((t) => t.order >= 10 && t.order < 20);
export const PROCESS_TAGS = MEASURE_TAGS.filter((t) => t.order >= 20 && t.order < 30);
export const UTILIZATION_TAGS = MEASURE_TAGS.filter((t) => t.order >= 30 && t.order < 90);
export const STATUS_TAGS = MEASURE_TAGS.filter((t) => t.order >= 90);

/** Derive tags for a measure from its properties and ID patterns. */
export function getTagsForMeasure(m: Measure): string[] {
  const tags: string[] = [];
  const id = m.measure_id;

  // Not reported — separate category, not mixed into domain tags
  if (m.suppressed || m.not_reported) {
    tags.push("not_reported");
    // Still tag with domain so filtering by domain includes them if desired,
    // but they won't appear in Critical Safety Indicators
  }

  // Critical Safety Indicators — only tail_risk measures WITH data
  if (m.tail_risk_flag && !m.suppressed && !m.not_reported) {
    tags.push("critical_safety");
  }

  // Domain tags from measure_group
  switch (m.measure_group) {
    case "INFECTIONS":
      tags.push("infections");
      break;
    case "MORTALITY":
      tags.push("mortality");
      break;
    case "COMPLICATIONS":
      tags.push("complications");
      break;
    case "SAFETY":
      tags.push("complications"); // PSI measures → Complications & Safety
      break;
    case "READMISSIONS":
      tags.push("readmissions");
      break;
    case "IMAGING_EFFICIENCY":
      tags.push("imaging");
      break;
    case "PATIENT_EXPERIENCE":
      tags.push("patient_experience");
      break;
    case "SPENDING":
      // Fix misclassified HCAHPS measures
      if (id.startsWith("H_")) {
        tags.push("patient_experience");
      } else {
        tags.push("spending");
      }
      break;
    case "TIMELY_EFFECTIVE_CARE":
      // Sub-categorize the grab bag
      if (id.startsWith("SEP_") || id.startsWith("SEV_SEP_")) {
        tags.push("timely_emergency");
        tags.push("sepsis");
      } else if (id.startsWith("OP_18") || id === "OP_22" || id === "OP_40") {
        tags.push("timely_emergency");
      } else if (id.startsWith("STK_") || id.startsWith("VTE_")) {
        tags.push("surgical");
      } else if (id === "OP_29" || id === "OP_31" || id === "SAFE_USE_OF_OPIOIDS") {
        tags.push("surgical");
      } else if (id.startsWith("OP_35")) {
        tags.push("surgical");
        tags.push("cancer");
      } else if (id.startsWith("HH_")) {
        tags.push("complications"); // Hospital Harm measures
      } else if (id === "OP_23") {
        tags.push("timely_emergency"); // Head CT results
      } else {
        tags.push("timely_emergency"); // default for T&E
      }
      break;
    default:
      // Unknown group — no domain tag
      break;
  }

  // Condition tags from measure_id patterns
  if (/AMI|CABG|HF|STEMI|OP_40/.test(id) && !id.startsWith("H_")) {
    tags.push("heart");
  }
  if (/COPD|PN(?!_)|_PN$/.test(id) && !id.startsWith("H_")) {
    tags.push("lung");
  }
  if (/HIP_KNEE/.test(id)) {
    tags.push("orthopedic");
  }
  if (/STK_/.test(id)) {
    tags.push("stroke");
  }
  if (/SEP_|SEV_SEP_/.test(id) || (id === "PSI_13")) {
    tags.push("sepsis");
  }
  if (/OP_35|OP_39/.test(id)) {
    tags.push("cancer");
  }
  if (/OP_29|OP_32/.test(id) || id === "HAI_3_SIR") {
    tags.push("colonoscopy");
  }
  if (id === "OP_31") {
    tags.push("cataract");
  }
  if (/VTE_|PSI_12/.test(id)) {
    tags.push("vte");
  }
  if (/OPIOID|HH_ORAE/.test(id)) {
    tags.push("opioid");
  }

  return [...new Set(tags)]; // deduplicate
}

// --- HCAHPS Collapse ---

/** HCAHPS question groups. Key = group base, value = consumer label. */
export const HCAHPS_GROUPS: Record<string, string> = {
  H_COMP_1:         "Nurse Communication",
  H_COMP_2:         "Doctor Communication",
  H_COMP_3:         "Staff Responsiveness",
  H_COMP_5:         "Communication About Medicines",
  H_COMP_6:         "Discharge Information",
  H_COMP_7:         "Care Transition",
  H_CLEAN:          "Cleanliness",
  H_CLEAN_HSP:      "Room Cleanliness",
  H_QUIET:          "Quietness",
  H_QUIET_HSP:      "Quietness at Night",
  H_HSP_RATING:     "Overall Hospital Rating",
  H_RECMND:         "Would Recommend",
  H_NURSE_EXPLAIN:  "Nurse Explanations",
  H_NURSE_LISTEN:   "Nurse Listening",
  H_NURSE_RESPECT:  "Nurse Courtesy & Respect",
  H_DOCTOR_EXPLAIN: "Doctor Explanations",
  H_DOCTOR_LISTEN:  "Doctor Listening",
  H_DOCTOR_RESPECT: "Doctor Courtesy & Respect",
  H_MED_FOR:        "New Medication Purpose",
  H_SIDE_EFFECTS:   "Medication Side Effects",
  H_DISCH_HELP:     "Post-Discharge Help",
  H_SYMPTOMS:       "Symptom Information",
  H_BATH_HELP:      "Bathing Help",
  H_CALL_BUTTON:    "Call Button Responsiveness",
  H_CT_MED:         "Care Transition: Medications",
  H_CT_PREFER:      "Care Transition: Preferences",
  H_CT_UNDER:       "Care Transition: Understanding",
};

export interface HCAHPSGroup {
  groupBase: string;
  label: string;
  /** The star rating measure, if present */
  starRating: Measure | null;
  /** The linear score measure, if present */
  linearScore: Measure | null;
  /** Always/Usually/Sometimes-Never or Yes/No response breakdown */
  responses: Measure[];
}

/** Extract the HCAHPS group base from a measure ID. */
function hcahpsBase(id: string): string | null {
  // Try longest match first
  const sorted = Object.keys(HCAHPS_GROUPS).sort((a, b) => b.length - a.length);
  for (const base of sorted) {
    if (id.startsWith(base + "_") || id === base) return base;
  }
  return null;
}

/** Returns true if this measure is part of an HCAHPS question group. */
export function isHCAHPS(m: Measure): boolean {
  return m.measure_id.startsWith("H_") && m.measure_id !== "H_STAR_RATING";
}

/** Group HCAHPS measures into collapsed question groups. */
export function groupHCAHPS(measures: Measure[]): HCAHPSGroup[] {
  const hcahps = measures.filter(isHCAHPS);
  const groupMap = new Map<string, HCAHPSGroup>();

  for (const m of hcahps) {
    const base = hcahpsBase(m.measure_id);
    if (!base) continue;

    if (!groupMap.has(base)) {
      groupMap.set(base, {
        groupBase: base,
        label: HCAHPS_GROUPS[base] ?? base,
        starRating: null,
        linearScore: null,
        responses: [],
      });
    }
    const group = groupMap.get(base)!;

    if (m.measure_id.endsWith("_STAR_RATING")) {
      group.starRating = m;
    } else if (m.measure_id.endsWith("_LINEAR_SCORE")) {
      group.linearScore = m;
    } else {
      group.responses.push(m);
    }
  }

  return Array.from(groupMap.values()).sort((a, b) =>
    a.label.localeCompare(b.label)
  );
}
