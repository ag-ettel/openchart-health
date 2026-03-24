"use client";

// Hospital Summary Dashboard — narrative "at a glance" hook.
// Tells the hospital's story in three parts:
// 1. What is this place? (context badges)
// 2. Is it safe? (CMS assessment narrative + critical flags)
// 3. What should I look at? (sparklines + bridge to categories)

import type { Measure, PaymentAdjustment, HospitalContext } from "@/types/provider";
import { consecutivePenalties, formatValue, measureHasData } from "@/lib/utils";
import { useDistribution } from "@/lib/use-distributions";

interface HospitalSummaryDashboardProps {
  measures: Measure[];
  paymentAdjustments: PaymentAdjustment[];
  hospitalContext: HospitalContext | null;
}

interface AssessmentCounts {
  better: number;
  noDifferent: number;
  worse: number;
  tooFew: number;
  total: number;
}

function countAssessments(measures: Measure[]): AssessmentCounts {
  const primary = measures.filter(
    (m) => !m.stratification && m.compared_to_national !== null && measureHasData(m)
  );
  let better = 0, noDifferent = 0, worse = 0, tooFew = 0;
  for (const m of primary) {
    switch (m.compared_to_national) {
      case "BETTER": better++; break;
      case "NO_DIFFERENT": noDifferent++; break;
      case "WORSE": worse++; break;
      case "TOO_FEW_CASES": tooFew++; break;
    }
  }
  return { better, noDifferent, worse, tooFew, total: better + noDifferent + worse + tooFew };
}

function Sparkline({ values, width = 72, height = 24 }: { values: (number | null)[]; width?: number; height?: number }): React.JSX.Element | null {
  const nums = values.filter((v): v is number => v !== null);
  if (nums.length < 2) return null;
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const range = max - min || 1;
  const p = 2;
  const pW = width - p * 2;
  const pH = height - p * 2;
  const points = nums.map((v, i) => {
    const x = p + (i / (nums.length - 1)) * pW;
    const y = p + pH - ((v - min) / range) * pH;
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg width={width} height={height} className="inline-block">
      <polyline points={points} fill="none" stroke="#2563eb" strokeWidth={1.5} strokeLinejoin="round" />
      {(() => {
        const last = nums[nums.length - 1];
        const x = p + pW;
        const y = p + pH - ((last - min) / range) * pH;
        return <circle cx={x} cy={y} r={2} fill="#2563eb" />;
      })()}
    </svg>
  );
}

/** Patient experience stat box with national average context from distribution data. */
function PEStat({ measure, label }: { measure: Measure | null; label: string }): React.JSX.Element | null {
  const dist = useDistribution(measure?.measure_id ?? "", measure?.period_label ?? "");
  if (!measure || measure.numeric_value === null) return null;

  const val = measure.numeric_value;
  const natAvg = dist ? Math.round(dist.mean) : null;

  return (
    <div className="rounded-md bg-gray-50 px-3 py-2 text-center">
      <div className="text-lg font-bold text-gray-800">{val}%</div>
      <div className="text-xs text-gray-500">{label}</div>
      {natAvg !== null && (
        <div className="mt-0.5 text-xs text-gray-400">
          National avg: {natAvg}%
        </div>
      )}
    </div>
  );
}

/** Headline sentence with national avg context for recommend + rating. */
function PEHeadline({ recommend, rating }: { recommend: Measure; rating: Measure | null }): React.JSX.Element {
  const recDist = useDistribution(recommend.measure_id, recommend.period_label);
  const ratDist = useDistribution(rating?.measure_id ?? "", rating?.period_label ?? "");

  const recVal = recommend.numeric_value!;
  const recAvg = recDist ? Math.round(recDist.mean) : null;
  const ratVal = rating?.numeric_value ?? null;
  const ratAvg = ratDist ? Math.round(ratDist.mean) : null;

  return (
    <p className="mb-3 text-sm leading-relaxed text-gray-700">
      <span className="text-lg font-bold text-blue-700">{recVal}%</span>
      {" "}of patients said they would definitely recommend this hospital
      {recAvg !== null && (
        <span className="text-gray-500"> (national average: {recAvg}%)</span>
      )}
      .
      {ratVal !== null && (
        <>
          {" "}<span className="font-semibold text-gray-800">{ratVal}%</span> rated their experience 9 or 10 out of 10
          {ratAvg !== null && (
            <span className="text-gray-500"> (national average: {ratAvg}%)</span>
          )}
          .
        </>
      )}
    </p>
  );
}

function PEStatsGrid({ measures }: { measures: { measure: Measure | null; label: string }[] }): React.JSX.Element {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {measures.map((m) => (
        <PEStat key={m.label} measure={m.measure} label={m.label} />
      ))}
    </div>
  );
}

export function HospitalSummaryDashboard({
  measures,
  paymentAdjustments,
  hospitalContext,
}: HospitalSummaryDashboardProps): React.JSX.Element {
  const counts = countAssessments(measures);
  const hacrpConsecutive = consecutivePenalties(paymentAdjustments, "HACRP");

  const worseMortality = measures.filter(
    (m) => !m.stratification && m.compared_to_national === "WORSE" &&
    (m.measure_group === "MORTALITY" || m.measure_group === "INFECTIONS")
  );
  const worseAny = measures.filter(
    (m) => !m.stratification && m.compared_to_national === "WORSE" && measureHasData(m)
  );

  // Sparkline measures — patient experience trends (matches the narrative)
  const PE_SPARKLINE_IDS = [
    "H_RECMND_DY",      // Would recommend
    "H_HSP_RATING_9_10", // Rated 9-10
    "H_COMP_1_A_P",     // Nurse communication
    "H_COMP_2_A_P",     // Doctor communication
    "H_CLEAN_HSP_A_P",  // Cleanliness
    "H_QUIET_HSP_A_P",  // Quietness
  ];
  const PE_SPARKLINE_LABELS: Record<string, string> = {
    H_RECMND_DY: "Would recommend",
    H_HSP_RATING_9_10: "Rated 9-10 out of 10",
    H_COMP_1_A_P: "Nurse communication",
    H_COMP_2_A_P: "Doctor communication",
    H_CLEAN_HSP_A_P: "Room cleanliness",
    H_QUIET_HSP_A_P: "Quiet at night",
  };
  const sparklineMeasures = PE_SPARKLINE_IDS
    .map((id) => measures.find((m) => m.measure_id === id && !m.stratification && measureHasData(m) && m.trend && m.trend.length >= 3))
    .filter(Boolean) as Measure[];

  // Build the headline insight — one honest sentence from CMS data
  const betterMeasures = measures.filter(
    (m) => !m.stratification && m.compared_to_national === "BETTER" && measureHasData(m)
  );
  const worseMeasures = worseAny;

  // Group "better" measures by domain for the headline
  const betterDomains = new Map<string, string[]>();
  for (const m of betterMeasures) {
    const GROUP_LABELS: Record<string, string> = {
      MORTALITY: "mortality", INFECTIONS: "infection prevention",
      SAFETY: "patient safety", COMPLICATIONS: "surgical complications",
      READMISSIONS: "readmissions", TIMELY_EFFECTIVE_CARE: "timely care",
      PATIENT_EXPERIENCE: "patient experience", IMAGING_EFFICIENCY: "imaging",
      SPENDING: "spending",
    };
    const label = GROUP_LABELS[m.measure_group] ?? m.measure_group.toLowerCase();
    if (!betterDomains.has(label)) betterDomains.set(label, []);
    betterDomains.get(label)!.push(m.measure_name ?? m.measure_id);
  }

  const headlineSentence = (() => {
    if (counts.total === 0) return null;

    // Lead with the finding, not the methodology
    if (counts.worse === 0 && counts.better > 0) {
      const domains = [...betterDomains.keys()].slice(0, 3);
      return `CMS rates this hospital as better than national averages in ${domains.join(", ")}, with no measures rated below national averages.`;
    }
    if (counts.worse === 0 && counts.better === 0) {
      return "CMS rates this hospital as comparable to national averages across all evaluated measures.";
    }
    if (counts.better > 0 && counts.worse > 0) {
      const betterDom = [...betterDomains.keys()].slice(0, 2);
      return `CMS rates this hospital as better than national averages in ${betterDom.join(" and ")}, but below national averages on ${counts.worse} measure${counts.worse > 1 ? "s" : ""}.`;
    }
    if (counts.better === 0 && counts.worse > 0) {
      return `CMS rates this hospital below national averages on ${counts.worse} measure${counts.worse > 1 ? "s" : ""}, with the remainder comparable to national averages.`;
    }
    return null;
  })();

  // Detail line — the methodology context
  const detailLine = counts.total > 0
    ? `Based on CMS evaluation of ${counts.total} measures: ${counts.better} better, ${counts.noDifferent} no different, ${counts.worse} worse${counts.tooFew > 0 ? `, ${counts.tooFew} too few cases` : ""}.`
    : null;

  // Patient experience snapshot — the most universally relatable data
  const peSnapshot = (() => {
    const find = (id: string) => measures.find(
      (m) => m.measure_id === id && !m.stratification && m.numeric_value !== null
    );
    const recommend = find("H_RECMND_DY");
    const rating = find("H_HSP_RATING_9_10");
    const nurseCom = find("H_COMP_1_A_P");
    const doctorCom = find("H_COMP_2_A_P");
    const clean = find("H_CLEAN_HSP_A_P");
    const quiet = find("H_QUIET_HSP_A_P");

    const surveyCount = recommend?.sample_size ?? nurseCom?.sample_size ?? null;

    return { recommend, rating, nurseCom, doctorCom, clean, quiet, surveyCount };
  })();

  // Context badges
  const badges: string[] = [];
  if (hospitalContext) {
    if (hospitalContext.birthing_friendly_designation) badges.push("Birthing Friendly");
    if (hospitalContext.is_emergency_services) badges.push("Emergency Services");
    if (hospitalContext.is_critical_access) badges.push("Critical Access Hospital");
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-5 shadow-sm">
      <h2 className="mb-3 text-lg font-semibold text-gray-900">At a Glance</h2>

      {/* Context badges — prominent, decision-relevant */}
      {badges.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-3">
          {badges.map((b) => {
            const icon = b === "Birthing Friendly"
              ? <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" /></svg>
              : b === "Emergency Services"
                ? <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                : <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21" /></svg>;
            return (
              <span key={b} className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700">
                {icon}
                {b}
              </span>
            );
          })}
        </div>
      )}

      {/* Patient Experience Snapshot — leads the narrative */}
      {peSnapshot.recommend && (
        <div className="mb-4">
          <p className="mb-1 text-sm font-semibold text-gray-700">
            Patient Experience
          </p>
          <p className="mb-3 text-xs text-gray-400">
            What recent patients reported about their stay, based on a standardized national survey.
          </p>

          {/* Headline with national context */}
          <PEHeadline recommend={peSnapshot.recommend} rating={peSnapshot.rating ?? null} />

          {/* Quick stats grid with national context */}
          <PEStatsGrid measures={[
            { measure: peSnapshot.doctorCom ?? null, label: "Doctors always communicated well" },
            { measure: peSnapshot.nurseCom ?? null, label: "Nurses always communicated well" },
            { measure: peSnapshot.clean ?? null, label: "Room always clean" },
            { measure: peSnapshot.quiet ?? null, label: "Always quiet at night" },
          ]} />

          {peSnapshot.surveyCount && (
            <p className="mt-2 text-xs text-gray-400">
              Based on {peSnapshot.surveyCount.toLocaleString("en-US")} patient surveys (HCAHPS).
              Explore all survey results in the Patient Experience category below.
            </p>
          )}
        </div>
      )}

      {/* Sparkline strip — patient experience trends */}
      {sparklineMeasures.length > 0 && (
        <div className="border-t border-gray-100 pt-4">
          <p className="mb-2 text-xs font-medium text-gray-500">
            Patient Experience Trends
          </p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
            {sparklineMeasures.map((m) => (
              <div key={m.measure_id} className="flex items-center gap-2">
                <Sparkline values={m.trend!.map((t) => t.numeric_value)} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium text-gray-700">
                    {PE_SPARKLINE_LABELS[m.measure_id] ?? m.measure_name ?? m.measure_id}
                  </p>
                  {m.numeric_value !== null && (
                    <p className="text-xs text-gray-400">{m.numeric_value}%</p>
                  )}
                </div>
              </div>
            ))}
          </div>

          <p className="mt-3 text-xs text-gray-400">
            Use the category filters below to explore measures by condition or concern.
          </p>
        </div>
      )}

      {/* CMS Quality Assessment — clinical measures lens */}
      {headlineSentence && (
        <div className="border-t border-gray-100 pt-4">
          <p className="mb-1 text-sm font-semibold text-gray-700">
            CMS Quality Assessment
          </p>
          <p className="mb-2 text-xs text-gray-400">
            Beyond patient experience, CMS evaluates clinical outcomes including mortality, infections, readmissions, and complications.
          </p>
          <p className="text-sm leading-relaxed text-gray-700">
            {headlineSentence}
          </p>

          {counts.total > 0 && (
            <div className="mt-2 flex h-3 overflow-hidden rounded-full">
              {counts.better > 0 && <div className="bg-blue-500" style={{ width: `${(counts.better / counts.total) * 100}%` }} />}
              {counts.noDifferent > 0 && <div className="bg-gray-300" style={{ width: `${(counts.noDifferent / counts.total) * 100}%` }} />}
              {counts.worse > 0 && <div className="bg-orange-400" style={{ width: `${(counts.worse / counts.total) * 100}%` }} />}
              {counts.tooFew > 0 && <div className="bg-gray-200" style={{ width: `${(counts.tooFew / counts.total) * 100}%` }} />}
            </div>
          )}

          {detailLine && <p className="mt-1.5 text-xs text-gray-400">{detailLine}</p>}

          {/* Name the worse measures — bold if tail risk */}
          {worseMeasures.length > 0 && (
            <p className="mt-1.5 text-xs text-gray-500">
              Below national averages on:{" "}
              {worseMeasures.map((m, i) => (
                <span key={m.measure_id}>
                  {i > 0 && ", "}
                  {m.tail_risk_flag ? (
                    <span className="font-semibold text-gray-800">{m.measure_name ?? m.measure_id}</span>
                  ) : (
                    <>{m.measure_name ?? m.measure_id}</>
                  )}
                </span>
              ))}.
            </p>
          )}
        </div>
      )}

      {/* Critical flags */}
      {(hacrpConsecutive >= 2 || worseMortality.length > 0) && (
        <div className="mt-4 space-y-2">
          {hacrpConsecutive >= 2 && (
            <div className="rounded border border-orange-200 bg-orange-50 px-3 py-2 text-xs text-orange-700">
              This hospital has received a patient safety penalty in {hacrpConsecutive} consecutive years.
            </div>
          )}
          {worseMortality.map((m) => (
            <div key={m.measure_id} className="rounded border border-orange-200 bg-orange-50 px-3 py-2 text-xs text-orange-700">
              CMS rates {m.measure_name ?? m.measure_id} as worse than the national rate.
            </div>
          ))}
        </div>
      )}

      {hacrpConsecutive < 2 && worseMortality.length === 0 && worseAny.length === 0 && counts.total > 0 && (
        <p className="mt-3 text-xs text-gray-500">
          No critical safety flags identified by CMS for this hospital.
        </p>
      )}
    </div>
  );
}
