import { useMemo } from 'react';
import { ChartCard } from '../components/ChartCard';
import { SignalBar, maxAbs } from '../components/SignalBar';
import { lineOption, periodRows, rangeOption, stackedOption, valueFormatter } from '../lib/chartOptions';
import { formatCountdown, formatDate, formatDateTime, formatNumber, formatPct, formatPeriod } from '../lib/format';
import type { Contribution, ContributionSet, Locale, SeriesSnapshot } from '../lib/types';
import type { Ctx } from './Country';

// The Summary tab: the release at a glance, then the charts and tables that explain it.
// Every number comes from the export; this file only arranges it.

/** ▲/▼ chip for a change in pp: red when it went up, green when it went down. */
function DeltaChip({ value, label }: { value: number | null; label: string }) {
  if (value === null) return null;
  const flat = Math.abs(value) < 0.005;
  const cls = flat ? 'delta delta--flat' : value > 0 ? 'delta delta--up' : 'delta delta--down';
  return (
    <span className={cls}>
      <span aria-hidden="true">{flat ? '●' : value > 0 ? '▲' : '▼'}</span> {label}
    </span>
  );
}

export function ReleaseOverview({ d, t, locale, L, pp }: Ctx) {
  const o = d.overview;
  const h = d.headline;
  if (!o) return null;
  const period = formatPeriod(h.reference_period, locale);
  const prevPeriod = formatPeriod(previousPeriod(h.reference_period), locale);
  const next = h.next_release;
  const b = d.base_effects;
  const now = new Date();
  const ok = d.validation.passed;
  const up = d.drivers.top_up[0];
  const down = d.drivers.top_down[0];
  const devUp = d.seasonality?.deviation.items_up[0];
  const devDown = d.seasonality?.deviation.items_down[0];
  const diff = d.composition.weighted_diffusion?.above_threshold;
  const diffLast = diff?.values.at(-1);

  return (
    <>
      <div className="overview-top">
        <div className="hero">
          <p className="hero__meta">
            {t('summary.lastRelease', {
              indicator: h.indicator,
              period,
              date: h.release_date ? formatDate(h.release_date, locale) : '—',
            })}
          </p>
          <p className="hero__headline">
            {t('summary.headline', { indicator: h.indicator, value: h.yoy_pct !== null ? formatPct(h.yoy_pct, locale) : '—' })}
          </p>
          <p className="hero__sub">
            {t('summary.heroSub', {
              core: o.core.yoy_pct !== null ? formatPct(o.core.yoy_pct, locale) : '—',
              noncore: o.noncore?.yoy_pct != null ? formatPct(o.noncore.yoy_pct, locale) : '—',
              mom: formatPct(h.mom_pct, locale, true),
            })}
          </p>
          {d.target.band_low_pct !== null && d.target.band_high_pct !== null && (
            <p className="hero__meta">
              {t('summary.target', {
                target: formatPct(d.target.target_pct, locale),
                low: formatPct(d.target.band_low_pct, locale),
                high: formatPct(d.target.band_high_pct, locale),
              })}
              {d.target.status && <b> {t(`target.${d.target.status}`)}</b>}
            </p>
          )}
        </div>
        <div className="panel next-card">
          <p className="tile__label">{t('summary.nextRelease')}</p>
          {next ? (
            <>
              <p className="next-card__date">{formatDateTime(next.scheduled_utc, locale)}</p>
              <span className="chip-soft">{formatCountdown(next.scheduled_utc, now, locale) ?? '—'}</span>
              {b.next_expected && (
                <p>
                  {t('summary.estimate', {
                    period: formatPeriod(next.reference_period, locale),
                    mom: formatPct(b.next_expected.median_pct, locale, true),
                    yoy: b.implied_next_yoy_pct !== null ? formatPct(b.implied_next_yoy_pct, locale) : '—',
                  })}
                </p>
              )}
              {b.next_spread && (
                <p className="muted">
                  {t('summary.range', {
                    min: formatPct(b.next_spread.min_mom_pct, locale, true),
                    max: formatPct(b.next_spread.max_mom_pct, locale, true),
                    minYoy: formatPct(b.next_spread.min_yoy_pct, locale),
                    maxYoy: formatPct(b.next_spread.max_yoy_pct, locale),
                  })}
                </p>
              )}
            </>
          ) : (
            <p className="muted">{t('card.notScheduled')}</p>
          )}
          <hr />
          <p className="muted small">{t('summary.updated', { when: formatDateTime(d.generated_at_utc, locale) })}</p>
          <p className={ok ? 'check check--ok small' : 'check check--fail small'}>
            <span aria-hidden="true">{ok ? '✓' : '✗'}</span>{' '}
            {t(ok ? 'summary.checked' : 'summary.notChecked', { period })}
          </p>
        </div>
      </div>

      <div className="kpi-grid">
        {o.cards.map((c) => (
          <div className="panel kpi" key={c.series_id}>
            <p className="kpi__label">{t('summary.kpiLabel', { name: L(c.label) })}</p>
            <p className="kpi__value">
              <span className="num">{c.yoy_pct !== null ? formatPct(c.yoy_pct, locale) : '—'}</span>{' '}
              <span className="kpi__mom">
                {c.mom_pct !== null ? formatPct(c.mom_pct, locale) : '—'} {t('summary.inMonth')}
              </span>
            </p>
            <DeltaChip
              value={c.yoy_change_pp}
              label={c.yoy_change_pp !== null ? t('summary.vsPrev', { value: pp(c.yoy_change_pp), period: prevPeriod }) : ''}
            />
          </div>
        ))}
      </div>

      <div className="insight-grid">
        <div className="insight">
          <p className="insight__title">{t('summary.insight.expected')}</p>
          <p>
            {h.expected && h.surprise_pp !== null
              ? t(h.surprise_pp >= 0 ? 'summary.insight.aboveExp' : 'summary.insight.belowExp', {
                  actual: formatPct(h.mom_pct, locale, true),
                  expected: formatPct(h.expected.median_pct, locale, true),
                  gap: pp(h.surprise_pp),
                })
              : t('summary.insight.noExp', { period })}
          </p>
        </div>
        <div className="insight">
          <p className="insight__title">{t('summary.insight.contributions')}</p>
          {up && <p>{t('summary.insight.upItem', { item: L(up.label), pp: pp(up.contribution_pp), pct: formatPct(up.mom_pct, locale, true) })}</p>}
          {down && <p>{t('summary.insight.downItem', { item: L(down.label), pp: pp(down.contribution_pp), pct: formatPct(down.mom_pct, locale, true) })}</p>}
        </div>
        <div className="insight">
          <p className="insight__title">{t('summary.insight.seasonal')}</p>
          <p>
            {devUp && t('summary.insight.devUp', { item: L(devUp.label), pp: pp(devUp.deviation_pp) })}
            {devUp && devDown && ' · '}
            {devDown && t('summary.insight.devDown', { item: L(devDown.label), pp: pp(devDown.deviation_pp) })}
          </p>
        </div>
        <div className="insight">
          <p className="insight__title">{t('summary.insight.diffusion')}</p>
          <p>
            {diff && diffLast != null
              ? t('summary.insight.diffusionText', {
                  share: wholePct(diffLast, locale),
                  threshold: formatPct(diff.threshold_pct, locale),
                  period: formatPeriod(diff.periods.at(-1) ?? '', locale),
                })
              : '—'}
          </p>
        </div>
      </div>
    </>
  );
}

function previousPeriod(period: string): string {
  const [y, m] = period.split('-').map(Number);
  const date = new Date(Date.UTC(y ?? 1970, (m ?? 1) - 2, 1));
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
}

export function TargetCharts({ d, t, locale, theme, L }: Ctx) {
  const o = d.overview;
  const band =
    d.target.band_low_pct !== null && d.target.band_high_pct !== null
      ? {
          low: d.target.band_low_pct,
          high: d.target.band_high_pct,
          target: d.target.target_pct,
          label: t('history.band'),
          targetLabel: t('history.target', { value: formatPct(d.target.target_pct, locale) }),
        }
      : null;
  const charts = useMemo(() => {
    const series = [
      { title: t('summary.vsTarget', { name: d.headline.indicator }), pts: d.history.headline_yoy, color: theme.series[0] ?? '' },
      ...(o ? [{ title: t('summary.vsTarget', { name: L(o.core_yoy.label) }), pts: o.core_yoy, color: theme.series[2] ?? '' }] : []),
    ];
    return series.map((s) => ({
      ...s,
      option: lineOption({
        periods: s.pts.periods,
        series: [{ name: s.title, values: s.pts.values, color: s.color }],
        theme,
        locale,
        unit: 'pct',
        band,
      }),
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [d, o, theme, locale, t, L]);
  return (
    <div className="split">
      {charts.map((c) => (
        <ChartCard
          key={c.title}
          title={c.title}
          subtitle={t('summary.vsTargetSubtitle', { last: formatPct(c.pts.values.at(-1) ?? 0, locale) })}
          option={c.option}
          table={{ columns: [t('table.month'), c.title], rows: periodRows(c.pts.periods, [c.pts.values], locale, 'pct') }}
        />
      ))}
    </div>
  );
}

// Color families: core and its parts in blues, non-core and its parts in yellows/golds
// (indexes into the country's validated series palette).
const FAMILY = { top: [0, 3], core: [2, 6], noncore: [3, 5] } as const;
type Family = keyof typeof FAMILY;

function stackOf(set: ContributionSet, total: string, ctx: Ctx, family: Family) {
  return stackedOption({
    periods: set.twelve_month.periods,
    stacks: set.twelve_month.series.map((s, i) => ({ name: ctx.L(s.label), values: s.values_pp, color: ctx.theme.series[FAMILY[family][i] ?? 7] ?? ctx.theme.ink })),
    total: { name: total, values: set.twelve_month.headline_yoy_pct },
    theme: ctx.theme,
    locale: ctx.locale,
  });
}

function yoyOf(set: ContributionSet, total: string, ctx: Ctx, family: Family) {
  const periods = set.yoy.series[0]?.periods ?? [];
  return lineOption({
    periods,
    series: [
      { name: total, values: periods.map((p) => set.twelve_month.headline_yoy_pct[set.twelve_month.periods.indexOf(p)] ?? null), color: ctx.theme.text },
      ...set.yoy.series.map((s, i) => ({ name: ctx.L(s.label), values: periods.map((p) => s.values[s.periods.indexOf(p)] ?? null), color: ctx.theme.series[FAMILY[family][i] ?? 7] ?? '' })),
    ],
    theme: ctx.theme,
    locale: ctx.locale,
    unit: 'pct',
  });
}

export function CoreCharts(ctx: Ctx) {
  const { d, t, locale, L } = ctx;
  const sets = d.composition.sets;
  const items = useMemo(() => {
    const top = sets.core_noncore;
    const core = sets.core;
    const noncore = sets.noncore;
    if (!top || !core || !noncore) return [];
    const ipca = L(d.headline.label);
    const coreName = t('composition.cnc.short.core');
    const noncoreName = t('composition.cnc.short.noncore');
    return [
      { set: top, stack: true, title: t('composition.cnc.contribTitle', { name: ipca }), option: stackOf(top, ipca, ctx, 'top') },
      { set: core, stack: true, title: t('composition.cnc.contribTitle', { name: coreName }), option: stackOf(core, coreName, ctx, 'core') },
      { set: core, stack: false, title: t('composition.cnc.yoyTitle', { name: coreName }), option: yoyOf(core, coreName, ctx, 'core') },
      { set: noncore, stack: false, title: t('composition.cnc.yoyTitle', { name: noncoreName }), option: yoyOf(noncore, noncoreName, ctx, 'noncore') },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sets, ctx.theme, locale, t, L, d.headline.label]);
  if (!items.length) return null;
  return (
    <div className="split">
      {items.map((c) => (
        <ChartCard
          key={c.title}
          title={c.title}
          subtitle={c.stack ? t('summary.stackSubtitle') : t('composition.cnc.yoySubtitle')}
          option={c.option}
          height={380}
          table={
            c.stack
              ? {
                  columns: [t('table.month'), ...c.set.twelve_month.series.map((s) => L(s.label)), t('drivers.headlineYoy')],
                  rows: periodRows(c.set.twelve_month.periods, [...c.set.twelve_month.series.map((s) => s.values_pp), c.set.twelve_month.headline_yoy_pct], locale, 'pp'),
                }
              : {
                  columns: [t('table.month'), ...c.set.yoy.series.map((s) => L(s.label))],
                  rows: periodRows(c.set.yoy.series[0]?.periods ?? [], c.set.yoy.series.map((s) => s.values), locale, 'pct'),
                }
          }
        />
      ))}
    </div>
  );
}

export function SeasonalNow({ d, t, locale, theme, L, pp }: Ctx) {
  const o = d.overview;
  const s = d.seasonality;
  const rows = s?.series.filter((r) => r.kind === 'aggregate') ?? [];
  const option = useMemo(
    () =>
      rangeOption({
        rows: rows.map((r) => ({ label: L(r.label) + (r.latest.n_years < 5 ? ' *' : ''), value: r.latest.value_pct, median: r.latest.median_pct, q25: r.latest.q25_pct, q75: r.latest.q75_pct })),
        theme,
        locale,
        names: { band: t('seasonality.band'), median: t('seasonality.median'), value: t('seasonality.thisYear', { year: (s?.period ?? '').slice(0, 4) }) },
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [s, theme, locale, t, L],
  );
  if (!o || !s) return null;
  const period = formatPeriod(o.period, locale);
  const prev = formatPeriod(previousPeriod(o.period), locale);
  const fmt = valueFormatter('pct', locale);
  const changeMax = maxAbs(o.table.map((r) => r.yoy_change_pp ?? 0));
  return (
    <>
      <ChartCard
        title={t('seasonality.patternTitle', { period: formatPeriod(s.period, locale, 'long') })}
        subtitle={t('seasonality.patternSubtitle')}
        option={option}
        height={Math.max(300, rows.length * 40)}
        table={{
          columns: ['', t('seasonality.thisYear', { year: s.period.slice(0, 4) }), t('seasonality.median')],
          rows: rows.map((r) => [L(r.label), fmt(r.latest.value_pct), fmt(r.latest.median_pct)]),
        }}
        footnote={rows.some((r) => r.latest.n_years < 5) ? t('seasonality.shortHistory') : undefined}
      />
      <div className="panel">
        <h3>{t('summary.tableTitle')}</h3>
        <p className="muted small">{t('summary.tableSubtitle')}</p>
        <div className="table-x">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">{t('summary.component')}</th>
                <th scope="col">{t('summary.monthChange', { period })}</th>
                <th scope="col">{t('summary.usual')}</th>
                <th scope="col">{t('summary.yoyAt', { period })}</th>
                <th scope="col">{t('summary.yoyAt', { period: prev })}</th>
                <th scope="col">{t('summary.yoyChange')}</th>
              </tr>
            </thead>
            <tbody>
              {o.table.map((r: SeriesSnapshot) => (
                <tr key={r.series_id}>
                  <th scope="row">{L(r.label)}</th>
                  <td className="num">{fmt(r.mom_pct)}</td>
                  <td className="num">
                    {fmt(r.usual_mom_pct)}
                    {r.usual_years > 0 && r.usual_years < 5 ? ' *' : ''}
                  </td>
                  <td className="num">{fmt(r.yoy_pct)}</td>
                  <td className="num">{fmt(r.yoy_prev_pct)}</td>
                  <td>{r.yoy_change_pp !== null && <SignalBar value={r.yoy_change_pp} max={changeMax} label={pp(r.yoy_change_pp)} />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small">{t('seasonality.shortHistory')}</p>
      </div>
    </>
  );
}

/** Top 5 items pushing up and holding down, with their group and a signal bar. */
export function MoverTables({ d, t, locale, L, pp }: Ctx) {
  const dr = d.drivers;
  const table = (rows: Contribution[], title: string) => {
    // Each table on its own scale; the signed numbers keep the true sizes.
    const max = maxAbs(rows.map((r) => r.contribution_pp));
    return (
      <div className="panel">
        <h3>{title}</h3>
        {rows.length === 0 ? (
          <p className="muted">{t('drivers.none')}</p>
        ) : (
          <div className="table-x">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">{t('drivers.item')}</th>
                  <th scope="col">{t('drivers.change')}</th>
                  <th scope="col">{t('drivers.contribution')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.series_id}>
                    <th scope="row">
                      {L(r.label)}
                      {r.group && <span className="row-sub">{L(r.group)}</span>}
                    </th>
                    <td className="num">{formatPct(r.mom_pct, locale, true)}</td>
                    <td>
                      <SignalBar value={r.contribution_pp} max={max} label={pp(r.contribution_pp)} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  };
  return (
    <div className="split">
      {table(dr.top_up, t('drivers.topUp'))}
      {table(dr.top_down, t('drivers.topDown'))}
    </div>
  );
}

/** A share in whole percent ("68%"), for parts of a total. */
const wholePct = (v: number, locale: Locale) => `${formatNumber(v, locale, 0)}%`;

/**
 * How much of inflation came from core vs non-core: one bar split in two (blue and yellow),
 * for the month and for the 12-month rate. Names and numbers sit beside the bar, so the
 * colors are never the only signal.
 */
export function CoreSplit({ d, t, locale, pp }: Ctx) {
  const set = d.composition.sets.core_noncore;
  const [core, noncore] = set?.parts ?? [];
  if (!set || !core || !noncore) return null;
  const rows = [
    {
      key: 'month',
      title: t('summary.splitMonth', { period: formatPeriod(set.period, locale, 'long'), value: formatPct(set.parent.mom_pct ?? 0, locale, true) }),
      parts: [
        { name: t('composition.cnc.short.core'), cls: 'core', pp: core.contribution_pp, share: core.share_of_change_pct ?? null },
        { name: t('composition.cnc.short.noncore'), cls: 'noncore', pp: noncore.contribution_pp, share: noncore.share_of_change_pct ?? null },
      ],
    },
    ...(set.twelve_month_period && core.twelve_month_pp != null && noncore.twelve_month_pp != null
      ? [
          {
            key: '12m',
            title: t('summary.split12m', {
              period: formatPeriod(set.twelve_month_period, locale, 'long'),
              value: set.parent.yoy_pct !== null ? formatPct(set.parent.yoy_pct, locale) : '—',
            }),
            parts: [
              { name: t('composition.cnc.short.core'), cls: 'core', pp: core.twelve_month_pp, share: core.twelve_month_share_pct ?? null },
              { name: t('composition.cnc.short.noncore'), cls: 'noncore', pp: noncore.twelve_month_pp, share: noncore.twelve_month_share_pct ?? null },
            ],
          },
        ]
      : []),
  ];
  return (
    <div className="panel core-split">
      <h3>{t('summary.splitTitle')}</h3>
      {rows.map((row) => {
        // A bar of shares only makes sense when both parts pushed the same way.
        const drawable = row.parts.every((p) => p.share !== null && p.share > 0);
        return (
          <div className="core-split__row" key={row.key}>
            <p className="core-split__label">{row.title}</p>
            {drawable && (
              <div className="core-split__bar" aria-hidden="true">
                {row.parts.map((p) => (
                  <span key={p.cls} className={`core-split__seg core-split__seg--${p.cls}`} style={{ flexGrow: p.share ?? 0 }}>
                    {(p.share ?? 0) >= 12 && wholePct(p.share ?? 0, locale)}
                  </span>
                ))}
              </div>
            )}
            <div className="core-split__legend">
              {row.parts.map((p) => (
                <span key={p.cls}>
                  <span className={`core-split__swatch core-split__seg--${p.cls}`} aria-hidden="true" />
                  <b>{p.name}</b> {pp(p.pp)}
                  {p.share !== null && ` (${wholePct(p.share, locale)})`}
                </span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
