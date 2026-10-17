import i18n from 'i18next';
import { useEffect } from 'react';
import { initReactI18next, useTranslation } from 'react-i18next';
import { getChosenLocale, setChosenLocale } from '../lib/preferences';
import type { Locale } from '../lib/types';
import en from './en.json';
import ptBR from './pt-BR.json';

export const LOCALES: Locale[] = ['en', 'pt-BR'];

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, 'pt-BR': { translation: ptBR } },
  // Until page data arrives with its configured default, start from the visitor's choice.
  lng: getChosenLocale() ?? 'pt-BR',
  fallbackLng: 'en',
  interpolation: { escapeValue: false }, // React already escapes output
});

i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng;
});

export function useLocale(): Locale {
  const { i18n: instance } = useTranslation();
  return instance.language === 'en' ? 'en' : 'pt-BR';
}

/**
 * Apply a page's default language (from config, via the exported JSON) unless the
 * visitor has picked one with the toggle, which always wins.
 */
export function usePageLocale(defaultLocale: Locale | undefined): void {
  useEffect(() => {
    if (defaultLocale && getChosenLocale() === null && i18n.language !== defaultLocale) {
      void i18n.changeLanguage(defaultLocale);
    }
  }, [defaultLocale]);
}

export function chooseLocale(locale: Locale): void {
  setChosenLocale(locale);
  void i18n.changeLanguage(locale);
}

export default i18n;
