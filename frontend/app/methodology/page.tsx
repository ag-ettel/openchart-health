import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Methodology — OpenChart Health",
  description:
    "How OpenChart Health displays CMS hospital quality data, including interval estimates, uncertainty visualization, and data sources.",
};

export default function MethodologyPage(): React.JSX.Element {
  return (
    <article className="prose prose-sm prose-gray max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900">Methodology</h1>
      <p className="text-sm leading-relaxed text-gray-600">
        This page explains how OpenChart Health processes and displays CMS
        hospital quality data. All data shown on this site is sourced from the
        Centers for Medicare &amp; Medicaid Services (CMS) Provider Data Catalog.
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
        Depending on the measure, these intervals may be frequentist confidence
        intervals or Bayesian credible intervals. When CMS publishes interval
        bounds, we display them as provided. When CMS does not publish bounds
        but provides sufficient data (numerator and denominator for unadjusted
        rate measures), we calculate 95% Bayesian credible intervals using a
        Beta-Binomial model.
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
        Data Sources
      </h2>
      <p className="text-sm leading-relaxed text-gray-600">
        All data is sourced from the CMS Provider Data Catalog, a publicly
        available dataset published by the Centers for Medicare &amp; Medicaid
        Services. Individual measure sources are listed on each measure card
        under the &quot;Source&quot; toggle. CMS typically refreshes hospital
        quality data quarterly.
      </p>
    </article>
  );
}
