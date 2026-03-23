# Visual Hooks — Landing Experience for Provider Pages

## Problem

Provider pages currently dive straight into metrics. There's no "at a glance" moment
that orients the user and tells the story of this facility before the detail.

---

## Hospital Pages — Summary Dashboard

### Concept: CMS Assessment Snapshot

A compact visual block between the header/context panel and the measures section.
Not a score or ranking — a factual aggregation of CMS's own assessments.

**Components:**

1. **CMS Assessment Summary Bar**
   A horizontal stacked bar (similar to HCAHPS response bars) showing the breakdown
   of CMS compared_to_national across all measures:
   - Blue: "Better than national" count
   - Gray: "No different from national" count
   - Light gray: "Too few cases" count
   - (No red — just neutral gray for "worse" with the count labeled)

   Example: "Of 49 measures with CMS assessments: 12 better, 28 no different,
   3 worse, 6 too few cases to compare."

   This is purely republished CMS data. No editorial framing.

2. **Critical Flags (if any)**
   - HACRP consecutive penalties → orange callout (already exists in CSI section,
     could be promoted to the hook)
   - Any "worse than national" on mortality or infection measures → brief note
   - If none: "No critical safety flags identified by CMS for this hospital."

3. **Sparkline Strip**
   Top 5-6 tail risk measures shown as tiny inline trend sparklines in a horizontal
   row. Each sparkline is ~60px wide, shows the trajectory, and is labeled with the
   short measure name. Click any sparkline to scroll to the full measure card.

   This gives visual rhythm and suggests temporal depth without requiring the user
   to open each measure individually.

4. **Key Context Badges**
   Promote birthing friendly, emergency services, critical access from the context
   panel into more prominent pills/badges at the top. These are decision-relevant
   for someone choosing a hospital.

### Not Included
- No composite score or overall rating (that's CMS's star rating, which we
  de-emphasize per design decisions)
- No "better/worse" color coding on the summary bar
- No "top hospital" or "ranked #X" language

---

## Nursing Home Pages — Event Timeline

### Concept: Facility History Timeline

A visual timeline as the primary landing hook showing the facility's history through
CMS-documented events. This is unique to nursing homes because the data includes
rich temporal event data that hospitals don't have.

**Timeline Events (chronological, newest first):**

1. **Inspection Events**
   - Health inspection dates with deficiency count and severity summary
   - Scope J-L citations highlighted in orange (immediate jeopardy)
   - Complaint inspections distinguished from standard cycles
   - Repeat deficiencies flagged

2. **Penalties**
   - Fine amounts and payment denial periods
   - Fine amount changes (DEC-028 transparency)
   - Penalty clustering patterns visible

3. **Ownership Changes**
   - Association dates for new owners/operators
   - Ownership percentage changes
   - Management company changes
   - Multiple simultaneous changes flagged as a data point (not editorially)

4. **Five-Star Rating Changes**
   - Overall and domain rating changes over time
   - Visible trajectory without editorial characterization

5. **Special Focus Facility Status**
   - Entry/exit from SFF or SFF Candidate status
   - Duration on the list

### Timeline Design
- Vertical timeline with events as cards on alternating sides
- Color coding only for categorical CMS designations (scope J-L = orange,
  SFF = orange) per DEC-030
- Each event card is expandable for detail
- Filters: by event type, by date range
- "This facility at a glance" summary at the top:
  "3 inspections in the last 12 months. 2 fines totaling $X. Ownership
  unchanged since [date]."

### Data Sources
All data already in the schema:
- `provider_inspection_events` — deficiency citations
- `provider_penalties` — fines and payment denials
- `provider_ownership` — entity-level ownership records
- `providers` table — SFF status, Five-Star ratings
- Nursing home measures — quality scores over time

### Legal Constraints (from legal-compliance.md)
- No causal language connecting ownership to quality
- Ownership data and quality data shown as separate panels in the same view
- Temporal proximity is factual; editorial connection is prohibited
- See Rule NH-6 in display-philosophy.md

---

## Implementation Priority

1. **Hospital summary dashboard** — can be built now with existing data
   (compared_to_national aggregation, sparklines from trend data)
2. **Nursing home timeline** — requires nursing home display build (Phase 1
   parallel track), but the data model is ready
