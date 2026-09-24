import React, { useEffect, useRef, useState } from 'react';
import { getAgentInfo } from '../constants/agents.js';

const ACCENT = '#00f59b'; // the agent's own line
const MEAN = '#737887'; // group-mean reference line (deliberately recessive)
const SURFACE = '#0c0e17'; // panel surface (surface-container-lowest), used for marker rings
const PLOT_H = 84;
const PAD = { top: 6, right: 8, bottom: 6, left: 4 };

// Shown only when the API has no per-round data yet — always badged as sample data
const SAMPLE_SERIES = [
  { id: 'performance_analyst', values: [0.5, 0.7, 0.83, 0.9] },
  { id: 'statistical_analyst', values: [0.2, 0.6, 0.75, 0.85] },
  { id: 'tactical_analyst', values: [-0.4, -0.1, 0.6, 0.8] },
  { id: 'context_analyst', values: [-0.6, -0.2, 0.5, 0.75] },
  { id: 'fan_analyst', values: [-0.85, -0.5, 0.1, 0.6] },
  { id: 'refereeing_analyst', values: [0.1, 0.2, 0.4, 0.5] },
];

const mean = (xs) => {
  const v = xs.filter((x) => typeof x === 'number');
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
};

/**
 * Normalises analytics into { kind, rounds, series: [{ id, values[] }] }.
 * Prefers scored stances; falls back to per-round message sentiment; then sample data.
 */
export function buildTrajectories(analytics) {
  const traj = analytics?.opinion_trajectories;
  if (traj && Object.keys(traj).length) {
    const rounds = [...new Set(Object.values(traj).flat().map((p) => p.round_num))].sort((a, b) => a - b);
    const series = Object.entries(traj).map(([id, pts]) => ({
      id,
      values: rounds.map((r) => pts.find((p) => p.round_num === r)?.stance_value ?? null),
    }));
    if (series.some((s) => s.values.some((v) => typeof v === 'number'))) return { kind: 'stance', rounds, series };
  }

  const sentiment = analytics?.sentiment;
  if (sentiment?.length) {
    const rounds = [...new Set(sentiment.map((s) => s.round_num))].sort((a, b) => a - b);
    const ids = [...new Set(sentiment.map((s) => s.sender_id))];
    const series = ids.map((id) => ({
      id,
      values: rounds.map((r) =>
        mean(sentiment.filter((s) => s.sender_id === id && s.round_num === r).map((s) => s.sentiment_score))
      ),
    }));
    return { kind: 'sentiment', rounds, series };
  }

  return { kind: 'sample', rounds: [0, 1, 2, 3], series: SAMPLE_SERIES };
}

const fmt = (v) => (typeof v === 'number' ? `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(2)}` : '—');
const lastValue = (values) => [...values].reverse().find((v) => typeof v === 'number') ?? null;
const firstValue = (values) => values.find((v) => typeof v === 'number') ?? null;

function useWidth() {
  const ref = useRef(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    if (!ref.current) return undefined;
    // Measure once up front: ResizeObserver doesn't deliver while the page is hidden
    setWidth(ref.current.getBoundingClientRect().width);
    const ro = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, width];
}

// Line path that breaks at missing rounds instead of interpolating through them
function linePath(values, x, y) {
  let d = '';
  let pen = false;
  values.forEach((v, i) => {
    if (typeof v !== 'number') {
      pen = false;
      return;
    }
    d += `${pen ? 'L' : 'M'} ${x(i).toFixed(1)},${y(v).toFixed(1)} `;
    pen = true;
  });
  return d.trim();
}

function Panel({ series, meanValues, rounds, hoverIdx, setHoverIdx, index }) {
  const [ref, width] = useWidth();
  const agent = getAgentInfo(series.id);
  const n = rounds.length;
  const plotW = Math.max(0, width - PAD.left - PAD.right);
  const x = (i) => PAD.left + (n > 1 ? (i / (n - 1)) * plotW : plotW / 2);
  const y = (v) => PAD.top + ((1 - v) / 2) * (PLOT_H - PAD.top - PAD.bottom);

  const start = firstValue(series.values);
  const end = lastValue(series.values);
  const shown = hoverIdx === null ? end : series.values[hoverIdx];
  const shift = start !== null && end !== null ? end - start : null;
  const endIdx = series.values.lastIndexOf(end);

  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const rel = (e.clientX - rect.left - PAD.left) / (plotW || 1);
    setHoverIdx(Math.max(0, Math.min(n - 1, Math.round(rel * (n - 1)))));
  };

  const d = linePath(series.values, x, y);
  const baseline = y(0);

  return (
    <div
      className="card-enter rounded-xl bg-surface-container-lowest border border-white/[0.05] p-3 flex flex-col gap-2 hover:border-white/[0.1] transition-colors"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className={`material-symbols-outlined text-[15px] ${agent.textColor}`}>{agent.icon}</span>
          <span className="font-headline text-[12px] font-semibold text-white truncate">{agent.name}</span>
        </div>
        <div className="flex flex-col items-end flex-shrink-0">
          <span className="font-mono text-[13px] font-bold text-white tabular-nums leading-none">{fmt(shown)}</span>
          <span className="font-mono text-[9px] text-on-surface-variant mt-1 tabular-nums">
            {hoverIdx === null ? (shift !== null ? `${fmt(shift)} since R${rounds[0]}` : 'no data') : `at R${rounds[hoverIdx]}`}
          </span>
        </div>
      </div>

      <div className="flex gap-1.5">
        {/* Y ticks — shared −1…+1 scale across every panel */}
        <div className="flex flex-col justify-between font-mono text-[8px] text-on-surface-variant/70 tabular-nums py-[2px]" style={{ height: PLOT_H }}>
          <span>+1</span>
          <span>0</span>
          <span>−1</span>
        </div>
        <div ref={ref} className="flex-1 min-w-0">
          {width > 0 && (
            <svg
              width={width}
              height={PLOT_H}
              className="block cursor-crosshair"
              onPointerMove={onMove}
              onPointerLeave={() => setHoverIdx(null)}
              role="img"
              aria-label={`${agent.name}: ${series.values.map((v, i) => `R${rounds[i]} ${fmt(v)}`).join(', ')}`}
            >
              <line x1={PAD.left} x2={width - PAD.right} y1={y(1)} y2={y(1)} stroke="rgba(255,255,255,0.04)" />
              <line x1={PAD.left} x2={width - PAD.right} y1={y(-1)} y2={y(-1)} stroke="rgba(255,255,255,0.04)" />
              <line x1={PAD.left} x2={width - PAD.right} y1={baseline} y2={baseline} stroke="rgba(255,255,255,0.12)" />

              {/* Wash between the line and zero */}
              {d && series.values.every((v) => typeof v === 'number') && (
                <path
                  d={`${d} L ${x(n - 1)},${baseline} L ${x(0)},${baseline} Z`}
                  fill={ACCENT}
                  fillOpacity="0.08"
                  className="fade-in-late"
                />
              )}

              <path d={linePath(meanValues, x, y)} fill="none" stroke={MEAN} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              <path
                d={d}
                fill="none"
                stroke={ACCENT}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                pathLength="1"
                className="path-draw"
                style={{ animationDelay: `${index * 60}ms` }}
              />

              {hoverIdx !== null && (
                <line x1={x(hoverIdx)} x2={x(hoverIdx)} y1={0} y2={PLOT_H} stroke="rgba(255,255,255,0.25)" />
              )}

              {/* End marker, or the hovered round's marker — 2px surface ring keeps it legible over lines */}
              {(hoverIdx === null ? endIdx >= 0 : typeof series.values[hoverIdx] === 'number') && (
                <circle
                  cx={x(hoverIdx === null ? endIdx : hoverIdx)}
                  cy={y(hoverIdx === null ? end : series.values[hoverIdx])}
                  r="4"
                  fill={ACCENT}
                  stroke={SURFACE}
                  strokeWidth="2"
                />
              )}
              {hoverIdx !== null && typeof meanValues[hoverIdx] === 'number' && (
                <circle cx={x(hoverIdx)} cy={y(meanValues[hoverIdx])} r="3" fill={MEAN} stroke={SURFACE} strokeWidth="2" />
              )}
            </svg>
          )}
          <div className="relative h-3 mt-1 font-mono text-[8px] text-on-surface-variant/70">
            {rounds.map((r, i) => (
              <span
                key={r}
                className={`absolute ${hoverIdx === i ? 'text-white' : ''}`}
                style={{
                  left: width ? x(i) : `${(i / Math.max(1, n - 1)) * 100}%`,
                  transform: i === 0 ? 'none' : i === n - 1 ? 'translateX(-100%)' : 'translateX(-50%)',
                }}
              >
                R{r}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function OpinionTrajectories({ analytics }) {
  const [view, setView] = useState('chart');
  const [hoverIdx, setHoverIdx] = useState(null);
  const { kind, rounds, series } = buildTrajectories(analytics);

  const meanValues = rounds.map((_, i) => mean(series.map((s) => s.values[i])));
  const ordered = [...series].sort((a, b) => (lastValue(b.values) ?? -2) - (lastValue(a.values) ?? -2));

  // Headline: did the room converge? Compare the spread of stances at the first and last round.
  const spreadAt = (i) => {
    const v = series.map((s) => s.values[i]).filter((x) => typeof x === 'number');
    return v.length > 1 ? Math.max(...v) - Math.min(...v) : null;
  };
  const spreadStart = spreadAt(0);
  const spreadEnd = spreadAt(rounds.length - 1);

  const subtitle =
    kind === 'sentiment'
      ? 'Mean message sentiment per round (−1 negative → +1 positive)'
      : 'Deliberation stance index (−1 opposed → +1 masterclass)';

  return (
    <div className="rounded-2xl bg-[#0d0f18]/90 border border-white/[0.08] p-4 shadow-xl flex flex-col space-y-3">
      <div className="flex items-start justify-between flex-wrap gap-2">
        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-headline text-[14px] font-bold text-white">Agent Opinion Trajectories</span>
            {kind !== 'stance' && (
              <span className="px-1.5 py-0.5 rounded bg-surface-container-high font-mono text-[9px] text-on-surface-variant uppercase tracking-wider">
                {kind === 'sentiment' ? 'Sentiment proxy — no stance scores yet' : 'Sample data'}
              </span>
            )}
          </div>
          <span className="font-mono text-[10px] text-on-surface-variant">{subtitle}</span>
        </div>
        <div className="flex items-center gap-1 bg-surface-container-low p-0.5 rounded-lg border border-white/[0.06]" role="tablist">
          {['chart', 'table'].map((v) => (
            <button
              key={v}
              role="tab"
              aria-selected={view === v}
              onClick={() => setView(v)}
              className={`px-2.5 py-1 rounded-md font-mono text-[10px] uppercase transition-colors active:scale-95 ${
                view === v ? 'bg-surface-container-highest text-white' : 'text-on-surface-variant hover:text-white'
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {/* Headline + legend */}
      <div className="flex items-center justify-between flex-wrap gap-x-4 gap-y-1.5">
        {spreadStart !== null && spreadEnd !== null && (
          <span className="font-sans text-[12px] text-on-surface-variant">
            Spread between agents{' '}
            <span className="font-mono text-white tabular-nums">{spreadStart.toFixed(2)}</span>
            {' → '}
            <span className="font-mono text-white tabular-nums">{spreadEnd.toFixed(2)}</span>
            <span className="text-on-surface-variant">
              {' '}
              ({spreadEnd < spreadStart ? 'converging' : spreadEnd > spreadStart ? 'diverging' : 'flat'})
            </span>
          </span>
        )}
        <div className="flex items-center gap-3 font-mono text-[10px] text-on-surface-variant">
          <span className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 rounded-full" style={{ background: ACCENT }}></span>
            Agent
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 rounded-full" style={{ background: MEAN }}></span>
            Group mean
          </span>
        </div>
      </div>

      {view === 'chart' ? (
        <div key="chart" className="fade-swap grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {ordered.map((s, i) => (
            <Panel
              key={s.id}
              index={i}
              series={s}
              meanValues={meanValues}
              rounds={rounds}
              hoverIdx={hoverIdx}
              setHoverIdx={setHoverIdx}
            />
          ))}
        </div>
      ) : (
        <div key="table" className="fade-swap overflow-x-auto rounded-xl border border-white/[0.05]">
          <table className="w-full font-mono text-[11px] tabular-nums">
            <thead>
              <tr className="text-on-surface-variant text-left">
                <th className="font-medium px-3 py-2">Agent</th>
                {rounds.map((r) => (
                  <th key={r} className="font-medium px-3 py-2 text-right">
                    R{r}
                  </th>
                ))}
                <th className="font-medium px-3 py-2 text-right">Shift</th>
              </tr>
            </thead>
            <tbody>
              {ordered.map((s) => {
                const a = firstValue(s.values);
                const b = lastValue(s.values);
                return (
                  <tr key={s.id} className="border-t border-white/[0.05] text-on-surface hover:bg-white/[0.02]">
                    <td className="px-3 py-2 font-sans text-white whitespace-nowrap">{getAgentInfo(s.id).name}</td>
                    {s.values.map((v, i) => (
                      <td key={i} className="px-3 py-2 text-right">
                        {fmt(v)}
                      </td>
                    ))}
                    <td className="px-3 py-2 text-right text-white">{a !== null && b !== null ? fmt(b - a) : '—'}</td>
                  </tr>
                );
              })}
              <tr className="border-t border-white/[0.1] text-on-surface-variant">
                <td className="px-3 py-2 font-sans">Group mean</td>
                {meanValues.map((v, i) => (
                  <td key={i} className="px-3 py-2 text-right">
                    {fmt(v)}
                  </td>
                ))}
                <td className="px-3 py-2"></td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
