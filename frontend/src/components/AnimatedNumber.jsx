import React, { useEffect, useRef, useState } from 'react';

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

// Tweens from the previously shown value to `value` with an ease-out curve.
export default function AnimatedNumber({ value, decimals = 0, duration = 700, className = '' }) {
  const target = Number(value) || 0;
  const [display, setDisplay] = useState(prefersReducedMotion() ? target : 0);
  const fromRef = useRef(display);

  useEffect(() => {
    if (prefersReducedMotion()) {
      setDisplay(target);
      fromRef.current = target;
      return undefined;
    }
    const from = fromRef.current;
    const start = performance.now();
    let frame;
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const next = from + (target - from) * eased;
      fromRef.current = next;
      setDisplay(next);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  return <span className={`tabular-nums ${className}`}>{display.toFixed(decimals)}</span>;
}
