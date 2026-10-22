import { useEffect, useState } from 'react';

// Charts are drawn on a canvas, so they can't use CSS variables directly. This reads the
// design tokens from the document and re-reads them whenever the theme changes.

export interface ChartTheme {
  series: string[];
  up: string;
  down: string;
  grid: string;
  axis: string;
  ink: string;
  text: string;
  surface: string;
  band: string;
  font: string;
  monoFont: string;
}

function readTheme(): ChartTheme {
  const style = getComputedStyle(document.documentElement);
  const v = (name: string) => style.getPropertyValue(name).trim();
  return {
    series: Array.from({ length: 8 }, (_, i) => v(`--series-${i + 1}`)),
    up: v('--diverging-up'),
    down: v('--diverging-down'),
    grid: v('--chart-grid'),
    axis: v('--chart-axis'),
    ink: v('--chart-ink'),
    text: v('--color-text'),
    surface: v('--color-surface'),
    band: v('--chart-band'),
    font: v('--font-sans'),
    monoFont: v('--font-mono'),
  };
}

export function useChartTheme(): ChartTheme {
  const [theme, setTheme] = useState<ChartTheme>(readTheme);

  useEffect(() => {
    const update = () => setTheme(readTheme());
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'data-country'] });
    const media = window.matchMedia?.('(prefers-color-scheme: dark)');
    media?.addEventListener?.('change', update);
    return () => {
      observer.disconnect();
      media?.removeEventListener?.('change', update);
    };
  }, []);

  return theme;
}
