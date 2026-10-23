import type { EChartsCoreOption } from 'echarts/core';
import type { ChartTheme } from './chartTheme';
import { formatNumber, formatPeriod } from './format';
import type { Locale } from './types';

// Shared chart styling (dataviz rules): 2px lines, hairline recessive grid, one y-axis,
// legend for 2+ series, crosshair tooltip on lines, per-bar tooltip on bars.

export type Unit = 'pct' | 'pp' | 'plain';

export interface LineSeries {
  name: string;
  values: (number | null)[];
  color: string;
  dashed?: boolean;
  /** Shade the area between this series' values and `bandLow` (e.g. a min–max range). */
  bandLow?: (number | null)[];
}

function unitSuffix(unit: Unit, locale: Locale): string {
  if (unit === 'pct') return '%';
  if (unit === 'pp') return locale === 'pt-BR' ? ' p.p.' : ' pp';
  return '';
}

export function valueFormatter(unit: Unit, locale: Locale, digits = 2) {
  return (v: number | null | undefined) =>
    v === null || v === undefined || Number.isNaN(v) ? '—' : `${formatNumber(v, locale, digits)}${unitSuffix(unit, locale)}`;
}

function axisCommon(theme: ChartTheme) {
  return {
    axisLine: { lineStyle: { color: theme.axis } },
    axisTick: { show: false },
    axisLabel: { color: theme.ink, fontFamily: theme.font, fontSize: 11 },
    splitLine: { lineStyle: { color: theme.grid, width: 1, type: 'solid' } },
  };
}

function base(theme: ChartTheme, showLegend: boolean): EChartsCoreOption {
  return {
    animationDuration: 300,
    textStyle: { fontFamily: theme.font, color: theme.ink },
    grid: { left: 8, right: 16, top: showLegend ? 40 : 16, bottom: 8, containLabel: true },
    legend: showLegend
      ? { top: 0, left: 0, icon: 'roundRect', itemWidth: 14, itemHeight: 4, textStyle: { color: theme.text, fontSize: 12 } }
      : { show: false },
    aria: { enabled: true },
  };
}

/** Category x-axis of months, labelled by year to stay readable on phones. */
function monthAxis(periods: string[], theme: ChartTheme, locale: Locale) {
  return {
    type: 'category',
    data: periods,
    boundaryGap: false,
    ...axisCommon(theme),
    splitLine: { show: false },
    axisLabel: {
      ...axisCommon(theme).axisLabel,
      interval: (_: number, value: string) => value.endsWith('-01'),
      formatter: (value: string) => value.slice(0, 4),
      hideOverlap: true,
    },
    axisPointer: { label: { formatter: ({ value }: { value: string }) => formatPeriod(value, locale) } },
  };
}

export function lineOption(opts: {
  periods: string[];
  series: LineSeries[];
  theme: ChartTheme;
  locale: Locale;
  unit: Unit;
  band?: { low: number; high: number; target: number; label: string; targetLabel: string } | null;
  zeroLine?: boolean;
}): EChartsCoreOption {
  const { periods, series, theme, locale, unit, band } = opts;
  const fmt = valueFormatter(unit, locale);
  const lines: object[] = [];
  for (const s of series) {
    if (s.bandLow) {
      // Range shading drawn as a stacked pair: an invisible base at the low edge and the
      // gap up to the high edge, filled with a light wash of the series color.
      lines.push({
        name: `${s.name}__low`,
        type: 'line',
        data: s.bandLow,
        stack: s.name,
        symbol: 'none',
        lineStyle: { opacity: 0 },
        tooltip: { show: false },
        silent: true,
      });
      lines.push({
        name: `${s.name}__range`,
        type: 'line',
        data: s.values.map((v, i) => (v === null || s.bandLow?.[i] == null ? null : v - (s.bandLow[i] as number))),
        stack: s.name,
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { color: s.color, opacity: 0.12 },
        tooltip: { show: false },
        silent: true,
      });
      continue;
    }
    lines.push({
      name: s.name,
      type: 'line',
      data: s.values,
      showSymbol: false,
      symbolSize: 8,
      connectNulls: false,
      lineStyle: { width: 2, color: s.color, type: s.dashed ? 'dashed' : 'solid', cap: 'round', join: 'round' },
      itemStyle: { color: s.color, borderColor: theme.surface, borderWidth: 2 },
      emphasis: { focus: 'series' },
    });
  }
  if (band && lines.length) {
    const first = lines.find((l) => !(l as { name: string }).name.includes('__')) as Record<string, unknown>;
    first.markArea = {
      silent: true,
      itemStyle: { color: theme.band },
      label: { show: false },
      data: [[{ yAxis: band.low, name: band.label }, { yAxis: band.high }]],
    };
    first.markLine = {
      silent: true,
      symbol: 'none',
      lineStyle: { color: theme.ink, type: 'dashed', width: 1 },
      label: { formatter: band.targetLabel, color: theme.ink, fontSize: 11, position: 'insideEndTop' },
      data: [{ yAxis: band.target }],
    };
  } else if (opts.zeroLine && lines.length) {
    (lines[0] as Record<string, unknown>).markLine = {
      silent: true,
      symbol: 'none',
      lineStyle: { color: theme.axis, width: 1 },
      label: { show: false },
      data: [{ yAxis: 0 }],
    };
  }
  const visible = series.filter((s) => !s.bandLow);
  return {
    ...base(theme, visible.length > 1),
    legend:
      visible.length > 1
        ? { ...(base(theme, true).legend as object), data: visible.map((s) => s.name) }
        : { show: false },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: theme.axis } },
      valueFormatter: fmt,
      order: 'valueDesc',
    },
    xAxis: monthAxis(periods, theme, locale),
    yAxis: {
      type: 'value',
      scale: true,
      ...axisCommon(theme),
      axisLabel: { ...axisCommon(theme).axisLabel, formatter: (v: number) => valueFormatter(unit, locale, 0)(v) },
    },
    series: lines,
  };
}

/** Horizontal bars for one month's contributions, colored by sign (up vs down). */
export function contributionBars(opts: {
  labels: string[];
  values: number[];
  theme: ChartTheme;
  locale: Locale;
}): EChartsCoreOption {
  const { labels, values, theme, locale } = opts;
  const fmt = valueFormatter('pp', locale);
  return {
    ...base(theme, false),
    grid: { left: 8, right: 56, top: 8, bottom: 8, containLabel: true },
    tooltip: { trigger: 'item', valueFormatter: fmt },
    xAxis: { type: 'value', ...axisCommon(theme), axisLabel: { show: false } },
    yAxis: {
      type: 'category',
      data: labels,
      inverse: true,
      ...axisCommon(theme),
      axisLine: { show: false },
      axisLabel: { ...axisCommon(theme).axisLabel, color: theme.text, fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 20,
        data: values.map((v) => ({
          value: v,
          itemStyle: {
            color: v >= 0 ? theme.up : theme.down,
            borderRadius: v >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4],
          },
        })),
        label: { show: true, position: 'right', formatter: ({ value }: { value: number }) => fmt(value), color: theme.text, fontSize: 11 },
      },
    ],
  };
}

/** Stacked monthly bars (contributions over time) plus the headline as a line. */
export function stackedOption(opts: {
  periods: string[];
  stacks: { name: string; values: (number | null)[]; color: string }[];
  total: { name: string; values: (number | null)[] };
  theme: ChartTheme;
  locale: Locale;
}): EChartsCoreOption {
  const { periods, stacks, total, theme, locale } = opts;
  const fmt = valueFormatter('pp', locale);
  return {
    ...base(theme, true),
    grid: { left: 8, right: 16, top: 64, bottom: 8, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: theme.axis } }, valueFormatter: fmt },
    xAxis: monthAxis(periods, theme, locale),
    yAxis: {
      type: 'value',
      ...axisCommon(theme),
      axisLabel: { ...axisCommon(theme).axisLabel, formatter: (v: number) => valueFormatter('pp', locale, 0)(v) },
    },
    series: [
      // Stacked areas rather than ~160 thin monthly bars: a long monthly series reads as
      // bands. Each band's top edge is drawn in the surface color, a 2px gap that keeps
      // neighbors apart alongside their color. Positive and negative values stack apart.
      ...stacks.map((s) => ({
        name: s.name,
        type: 'line',
        stack: 'c',
        stackStrategy: 'samesign',
        data: s.values,
        showSymbol: false,
        lineStyle: { width: 2, color: theme.surface },
        areaStyle: { color: s.color, opacity: 0.9 },
        itemStyle: { color: s.color },
        emphasis: { focus: 'series' },
      })),
      {
        name: total.name,
        type: 'line',
        data: total.values,
        showSymbol: false,
        lineStyle: { width: 2, color: theme.text },
        itemStyle: { color: theme.text },
        z: 10,
      },
    ],
  };
}

/** Table rows from a shared period axis and several value columns. */
export function periodRows(
  periods: string[],
  columns: (number | null | undefined)[][],
  locale: Locale,
  unit: Unit,
  newestFirst = true,
): (string | number)[][] {
  const fmt = valueFormatter(unit, locale);
  const rows = periods.map((p, i) => [formatPeriod(p, locale), ...columns.map((c) => fmt(c[i] ?? null))]);
  return newestFirst ? rows.reverse() : rows;
}
