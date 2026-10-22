import { useEffect, useState } from 'react';
import type { CountryData, OverviewData } from './types';

// The pipeline writes these into public/data/ (gitignored) before each build.
const DATA_URL = `${import.meta.env.BASE_URL}data/`;

export type LoadState<T> =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: T };

function useJson<T>(file: string): LoadState<T> {
  const [state, setState] = useState<LoadState<T>>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });
    fetch(`${DATA_URL}${file}`)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<T>;
      })
      .then((data) => {
        if (!cancelled) setState({ status: 'ready', data });
      })
      .catch(() => {
        if (!cancelled) setState({ status: 'error' });
      });
    return () => {
      cancelled = true;
    };
  }, [file]);

  return state;
}

export function useOverview(): LoadState<OverviewData> {
  return useJson<OverviewData>('overview.json');
}

export function useCountry(code: string): LoadState<CountryData> {
  return useJson<CountryData>(`${code}.json`);
}
