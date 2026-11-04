import { createContext, useContext } from 'react';

// One time range for every time chart on a tab (dataviz: filters sit in one row above the
// charts and scope all of them). Each chart's own slider can still adjust it afterwards.

export const RANGES = ['1y', '3y', '5y', '10y', 'all'] as const;
export type Range = (typeof RANGES)[number];

export const RANGE_MONTHS: Record<Range, number | null> = { '1y': 12, '3y': 36, '5y': 60, '10y': 120, all: null };

export const ZoomContext = createContext<Range>('all');

export function useZoomRange(): Range {
  return useContext(ZoomContext);
}

/** Index of the first category to show for a range, given how many months the chart has. */
export function rangeStartIndex(range: Range, length: number): number {
  const months = RANGE_MONTHS[range];
  return months === null ? 0 : Math.max(0, length - months);
}
