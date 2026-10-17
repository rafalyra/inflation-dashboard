// Shape of the JSON the pipeline exports (src/inflation/export.py). The web app only
// displays these values; every metric is computed in Python.

export type Locale = 'en' | 'pt-BR';

export type LocalizedText = Record<Locale, string>;

export type TargetStatus = 'inside' | 'above' | 'below';

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
  target_status: TargetStatus;
  last_release_date: string; // YYYY-MM-DD
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
  /** True for the hand-made layout sample; real exports set false. */
  sample: boolean;
  generated_at_utc: string;
  site: { default_locale: Locale };
  countries: CountrySummary[];
  latest_releases: ReleaseFeedItem[];
}
