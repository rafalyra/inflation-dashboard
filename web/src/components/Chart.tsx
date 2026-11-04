import { BarChart, LineChart, ScatterChart, TreemapChart } from 'echarts/charts';
import {
  AriaComponent,
  DataZoomInsideComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components';
import * as echarts from 'echarts/core';
import type { EChartsCoreOption } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { type PointerEvent, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocale } from '../i18n';
import { formatPeriod } from '../lib/format';
import { rangeStartIndex, useZoomRange } from '../lib/zoom';

echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  TreemapChart,
  AriaComponent,
  DataZoomInsideComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
  CanvasRenderer,
]);

interface Props {
  option: EChartsCoreOption;
  /** Accessible summary of what the chart shows. */
  label: string;
  height?: number;
}

// A drag shorter than this (in pixels) is a click, left to the tooltip.
const MIN_DRAG_PX = 8;

function categories(option: EChartsCoreOption): unknown[] {
  const x = (option as { xAxis?: { data?: unknown[] } }).xAxis;
  return Array.isArray(x?.data) ? x.data : [];
}

function categoryCount(option: EChartsCoreOption): number {
  return categories(option).length;
}

/**
 * A thin wrapper around ECharts: create the chart once, update its option, resize with its
 * container. Time charts (options with a dataZoom) can be zoomed by pressing, dragging across
 * a period and releasing; "Reset zoom" or a double-click returns to the tab's period.
 */
export function Chart({ option, label, height = 300 }: Props) {
  const { t } = useTranslation();
  const locale = useLocale();
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const range = useZoomRange();
  const zoomable = Boolean((option as { dataZoom?: unknown }).dataZoom);
  const [drag, setDrag] = useState<{ start: number; end: number } | null>(null);
  // The zoomed window (category indices), shown under the chart with a reset button.
  const [zoomed, setZoomed] = useState<{ start: number; end: number } | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    chart.current = echarts.init(ref.current, undefined, { renderer: 'canvas' });
    const observer = new ResizeObserver(() => chart.current?.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.current?.dispose();
      chart.current = null;
    };
  }, []);

  const applyRange = () => {
    const c = chart.current;
    if (!c || !zoomable) return;
    const n = categoryCount(option);
    c.dispatchAction({ type: 'dataZoom', startValue: rangeStartIndex(range, n), endValue: Math.max(0, n - 1) });
    setZoomed(null);
  };

  useEffect(() => {
    chart.current?.setOption(option, { notMerge: true });
    applyRange();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [option, range]);

  // Pixel x (relative to the chart) → category index, or null outside the plot area.
  const indexAt = (x: number): number | null => {
    const c = chart.current;
    if (!c) return null;
    const value = c.convertFromPixel({ xAxisIndex: 0 }, x) as number | number[] | undefined;
    const idx = Array.isArray(value) ? value[0] : value;
    return typeof idx === 'number' && Number.isFinite(idx) ? Math.round(idx) : null;
  };

  const localX = (e: PointerEvent<HTMLDivElement>) => e.clientX - e.currentTarget.getBoundingClientRect().left;

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    // Mouse and pen only: a finger drag keeps scrolling the page.
    if (!zoomable || e.pointerType === 'touch' || e.button !== 0) return;
    const x = localX(e);
    if (indexAt(x) === null) return;
    setDrag({ start: x, end: x });
  };
  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (drag) setDrag({ ...drag, end: localX(e) });
  };
  const onPointerUp = () => {
    if (!drag) return;
    const { start, end } = drag;
    setDrag(null);
    if (Math.abs(end - start) < MIN_DRAG_PX) return;
    const a = indexAt(Math.min(start, end));
    const b = indexAt(Math.max(start, end));
    if (a === null || b === null || b <= a) return;
    chart.current?.dispatchAction({ type: 'dataZoom', startValue: a, endValue: b });
    setZoomed({ start: a, end: b });
  };

  return (
    <div
      className={zoomable ? 'chart chart--zoomable' : 'chart'}
    >
      <div
        className="chart__plot"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={() => setDrag(null)}
        onDoubleClick={zoomable ? applyRange : undefined}
      >
        <div ref={ref} role="img" aria-label={label} style={{ width: '100%', height }} />
      {drag && Math.abs(drag.end - drag.start) >= MIN_DRAG_PX && (
        <div
          className="chart__selection"
          style={{ left: Math.min(drag.start, drag.end), width: Math.abs(drag.end - drag.start) }}
          aria-hidden="true"
        />
      )}
      </div>
      {zoomed && (
        <div className="chart__zoombar">
          <span className="muted">
            {t('chart.zoomedTo', {
              from: formatPeriod(String(categories(option)[zoomed.start] ?? ''), locale),
              to: formatPeriod(String(categories(option)[zoomed.end] ?? ''), locale),
            })}
          </span>
          <button type="button" className="button button--small" onClick={applyRange}>
            {t('chart.resetZoom')}
          </button>
        </div>
      )}
    </div>
  );
}
