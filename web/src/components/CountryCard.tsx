import type { CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { useLocale } from '../i18n';
import { formatCountdown, formatDate, formatPct, formatPeriod } from '../lib/format';
import type { CountrySummary } from '../lib/types';
import { TargetChip } from './TargetChip';

interface Props {
  country: CountrySummary;
  now: Date;
}

export function CountryCard({ country, now }: Props) {
  const { t } = useTranslation();
  const locale = useLocale();
  const name = country.name[locale];
  const countdown = country.next_release_utc
    ? formatCountdown(country.next_release_utc, now, locale)
    : null;

  return (
    <article className="card" style={{ '--card-accent': `var(--${country.color_token})` } as CSSProperties}>
      <div className="card__head">
        <h3>
          <Link to={`/country/${country.code}`} aria-label={t('card.open', { country: name })}>
            {name}
          </Link>
        </h3>
        <span className="muted">
          {country.indicator} · {formatPeriod(country.reference_period, locale)}
        </span>
      </div>

      <div>
        <div className="muted">{t('card.headlineYoy')}</div>
        <div className="card__headline num">{formatPct(country.headline_yoy_pct, locale)}</div>
      </div>
      {country.target_status && <TargetChip status={country.target_status} />}

      <dl className="card__stats">
        <div>
          <dt>{t('card.mom')}</dt>
          <dd className="num">{formatPct(country.headline_mom_pct, locale, true)}</dd>
        </div>
        <div>
          <dt>{t('card.coreYoy')}</dt>
          <dd className="num">
            {country.core_yoy_pct === null
              ? t('card.notAvailable')
              : formatPct(country.core_yoy_pct, locale)}
          </dd>
        </div>
      </dl>

      <dl className="card__meta">
        <div>
          <dt>{t('card.lastRelease')}</dt>
          <dd>{country.last_release_date ? formatDate(country.last_release_date, locale) : '—'}</dd>
        </div>
        <div>
          <dt>{t('card.nextRelease')}</dt>
          <dd>{countdown ?? t('card.notScheduled')}</dd>
        </div>
      </dl>
    </article>
  );
}
