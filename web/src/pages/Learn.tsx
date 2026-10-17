import { useTranslation } from 'react-i18next';

export function LearnPage() {
  const { t } = useTranslation();
  return (
    <>
      <h1>{t('learn.heading')}</h1>
      <p className="muted">{t('learn.intro')}</p>
    </>
  );
}
