import { useTranslation } from 'react-i18next';
import { CountryCard } from '../components/CountryCard';
import { usePageLocale, useLocale } from '../i18n';
import { useOverview } from '../lib/data';
import { formatDateTime, formatPct, formatPeriod } from '../lib/format';
import type { OverviewData } from '../lib/types';

export function OverviewPage() {
  const { t } = useTranslation();
  const state = useOverview();
  usePageLocale(state.status === 'ready' ? state.data.site.default_locale : undefined);

  if (state.status === 'loading') return <p className="muted">{t('status.loading')}</p>;
  if (state.status === 'error') return <p role="alert">{t('status.error')}</p>;
  return <OverviewView data={state.data} now={new Date()} />;
}

export function OverviewView({ data, now }: { data: OverviewData; now: Date }) {
  const { t } = useTranslation();
  const locale = useLocale();
  const nameOf = (code: string) =>
    data.countries.find((c) => c.code === code)?.name[locale] ?? code.toUpperCase();

  return (
    <>
      {data.sample && (
        <p className="notice" role="note">
          {t('sample.banner')}
        </p>
      )}
      <h1>{t('overview.heading')}</h1>
      <p className="muted">{t('overview.updated', { when: formatDateTime(data.generated_at_utc, locale) })}</p>

      <section aria-labelledby="countries-heading">
        <h2 id="countries-heading" className="sr-only-heading">
          {t('overview.countries')}
        </h2>
        <div className="card-grid">
          {data.countries.map((country) => (
            <CountryCard key={country.code} country={country} now={now} />
          ))}
        </div>
      </section>

      <section aria-labelledby="releases-heading">
        <h2 id="releases-heading">{t('overview.latestReleases')}</h2>
        {data.latest_releases.length === 0 ? (
          <p className="muted">{t('overview.noReleases')}</p>
        ) : (
          <ul className="feed">
            {data.latest_releases.map((item) => (
              <li key={`${item.country}-${item.indicator}-${item.reference_period}`}>
                <span>
                  {nameOf(item.country)} · {item.indicator} · {formatPeriod(item.reference_period, locale)}
                </span>
                <span className="num">{formatPct(item.mom_pct, locale, true)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
