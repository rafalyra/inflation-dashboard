import { useTranslation } from 'react-i18next';
import { usePageLocale, useLocale } from '../i18n';
import { useCountry, useOverview } from '../lib/data';
import { formatDateTime } from '../lib/format';

const REPO_DOCS = 'https://github.com/rafalyra/inflation-dashboard/tree/main/docs';

export function MethodologyPage() {
  const { t } = useTranslation();
  const locale = useLocale();
  const overview = useOverview();
  usePageLocale(overview.status === 'ready' ? overview.data.site.default_locale : undefined);
  const code = overview.status === 'ready' ? overview.data.countries[0]?.code : undefined;
  const country = useCountry(code ?? '__none__');
  const methods = t('methodology.methods', { returnObjects: true }) as string[];
  const limits = t('methodology.limits', { returnObjects: true }) as string[];
  const v = country.status === 'ready' ? country.data.validation : null;

  return (
    <>
      <h1>{t('methodology.heading')}</h1>
      <p className="lead">{t('methodology.intro')}</p>

      {v && (
        <section className="panel" aria-labelledby="validation">
          <h2 id="validation">{t('methodology.validation')}</h2>
          <p>
            <span aria-hidden="true">{v.passed ? '✓ ' : '✗ '}</span>
            {v.passed
              ? t('methodology.validationPassed', { count: v.checks.length, when: formatDateTime(v.checked_at_utc, locale) })
              : t('methodology.validationFailed', { when: formatDateTime(v.checked_at_utc, locale) })}
          </p>
        </section>
      )}

      <section className="panel" aria-labelledby="sources">
        <h2 id="sources">{t('methodology.sourcesTitle')}</h2>
        <ul>
          <li>
            <a href="https://sidra.ibge.gov.br/">{t('methodology.sourcesBr.ibge')}</a>
          </li>
          <li>
            <a href="https://www3.bcb.gov.br/sgspub/">{t('methodology.sourcesBr.sgs')}</a>
          </li>
          <li>
            <a href="https://www.bcb.gov.br/publicacoes/focus">{t('methodology.sourcesBr.focus')}</a>
          </li>
        </ul>
      </section>

      <section className="panel" aria-labelledby="methods">
        <h2 id="methods">{t('methodology.methodsTitle')}</h2>
        <ul>
          {methods.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      </section>

      <section className="panel" aria-labelledby="limits">
        <h2 id="limits">{t('methodology.limitsTitle')}</h2>
        <ul>
          {limits.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
        <p>
          <a href={REPO_DOCS}>{t('methodology.docs')}</a>
        </p>
      </section>
    </>
  );
}
