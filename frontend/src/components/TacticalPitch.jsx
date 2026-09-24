import React, { useId, useMemo, useState } from 'react';
import { AGENTS, PITCH_POSITIONS, DEFAULT_LANES } from '../constants/agents.js';

const W = 680;
const H = 440;
const LINE = 'rgba(225,225,239,0.16)';

const DEFAULT_PRESS_ZONES = [
  { x: 572, y: 150, rx: 74, ry: 50, color: '#00f59b', label: 'COUNTER-PRESS' },
  { x: 430, y: 318, rx: 62, ry: 44, color: '#00d2ff', label: 'TRAP ZONE' },
];

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

// Quadratic curve between two points, bowed perpendicular to the lane so overlapping lanes stay readable.
function lanePath(a, b, bow) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const cx = mx + (-dy / len) * len * bow;
  const cy = my + (dx / len) * len * bow;
  return `M ${a.x},${a.y} Q ${cx},${cy} ${b.x},${b.y}`;
}

function PitchMarkings() {
  const stripes = Array.from({ length: 12 }, (_, i) => i);
  return (
    <g>
      {stripes.map((i) => (
        <rect
          key={i}
          x={20 + (i * 640) / 12}
          y={20}
          width={640 / 12}
          height={400}
          fill="#00f59b"
          opacity={i % 2 === 0 ? 0.035 : 0.015}
        />
      ))}
      <g fill="none" stroke={LINE} strokeWidth="1.5">
        <rect x="20" y="20" width="640" height="400" rx="2" />
        <line x1="340" y1="20" x2="340" y2="420" />
        <circle cx="340" cy="220" r="48" />
        {/* Penalty & goal areas */}
        <rect x="20" y="101" width="100" height="238" />
        <rect x="560" y="101" width="100" height="238" />
        <rect x="20" y="166" width="34" height="108" />
        <rect x="626" y="166" width="34" height="108" />
        <path d="M 120,188 A 48,48 0 0 1 120,252" />
        <path d="M 560,188 A 48,48 0 0 0 560,252" />
        {/* Goals */}
        <rect x="12" y="198" width="8" height="44" stroke="rgba(225,225,239,0.28)" />
        <rect x="660" y="198" width="8" height="44" stroke="rgba(225,225,239,0.28)" />
        {/* Corner arcs */}
        <path d="M 20,30 A 10,10 0 0 0 30,20" />
        <path d="M 650,20 A 10,10 0 0 0 660,30" />
        <path d="M 20,410 A 10,10 0 0 1 30,420" />
        <path d="M 650,420 A 10,10 0 0 1 660,410" />
      </g>
      <g fill={LINE}>
        <circle cx="340" cy="220" r="2.5" />
        <circle cx="87" cy="220" r="2" />
        <circle cx="593" cy="220" r="2" />
      </g>
      {/* Half-space guides */}
      <g stroke="rgba(0,210,255,0.08)" strokeDasharray="2 6" strokeWidth="1">
        <line x1="20" y1="154" x2="660" y2="154" />
        <line x1="20" y1="286" x2="660" y2="286" />
      </g>
    </g>
  );
}

/**
 * Interactive tactical pitch showing the six specialist agents as players,
 * animated passing lanes between them and pulsing pressing zones.
 *
 * Props:
 *  - activeAgentIds: agents currently "on the ball" (speaking this round) — get a live halo
 *  - highlightId / onHighlight: controlled hover state, so sibling UI (agent cards) can sync
 *  - focusId: agent to mark with an orbit ring (e.g. top influencer)
 *  - lanes: [fromId, toId, weight] tuples
 *  - stances: { [agentId]: number } shown in the hover tooltip
 */
export default function TacticalPitch({
  activeAgentIds = [],
  highlightId,
  onHighlight,
  focusId = null,
  lanes = DEFAULT_LANES,
  pressZones = DEFAULT_PRESS_ZONES,
  stances = {},
}) {
  const uid = useId().replace(/:/g, '');
  const [internalHighlight, setInternalHighlight] = useState(null);
  const hl = onHighlight ? highlightId ?? null : internalHighlight;
  const setHl = onHighlight || setInternalHighlight;
  const animate = useMemo(() => !prefersReducedMotion(), []);

  const nodes = AGENTS.filter((a) => PITCH_POSITIONS[a.id]).map((a) => ({ ...a, ...PITCH_POSITIONS[a.id] }));
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const active = new Set(activeAgentIds);

  const laneData = lanes
    .filter(([from, to]) => byId[from] && byId[to])
    .map(([from, to, weight], i) => ({
      id: `${uid}-lane-${i}`,
      from,
      to,
      weight,
      d: lanePath(byId[from], byId[to], i % 2 === 0 ? 0.12 : -0.12),
      color: byId[from].strokeColor,
    }));

  const connected = new Set();
  if (hl) {
    laneData.forEach((l) => {
      if (l.from === hl || l.to === hl) {
        connected.add(l.from);
        connected.add(l.to);
      }
    });
  }

  // The ball travels along the strongest lanes
  const ballLanes = [...laneData].sort((a, b) => b.weight - a.weight).slice(0, 3);
  const hovered = hl ? byId[hl] : null;

  return (
    <div className="relative w-full max-w-3xl mx-auto select-none">
      <div className="relative w-full rounded-xl overflow-hidden bg-[#06070a] border border-white/[0.04]">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full h-auto block"
          role="img"
          aria-label="Tactical pitch showing specialist agents, passing lanes and pressing zones"
          onPointerLeave={(e) => e.pointerType === 'mouse' && setHl(null)}
          onClick={() => setHl(null)}
        >
          <defs>
            {pressZones.map((z, i) => (
              <radialGradient key={i} id={`${uid}-press-${i}`}>
                <stop offset="0%" stopColor={z.color} stopOpacity="0.32" />
                <stop offset="70%" stopColor={z.color} stopOpacity="0.08" />
                <stop offset="100%" stopColor={z.color} stopOpacity="0" />
              </radialGradient>
            ))}
            <filter id={`${uid}-glow`} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <radialGradient id={`${uid}-vignette`} cx="50%" cy="50%" r="75%">
              <stop offset="60%" stopColor="#06070a" stopOpacity="0" />
              <stop offset="100%" stopColor="#06070a" stopOpacity="0.85" />
            </radialGradient>
          </defs>

          <PitchMarkings />

          {/* Pressing zones */}
          {pressZones.map((z, i) => (
            <g key={i} className={hl ? 'opacity-40 transition-opacity duration-300' : 'transition-opacity duration-300'}>
              <ellipse
                className="pitch-press"
                style={{ animationDelay: `${i * 0.9}s` }}
                cx={z.x}
                cy={z.y}
                rx={z.rx}
                ry={z.ry}
                fill={`url(#${uid}-press-${i})`}
              />
              <ellipse
                cx={z.x}
                cy={z.y}
                rx={z.rx * 0.82}
                ry={z.ry * 0.82}
                fill="none"
                stroke={z.color}
                strokeOpacity="0.35"
                strokeDasharray="3 5"
                className="pitch-dash-drift"
              />
              <text
                x={z.x}
                y={z.y - z.ry - 6}
                textAnchor="middle"
                fill={z.color}
                fillOpacity="0.7"
                fontFamily="JetBrains Mono, monospace"
                fontSize="9"
                letterSpacing="1.2"
              >
                {z.label}
              </text>
            </g>
          ))}

          {/* Passing lanes */}
          {laneData.map((l) => {
            const involved = hl && (l.from === hl || l.to === hl);
            const dimmed = hl && !involved;
            const width = 1 + l.weight * 2.4 + (involved ? 1.2 : 0);
            return (
              <g key={l.id} className="transition-opacity duration-300" style={{ opacity: dimmed ? 0.1 : 1 }}>
                <path id={l.id} d={l.d} fill="none" stroke={l.color} strokeOpacity={involved ? 0.45 : 0.18} strokeWidth={width} strokeLinecap="round" />
                <path
                  d={l.d}
                  fill="none"
                  stroke={l.color}
                  strokeOpacity={involved ? 1 : 0.7}
                  strokeWidth={Math.max(1.2, width - 0.8)}
                  strokeLinecap="round"
                  strokeDasharray="4 12"
                  className="pitch-lane-flow"
                  style={{ animationDuration: `${2.6 - l.weight * 1.4}s` }}
                  filter={involved ? `url(#${uid}-glow)` : undefined}
                />
              </g>
            );
          })}

          {/* Ball moving along the strongest lanes */}
          {animate &&
            !hl &&
            ballLanes.map((l, i) => (
              <circle key={l.id} r="3.5" fill="#ffffff" filter={`url(#${uid}-glow)`} opacity="0.9">
                <animateMotion dur={`${2.4 + i * 0.7}s`} repeatCount="indefinite" begin={`${i * 0.8}s`}>
                  <mpath href={`#${l.id}`} />
                </animateMotion>
              </circle>
            ))}

          <rect x="0" y="0" width={W} height={H} fill={`url(#${uid}-vignette)`} pointerEvents="none" />

          {/* Agent nodes */}
          {nodes.map((n) => {
            const isHl = hl === n.id;
            const isLinked = connected.has(n.id);
            const dimmed = hl && !isHl && !isLinked;
            const speaking = active.has(n.id);
            return (
              <g
                key={n.id}
                transform={`translate(${n.x},${n.y})`}
                role="button"
                tabIndex={0}
                aria-label={`${n.name} — ${n.role}`}
                className="cursor-pointer outline-none"
                style={{ opacity: dimmed ? 0.35 : 1, transition: 'opacity 250ms ease' }}
                onPointerEnter={(e) => e.pointerType === 'mouse' && setHl(n.id)}
                onFocus={() => setHl(n.id)}
                onBlur={() => setHl(null)}
                onClick={(e) => {
                  e.stopPropagation();
                  setHl(n.id);
                }}
              >
                <circle r="28" fill="transparent" />
                {speaking && <circle r="17" fill="none" stroke={n.strokeColor} strokeWidth="2" className="pitch-node-ping" />}
                {focusId === n.id && (
                  <circle r="24" fill="none" stroke={n.strokeColor} strokeOpacity="0.8" strokeWidth="1.2" strokeDasharray="2 4" className="pitch-orbit" />
                )}
                <g className={`pitch-node ${isHl ? 'is-active' : ''}`}>
                  <circle r="19" fill={n.strokeColor} opacity={isHl ? 0.22 : 0} className="transition-opacity duration-200" />
                  <circle
                    r="15"
                    fill="#11131c"
                    stroke={n.strokeColor}
                    strokeWidth={isHl ? 2.5 : 1.8}
                    filter={isHl || speaking ? `url(#${uid}-glow)` : undefined}
                  />
                  <text
                    textAnchor="middle"
                    dy="3.5"
                    fill={n.strokeColor}
                    fontFamily="JetBrains Mono, monospace"
                    fontSize="10"
                    fontWeight="700"
                  >
                    {n.code.split('-')[0]}
                  </text>
                </g>
                <text
                  y="31"
                  textAnchor="middle"
                  fill={isHl ? '#ffffff' : '#b9cbbd'}
                  fontFamily="Manrope, sans-serif"
                  fontSize="10"
                  fontWeight="600"
                  className="transition-colors duration-200"
                >
                  {n.shortName}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover tooltip */}
        {hovered && (
          <div
            key={hovered.id}
            className="pitch-tooltip pointer-events-none absolute z-20 min-w-[150px] rounded-lg border bg-[#11131c]/95 backdrop-blur-md px-2.5 py-2 shadow-[0_8px_24px_rgba(0,0,0,0.6)]"
            style={{
              left: `${(hovered.x / W) * 100}%`,
              top: `${(hovered.y / H) * 100}%`,
              // Flip below the node near the top edge and hug the side edges so the card never clips
              transform: `translate(${hovered.x < 170 ? '-20%' : hovered.x > 510 ? '-80%' : '-50%'}, ${
                hovered.y < 180 ? '30px' : 'calc(-100% - 30px)'
              })`,
              borderColor: `${hovered.strokeColor}55`,
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-headline text-[12px] font-bold text-white whitespace-nowrap">{hovered.name}</span>
              <span className="font-mono text-[9px]" style={{ color: hovered.strokeColor }}>
                #{hovered.code}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2 mt-0.5 font-mono text-[9px] text-on-surface-variant">
              <span>{hovered.role}</span>
              <span>{hovered.sublabel}</span>
            </div>
            {typeof stances[hovered.id] === 'number' && (
              <div className="mt-1.5 flex items-center gap-1.5">
                <div className="flex-1 h-1 rounded-full bg-surface-container-highest overflow-hidden">
                  <div
                    className="h-full rounded-full bar-grow"
                    style={{
                      width: `${Math.round(((stances[hovered.id] + 1) / 2) * 100)}%`,
                      background: hovered.strokeColor,
                    }}
                  />
                </div>
                <span className="font-mono text-[9px] font-bold" style={{ color: hovered.strokeColor }}>
                  {stances[hovered.id] > 0 ? '+' : ''}
                  {stances[hovered.id].toFixed(2)}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 pt-2 font-mono text-[9px] uppercase tracking-wider text-on-surface-variant">
        <span className="flex items-center gap-1.5">
          <span className="w-4 h-0.5 rounded-full bg-gradient-to-r from-primary-container to-secondary-container"></span>
          Passing lane
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-primary-container/25 border border-primary-container/40"></span>
          Pressing zone
        </span>
        <span className="flex items-center gap-1.5">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary-container opacity-60"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-secondary-container"></span>
          </span>
          On the ball
        </span>
        <span className="ml-auto hidden sm:inline text-on-surface-variant/70 normal-case tracking-normal">
          Hover or tap an agent to trace its lanes
        </span>
      </div>
    </div>
  );
}
