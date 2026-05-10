import type { Metadata } from "next";
import { buildMethodologyMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMethodologyMetadata();

export default function MethodologyPage(): React.JSX.Element {
  return (
    <article className="prose prose-sm prose-gray max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900">Methodology</h1>
      <p className="text-sm leading-relaxed text-gray-600">
        This page explains how OpenChart Health processes and displays CMS
        hospital and nursing home quality data. All data shown on this site is
        sourced from the Centers for Medicare &amp; Medicaid Services (CMS)
        Provider Data Catalog and related CMS publications. The site is a data
        aggregator: it republishes federal data with statistical uncertainty
        made visible. It does not produce ratings or rankings of its own. {/* compliance-ok */}
      </p>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        Two-Tier Measure Descriptions
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        Each measure is described twice. A plain-language gloss (8th-grade
        reading level) is presented first for readability — this is our
        consumer-friendly interpretation, not a CMS definition. Where
        available, the verbatim CMS measure definition follows in a labeled
        block: &quot;CMS defines this measure as: ...&quot;. The CMS definition
        is the legally authoritative description; the plain-language gloss is
        supplementary. The two are presented together so any drift between
        them is visible to readers.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        Why No Directional Color Coding
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        Measure values render in neutral gray, not red or green. Color coding
        a value as &quot;good&quot; or &quot;bad&quot; relative to an average
        is an editorial judgment, and averages themselves carry uncertainty.
        Visual position relative to the national average — shown on the
        benchmark bar and the distribution histogram — communicates the
        comparison without imposing a third-party verdict. Color is reserved
        for two threshold-based signals: tail-risk states defined by external
        standards (immediate jeopardy citations, Special Focus Facility
        status, abuse findings) and repeat deficiencies cited across multiple
        inspection cycles. These are CMS&apos;s own categorical
        determinations, not statistical comparisons.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        Tail Risk in the Primary View
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        Mortality, infections, complications, and other adverse-event measures
        appear in the primary profile view alongside other measures. They are
        not buried in a sub-panel. Adverse events are low-frequency and
        high-severity by nature; presenting them at the same level as
        higher-frequency process measures keeps the asymmetry visible to
        readers. Each tail-risk measure is flagged with a category badge.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        Three Reporting States: Reported, Suppressed, Not Reported
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        A measure can be in three distinct states, each displayed prominently
        rather than hidden. <strong>Reported</strong> values include a numeric
        value, sample size, period label, and any applicable footnote codes.
        <strong>Suppressed</strong> values are ones CMS has withheld — usually
        because the sample is too small to publish without privacy or
        reliability concerns. The reason is shown alongside the suppression
        notice. <strong>Not reported</strong> values are ones the provider
        did not submit to CMS at all. This is a distinct state from
        suppression, and it is surfaced at full visual weight: a missing
        report is itself information about the provider.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        Interval Estimates
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        Every measure on this site displays an interval estimate alongside the
        point value. Interval estimates reflect statistical uncertainty — the
        range within which the true value plausibly falls given the available
        data. A narrower interval means more precision; a wider interval means
        more uncertainty.
      </p>
      <p className="text-sm leading-relaxed text-gray-600">
        Where CMS publishes interval bounds for a measure, we display those
        values directly. For measures where CMS publishes a rate and sample size
        but not interval bounds, we calculate a 95% Bayesian credible interval
        using a Beta-Binomial model. This includes patient experience survey
        measures (HCAHPS), where CMS adjusts for patient mix but does not
        publish interval bounds — the sampling uncertainty from finite survey
        counts is real and the adjusted percentage is treated as a binomial
        proportion. The prior is informed by the CMS-published state average
        rate for the measure when available, or the CMS-published national
        average rate as a fallback. When neither CMS-published average is
        available, an uninformative prior is used. This approach provides
        meaningful uncertainty estimates while appropriately shrinking extreme
        rates from very small samples toward the population average.
      </p>

      <h3 className="mt-6 text-base font-semibold text-gray-900">
        Patient Experience Survey Intervals
      </h3>
      <p className="text-sm leading-relaxed text-gray-600">
        HCAHPS patient experience scores are adjusted by CMS for patient mix
        (age, education, language, etc.) to allow fair comparison across
        hospitals. CMS does not publish interval bounds for these measures, but
        the sampling uncertainty from the number of completed surveys is real. A
        hospital where 50 patients completed the survey has much more
        uncertainty than one where 5,000 did.
      </p>
      <p className="text-sm leading-relaxed text-gray-600">
        We calculate credible intervals for the primary response on each survey
        question (the &quot;Always,&quot; &quot;Definitely Yes,&quot; or
        &quot;9-10&quot; percentage) by treating the adjusted percentage as a
        binomial proportion with the number of completed surveys as the
        denominator. These intervals are labeled as &quot;calculated using a
        Bayesian Beta-Binomial model&quot; to distinguish them from
        CMS-published intervals.
      </p>

      <h3 className="mt-6 text-base font-semibold text-gray-900">
        Why Some Intervals Are Very Wide
      </h3>
      <p className="text-sm leading-relaxed text-gray-600">
        For HGLM-adjusted measures (mortality, readmissions, complications),
        CMS-published intervals are often wider than users expect. This is
        because the CMS hierarchical model accounts for uncertainty between
        hospitals, not just within a single hospital&apos;s data. A hospital with
        1,800 patients may still have a wide interval because the model is
        conservative about how much the data should shift the estimate away from
        the national average.
      </p>
      <p className="text-sm leading-relaxed text-gray-600">
        On the distribution histogram, this means the blue shaded region (showing
        the plausible range for a hospital&apos;s result) may cover a large
        portion of the national distribution. This is not a display error — it
        reflects the genuine statistical uncertainty in these estimates. When the
        blue zone spans most of the distribution, it means the data does not
        provide strong evidence that this hospital differs from average.
      </p>

      <h3 className="mt-6 text-base font-semibold text-gray-900">
        Small Sample Sizes
      </h3>
      <p className="text-sm leading-relaxed text-gray-600">
        Measures based on fewer than 30 cases carry an amber warning. With small
        samples, the observed rate is highly uncertain and may not reflect the
        hospital&apos;s typical performance. The distribution histogram
        visualizes this — a wide blue zone on a small-sample measure shows that
        the true rate could fall almost anywhere in the national distribution.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        Standardized Infection Ratios (SIR)
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        Healthcare-associated infection measures use the CDC&apos;s Standardized
        Infection Ratio (SIR). A ratio of 1.0 means the hospital had exactly
        as many infections as expected given its patient volume and case mix.
        Below 1.0 means fewer infections than expected; above 1.0 means more.
      </p>
      <p className="text-sm leading-relaxed text-gray-600">
        The &quot;expected&quot; rate is based on a national baseline period. As
        infection prevention has improved nationally, the average hospital now
        performs better than the baseline — which is why the national average SIR
        for many infection types is below 1.0. This does not mean the baseline
        is wrong; it means hospitals have collectively improved since it was set.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        CMS Direction Indicators
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        Each measure displays which direction CMS designates as associated with
        better outcomes — either &quot;lower is better&quot; (e.g., death rates,
        infection ratios) or &quot;higher is better&quot; (e.g., patient
        experience scores, compliance rates). This directional guidance comes
        from CMS technical documentation, not from this site&apos;s editorial
        judgment.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        Distribution Histograms
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        Each measure card includes a histogram showing how all hospitals
        nationally are distributed on that measure. The histogram uses 25 bins
        computed from all reporting hospitals for the same measure and period.
      </p>
      <ul className="text-sm leading-relaxed text-gray-600">
        <li>
          <strong>Blue shading</strong> marks the bins that fall within this
          hospital&apos;s interval estimate — the plausible range for the true
          value. A wider blue zone means more uncertainty.
        </li>
        <li>
          <strong>Blue dashed line</strong> shows this hospital&apos;s observed
          value.
        </li>
        <li>
          <strong>Orange dashed line</strong> shows the national average.
        </li>
      </ul>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        Comparing Two Providers
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        The compare page renders two providers side by side on the same
        measures. For each measure, both providers&apos; values appear on a
        single horizontal axis with their credible intervals as
        whisker-and-band marks and the national average as a reference line.
        When the two intervals overlap, a note states that the difference
        between the providers may not be meaningful given the available data;
        when they do not overlap, the note states that the difference appears
        meaningful. This is a conservative factual statement, not a verdict.
        Trend lines for both providers are overlaid on the same chart so
        trajectory differences are visible without scanning between separate
        charts.
      </p>
      <p className="text-sm leading-relaxed text-gray-600">
        State averages are intentionally omitted from the side-by-side
        interval plot. Two providers from different states would have
        different state-level reference values for the same measure, and
        showing only one (or both) would clutter the visualization without
        clarifying the comparison. State averages remain available on the
        per-provider benchmark bar.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        Sort and Filter, Not Ranking {/* compliance-ok */}
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        The Explore view lets users sort hospitals or nursing homes by any
        CMS-reported measure and filter by state, subtype, or name. This is
        factual ordering of CMS data — the same operation as sorting a
        spreadsheet column. The default sort when a measure is selected is
        alphabetical by provider name, not by value: the tool does not
        editorialize which end of the value distribution matters. When a user
        sorts by value, the column renders with full context (sample size,
        period label, footnote codes, suppression state) so the sorted view
        is not stripped of the qualifications that accompany every value
        elsewhere on the site.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        Nursing Home Specifics
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        <strong>Five-Star Ratings.</strong> CMS publishes a Five-Star overall
        rating with three domain sub-ratings (health inspection, staffing,
        quality measures). Star ratings are ordinal categorical outputs, not
        continuous rates — credible intervals do not apply to them. Instead
        of placing uncertainty bands on the stars, the site shows the
        constituent measures that feed each domain so the inputs are visible.
      </p>
      <p className="text-sm leading-relaxed text-gray-600">
        <strong>Scope and Severity Codes.</strong> Inspection deficiencies
        are coded A through L. Codes A–C indicate no harm with minimal risk;
        D–F indicate no harm with potential for more than minimal harm; G–I
        indicate actual harm short of immediate jeopardy; J–L indicate
        immediate jeopardy to resident health or safety. J–L citations and
        repeat deficiencies in the same category across multiple inspection
        cycles are the only states where color encoding is used (orange).
      </p>
      <p className="text-sm leading-relaxed text-gray-600">
        <strong>Ownership Data.</strong> CMS publishes nursing home ownership
        records identifying named individuals, organizations, and management
        companies. The site displays this data as structural information
        without editorial characterization. Association with a facility does
        not establish a causal relationship between ownership structure and
        quality outcomes; ownership and quality are republished from separate
        CMS datasets and presented in the same view so the juxtaposition is
        visible. Cross-facility patterns within an ownership group are
        presented factually (e.g., &quot;N of M facilities cited for
        Category X in their most recent inspection cycle&quot;) without
        narrative interpretation.
      </p>
      <p className="text-sm leading-relaxed text-gray-600">
        <strong>Special Focus Facility (SFF) Status.</strong> SFF and SFF
        Candidate designations are CMS determinations for facilities under
        intensive oversight due to inspection history. These appear at the
        top of a facility profile with full visual prominence — they are
        gate conditions, not metadata. The abuse icon, when CMS has flagged
        a substantiated finding, is treated the same way.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        Population Context Limitations
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        CMS risk-adjusts most outcome measures for clinical factors (age,
        comorbidities, diagnosis) but does not fully adjust for patient
        socioeconomic characteristics. Hospitals serving higher proportions
        of low-income or dual-eligible patients may show higher rates on
        readmission and mortality measures partly due to patient population
        factors, not care quality alone. The site does not currently include
        hospital-level socioeconomic population data that would aid direct
        interpretation. The SES disclosure block accompanies any measure
        group containing SES-sensitive measures so the limitation is visible
        wherever it applies.
      </p>

      <h2 className="mt-8 text-lg font-semibold text-gray-900">
        Data Sources and Refresh Cadence
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        All data is sourced from the CMS Provider Data Catalog and related
        CMS publications. Individual measure sources, including dataset name
        and reporting period, are listed on each measure card under the
        Source toggle.
      </p>
      <p className="text-sm leading-relaxed text-gray-600">
        Hospital quality data is typically refreshed quarterly by CMS, with
        annual refreshes for some measures. Nursing home Provider Information
        and inspection records refresh monthly. SNF QRP and SNF VBP refresh
        on federal fiscal year cycles. The site re-ingests CMS data after
        each publication; the date a provider&apos;s record was last refreshed
        is shown in the page footer.
      </p>
      <p className="text-sm leading-relaxed text-gray-600">
        Measure methodology occasionally changes between reporting periods.
        CMS signals these via footnote code 29. Trend lines that cross a
        methodology boundary are flagged so cross-period comparisons do not
        silently mix incompatible metrics.
      </p>
    </article>
  );
}
