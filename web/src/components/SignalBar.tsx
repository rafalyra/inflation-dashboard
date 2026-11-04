import type { CSSProperties } from 'react';

interface Props {
  value: number;
  /** The largest absolute value in the table, so bar lengths compare within it. */
  max: number;
  /** Already-formatted value, e.g. "+0,32 p.p.". */
  label: string;
}

/**
 * A small bar whose length shows how much something moved: red ▲ for increases, green ▼ for
 * decreases (for inflation a rise is bad news). The arrow and the signed number carry the
 * meaning too, so color is never the only signal.
 */
export function SignalBar({ value, max, label }: Props) {
  const up = value > 0;
  const flat = Math.abs(value) < 0.005;
  const width = max > 0 ? Math.max(4, (Math.abs(value) / max) * 100) : 0;
  return (
    <span className="signal">
      <span className="signal__track" aria-hidden="true">
        {!flat && (
          <span
            className={up ? 'signal__bar signal__bar--up' : 'signal__bar signal__bar--down'}
            style={{ width: `${width}%` } as CSSProperties}
          />
        )}
      </span>
      <span className="signal__arrow" aria-hidden="true">
        {flat ? '●' : up ? '▲' : '▼'}
      </span>
      <span className="num">{label}</span>
    </span>
  );
}

/** Largest absolute value, for sizing a table's bars. */
export function maxAbs(values: number[]): number {
  return values.reduce((m, v) => Math.max(m, Math.abs(v)), 0);
}
