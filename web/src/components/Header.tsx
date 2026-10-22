import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, NavLink } from 'react-router';
import { chooseLocale, useLocale } from '../i18n';
import { useOverview } from '../lib/data';
import { applyTheme, getThemeChoice, setThemeChoice, type ThemeChoice } from '../lib/preferences';

const NEXT_THEME: Record<ThemeChoice, ThemeChoice> = { system: 'light', light: 'dark', dark: 'system' };

export function Header() {
  const { t } = useTranslation();
  const locale = useLocale();
  const [theme, setTheme] = useState<ThemeChoice>(getThemeChoice);
  // One nav link per exported country, so no country is hard-coded in the web app.
  const overview = useOverview();
  const countries = overview.status === 'ready' ? overview.data.countries : [];

  const cycleTheme = () => {
    const next = NEXT_THEME[theme];
    setTheme(next);
    setThemeChoice(next);
    applyTheme(next);
  };

  return (
    <header className="header">
      <div className="header__inner">
        <Link to="/" className="header__title">
          {t('app.title')}
        </Link>
        <nav className="header__nav" aria-label={t('nav.label')}>
          <NavLink to="/" end>
            {t('nav.overview')}
          </NavLink>
          {countries.map((c) => (
            <NavLink key={c.code} to={`/country/${c.code}`}>
              {c.name[locale]}
            </NavLink>
          ))}
          <NavLink to="/learn">{t('nav.learn')}</NavLink>
          <NavLink to="/methodology">{t('nav.methodology')}</NavLink>
        </nav>
        <div className="header__controls">
          <button
            type="button"
            className="button"
            lang={locale === 'en' ? 'pt-BR' : 'en'}
            aria-label={t('language.switchLabel')}
            onClick={() => chooseLocale(locale === 'en' ? 'pt-BR' : 'en')}
          >
            {t('language.switchTo')}
          </button>
          <button
            type="button"
            className="button"
            aria-label={t('theme.label', { current: t(`theme.${theme}`) })}
            onClick={cycleTheme}
          >
            {t(`theme.${theme}`)}
          </button>
        </div>
      </div>
    </header>
  );
}
