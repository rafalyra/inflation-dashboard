import { useMemo, useState } from 'react';
import { ChartCard } from '../components/ChartCard';
import { Chart } from '../components/Chart';
import {
  contributionBars,
  lineOption,
  monthlyBarsOption,
  periodRows,
  profileOption,
  rangeOption,
  stackedOption,
  changeColor,
  treemapOption,
  type TreeNode,
  valueFormatter,
} from '../lib/chartOptions';
import { useExplore } from '../lib/data';
import { formatPct, formatPeriod } from '../lib/format';
import type { ContributionSet, ExploreSeries, TreemapNode } from '../lib/types';
import type { Ctx } from './Country';

// Composition, Seasonality and Explore tabs. Every number comes from the export; this file
// only arranges values into charts and tables.

const MONTH_INDEX = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'];

function monthLabels(locale: string): string[] {
  return MONTH_INDEX.map((m) =>
    new Intl.DateTimeFormat(locale, { month: 'short', timeZone: 'UTC' }).format(new Date(Date.UTC(2020, Number(m) - 1, 1))),
  );
}

/** A row of buttons to pick one option, marked with aria-pressed. */
function Picker<T extends string>({ options, value, onChange, label }: { options: { id: T; name: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div className="picker" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} type="button" className="section-nav__button" aria-pressed={o.id === value} onClick={() => onChange(o.id)}>
          {o.name}
        </button>
      ))}
    </div>
  );
}

// ---- Composition --------------------------------------------------------------------------

export function RecentContributions({ d, t, locale, theme, L }: Ctx) {
  const sets = d.composition.sets;
  const ids = Object.keys(sets);
  const [setId, setSetId] = useState(ids[0] ?? 'groups');
  const set = sets[setId];
  const option = useMemo(
    () =>
      set &&
      monthlyBarsOption({
        periods: set.monthly.periods,
        stacks: set.monthly.series.map((s, i) => ({ name: L(s.label), values: s.values_pp, color: theme.series[i % 8] ?? theme.ink })),
        total: { name: t('composition.headlineMom'), values: set.monthly.headline_mom_pct },
        theme,
        locale,
      }),
    [set, theme, locale, L, t],
  );
  if (!set || !option) return null;
  return (
    <>
      <Picker label={t('composition.splitBy')} value={setId} onChange={setSetId} options={ids.map((id) => ({ id, name: t(`composition.set.${id}`) }))} />
      <ChartCard
        title={t('composition.recentTitle')}
        subtitle={t('composition.recentSubtitle')}
        option={option}
        height={380}
        table={{
          columns: [t('table.month'), ...set.monthly.series.map((s) => L(s.label)), t('composition.headlineMom')],
          rows: periodRows(set.monthly.periods, [...set.monthly.series.map((s) => s.values_pp), set.monthly.headline_mom_pct], locale, 'pp'),
        }}
        footnote={(() => {
          const other = set.monthly.series.find((s) => s.series_id === 'other') as { members?: { en: string; 'pt-BR': string }[] } | undefined;
          return other?.members ? t('drivers.otherNote', { groups: other.members.map(L).join(', ') }) : undefined;
        })()}
      />
    </>
  );
}

export function Segments({ d, t, locale, theme, L, pp }: Ctx) {
  const set: ContributionSet | undefined = d.composition.sets.bcb_segments;
  const stacked = useMemo(
    () =>
      set &&
      stackedOption({
        periods: set.twelve_month.periods,
        stacks: set.twelve_month.series.map((s, i) => ({ name: L(s.label), values: s.values_pp, color: theme.series[i] ?? theme.ink })),
        total: { name: t('drivers.headlineYoy'), values: set.twelve_month.headline_yoy_pct },
        theme,
        locale,
      }),
    [set, theme, locale, L, t],
  );
  const yoy = useMemo(() => {
    if (!set) return null;
    const periods = set.yoy.series[0]?.periods ?? [];
    return lineOption({
      periods,
      series: set.yoy.series.map((s, i) => ({ name: L(s.label), values: periods.map((p) => s.values[s.periods.indexOf(p)] ?? null), color: theme.series[i] ?? '' })),
      theme,
      locale,
      unit: 'pct',
    });
  }, [set, theme, locale, L]);
  if (!set || !stacked || !yoy) return <p className="muted">{t('composition.noSegments')}</p>;
  return (
    <>
      <p>{t('composition.segmentsIntro', { period: formatPeriod(set.period, locale, 'long') })}</p>
      <div className="panel table-x">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">{t('composition.segment')}</th>
              <th scope="col">{t('drivers.weight')}</th>
              <th scope="col">{t('drivers.change')}</th>
              <th scope="col">{t('drivers.contribution')}</th>
              <th scope="col">{t('snapshot.yoy')}</th>
            </tr>
          </thead>
          <tbody>
            {set.parts.map((p) => (
              <tr key={p.series_id}>
                <th scope="row">{L(p.label)}</th>
                <td className="num">{formatPct(p.weight_pct, locale)}</td>
                <td className="num">{formatPct(p.mom_pct, locale, true)}</td>
                <td className="num">{pp(p.contribution_pp)}</td>
                <td className="num">{p.yoy_pct !== null ? formatPct(p.yoy_pct, locale) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="split">
        <ChartCard
          title={t('composition.segments12mTitle')}
          subtitle={t('composition.segments12mSubtitle')}
          option={stacked}
          height={340}
          table={{
            columns: [t('table.month'), ...set.twelve_month.series.map((s) => L(s.label)), t('drivers.headlineYoy')],
            rows: periodRows(set.twelve_month.periods, [...set.twelve_month.series.map((s) => s.values_pp), set.twelve_month.headline_yoy_pct], locale, 'pp'),
          }}
        />
        <ChartCard
          title={t('composition.segmentsYoyTitle')}
          subtitle={t('composition.segmentsYoySubtitle')}
          option={yoy}
          height={340}
          table={{
            columns: [t('table.month'), ...set.yoy.series.map((s) => L(s.label))],
            rows: periodRows(set.yoy.series[0]?.periods ?? [], set.yoy.series.map((s) => s.values), locale, 'pct'),
          }}
        />
      </div>
    </>
  );
}

function toTree(nodes: TreemapNode[], parent: string, L: Ctx['L'], theme: Ctx['theme']): TreeNode[] {
  return nodes
    .filter((n) => n.parent === parent)
    .map((n) => {
      const children = toTree(nodes, n.id, L, theme);
      return {
        name: L(n.label),
        value: [n.weight_pct, n.mom_pct] as [number, number],
        contribution: n.contribution_pp,
        itemStyle: { color: changeColor(n.mom_pct, theme) },
        ...(children.length ? { children } : {}),
      };
    });
}

export function BasketMap({ d, t, locale, theme, L }: Ctx) {
  const tm = d.composition.treemap;
  const root = d.headline.series_id;
  const option = useMemo(
    () =>
      treemapOption({
        data: toTree(tm.nodes, root, L, theme),
        theme,
        locale,
        rootName: L(d.headline.label),
        names: { weight: t('drivers.weight'), change: t('drivers.change'), contribution: t('drivers.contribution') },
      }),
    [tm, root, theme, locale, L, t, d.headline.label],
  );
  const groups = tm.nodes.filter((n) => n.level === 1);
  return (
    <ChartCard
      title={t('composition.basketTitle', { period: formatPeriod(tm.period, locale, 'long') })}
      subtitle={t('composition.basketSubtitle')}
      option={option}
      height={520}
      table={{
        columns: [t('drivers.group'), t('drivers.weight'), t('drivers.change'), t('drivers.contribution')],
        rows: groups.map((g) => [L(g.label), formatPct(g.weight_pct, locale), formatPct(g.mom_pct, locale, true), valueFormatter('pp', locale)(g.contribution_pp)]),
      }}
    />
  );
}

export function GroupsSmallMultiples({ d, t, locale, theme, L }: Ctx) {
  const groups = d.composition.groups_yoy;
  const all = groups.flatMap((g) => g.values.filter((v): v is number => v !== null));
  const yRange = { min: Math.floor(Math.min(...all, 0)), max: Math.ceil(Math.max(...all)) };
  const band = d.target.band_low_pct !== null && d.target.band_high_pct !== null;
  return (
    <>
      <p className="muted">{t('composition.smallMultiplesNote', { min: formatPct(yRange.min, locale), max: formatPct(yRange.max, locale) })}</p>
      <div className="multiples">
        {groups.map((g) => (
          <figure key={g.series_id} className="multiple">
            <figcaption>
              <span>{L(g.label)}</span>
              <span className="num">{formatPct(g.values.at(-1) ?? 0, locale)}</span>
            </figcaption>
            <Chart
              label={L(g.label)}
              height={150}
              option={{
                ...lineOption({
                  periods: g.periods,
                  series: [{ name: L(g.label), values: g.values, color: theme.series[0] ?? '' }],
                  theme,
                  locale,
                  unit: 'pct',
                  yRange,
                  band: band
                    ? { low: d.target.band_low_pct as number, high: d.target.band_high_pct as number, target: d.target.target_pct, label: t('history.band'), targetLabel: '' }
                    : null,
                }),
                grid: { left: 4, right: 8, top: 8, bottom: 4, containLabel: true },
              }}
            />
          </figure>
        ))}
      </div>
    </>
  );
}

export function WeightedDiffusion({ d, t, locale, theme }: Ctx) {
  const wd = d.composition.weighted_diffusion;
  const bcb = d.trend.diffusion;
  const option = useMemo(() => {
    if (!wd) return null;
    const periods = wd.rising.periods;
    const align = (pts: { periods: string[]; values: (number | null)[] } | null | undefined) =>
      periods.map((p) => (pts ? pts.values[pts.periods.indexOf(p)] ?? null : null));
    return lineOption({
      periods,
      series: [
        { name: t('composition.diffusionWeighted'), values: wd.rising.values, color: theme.series[0] ?? '' },
        ...(bcb ? [{ name: t('composition.diffusionCount'), values: align(bcb), color: theme.series[1] ?? '' }] : []),
        ...(wd.above_threshold
          ? [{ name: t('composition.diffusionAbove', { value: formatPct(wd.above_threshold.threshold_pct, locale) }), values: align(wd.above_threshold), color: theme.series[3] ?? '' }]
          : []),
      ],
      theme,
      locale,
      unit: 'pct',
    });
  }, [wd, bcb, theme, locale, t]);
  if (!wd || !option) return null;
  return (
    <ChartCard
      title={t('composition.diffusionTitle')}
      subtitle={t('composition.diffusionSubtitle')}
      option={option}
      table={{
        columns: [t('table.month'), t('composition.diffusionWeighted'), t('composition.diffusionAboveShort')],
        rows: periodRows(wd.rising.periods, [wd.rising.values, wd.rising.periods.map((p) => wd.above_threshold?.values[wd.above_threshold.periods.indexOf(p)] ?? null)], locale, 'pct'),
      }}
    />
  );
}

// ---- Seasonality --------------------------------------------------------------------------

export function SeasonalPattern({ d, t, locale, theme, L }: Ctx) {
  const s = d.seasonality;
  const option = useMemo(
    () =>
      s &&
      rangeOption({
        rows: s.series.map((r) => ({
          label: L(r.label) + (r.latest.n_years < 5 ? ' *' : ''),
          value: r.latest.value_pct,
          median: r.latest.median_pct,
          q25: r.latest.q25_pct,
          q75: r.latest.q75_pct,
        })),
        theme,
        locale,
        names: { band: t('seasonality.band'), median: t('seasonality.median'), value: t('seasonality.thisYear', { year: s.period.slice(0, 4) }) },
      }),
    [s, theme, locale, L, t],
  );
  if (!s || !option) return null;
  const month = formatPeriod(s.period, locale, 'long');
  const years = s.baseline_years;
  return (
    <ChartCard
      title={t('seasonality.patternTitle', { period: month })}
      subtitle={t('seasonality.patternSubtitle')}
      option={option}
      height={Math.max(320, s.series.length * 34)}
      table={{
        columns: ['', t('seasonality.thisYear', { year: s.period.slice(0, 4) }), t('seasonality.median'), t('seasonality.band'), t('seasonality.deviation')],
        rows: s.series.map((r) => [
          L(r.label),
          formatPct(r.latest.value_pct, locale, true),
          r.latest.median_pct !== null ? formatPct(r.latest.median_pct, locale, true) : '—',
          r.latest.q25_pct !== null && r.latest.q75_pct !== null ? `${formatPct(r.latest.q25_pct, locale)} – ${formatPct(r.latest.q75_pct, locale)}` : '—',
          r.latest.deviation_pp !== null ? valueFormatter('pp', locale)(r.latest.deviation_pp) : '—',
        ]),
      }}
      footnote={
        <>
          {t('seasonality.baselineNote', { first: years[0], last: years.at(-1), count: years.length })}{' '}
          {s.series.some((r) => r.latest.n_years < 5) && t('seasonality.shortHistory')}
        </>
      }
    />
  );
}

export function SeasonalDeviation({ d, t, locale, theme, L, pp }: Ctx) {
  const s = d.seasonality;
  const option = useMemo(
    () => s && contributionBars({ labels: s.deviation.groups.map((g) => L(g.label)), values: s.deviation.groups.map((g) => g.deviation_pp), theme, locale }),
    [s, theme, locale, L],
  );
  if (!s || !option) return null;
  const table = (rows: typeof s.deviation.items_up, title: string) => (
    <div className="panel">
      <h3>{title}</h3>
      <div className="table-x">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">{t('drivers.item')}</th>
              <th scope="col">{t('seasonality.deviation')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.series_id}>
                <th scope="row">{L(r.label)}</th>
                <td className="num">{pp(r.deviation_pp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
  return (
    <>
      <p>{t('seasonality.deviationIntro', { total: pp(s.deviation.total_pp) })}</p>
      <ChartCard
        title={t('seasonality.deviationTitle')}
        subtitle={t('seasonality.deviationSubtitle')}
        option={option}
        height={Math.max(240, s.deviation.groups.length * 34)}
        table={{ columns: [t('drivers.group'), t('seasonality.deviation')], rows: s.deviation.groups.map((g) => [L(g.label), pp(g.deviation_pp)]) }}
      />
      <div className="split">
        {table(s.deviation.items_up, t('seasonality.itemsUp'))}
        {table(s.deviation.items_down, t('seasonality.itemsDown'))}
      </div>
    </>
  );
}

export function SeasonalProfiles({ d, t, locale, theme, L }: Ctx) {
  const s = d.seasonality;
  const [id, setId] = useState(s?.series[0]?.series_id ?? '');
  const row = s?.series.find((r) => r.series_id === id) ?? s?.series[0];
  const option = useMemo(
    () =>
      row &&
      profileOption({
        months: monthLabels(locale),
        current: { name: String(row.profile.year), values: row.profile.current },
        previous: Object.entries(row.profile.previous).map(([y, v]) => ({ name: y, values: v })),
        median: row.profile.median_pct,
        q25: row.profile.q25_pct,
        q75: row.profile.q75_pct,
        theme,
        locale,
        names: { band: t('seasonality.band'), median: t('seasonality.median') },
      }),
    [row, theme, locale, t],
  );
  if (!s || !row || !option) return null;
  const months = monthLabels(locale);
  const prevYears = Object.keys(row.profile.previous);
  return (
    <>
      <Picker label={t('seasonality.pickSeries')} value={row.series_id} onChange={setId} options={s.series.map((r) => ({ id: r.series_id, name: L(r.label) }))} />
      <ChartCard
        title={t('seasonality.profileTitle', { name: L(row.label) })}
        subtitle={t('seasonality.profileSubtitle')}
        option={option}
        height={360}
        table={{
          columns: [t('table.month'), String(row.profile.year), ...prevYears, t('seasonality.median')],
          rows: months.map((m, i) => [
            m,
            ...[row.profile.current[i], ...prevYears.map((y) => row.profile.previous[y]?.[i] ?? null), row.profile.median_pct[i]].map((v) => valueFormatter('pct', locale)(v ?? null)),
          ]),
        }}
      />
    </>
  );
}

export function AdjustedChange({ d, t, locale, theme }: Ctx) {
  const a = d.adjusted;
  const sa = useMemo(
    () =>
      a.available
        ? lineOption({
            periods: a.sa_mom.periods,
            series: [
              { name: t('seasonality.saHeadline'), values: a.sa_mom.headline_pct, color: theme.series[0] ?? '' },
              { name: t('seasonality.saCore'), values: a.sa_mom.core_pct, color: theme.series[1] ?? '' },
            ],
            theme,
            locale,
            unit: 'pct',
            zeroLine: true,
          })
        : null,
    [a, theme, locale, t],
  );
  const core = useMemo(
    () =>
      a.available
        ? lineOption({
            periods: a.core_saar.periods,
            series: [
              { name: t('momentum.saar3'), values: a.core_saar.saar3_pct, color: theme.series[0] ?? '' },
              { name: t('momentum.saar6'), values: a.core_saar.saar6_pct, color: theme.series[1] ?? '' },
              { name: t('momentum.yoy'), values: a.core_saar.yoy_pct, color: theme.ink, dashed: true },
            ],
            theme,
            locale,
            unit: 'pct',
            zeroLine: true,
          })
        : null,
    [a, theme, locale, t],
  );
  if (!a.available || !sa || !core) return <p className="notice">{t('momentum.unavailable')}</p>;
  const note = t('momentum.revisable', { from: formatPeriod(a.revisable_from, locale) });
  return (
    <div className="split">
      <ChartCard
        title={t('seasonality.saTitle')}
        subtitle={t('seasonality.saSubtitle')}
        option={sa}
        table={{ columns: [t('table.month'), t('seasonality.saHeadline'), t('seasonality.saCore')], rows: periodRows(a.sa_mom.periods, [a.sa_mom.headline_pct, a.sa_mom.core_pct], locale, 'pct') }}
        footnote={note}
      />
      <ChartCard
        title={t('seasonality.coreMomentumTitle')}
        subtitle={t('seasonality.coreMomentumSubtitle')}
        option={core}
        table={{
          columns: [t('table.month'), t('momentum.saar3'), t('momentum.saar6'), t('momentum.yoy')],
          rows: periodRows(a.core_saar.periods, [a.core_saar.saar3_pct, a.core_saar.saar6_pct, a.core_saar.yoy_pct], locale, 'pct'),
        }}
        footnote={note}
      />
    </div>
  );
}

// ---- Explore ------------------------------------------------------------------------------

const MAX_RESULTS = 40;

function normalize(text: string): string {
  return text.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
}

export function Explore(ctx: Ctx) {
  const { d, t } = ctx;
  const state = useExplore(d.country.code);
  if (state.status === 'loading') return <p className="muted">{t('status.loading')}</p>;
  if (state.status === 'error') return <p role="alert">{t('status.error')}</p>;
  return <ExploreView {...ctx} periods={state.data.periods} series={state.data.series} baselineYears={state.data.baseline_years} />;
}

function ExploreView({ t, locale, theme, L, periods, series, baselineYears }: Ctx & { periods: string[]; series: ExploreSeries[]; baselineYears: number[] }) {
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState(series[0]?.series_id ?? '');
  const byId = useMemo(() => new Map(series.map((s) => [s.series_id, s])), [series]);
  const results = useMemo(() => {
    const q = normalize(query.trim());
    const list = q ? series.filter((s) => normalize(`${s.label.en} ${s.label['pt-BR']}`).includes(q)) : series.filter((s) => s.level <= 1 || s.concept === 'bcb_segment');
    return list.slice(0, MAX_RESULTS);
  }, [query, series]);
  const sel = byId.get(selectedId) ?? series[0];

  const history = useMemo(
    () =>
      sel &&
      lineOption({
        periods,
        series: [
          { name: t('explore.yoy'), values: sel.yoy_pct, color: theme.series[0] ?? '' },
          { name: t('explore.mom'), values: sel.mom_pct, color: theme.series[1] ?? '' },
        ],
        theme,
        locale,
        unit: 'pct',
        zeroLine: true,
      }),
    [sel, periods, theme, locale, t],
  );
  const lastYear = Number(periods.at(-1)?.slice(0, 4));
  const profile = useMemo(() => {
    if (!sel) return null;
    const valuesFor = (year: number) =>
      MONTH_INDEX.map((m) => {
        const i = periods.indexOf(`${year}-${m}`);
        return i >= 0 ? (sel.mom_pct[i] ?? null) : null;
      });
    return profileOption({
      months: monthLabels(locale),
      current: { name: String(lastYear), values: valuesFor(lastYear) },
      previous: [lastYear - 1].map((y) => ({ name: String(y), values: valuesFor(y) })),
      median: sel.seasonal.median_pct,
      q25: sel.seasonal.q25_pct,
      q75: sel.seasonal.q75_pct,
      theme,
      locale,
      names: { band: t('seasonality.band'), median: t('seasonality.median') },
    });
  }, [sel, periods, lastYear, theme, locale, t]);
  if (!sel || !history || !profile) return null;
  const parent = sel.parent ? byId.get(sel.parent) : undefined;
  const lastWeight = [...sel.weight_pct].reverse().find((v) => v !== null);
  const lastIdx = periods.length - 1;

  return (
    <>
      <p>{t('explore.intro', { count: series.length })}</p>
      <div className="explore">
        <div className="panel explore__search">
          <label htmlFor="explore-query" className="tile__label">
            {t('explore.search')}
          </label>
          <input
            id="explore-query"
            className="input"
            type="search"
            value={query}
            placeholder={t('explore.placeholder')}
            onChange={(e) => setQuery(e.target.value)}
          />
          <ul className="explore__results" aria-label={t('explore.results')}>
            {results.map((s) => (
              <li key={s.series_id}>
                <button type="button" className="explore__result" aria-pressed={s.series_id === sel.series_id} onClick={() => setSelectedId(s.series_id)}>
                  <span>{L(s.label)}</span>
                  <span className="muted">{t(`explore.level.${s.concept}`, { defaultValue: s.concept })}</span>
                </button>
              </li>
            ))}
            {results.length === 0 && <li className="muted">{t('explore.noResults')}</li>}
          </ul>
        </div>
        <div className="explore__detail">
          <div className="panel">
            <h3>{L(sel.label)}</h3>
            <p className="muted">
              {t(`explore.level.${sel.concept}`, { defaultValue: sel.concept })}
              {parent && ` · ${t('explore.partOf', { parent: L(parent.label) })}`}
              {lastWeight != null && ` · ${t('explore.weight', { value: formatPct(lastWeight, locale) })}`}
            </p>
            <p>
              {t('explore.latest', {
                period: formatPeriod(periods[lastIdx] ?? '', locale, 'long'),
                mom: sel.mom_pct[lastIdx] != null ? formatPct(sel.mom_pct[lastIdx] as number, locale, true) : '—',
                yoy: sel.yoy_pct[lastIdx] != null ? formatPct(sel.yoy_pct[lastIdx] as number, locale) : '—',
              })}
            </p>
          </div>
          <ChartCard
            title={t('explore.historyTitle')}
            subtitle={t('explore.historySubtitle')}
            option={history}
            table={{ columns: [t('table.month'), t('explore.yoy'), t('explore.mom')], rows: periodRows(periods, [sel.yoy_pct, sel.mom_pct], locale, 'pct') }}
          />
          <ChartCard
            title={t('explore.profileTitle')}
            subtitle={t('explore.profileSubtitle', { first: baselineYears[0], last: baselineYears.at(-1) })}
            option={profile}
            table={{
              columns: [t('table.month'), String(lastYear), t('seasonality.median')],
              rows: monthLabels(locale).map((m, i) => {
                const idx = periods.indexOf(`${lastYear}-${MONTH_INDEX[i]}`);
                return [m, valueFormatter('pct', locale)(idx >= 0 ? sel.mom_pct[idx] : null), valueFormatter('pct', locale)(sel.seasonal.median_pct[i])];
              }),
            }}
          />
        </div>
      </div>
    </>
  );
}
