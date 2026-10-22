import type { EChartsCoreOption } from 'echarts/core';
import { type ReactNode, useId, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Chart } from './Chart';

export interface TableData {
  columns: string[];
  rows: (string | number)[][];
}

interface Props {
  title: string;
  subtitle?: string;
  option: EChartsCoreOption;
  table: TableData;
  height?: number;
  footnote?: ReactNode;
}

/**
 * A chart with a title and a "Show table" toggle. The table is the accessible view of
 * the same numbers (and the fallback where a series color is low-contrast).
 */
export function ChartCard({ title, subtitle, option, table, height, footnote }: Props) {
  const { t } = useTranslation();
  const [showTable, setShowTable] = useState(false);
  const id = useId();

  return (
    <figure className="chart-card" aria-labelledby={`${id}-title`}>
      <div className="chart-card__head">
        <div>
          <h3 id={`${id}-title`}>{title}</h3>
          {subtitle && <p className="muted chart-card__subtitle">{subtitle}</p>}
        </div>
        <button
          type="button"
          className="button button--small"
          aria-expanded={showTable}
          aria-controls={`${id}-table`}
          onClick={() => setShowTable((v) => !v)}
        >
          {showTable ? t('chart.showChart') : t('chart.showTable')}
        </button>
      </div>
      {showTable ? (
        <div className="table-scroll" id={`${id}-table`}>
          <table className="data-table">
            <thead>
              <tr>
                {table.columns.map((c) => (
                  <th key={c} scope="col">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) =>
                    j === 0 ? (
                      <th key={j} scope="row">
                        {cell}
                      </th>
                    ) : (
                      <td key={j} className="num">
                        {cell}
                      </td>
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Chart option={option} label={title} height={height} />
      )}
      {footnote && <figcaption className="muted chart-card__note">{footnote}</figcaption>}
    </figure>
  );
}
