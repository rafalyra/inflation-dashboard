import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router';
import { ChartCard } from '../components/ChartCard';
import { Direction, StatTile } from '../components/StatTile';
import { TargetChip } from '../components/TargetChip';
import { usePageLocale, useLocale } from '../i18n';
import { contributionBars, lineOption, periodRows, stackedOption, valueFormatter } from '../lib/chartOptions';
import { type ChartTheme, useChartTheme } from '../lib/chartTheme';
import { useCountryTheme } from '../lib/countryTheme';
import { useCountry } from '../lib/data';
import {
  formatCountdown,
  formatDate,
  formatDateTime,
  formatMonthName,
  formatNumber,
  formatPct,
  formatPeriod,
  formatPpNumber,
} from '../lib/format';
import type { CountryData, Locale, LocalizedText } from '../lib/types';
import { NotFoundPage } from './NotFound';

interface Ctx {
  d: CountryData;
  locale: Locale;
  theme: ChartTheme;
  t: ReturnType<typeof useTranslation>['t'];
  L: (text: LocalizedText) => string;
  pp: (v: number, signed?: boolean) => string;
}

export function CountryPage() {
  const { t } = useTranslation();
  const { code = '' } = useParams();
  const state = useCountry(code);
  // Each country page opens in its own configured language (e.g. Brazil in Portuguese).
  usePageLocale(state.status === 'ready' ? state.data.country.default_locale : undefined);
  // The country's own palette (from config) while its page is open.
  useCountryTheme(code, state.status === 'ready' ? state.data.country.theme : null);

  if (state.status === 'loading') return <p className="muted">{t('status.loading')}</p>;
  if (state.status === 'error') return <NotFoundPage />;
  return <CountryView d={state.data} />;
}

export function CountryView({ d }: { d: CountryData }) {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const ctx: Ctx = {
    d,
    locale,
    theme,
    t,
    L: (text) => text[locale],
    pp: (v, signed = true) => t('units.pp', { value: formatPpNumber(v, locale, signed) }),
  };
  const sections = [
    ['snapshot', <Snapshot key="s" {...ctx} />],
    ['drivers', <Drivers key="d" {...ctx} />],
    ['trend', <Trend key="t" {...ctx} />],
    ['momentum', <Momentum key="m" {...ctx} />],
    ['base', <BaseEffects key="b" {...ctx} />],
    ['policy', <Policy key="p" {...ctx} />],
    ['history', <History key="h" {...ctx} />],
  ] as const;

  return (
    <>
      {d.sample && (
        <p className="notice" role="note">
          {t('sample.banner')}
        </p>
      )}
      <header className="country-head">
        <h1>{d.country.name[locale]}</h1>
        <SectionNav ids={sections.map(([id]) => id)} label={t('country.sections')} names={(id) => t(`country.section.${id}`)} />
      </header>
      {sections.map(([id, node]) => (
        <section key={id} id={id} className="country-section" aria-labelledby={`${id}-h`}>
          <h2 id={`${id}-h`}>{t(`country.section.${id}`)}</h2>
          {node}
        </section>
      ))}
    </>
  );
}

/**
 * Buttons that scroll to each section. The one for the section in view is highlighted
 * (and marked with aria-current), so the reader always knows where they are.
 */
function SectionNav({ ids, label, names }: { ids: readonly string[]; label: string; names: (id: string) => string }) {
  const [active, setActive] = useState(ids[0]);
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: '-80px 0px -60% 0px' },
    );
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [ids]);

  return (
    <nav className="section-nav" aria-label={label}>
      {ids.map((id) => (
        <button
          key={id}
          type="button"
          className="section-nav__button"
          aria-current={active === id ? 'true' : undefined}
          onClick={() => {
            setActive(id);
            const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
            document.getElementById(id)?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth' });
          }}
        >
          {names(id)}
        </button>
      ))}
    </nav>
  );
}

// ---- 1. Release snapshot ----------------------------------------------------------------

function Snapshot({ d, t, locale, L, pp }: Ctx) {
  const h = d.headline;
  const exp = h.expected;
  const month = formatMonthName(h.reference_period, locale);
  const driver = d.summary.top_driver;
  const p = d.preview;
  const now = new Date();
  return (
    <>
      <p className="lead">
        {t(h.mom_pct >= 0 ? 'snapshot.sentenceUp' : 'snapshot.sentenceDown', {
          indicator: h.indicator,
          month,
          value: formatPct(Math.abs(h.mom_pct), locale),
        })}
        {driver && ` ${t('snapshot.sentenceDriver', { driver: L(driver.label), value: pp(driver.contribution_pp) })}`}
        {d.summary.all_groups_rose && ` ${t('snapshot.allGroupsRose')}`}
      </p>
      <div className="tile-grid">
        <StatTile
          hero
          label={t('snapshot.mom', { indicator: h.indicator, period: formatPeriod(h.reference_period, locale, 'long') })}
          value={<span className="num">{formatPct(h.mom_pct, locale, true)}</span>}
          note={
            h.previous_mom_pct !== null &&
            t('snapshot.previous', { value: formatPct(h.previous_mom_pct, locale, true) })
          }
        />
        {h.yoy_pct !== null && (
          <StatTile label={t('snapshot.yoy')} value={<span className="num">{formatPct(h.yoy_pct, locale)}</span>} />
        )}
        {h.ytd_pct !== null && (
          <StatTile label={t('snapshot.ytd')} value={<span className="num">{formatPct(h.ytd_pct, locale)}</span>} />
        )}
        {d.core.available && d.core.latest_mean_pct !== undefined && (
          <StatTile
            label={t('snapshot.core')}
            value={<span className="num">{formatPct(d.core.latest_mean_pct, locale)}</span>}
            note={t('snapshot.coreNote', { count: d.core.members?.length ?? 0 })}
          />
        )}
      </div>

      <div className="tile-grid">
        <StatTile
          label={t('snapshot.expected')}
          value={exp ? <span className="num">{formatPct(exp.median_pct, locale, true)}</span> : t('snapshot.noExpectation')}
          note={
            exp &&
            t('snapshot.expectedNote', {
              source: t(`sources.${exp.source}`),
              date: formatDate(exp.survey_date, locale),
              count: exp.n_respondents ?? 0,
            })
          }
        />
        {h.surprise_pp !== null && (
          <StatTile
            label={t('snapshot.surprise')}
            value={<span className="num">{pp(h.surprise_pp)}</span>}
            note={
              <Direction
                value={h.surprise_pp}
                up={t('snapshot.aboveExpected')}
                down={t('snapshot.belowExpected')}
                flat={t('snapshot.asExpected')}
              />
            }
          />
        )}
        <StatTile
          label={t('snapshot.distance', { target: formatPct(d.target.target_pct, locale) })}
          value={<span className="num">{pp(d.target.distance_pp)}</span>}
          note={d.target.status && <TargetChip status={d.target.status} />}
        />
        {d.target.months_outside_band !== null && (
          <StatTile
            label={t('snapshot.outsideBand')}
            value={<span className="num">{t('snapshot.months', { count: d.target.months_outside_band })}</span>}
            note={
              d.target.miss_threshold_months &&
              t(d.target.missed ? 'snapshot.missed' : 'snapshot.missRule', { count: d.target.miss_threshold_months })
            }
          />
        )}
      </div>

      <div className="split">
        {p && (
          <div className="panel">
            <h3>
              {t('snapshot.preview', { indicator: L(p.label), period: formatPeriod(p.reference_period, locale, 'long') })}
            </h3>
            <p className="num big">{formatPct(p.mom_pct, locale, true)}</p>
            {p.yoy_pct !== null && <p>{t('snapshot.previewYoy', { value: formatPct(p.yoy_pct, locale) })}</p>}
            <p className="muted">{p.expected ? '' : t('snapshot.noExpectationPreview', { indicator: L(p.label) })}</p>
            {p.next_release && (
              <p className="muted">
                {t('snapshot.nextRelease', {
                  period: formatPeriod(p.next_release.reference_period, locale, 'long'),
                  when: formatDateTime(p.next_release.scheduled_utc, locale),
                  countdown: formatCountdown(p.next_release.scheduled_utc, now, locale) ?? '',
                })}
              </p>
            )}
          </div>
        )}
        {h.next_release && (
          <div className="panel">
            <h3>{t('snapshot.nextHeadline', { indicator: L(h.label) })}</h3>
            <p className="big">{formatCountdown(h.next_release.scheduled_utc, now, locale) ?? '—'}</p>
            <p className="muted">
              {t('snapshot.nextRelease', {
                period: formatPeriod(h.next_release.reference_period, locale, 'long'),
                when: formatDateTime(h.next_release.scheduled_utc, locale),
                countdown: '',
              })}
            </p>
          </div>
        )}
      </div>
    </>
  );
}

// ---- 2. Drivers ---------------------------------------------------------------------------

function Drivers({ d, t, locale, theme, L, pp }: Ctx) {
  const dr = d.drivers;
  const bars = useMemo(
    () =>
      contributionBars({
        labels: dr.groups.map((g) => L(g.label)),
        values: dr.groups.map((g) => g.contribution_pp),
        theme,
        locale,
      }),
    [dr, theme, locale, L],
  );
  const tm = dr.twelve_month;
  const stacked = useMemo(
    () =>
      stackedOption({
        periods: tm.periods,
        stacks: tm.series.map((s, i) => ({ name: L(s.label), values: s.values_pp, color: theme.series[i] ?? theme.ink })),
        total: { name: t('drivers.headlineYoy'), values: tm.headline_yoy_pct },
        theme,
        locale,
      }),
    [tm, theme, locale, L, t],
  );
  const fmtPp = valueFormatter('pp', locale);
  const other = tm.series.find((s) => s.series_id === 'other');

  const moverTable = (rows: typeof dr.top_up, title: string) => (
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
                <th scope="row">{L(r.label)}</th>
                <td className="num">{formatPct(r.mom_pct, locale, true)}</td>
                <td className="num">{pp(r.contribution_pp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );

  return (
    <>
      <ChartCard
        title={t('drivers.groupsTitle', { period: formatPeriod(dr.period, locale, 'long') })}
        subtitle={t('drivers.groupsSubtitle', { sum: pp(dr.sum_pp), headline: formatPct(dr.headline_mom_pct, locale, true) })}
        option={bars}
        height={Math.max(240, dr.groups.length * 34)}
        table={{
          columns: [t('drivers.group'), t('drivers.weight'), t('drivers.change'), t('drivers.contribution')],
          rows: dr.groups.map((g) => [
            L(g.label),
            g.weight_pct !== undefined ? formatPct(g.weight_pct, locale) : '—',
            formatPct(g.mom_pct, locale, true),
            fmtPp(g.contribution_pp),
          ]),
        }}
      />
      <div className="split">
        {moverTable(dr.top_up, t('drivers.topUp'))}
        {moverTable(dr.top_down, t('drivers.topDown'))}
      </div>
      <ChartCard
        title={t('drivers.stackedTitle')}
        subtitle={t('drivers.stackedSubtitle')}
        option={stacked}
        height={360}
        table={{
          columns: [t('table.month'), ...tm.series.map((s) => L(s.label)), t('drivers.headlineYoy'), t('drivers.rounding')],
          rows: periodRows(tm.periods, [...tm.series.map((s) => s.values_pp), tm.headline_yoy_pct, tm.rounding_pp], locale, 'pp'),
        }}
        footnote={
          <>
            {other?.members && t('drivers.otherNote', { groups: other.members.map(L).join(', ') })}{' '}
            {t('drivers.roundingNote')}
          </>
        }
      />
    </>
  );
}

// ---- 3. Underlying trend --------------------------------------------------------------------

function Trend({ d, t, locale, theme, L }: Ctx) {
  const core = d.core;
  const head = d.history.headline_yoy;
  const coreOption = useMemo(() => {
    if (!core.available || !core.periods) return null;
    const periods = core.periods;
    const headAligned = periods.map((p) => head.values[head.periods.indexOf(p)] ?? null);
    return lineOption({
      periods,
      series: [
        { name: t('trend.coreRange'), values: core.max_pct ?? [], bandLow: core.min_pct, color: theme.series[0] ?? '' },
        { name: t('trend.coreMean'), values: core.mean_pct ?? [], color: theme.series[0] ?? '' },
        { name: t('trend.headline'), values: headAligned, color: theme.series[1] ?? '' },
      ],
      theme,
      locale,
      unit: 'pct',
    });
  }, [core, head, theme, locale, t]);

  const panels = Object.entries(d.trend.panels);
  return (
    <>
      {coreOption && core.periods && (
        <ChartCard
          title={t('trend.coreTitle')}
          subtitle={t('trend.coreSubtitle', { members: (core.members ?? []).map((m) => L(m.label)).join(', ') })}
          option={coreOption}
          table={{
            columns: [t('table.month'), t('trend.coreMean'), t('trend.coreMin'), t('trend.coreMax')],
            rows: periodRows(core.periods, [core.mean_pct ?? [], core.min_pct ?? [], core.max_pct ?? []], locale, 'pct'),
          }}
        />
      )}
      <div className="split">
        {panels.map(([name, panel]) => (
          <PanelChart key={name} name={name} panel={panel} {...{ d, t, locale, theme, L }} />
        ))}
      </div>
      {d.trend.diffusion && <DiffusionChart {...{ d, t, locale, theme, L }} />}
    </>
  );
}

function PanelChart({
  name,
  panel,
  t,
  locale,
  theme,
  L,
}: Pick<Ctx, 't' | 'locale' | 'theme' | 'L'> & { name: string; panel: CountryData['trend']['panels'][string]; d: CountryData }) {
  const periods = panel.series[0]?.periods ?? [];
  const option = useMemo(
    () =>
      lineOption({
        periods,
        series: panel.series.map((s, i) => ({
          name: L(s.label),
          values: periods.map((p) => s.values[s.periods.indexOf(p)] ?? null),
          color: theme.series[i] ?? '',
        })),
        theme,
        locale,
        unit: 'pct',
      }),
    [panel, periods, theme, locale, L],
  );
  return (
    <ChartCard
      title={t(`trend.panel.${name}.title`)}
      subtitle={t(`trend.panel.${name}.subtitle`)}
      option={option}
      table={{
        columns: [t('table.month'), ...panel.series.map((s) => L(s.label))],
        rows: periodRows(periods, panel.series.map((s) => periods.map((p) => s.values[s.periods.indexOf(p)] ?? null)), locale, 'pct'),
      }}
    />
  );
}

function DiffusionChart({ d, t, locale, theme }: Pick<Ctx, 'd' | 't' | 'locale' | 'theme' | 'L'>) {
  const diff = d.trend.diffusion;
  const option = useMemo(
    () =>
      diff &&
      lineOption({
        periods: diff.periods,
        series: [{ name: t('trend.diffusion'), values: diff.values, color: theme.series[0] ?? '' }],
        theme,
        locale,
        unit: 'pct',
      }),
    [diff, theme, locale, t],
  );
  if (!diff || !option) return null;
  return (
    <ChartCard
      title={t('trend.diffusion')}
      subtitle={t('trend.diffusionSubtitle')}
      option={option}
      table={{ columns: [t('table.month'), t('trend.diffusion')], rows: periodRows(diff.periods, [diff.values], locale, 'pct') }}
    />
  );
}

// ---- 4. Momentum ----------------------------------------------------------------------------

function Momentum({ d, t, locale, theme }: Ctx) {
  const m = d.momentum;
  const saar = m.saar;
  const option = useMemo(
    () =>
      saar.available
        ? lineOption({
            periods: saar.periods,
            series: [
              { name: t('momentum.saar3'), values: saar.saar3_pct, color: theme.series[0] ?? '' },
              { name: t('momentum.saar6'), values: saar.saar6_pct, color: theme.series[1] ?? '' },
              { name: t('momentum.yoy'), values: saar.yoy_pct, color: theme.ink, dashed: true },
            ],
            theme,
            locale,
            unit: 'pct',
            zeroLine: true,
          })
        : null,
    [saar, theme, locale, t],
  );
  const sm = m.same_month;
  const sameOption = useMemo(
    () => ({
      ...lineOption({ periods: [], series: [], theme, locale, unit: 'pct' }),
      xAxis: {
        type: 'category',
        data: [...sm.years, sm.period.slice(0, 4)],
        axisLabel: { color: theme.ink, fontSize: 11 },
        axisLine: { lineStyle: { color: theme.axis } },
        axisTick: { show: false },
      },
      tooltip: { trigger: 'item', valueFormatter: valueFormatter('pct', locale) },
      series: [
        {
          type: 'bar',
          barMaxWidth: 20,
          data: [
            ...sm.past_pct.map((v) => ({ value: v, itemStyle: { color: theme.axis, borderRadius: v >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4] } })),
            { value: sm.value_pct, itemStyle: { color: theme.series[1], borderRadius: sm.value_pct >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4] } },
          ],
          markLine:
            sm.median_pct !== null
              ? {
                  silent: true,
                  symbol: 'none',
                  lineStyle: { color: theme.ink, type: 'dashed', width: 1 },
                  label: { formatter: t('momentum.median'), color: theme.ink, fontSize: 11 },
                  data: [{ yAxis: sm.median_pct }],
                }
              : undefined,
        },
      ],
    }),
    [sm, theme, locale, t],
  );
  const monthName = formatMonthName(sm.period, locale);
  return (
    <>
      {saar.available && option ? (
        <ChartCard
          title={t('momentum.title')}
          subtitle={t('momentum.subtitle')}
          option={option}
          table={{
            columns: [t('table.month'), t('momentum.saar3'), t('momentum.saar6'), t('momentum.yoy')],
            rows: periodRows(saar.periods, [saar.saar3_pct, saar.saar6_pct, saar.yoy_pct], locale, 'pct'),
          }}
          footnote={t('momentum.revisable', { from: formatPeriod(saar.revisable_from, locale) })}
        />
      ) : (
        <p className="notice">{t('momentum.unavailable')}</p>
      )}
      <ChartCard
        title={t('momentum.sameMonthTitle', { month: monthName })}
        subtitle={t('momentum.sameMonthSubtitle', {
          value: formatPct(sm.value_pct, locale, true),
          median: sm.median_pct !== null ? formatPct(sm.median_pct, locale, true) : '—',
          count: sm.years.length,
        })}
        option={sameOption}
        height={260}
        table={{
          columns: [t('table.year'), t('momentum.change')],
          rows: [...sm.years.map((y, i) => [y, formatPct(sm.past_pct[i] ?? 0, locale, true)]), [sm.period.slice(0, 4), formatPct(sm.value_pct, locale, true)]].reverse(),
        }}
      />
    </>
  );
}

// ---- 5. Base effects --------------------------------------------------------------------------

function BaseEffects({ d, t, locale }: Ctx) {
  const b = d.base_effects;
  const first = b.dropping_out[0];
  return (
    <>
      <p>{t('base.explainer')}</p>
      <div className="tile-grid">
        {b.dropping_out.map((row) => (
          <StatTile
            key={row.period}
            label={t('base.release', { period: formatPeriod(row.period, locale, 'long') })}
            value={<span className="num">{row.leaving_mom_pct !== null ? formatPct(row.leaving_mom_pct, locale, true) : '—'}</span>}
            note={t('base.leaving', { period: formatPeriod(row.leaving_period, locale, 'long') })}
          />
        ))}
      </div>
      {first && b.next_expected && b.implied_next_yoy_pct !== null && d.headline.yoy_pct !== null ? (
        <p className="lead">
          {t('base.implied', {
            period: formatMonthName(first.period, locale),
            expected: formatPct(b.next_expected.median_pct, locale, true),
            leaving: first.leaving_mom_pct !== null ? formatPct(first.leaving_mom_pct, locale, true) : '—',
            from: formatPct(d.headline.yoy_pct, locale),
            to: formatPct(b.implied_next_yoy_pct, locale),
          })}{' '}
          <span className="muted">
            {t('base.impliedSource', { source: t(`sources.${b.next_expected.source}`), date: formatDate(b.next_expected.survey_date, locale) })}
          </span>
        </p>
      ) : (
        <p className="muted">{t('base.noExpectation')}</p>
      )}
    </>
  );
}

// ---- 6. Policy and markets ----------------------------------------------------------------------

function Policy({ d, t, locale, theme, L }: Ctx) {
  const p = d.policy;
  const rateOption = useMemo(() => {
    if (!p.policy_rate) return null;
    const periods = p.policy_rate.history.periods;
    const real = p.real_ex_ante?.history;
    return lineOption({
      periods,
      series: [
        { name: L(p.policy_rate.label), values: p.policy_rate.history.values, color: theme.series[0] ?? '' },
        ...(real
          ? [{ name: t('policy.realRate'), values: periods.map((x) => real.values[real.periods.indexOf(x)] ?? null), color: theme.series[1] ?? '' }]
          : []),
      ],
      theme,
      locale,
      unit: 'pct',
    });
  }, [p, theme, locale, L, t]);
  const expOption = useMemo(
    () =>
      p.expectations_12m &&
      lineOption({
        periods: p.expectations_12m.periods,
        series: [{ name: t('policy.exp12m'), values: p.expectations_12m.values, color: theme.series[0] ?? '' }],
        theme,
        locale,
        unit: 'pct',
        band:
          d.target.band_low_pct !== null && d.target.band_high_pct !== null
            ? {
                low: d.target.band_low_pct,
                high: d.target.band_high_pct,
                target: d.target.target_pct,
                label: t('history.band'),
                targetLabel: t('history.target', { value: formatPct(d.target.target_pct, locale) }),
              }
            : null,
      }),
    [p, d.target, theme, locale, t],
  );
  const fxOption = useMemo(
    () =>
      p.fx &&
      lineOption({
        periods: p.fx.monthly_average.periods,
        series: [{ name: L(p.fx.label), values: p.fx.monthly_average.values, color: theme.series[0] ?? '' }],
        theme,
        locale,
        unit: 'plain',
      }),
    [p, theme, locale, L],
  );
  return (
    <>
      <div className="tile-grid">
        {p.policy_rate && (
          <StatTile
            label={L(p.policy_rate.label)}
            value={<span className="num">{formatPct(p.policy_rate.rate_pct, locale)}</span>}
            note={formatDate(p.policy_rate.date, locale)}
          />
        )}
        {p.real_ex_ante && (
          <StatTile
            label={t('policy.realRate')}
            value={<span className="num">{formatPct(p.real_ex_ante.rate_pct, locale)}</span>}
            note={t('policy.realNote', { value: formatPct(p.real_ex_ante.expected_inflation_pct, locale) })}
          />
        )}
        {p.year_end_expectations.map((y) => (
          <StatTile
            key={y.year}
            label={t('policy.yearEnd', { year: y.year })}
            value={<span className="num">{formatPct(y.median_pct, locale)}</span>}
            note={t('policy.surveyOf', { date: formatDate(y.survey_date, locale) })}
          />
        ))}
        {p.fx && (
          <StatTile
            label={L(p.fx.label)}
            value={<span className="num">{formatNumber(p.fx.value, locale, 4)}</span>}
            note={p.fx.yoy_pct !== null && t('policy.fxChange', { value: formatPct(p.fx.yoy_pct, locale, true), date: formatDate(p.fx.date, locale) })}
          />
        )}
      </div>
      {rateOption && p.policy_rate && (
        <ChartCard
          title={t('policy.ratesTitle')}
          subtitle={t('policy.ratesSubtitle')}
          option={rateOption}
          table={{
            columns: [t('table.month'), L(p.policy_rate.label), t('policy.realRate')],
            rows: periodRows(
              p.policy_rate.history.periods,
              [p.policy_rate.history.values, p.policy_rate.history.periods.map((x) => p.real_ex_ante?.history.values[p.real_ex_ante.history.periods.indexOf(x)] ?? null)],
              locale,
              'pct',
            ),
          }}
        />
      )}
      <div className="split">
        {expOption && p.expectations_12m && (
          <ChartCard
            title={t('policy.exp12m')}
            subtitle={t('policy.exp12mSubtitle', { source: t(`sources.${p.expectations_12m.source}`) })}
            option={expOption}
            table={{ columns: [t('table.month'), t('policy.exp12m')], rows: periodRows(p.expectations_12m.periods, [p.expectations_12m.values], locale, 'pct') }}
          />
        )}
        {fxOption && p.fx && (
          <ChartCard
            title={t('policy.fxTitle', { label: L(p.fx.label) })}
            subtitle={t('policy.fxSubtitle')}
            option={fxOption}
            table={{
              columns: [t('table.month'), L(p.fx.label)],
              rows: p.fx.monthly_average.periods
                .map((x, i) => [formatPeriod(x, locale), formatNumber(p.fx?.monthly_average.values[i] ?? 0, locale, 4)])
                .reverse(),
            }}
          />
        )}
      </div>
    </>
  );
}

// ---- 7. History -------------------------------------------------------------------------------

function History({ d, t, locale, theme }: Ctx) {
  const h = d.history;
  const option = useMemo(
    () =>
      lineOption({
        periods: h.headline_yoy.periods,
        series: [
          { name: t('history.headline', { indicator: d.headline.indicator }), values: h.headline_yoy.values, color: theme.series[1] ?? '' },
          {
            name: t('history.core'),
            values: h.headline_yoy.periods.map((p) => h.core_mean_yoy.values[h.core_mean_yoy.periods.indexOf(p)] ?? null),
            color: theme.series[0] ?? '',
          },
        ],
        theme,
        locale,
        unit: 'pct',
        band:
          d.target.band_low_pct !== null && d.target.band_high_pct !== null
            ? {
                low: d.target.band_low_pct,
                high: d.target.band_high_pct,
                target: d.target.target_pct,
                label: t('history.band'),
                targetLabel: t('history.target', { value: formatPct(d.target.target_pct, locale) }),
              }
            : null,
      }),
    [h, d.target, d.headline.indicator, theme, locale, t],
  );
  return (
    <>
      {d.target.months_outside_band !== null && (
        <p className="lead">
          {d.target.months_outside_band === 0
            ? t('history.insideNow')
            : t('history.streak', { count: d.target.months_outside_band, threshold: d.target.miss_threshold_months ?? 0 })}
        </p>
      )}
      <ChartCard
        title={t('history.title', { indicator: d.headline.indicator })}
        subtitle={t('history.subtitle', {
          low: formatPct(d.target.band_low_pct ?? 0, locale),
          high: formatPct(d.target.band_high_pct ?? 0, locale),
        })}
        option={option}
        height={340}
        table={{
          columns: [t('table.month'), t('history.headline', { indicator: d.headline.indicator }), t('history.core')],
          rows: periodRows(
            h.headline_yoy.periods,
            [h.headline_yoy.values, h.headline_yoy.periods.map((p) => h.core_mean_yoy.values[h.core_mean_yoy.periods.indexOf(p)] ?? null)],
            locale,
            'pct',
          ),
        }}
      />
    </>
  );
}
