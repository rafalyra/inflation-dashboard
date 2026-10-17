import type { Locale } from './types';

// All numbers go through Intl so the decimal separator follows the UI language
// (0.82 in English, 0,82 in Portuguese). Percent and pp values use 2 decimals (SPEC §5.6).

function fixed2(locale: Locale, signed: boolean): Intl.NumberFormat {
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    signDisplay: signed ? 'exceptZero' : 'auto',
  });
}

/** A value already expressed in percent, e.g. 4.47 → "4.47%". */
export function formatPct(value: number, locale: Locale, signed = false): string {
  return `${fixed2(locale, signed).format(value)}%`;
}

/** The bare number for a percentage-point value; the unit label comes from i18n. */
export function formatPpNumber(value: number, locale: Locale, signed = true): string {
  return fixed2(locale, signed).format(value);
}

/** "2026-09" → "Sep 2026" / "set. de 2026". */
export function formatPeriod(period: string, locale: Locale): string {
  const [year, month] = period.split('-').map(Number);
  const date = new Date(Date.UTC(year ?? 1970, (month ?? 1) - 1, 1));
  return new Intl.DateTimeFormat(locale, { month: 'short', year: 'numeric', timeZone: 'UTC' }).format(date);
}

/** "2026-10-09" → "Oct 9, 2026" / "9 de out. de 2026". */
export function formatDate(isoDate: string, locale: Locale): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeZone: 'UTC' }).format(date);
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
