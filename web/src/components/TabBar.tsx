import { useLayoutEffect, useRef, useState } from 'react';

interface Props<T extends string> {
  tabs: readonly T[];
  active: T;
  label: string;
  name: (id: T) => string;
  onSelect: (id: T) => void;
}

/**
 * Tabs in one rounded bar. A soft highlight slides (and fades) to whichever tab the cursor
 * is over, and settles back on the current tab when the cursor leaves.
 */
export function TabBar<T extends string>({ tabs, active, label, name, onSelect }: Props<T>) {
  const buttons = useRef(new Map<T, HTMLButtonElement>());
  const [hovered, setHovered] = useState<T | null>(null);
  const [box, setBox] = useState<{ left: number; top: number; width: number; height: number } | null>(null);
  const target = hovered ?? active;

  useLayoutEffect(() => {
    const place = () => {
      const el = buttons.current.get(target);
      if (el) setBox({ left: el.offsetLeft, top: el.offsetTop, width: el.offsetWidth, height: el.offsetHeight });
    };
    place();
    window.addEventListener('resize', place);
    return () => window.removeEventListener('resize', place);
  }, [target, tabs]);

  return (
    <nav className="tabbar" aria-label={label} onMouseLeave={() => setHovered(null)}>
      {box && (
        <span
          className={hovered && hovered !== active ? 'tabbar__glow tabbar__glow--hover' : 'tabbar__glow'}
          style={{ transform: `translate(${box.left}px, ${box.top}px)`, width: box.width, height: box.height }}
          aria-hidden="true"
        />
      )}
      {tabs.map((id) => (
        <button
          key={id}
          ref={(el) => {
            if (el) buttons.current.set(id, el);
          }}
          type="button"
          className="tabbar__tab"
          aria-current={id === active ? 'page' : undefined}
          onMouseEnter={() => setHovered(id)}
          onFocus={() => setHovered(id)}
          onBlur={() => setHovered(null)}
          onClick={() => onSelect(id)}
        >
          {name(id)}
        </button>
      ))}
    </nav>
  );
}
