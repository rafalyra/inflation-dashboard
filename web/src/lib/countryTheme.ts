import { useEffect } from 'react';
import type { CountryTheme, ThemeColors } from './types';

// A country's palette comes from config/countries.yaml (via the exported JSON) and is
// applied as CSS design tokens while that country's page is open. The default tokens in
// styles/tokens.css stay in force everywhere else.

const STYLE_ID = 'country-theme';

function tokens(c: ThemeColors): string {
  const pairs: [string, string][] = [
    ['--color-bg', c.bg],
    ['--color-surface', c.surface],
    ['--color-surface-muted', c.surface_muted],
    ['--color-border', c.border],
    ['--color-text', c.text],
    ['--color-text-muted', c.text_muted],
    ['--color-link', c.link],
    ['--color-focus', c.link],
    ['--header-bg', c.header_bg],
    ['--header-text', c.header_text],
    ['--color-accent', c.accent],
    ['--chart-band', c.band],
    ['--diverging-up', c.up],
    ['--diverging-down', c.down],
    ...c.series.map((hex, i): [string, string] => [`--series-${i + 1}`, hex]),
  ];
  return pairs.map(([k, v]) => `${k}: ${v};`).join(' ');
}

/** CSS for both modes, following the same light/dark/system rules as tokens.css. */
export function themeCss(code: string, theme: CountryTheme): string {
  const root = `:root[data-country='${code}']`;
  return [
    `${root} { ${tokens(theme.light)} }`,
    `@media (prefers-color-scheme: dark) { ${root}:not([data-theme='light']) { ${tokens(theme.dark)} } }`,
    `${root}[data-theme='dark'] { ${tokens(theme.dark)} }`,
  ].join('\n');
}

export function useCountryTheme(code: string | undefined, theme: CountryTheme | null | undefined): void {
  useEffect(() => {
    if (!code || !theme) return;
    let style = document.getElementById(STYLE_ID);
    if (!style) {
      style = document.createElement('style');
      style.id = STYLE_ID;
      document.head.appendChild(style);
    }
    style.textContent = themeCss(code, theme);
    document.documentElement.dataset.country = code;
    return () => {
      delete document.documentElement.dataset.country;
    };
  }, [code, theme]);
}
