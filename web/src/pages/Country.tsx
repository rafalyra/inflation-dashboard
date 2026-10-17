import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router';
import { usePageLocale, useLocale } from '../i18n';
import { useOverview } from '../lib/data';
import { NotFoundPage } from './NotFound';

export function CountryPage() {
  const { t } = useTranslation();
  const locale = useLocale();
  const { code } = useParams();
  const state = useOverview();
  const country =
    state.status === 'ready' ? state.data.countries.find((c) => c.code === code) : undefined;
  // Each country page opens in its own configured language (e.g. Brazil in Portuguese).
  usePageLocale(country?.default_locale);

  if (state.status === 'loading') return <p className="muted">{t('status.loading')}</p>;
  if (state.status === 'error') return <p role="alert">{t('status.error')}</p>;
  if (!country) return <NotFoundPage />;

  return (
    <>
      <h1>{country.name[locale]}</h1>
      <p className="muted">{t('country.underConstruction')}</p>
    </>
  );
}
