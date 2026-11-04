import { BarChart, LineChart, ScatterChart, TreemapChart } from 'echarts/charts';
import {
  AriaComponent,
  DataZoomInsideComponent,
  DataZoomSliderComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components';
import * as echarts from 'echarts/core';
import type { EChartsCoreOption } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { useEffect, useRef } from 'react';
import { rangeStartIndex, useZoomRange } from '../lib/zoom';

echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  TreemapChart,
  AriaComponent,
  DataZoomInsideComponent,
  DataZoomSliderComponent,
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

function categoryCount(option: EChartsCoreOption): number {
  const x = (option as { xAxis?: { data?: unknown[] } }).xAxis;
  return Array.isArray(x?.data) ? x.data.length : 0;
}

/** A thin wrapper: create the chart once, update its option, resize with its container,
 *  and follow the tab's time range when the chart is zoomable. */
export function Chart({ option, label, height = 300 }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const range = useZoomRange();

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

  useEffect(() => {
    const c = chart.current;
    if (!c) return;
    c.setOption(option, { notMerge: true });
    if ((option as { dataZoom?: unknown }).dataZoom) {
      const n = categoryCount(option);
      c.dispatchAction({ type: 'dataZoom', startValue: rangeStartIndex(range, n), endValue: Math.max(0, n - 1) });
    }
  }, [option, range]);

  return <div ref={ref} role="img" aria-label={label} style={{ width: '100%', height }} />;
}
