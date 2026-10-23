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
  /** Fixed y-range, so small multiples share one scale. */
  yRange?: { min: number; max: number };
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
      scale: !opts.yRange,
      min: opts.yRange?.min,
      max: opts.yRange?.max,
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

/** Stacked bars for a short monthly window (e.g. the last 24 months), with the total as a line. */
export function monthlyBarsOption(opts: {
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
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: fmt },
    xAxis: {
      type: 'category',
      data: periods,
      ...axisCommon(theme),
      splitLine: { show: false },
      axisLabel: { ...axisCommon(theme).axisLabel, formatter: (v: string) => formatPeriod(v, locale), hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      ...axisCommon(theme),
      axisLabel: { ...axisCommon(theme).axisLabel, formatter: (v: number) => valueFormatter('pp', locale, 1)(v) },
    },
    series: [
      ...stacks.map((s) => ({
        name: s.name,
        type: 'bar',
        stack: 'c',
        stackStrategy: 'samesign',
        data: s.values,
        barMaxWidth: 24,
        // 2px surface gap between stacked segments.
        itemStyle: { color: s.color, borderColor: theme.surface, borderWidth: 2 },
        emphasis: { focus: 'series' },
      })),
      {
        name: total.name,
        type: 'line',
        data: total.values,
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { width: 2, color: theme.text },
        itemStyle: { color: theme.text, borderColor: theme.surface, borderWidth: 2 },
        z: 10,
      },
    ],
  };
}

export interface RangeRow {
  label: string;
  value: number;
  median: number | null;
  q25: number | null;
  q75: number | null;
}

/** A translucent version of the theme's band color (the band token is an rgba() string). */
function bandAlpha(theme: ChartTheme, alpha: number): string {
  return theme.band.replace(/[\d.]+\)$/, `${alpha})`);
}

/**
 * This month against its seasonal pattern: a band from the 25th to the 75th percentile of
 * the same calendar month in baseline years, a tick at the median, and a dot for this year.
 */
export function rangeOption(opts: {
  rows: RangeRow[];
  theme: ChartTheme;
  locale: Locale;
  names: { band: string; median: string; value: string };
}): EChartsCoreOption {
  const { rows, theme, locale, names } = opts;
  const fmt = valueFormatter('pct', locale);
  return {
    ...base(theme, true),
    legend: { ...(base(theme, true).legend as object), data: [names.band, names.median, names.value] },
    grid: { left: 8, right: 24, top: 40, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: { dataIndex: number }[]) => {
        const r = rows[params[0]?.dataIndex ?? 0];
        if (!r) return '';
        return `<b>${r.label}</b><br/>${names.value}: ${fmt(r.value)}<br/>${names.median}: ${fmt(r.median)}<br/>${names.band}: ${fmt(r.q25)} – ${fmt(r.q75)}`;
      },
    },
    xAxis: {
      type: 'value',
      ...axisCommon(theme),
      axisLabel: { ...axisCommon(theme).axisLabel, formatter: (v: number) => valueFormatter('pct', locale, 1)(v) },
    },
    yAxis: {
      type: 'category',
      data: rows.map((r) => r.label),
      inverse: true,
      ...axisCommon(theme),
      axisLine: { show: false },
      axisLabel: { ...axisCommon(theme).axisLabel, color: theme.text, fontSize: 12 },
    },
    series: [
      {
        name: '__base',
        type: 'bar',
        stack: 'band',
        data: rows.map((r) => r.q25),
        itemStyle: { color: 'transparent' },
        silent: true,
        barWidth: 14,
      },
      {
        name: names.band,
        type: 'bar',
        stack: 'band',
        data: rows.map((r) => (r.q25 === null || r.q75 === null ? null : r.q75 - r.q25)),
        itemStyle: { color: bandAlpha(theme, 0.45), borderRadius: 4 },
        barWidth: 14,
      },
      {
        name: names.median,
        type: 'scatter',
        data: rows.map((r) => r.median),
        symbol: 'rect',
        symbolSize: [3, 20],
        itemStyle: { color: theme.ink },
        z: 5,
      },
      {
        name: names.value,
        type: 'scatter',
        data: rows.map((r) => r.value),
        symbolSize: 12,
        itemStyle: { color: theme.series[0], borderColor: theme.surface, borderWidth: 2 },
        z: 6,
      },
    ],
  };
}

/** Jan–Dec monthly changes: this year (bold), recent years (thin), baseline median and middle half. */
export function profileOption(opts: {
  months: string[];
  current: { name: string; values: (number | null)[] };
  previous: { name: string; values: (number | null)[] }[];
  median: (number | null)[];
  q25: (number | null)[];
  q75: (number | null)[];
  theme: ChartTheme;
  locale: Locale;
  names: { band: string; median: string };
}): EChartsCoreOption {
  const { months, current, previous, median, q25, q75, theme, locale, names } = opts;
  const fmt = valueFormatter('pct', locale);
  const muted = [theme.series[2], theme.series[4], theme.series[6]];
  return {
    ...base(theme, true),
    legend: {
      ...(base(theme, true).legend as object),
      data: [current.name, ...previous.map((p) => p.name), names.median, names.band],
    },
    grid: { left: 8, right: 16, top: 56, bottom: 8, containLabel: true },
    tooltip: { trigger: 'axis', valueFormatter: fmt },
    xAxis: { type: 'category', data: months, boundaryGap: false, ...axisCommon(theme), splitLine: { show: false } },
    yAxis: {
      type: 'value',
      ...axisCommon(theme),
      axisLabel: { ...axisCommon(theme).axisLabel, formatter: (v: number) => valueFormatter('pct', locale, 1)(v) },
    },
    series: [
      {
        name: '__q25',
        type: 'line',
        data: q25,
        stack: 'band',
        symbol: 'none',
        lineStyle: { opacity: 0 },
        silent: true,
        tooltip: { show: false },
      },
      {
        name: names.band,
        type: 'line',
        data: q75.map((v, i) => (v === null || q25[i] == null ? null : v - (q25[i] as number))),
        stack: 'band',
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { color: bandAlpha(theme, 0.4) },
        itemStyle: { color: bandAlpha(theme, 0.6) },
        tooltip: { show: false },
      },
      {
        name: names.median,
        type: 'line',
        data: median,
        symbol: 'none',
        lineStyle: { width: 1.5, type: 'dashed', color: theme.ink },
        itemStyle: { color: theme.ink },
      },
      ...previous.map((p, i) => ({
        name: p.name,
        type: 'line',
        data: p.values,
        symbol: 'none',
        lineStyle: { width: 1.5, color: muted[i % muted.length], opacity: 0.85 },
        itemStyle: { color: muted[i % muted.length] },
      })),
      {
        name: current.name,
        type: 'line',
        data: current.values,
        symbolSize: 8,
        lineStyle: { width: 3, color: theme.series[0] },
        itemStyle: { color: theme.series[0], borderColor: theme.surface, borderWidth: 2 },
        z: 10,
      },
    ],
  };
}

export interface TreeNode {
  name: string;
  value: [number, number]; // [weight, monthly change]
  contribution: number;
  itemStyle?: { color: string };
  children?: TreeNode[];
}

/** Mix two #rrggbb colors; t = 0 gives a, t = 1 gives b. */
function mixHex(a: string, b: string, t: number): string {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return '#' + pa.map((v, i) => Math.round(v + ((pb[i] as number) - v) * t).toString(16).padStart(2, '0')).join('');
}

/**
 * Box color for a monthly change: the surface color for no change, shading toward gold for
 * rises and navy for falls, reaching full strength at ±2% (capped at 70% so labels stay
 * readable). Display only: the change itself comes from the export.
 */
export function changeColor(mom: number, theme: ChartTheme): string {
  const strength = Math.min(Math.abs(mom) / 2, 1) * 0.7;
  return mixHex(theme.surface, mom >= 0 ? theme.up : theme.down, strength);
}

/**
 * The basket as nested boxes: area = weight, color = this month's change (navy for falls,
 * gold for rises, neutral near zero). Click a box to zoom into its parts.
 */
export function treemapOption(opts: {
  data: TreeNode[];
  theme: ChartTheme;
  locale: Locale;
  rootName: string;
  names: { weight: string; change: string; contribution: string };
}): EChartsCoreOption {
  const { data, theme, locale, rootName, names } = opts;
  const pct = valueFormatter('pct', locale);
  const pp = valueFormatter('pp', locale);
  return {
    textStyle: { fontFamily: theme.font, color: theme.ink },
    tooltip: {
      formatter: (info: { name: string; data: TreeNode }) =>
        `<b>${info.name}</b><br/>${names.weight}: ${pct(info.data.value[0])}<br/>${names.change}: ${pct(info.data.value[1])}<br/>${names.contribution}: ${pp(info.data.contribution)}`,
    },
    series: [
      {
        type: 'treemap',
        name: rootName,
        data,
        roam: false,
        leafDepth: 1,
        top: 8,
        bottom: 36,
        left: 0,
        right: 0,
        breadcrumb: {
          bottom: 4,
          itemStyle: { color: theme.surface, borderColor: theme.axis, textStyle: { color: theme.text } },
          emphasis: { itemStyle: { color: theme.grid } },
        },
        label: {
          formatter: (info: { name: string; data: TreeNode }) => `${info.name}\n${pct(info.data.value[1])}`,
          color: theme.text,
          fontSize: 12,
          overflow: 'truncate',
        },
        upperLabel: { show: true, height: 22, color: theme.text },
        itemStyle: { borderColor: theme.surface, borderWidth: 2, gapWidth: 2 },
        levels: [{ itemStyle: { borderWidth: 3, gapWidth: 3 } }, { itemStyle: { gapWidth: 2 } }],
      },
    ],
  };
}
