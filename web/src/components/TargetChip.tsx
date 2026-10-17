import { useTranslation } from 'react-i18next';
import type { TargetStatus } from '../lib/types';

// The arrow shape and the text carry the meaning; color only reinforces it.
const ICON: Record<TargetStatus, string> = { above: '▲', inside: '●', below: '▼' };

export function TargetChip({ status }: { status: TargetStatus }) {
  const { t } = useTranslation();
  return (
    <span className={`chip chip--${status}`}>
      <span aria-hidden="true">{ICON[status]}</span>
      {t(`target.${status}`)}
    </span>
  );
}
