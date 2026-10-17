import { useTranslation } from 'react-i18next';

export function MethodologyPage() {
  const { t } = useTranslation();
  return (
    <>
      <h1>{t('methodology.heading')}</h1>
      <p className="muted">{t('methodology.intro')}</p>
    </>
  );
}
