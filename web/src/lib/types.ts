// Shape of the JSON the pipeline exports (src/inflation/export.py). The web app only
// displays these values; every metric is computed in Python.

export type Locale = 'en' | 'pt-BR';

export type LocalizedText = Record<Locale, string>;

export type TargetStatus = 'inside' | 'above' | 'below';

// ---- overview.json ----

export interface CountrySummary {
  code: string;
  name: LocalizedText;
  default_locale: Locale;
  color_token: string;
  indicator: string;
  reference_period: string; // YYYY-MM
  headline_yoy_pct: number;
  headline_mom_pct: number;
  core_yoy_pct: number | null;
  target_status: TargetStatus | null;
  last_release_date: string | null; // YYYY-MM-DD
  next_release_utc: string | null; // ISO 8601
}

export interface ReleaseFeedItem {
  country: string;
  indicator: string;
  reference_period: string;
  released_utc: string;
  mom_pct: number;
}

export interface OverviewData {
  schema_version: number;
  /** True for hand-made layout samples (tests); real exports set false. */
  sample: boolean;
  generated_at_utc: string;
  site: { default_locale: Locale };
  countries: CountrySummary[];
  latest_releases: ReleaseFeedItem[];
}

// ---- <country>.json ----

/** One mode of a country's palette (config/countries.yaml → CSS tokens). */
export interface ThemeColors {
  bg: string;
  surface: string;
  surface_muted: string;
  border: string;
  text: string;
  text_muted: string;
  link: string;
  header_bg: string;
  header_text: string;
  accent: string;
  band: string;
  up: string;
  down: string;
  series: string[];
}

export interface CountryTheme {
  light: ThemeColors;
  dark: ThemeColors;
}

export interface Points {
  periods: string[];
  values: (number | null)[];
}

export interface Expectation {
  source: string;
  median_pct: number;
  survey_date: string;
  n_respondents: number | null;
  other_sources: { source: string; median_pct: number; survey_date: string }[];
}

export interface Release {
  series_id: string;
  indicator: string;
  label: LocalizedText;
  reference_period: string;
  release_date: string | null;
  mom_pct: number;
  yoy_pct: number | null;
  ytd_pct: number | null;
  previous_mom_pct: number | null;
  expected: Expectation | null;
  surprise_pp: number | null;
  next_release: { reference_period: string; scheduled_utc: string } | null;
}

export interface Contribution {
  series_id: string;
  label: LocalizedText;
  contribution_pp: number;
  mom_pct: number;
  weight_pct?: number;
}

export interface LabeledPoints extends Points {
  series_id: string;
  label: LocalizedText;
}

export interface CountryData {
  schema_version: number;
  sample: boolean;
  generated_at_utc: string;
  country: {
    code: string;
    name: LocalizedText;
    default_locale: Locale;
    color_token: string;
    currency: string;
    theme: CountryTheme | null;
  };
  headline: Release;
  preview: Release | null;
  target: {
    target_pct: number;
    band_low_pct: number | null;
    band_high_pct: number | null;
    distance_pp: number;
    status: TargetStatus | null;
    months_outside_band: number | null;
    miss_threshold_months: number | null;
    missed: boolean | null;
  };
  summary: {
    period: string;
    mom_pct: number;
    top_driver: Contribution | null;
    all_groups_rose: boolean;
  };
  core: {
    available: boolean;
    members?: { series_id: string; label: LocalizedText; latest_pct: number }[];
    periods?: string[];
    mean_pct?: number[];
    min_pct?: number[];
    max_pct?: number[];
    latest_mean_pct?: number;
    latest_period?: string;
  };
  drivers: {
    period: string;
    groups: Contribution[];
    sum_pp: number;
    headline_mom_pct: number;
    top_up: Contribution[];
    top_down: Contribution[];
    twelve_month: {
      periods: string[];
      series: { series_id: string; label: LocalizedText; members?: LocalizedText[]; values_pp: (number | null)[] }[];
      headline_yoy_pct: (number | null)[];
      rounding_pp: (number | null)[];
    };
  };
  trend: {
    panels: Record<string, { series: LabeledPoints[] }>;
    diffusion: LabeledPoints | null;
  };
  momentum: {
    same_month: {
      period: string;
      value_pct: number;
      years: string[];
      past_pct: number[];
      median_pct: number | null;
      min_pct: number | null;
      max_pct: number | null;
    };
    saar:
      | { available: false; reason: string }
      | {
          available: true;
          method: string;
          periods: string[];
          saar3_pct: (number | null)[];
          saar6_pct: (number | null)[];
          yoy_pct: (number | null)[];
          revisable_from: string;
        };
  };
  base_effects: {
    dropping_out: { period: string; leaving_period: string; leaving_mom_pct: number | null }[];
    next_expected: Expectation | null;
    implied_next_yoy_pct: number | null;
  };
  policy: {
    policy_rate?: { label: LocalizedText; date: string; rate_pct: number; history: Points };
    real_ex_ante?: {
      rate_pct: number;
      expected_inflation_pct: number;
      survey_date: string;
      history: Points;
    };
    expectations_12m?: Points & { source: string };
    year_end_expectations: { year: number; median_pct: number; survey_date: string }[];
    fx?: { label: LocalizedText; date: string; value: number; yoy_pct: number | null; monthly_average: Points };
  };
  history: { headline_yoy: Points; core_mean_yoy: Points };
  validation: { passed: boolean; checked_at_utc: string; checks: { name: string; passed: boolean }[] };
}
