import type { Locale } from './types';

// Per-visitor conveniences kept in localStorage. Storage can be unavailable (private
// windows, blocked site data), so every access is guarded and the app works without it.

const LOCALE_KEY = 'inflation.locale';
const THEME_KEY = 'inflation.theme';

export type ThemeChoice = 'system' | 'light' | 'dark';

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Not persisted; the choice still applies for this visit.
  }
}

/** The language the visitor picked explicitly, if any. It overrides page defaults. */
export function getChosenLocale(): Locale | null {
  const value = read(LOCALE_KEY);
  return value === 'en' || value === 'pt-BR' ? value : null;
}

export function setChosenLocale(locale: Locale): void {
  write(LOCALE_KEY, locale);
}

export function getThemeChoice(): ThemeChoice {
  const value = read(THEME_KEY);
  return value === 'light' || value === 'dark' ? value : 'system';
}

export function setThemeChoice(choice: ThemeChoice): void {
  write(THEME_KEY, choice);
}

export function applyTheme(choice: ThemeChoice): void {
  const root = document.documentElement;
  if (choice === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', choice);
}
