import { useEffect, useState } from 'react';
import type { OverviewData } from './types';

// Phase 0 reads the layout sample. Phase 1 switches this to the pipeline export in data/.
const OVERVIEW_URL = `${import.meta.env.BASE_URL}sample/overview.json`;

export type LoadState<T> =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: T };

export function useOverview(): LoadState<OverviewData> {
  const [state, setState] = useState<LoadState<OverviewData>>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    fetch(OVERVIEW_URL)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<OverviewData>;
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
  }, []);

  return state;
}
