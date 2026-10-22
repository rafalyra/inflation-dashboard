import type { ReactNode } from 'react';

interface Props {
  label: string;
  value: ReactNode;
  note?: ReactNode;
  hero?: boolean;
}

export function StatTile({ label, value, note, hero }: Props) {
  return (
    <div className={hero ? 'tile tile--hero' : 'tile'}>
      <div className="tile__label">{label}</div>
      <div className="tile__value">{value}</div>
      {note && <div className="tile__note muted">{note}</div>}
    </div>
  );
}

/** ▲ / ▼ with words, so direction never relies on color. */
export function Direction({ value, up, down, flat }: { value: number; up: string; down: string; flat: string }) {
  if (Math.abs(value) < 0.005) return <span className="dir dir--flat">● {flat}</span>;
  return value > 0 ? (
    <span className="dir dir--up">
      <span aria-hidden="true">▲</span> {up}
    </span>
  ) : (
    <span className="dir dir--down">
      <span aria-hidden="true">▼</span> {down}
    </span>
  );
}
