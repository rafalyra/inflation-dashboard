import type { Locale } from './types';

// All numbers go through Intl so the decimal separator follows the UI language
// (0.82 in English, 0,82 in Portuguese). Percent and pp values use 2 decimals (SPEC §5.6).

function fixed(locale: Locale, signed: boolean, digits = 2): Intl.NumberFormat {
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    signDisplay: signed ? 'exceptZero' : 'auto',
  });
}

/** A value already expressed in percent, e.g. 4.47 → "4.47%". */
export function formatPct(value: number, locale: Locale, signed = false): string {
  return `${fixed(locale, signed).format(value)}%`;
}

/** The bare number for a percentage-point value; the unit label comes from i18n. */
export function formatPpNumber(value: number, locale: Locale, signed = true): string {
  return fixed(locale, signed).format(value);
}

/** A plain number with a fixed number of decimals (e.g. an exchange rate). */
export function formatNumber(value: number, locale: Locale, digits = 2): string {
  return fixed(locale, false, digits).format(value);
}

/** "2026-09" → "Sep 2026" / "set. de 2026". */
export function formatPeriod(period: string, locale: Locale, month: 'short' | 'long' = 'short'): string {
  const [year, m] = period.split('-').map(Number);
  const date = new Date(Date.UTC(year ?? 1970, (m ?? 1) - 1, 1));
  return new Intl.DateTimeFormat(locale, { month, year: 'numeric', timeZone: 'UTC' }).format(date);
}

/** "2026-09" → "September" / "setembro". */
export function formatMonthName(period: string, locale: Locale): string {
  const [year, m] = period.split('-').map(Number);
  const date = new Date(Date.UTC(year ?? 1970, (m ?? 1) - 1, 1));
  return new Intl.DateTimeFormat(locale, { month: 'long', timeZone: 'UTC' }).format(date);
}

/** "2026-10-09" → "Oct 9, 2026" / "9 de out. de 2026". */
export function formatDate(isoDate: string, locale: Locale): string {
  const date = new Date(`${isoDate.slice(0, 10)}T00:00:00Z`);
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeZone: 'UTC' }).format(date);
}

/** A release time in the viewer's own time zone, with the zone named so it's unambiguous. */
export function formatDateTime(isoUtc: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(new Date(isoUtc));
}

/** Time until a future instant as "in 3 days" / "em 3 dias"; null once it has passed. */
export function formatCountdown(targetUtc: string, now: Date, locale: Locale): string | null {
  const diffMs = new Date(targetUtc).getTime() - now.getTime();
  if (diffMs <= 0) return null;
  const minutes = Math.round(diffMs / 60_000);
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
  if (minutes < 60) return rtf.format(minutes, 'minute');
  const hours = Math.round(minutes / 60);
  if (hours < 48) return rtf.format(hours, 'hour');
  return rtf.format(Math.round(hours / 24), 'day');
}
