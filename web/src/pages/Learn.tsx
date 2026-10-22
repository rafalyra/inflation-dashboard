import { useTranslation } from 'react-i18next';
import { usePageLocale, useLocale } from '../i18n';
import { useCountry, useOverview } from '../lib/data';
import { formatPct, formatPeriod, formatPpNumber } from '../lib/format';
import type { CountryData, Locale } from '../lib/types';

const CONCEPTS = ['mom', 'yoy', 'ytd', 'sa', 'saar', 'core', 'contribution', 'diffusion', 'band', 'surprise', 'base', 'real', 'vintage'] as const;
type Concept = (typeof CONCEPTS)[number];

/** Values for each concept's live example, taken from the exported data (never computed here). */
function examples(d: CountryData, locale: Locale, pp: (v: number) => string): Partial<Record<Concept, Record<string, string>>> {
  const h = d.headline;
  const period = formatPeriod(h.reference_period, locale, 'long');
  const out: Partial<Record<Concept, Record<string, string>>> = {
    mom: { indicator: h.indicator, value: formatPct(h.mom_pct, locale, true), period },
  };
  if (h.yoy_pct !== null) out.yoy = { value: formatPct(h.yoy_pct, locale), period };
  if (h.ytd_pct !== null) out.ytd = { value: formatPct(h.ytd_pct, locale), period };
  if (d.momentum.saar.available) {
    const last = d.momentum.saar.saar3_pct.at(-1);
    if (last != null) out.saar = { value: formatPct(last, locale) };
  }
  if (d.core.latest_mean_pct !== undefined) out.core = { value: formatPct(d.core.latest_mean_pct, locale) };
  if (d.summary.top_driver) {
    out.contribution = { driver: d.summary.top_driver.label[locale], value: pp(d.summary.top_driver.contribution_pp) };
  }
  const diff = d.trend.diffusion;
  const diffLast = diff?.values.at(-1);
  if (diff && diffLast != null) out.diffusion = { value: formatPct(diffLast, locale), period: formatPeriod(diff.periods.at(-1) ?? '', locale, 'long') };
  out.band = { value: pp(d.target.distance_pp) };
  if (h.surprise_pp !== null) out.surprise = { value: pp(h.surprise_pp) };
  const leaving = d.base_effects.dropping_out[0];
  if (leaving?.leaving_mom_pct != null) {
    out.base = { period: formatPeriod(leaving.leaving_period, locale, 'long'), value: formatPct(leaving.leaving_mom_pct, locale, true) };
  }
  if (d.policy.real_ex_ante) out.real = { value: formatPct(d.policy.real_ex_ante.rate_pct, locale) };
  return out;
}

export function LearnPage() {
  const overview = useOverview();
  usePageLocale(overview.status === 'ready' ? overview.data.site.default_locale : undefined);
  const code = overview.status === 'ready' ? overview.data.countries[0]?.code : undefined;
  return <LearnContent code={code} />;
}

function LearnContent({ code }: { code: string | undefined }) {
  const { t } = useTranslation();
  const locale = useLocale();
  const country = useCountry(code ?? '__none__');
  const pp = (v: number) => t('units.pp', { value: formatPpNumber(v, locale) });
  const ex = country.status === 'ready' ? examples(country.data, locale, pp) : {};
  const steps = t('learn.howTo.steps', { returnObjects: true }) as string[];

  return (
    <>
      <h1>{t('learn.heading')}</h1>
      <p className="lead">{t('learn.intro')}</p>
      <section className="panel" aria-labelledby="howto">
        <h2 id="howto">{t('learn.howTo.title')}</h2>
        <ol className="steps">
          {steps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
      </section>
      <div className="concept-grid">
        {CONCEPTS.map((c) => (
          <article key={c} className="panel concept" id={`learn-${c}`}>
            <h2>{t(`learn.concepts.${c}.title`)}</h2>
            <p>{t(`learn.concepts.${c}.body`)}</p>
            {ex[c] && (
              <p className="example">
                <span className="example__label">{t('learn.exampleLabel')}</span> {t(`learn.concepts.${c}.example`, ex[c])}
              </p>
            )}
          </article>
        ))}
      </div>
    </>
  );
}
