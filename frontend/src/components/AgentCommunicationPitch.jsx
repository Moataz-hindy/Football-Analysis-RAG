import React, { useState, useEffect, useMemo, useRef } from 'react';

/**
 * Agent Communication Graph on a Football Pitch.
 *
 * Recreates the exact command-center pitch visualization from the specification:
 * - Top header: "NETWORKX GRAPH ROUTING • ROUND X" + "Consensus: XX%" pill
 * - Title: "Agent Communication Graph"
 * - Tactical football pitch with emerald/cyan markings
 * - Agents positioned on the pitch as tactical nodes with initial and label
 * - Animated passes between agents representing dialogue routing
 * - Legend with colored dots matching active personas
 */

const PITCH_WIDTH = 581;
const PITCH_HEIGHT = 380;

// Default color palette matching Image #1
const AGENT_COLORS = {
  arg_coach: '#34d399',      // Mint/Emerald
  arg_fan: '#38bdf8',        // Sky Blue / Cyan
  arg_pundit: '#a78bfa',     // Lavender / Purple
  france_coach: '#fb7185',   // Coral / Rose
  france_fan: '#fbbf24',     // Amber / Gold
  france_pundit: '#00f59b',  // Neon Green
  tactical_analyst: '#10b981',
  statistical_analyst: '#00d2ff',
  fan_analyst: '#ec4899',
  refereeing_analyst: '#f59e0b',
  performance_analyst: '#f43f5e',
  context_analyst: '#a78bfa',
};

// Fallback tactical pitch positions (x, y in SVG coordinates)
const DEFAULT_POSITIONS_6 = {
  // Left side (Home / Camp A)
  arg_coach: { x: 130, y: 110, role: 'Coach' },
  arg_fan: { x: 90, y: 290, role: 'Fan' },
  arg_pundit: { x: 220, y: 200, role: 'Pundit' },
  // Right side (Away / Camp B)
  france_coach: { x: 450, y: 110, role: 'Coach' },
  france_fan: { x: 490, y: 290, role: 'Fan' },
  france_pundit: { x: 360, y: 200, role: 'Pundit' },
  // Standard specialist analysts
  tactical_analyst: { x: 140, y: 120, role: 'Tactical' },
  statistical_analyst: { x: 230, y: 270, role: 'Data' },
  performance_analyst: { x: 290, y: 130, role: 'Physical' },
  fan_analyst: { x: 440, y: 270, role: 'Fan' },
  refereeing_analyst: { x: 290, y: 330, role: 'Referee' },
  context_analyst: { x: 440, y: 120, role: 'Context' },
};

function getCurvedPath(x1, y1, x2, y2, curvature = 0.18) {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const dist = Math.hypot(dx, dy) || 1;
  // Perpendicular offset for organic ball trajectory arc
  const cx = mx - (dy / dist) * dist * curvature;
  const cy = my + (dx / dist) * dist * curvature;
  return `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;
}

export default function AgentCommunicationPitch({
  agents = [],
  messages = [],
  activeRound = 0,
  consensus = 54,
  cursor = 0,
  playing = false,
  activePassEvent = null,
  onSelectAgent = null,
}) {
  const [hoveredAgentId, setHoveredAgentId] = useState(null);
  const [activePass, setActivePass] = useState(null);
  const [passAnimActive, setPassAnimActive] = useState(false);
  const [ballPossessor, setBallPossessor] = useState(null);
  const [passKey, setPassKey] = useState(0);
  const passTimerRef = useRef(null);
  const prevCursorRef = useRef(cursor);
  // Normalize active agents list
  const activeAgentList = useMemo(() => {
    if (agents && agents.length > 0) {
      return agents.map((a, idx) => {
        const id = a.id || a.agent_id || `agent_${idx}`;
        const name = a.name || id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        const color = a.color || AGENT_COLORS[id] || (idx % 2 === 0 ? '#00f59b' : '#00d2ff');
        const initial = (name.replace(/^(arg|france)\s+/i, '').trim()[0] || name[0] || 'A').toUpperCase();
        return { id, name, color, initial, raw: a };
      });
    }
    // Fallback default agents matching Image #1
    return [
      { id: 'arg_coach', name: 'Arg Coach', color: '#34d399', initial: 'A' },
      { id: 'arg_fan', name: 'Arg Fan', color: '#38bdf8', initial: 'A' },
      { id: 'arg_pundit', name: 'Arg Pundit', color: '#a78bfa', initial: 'A' },
      { id: 'france_coach', name: 'France Coach', color: '#fb7185', initial: 'F' },
      { id: 'france_fan', name: 'France Fan', color: '#fbbf24', initial: 'F' },
      { id: 'france_pundit', name: 'France Pundit', color: '#00f59b', initial: 'F' },
    ];
  }, [agents]);

  // Compute node coordinates on the pitch dynamically
  const nodePositions = useMemo(() => {
    const map = {};
    const count = activeAgentList.length;

    activeAgentList.forEach((a, idx) => {
      // 1. Direct static preset if available
      if (DEFAULT_POSITIONS_6[a.id]) {
        map[a.id] = { ...DEFAULT_POSITIONS_6[a.id], ...a };
        return;
      }

      // 2. Dynamic 2-team layout or circular distribution
      if (count <= 4) {
        const xStep = PITCH_WIDTH / (count + 1);
        map[a.id] = {
          x: Math.round(xStep * (idx + 1)),
          y: idx % 2 === 0 ? 150 : 250,
          ...a,
        };
      } else {
        const isCampA = idx < count / 2;
        const subIdx = isCampA ? idx : idx - Math.floor(count / 2);
        const subTotal = isCampA ? Math.floor(count / 2) : count - Math.floor(count / 2);

        const xBase = isCampA ? 140 : 440;
        const xOffset = (subIdx % 2 === 0 ? -40 : 40) * (subIdx > 0 ? 1 : 0);
        const yStep = 240 / Math.max(1, subTotal - 1 || 1);
        const yBase = 90 + subIdx * yStep;

        map[a.id] = {
          x: Math.max(60, Math.min(PITCH_WIDTH - 60, xBase + xOffset)),
          y: Math.max(80, Math.min(PITCH_HEIGHT - 60, yBase)),
          ...a,
        };
      }
    });
    return map;
  }, [activeAgentList]);

  // Extract passes from messages
  const communicationPasses = useMemo(() => {
    const passes = [];
    if (!messages || messages.length === 0) {
      // Default sample passes matching Image #1
      return [
        { from: 'arg_coach', to: 'arg_pundit', round: 0, weight: 3 },
        { from: 'arg_pundit', to: 'france_pundit', round: 0, weight: 2 },
        { from: 'france_pundit', to: 'france_coach', round: 0, weight: 2 },
        { from: 'arg_fan', to: 'france_fan', round: 0, weight: 1 },
      ];
    }

    const filtered = activeRound === -1
      ? messages
      : messages.filter((m) => m.round_num === activeRound);

    const msgsToAnalyze = filtered.length > 0 ? filtered : messages;

    for (let i = 0; i < msgsToAnalyze.length; i++) {
      const m = msgsToAnalyze[i];
      const fromId = m.sender_id;

      if (Array.isArray(m.recipient_ids) && m.recipient_ids.length > 0) {
        m.recipient_ids.forEach((toId) => {
          if (nodePositions[fromId] && nodePositions[toId] && fromId !== toId) {
            passes.push({
              from: fromId,
              to: toId,
              round: m.round_num,
              content: m.content?.slice(0, 80) || '',
              weight: 2,
            });
          }
        });
      } else if (i > 0) {
        const prev = msgsToAnalyze[i - 1];
        if (nodePositions[prev.sender_id] && nodePositions[fromId] && prev.sender_id !== fromId) {
          passes.push({
            from: prev.sender_id,
            to: fromId,
            round: m.round_num,
            content: m.content?.slice(0, 80) || '',
            weight: 2,
          });
        }
      }
    }

    return passes.length > 0
      ? passes
      : [
          { from: activeAgentList[0]?.id, to: activeAgentList[1]?.id, round: 0, weight: 2 },
        ];
  }, [messages, activeRound, nodePositions, activeAgentList]);

  // On-demand pass trigger function (single smooth 1.6s pass)
  const triggerPass = (fromId, toId, roundNum = activeRound) => {
    if (!fromId || !toId || fromId === toId || !nodePositions[fromId] || !nodePositions[toId]) {
      if (toId && nodePositions[toId]) setBallPossessor(toId);
      return;
    }
    clearTimeout(passTimerRef.current);
    setActivePass({ from: fromId, to: toId, round: roundNum });
    setPassAnimActive(true);
    setPassKey((k) => k + 1);

    passTimerRef.current = setTimeout(() => {
      setPassAnimActive(false);
      setBallPossessor(toId);
    }, 1600);
  };

  // On-demand pass animation triggered when stepping messages (cursor change)
  useEffect(() => {
    if (cursor <= 0 || !messages || messages.length === 0) {
      clearTimeout(passTimerRef.current);
      setActivePass(null);
      setPassAnimActive(false);
      setBallPossessor(null);
      prevCursorRef.current = cursor;
      return;
    }

    const currentMsg = messages[cursor - 1];
    if (!currentMsg) return;

    const senderId = currentMsg.sender_id;
    let receiverId = null;

    // 1. Direct recipient addressed in message
    if (Array.isArray(currentMsg.recipient_ids) && currentMsg.recipient_ids.length > 0) {
      receiverId = currentMsg.recipient_ids.find((id) => id !== senderId && nodePositions[id]);
    }

    // 2. Interlocutor pass from previous speaker to current speaker
    if (!receiverId && cursor > 1 && messages[cursor - 2]) {
      const prevSender = messages[cursor - 2].sender_id;
      if (prevSender !== senderId && nodePositions[prevSender]) {
        triggerPass(prevSender, senderId, currentMsg.round_num);
        prevCursorRef.current = cursor;
        return;
      }
    }

    // 3. Fallback to next tactical specialist on pitch
    if (!receiverId) {
      const other = activeAgentList.find((a) => a.id !== senderId && nodePositions[a.id]);
      if (other) receiverId = other.id;
    }

    if (senderId && receiverId && nodePositions[senderId] && nodePositions[receiverId]) {
      triggerPass(senderId, receiverId, currentMsg.round_num);
    } else {
      setBallPossessor(senderId);
    }

    prevCursorRef.current = cursor;
  }, [cursor, messages, nodePositions, activeAgentList]);

  // React to explicit external pass event if provided
  useEffect(() => {
    if (!activePassEvent || !activePassEvent.from || !activePassEvent.to) return;
    triggerPass(activePassEvent.from, activePassEvent.to, activePassEvent.round);
  }, [activePassEvent]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      clearTimeout(passTimerRef.current);
    };
  }, []);

  // Manual Replay Pass handler
  const handleReplayPass = () => {
    if (activePass && activePass.from && activePass.to) {
      triggerPass(activePass.from, activePass.to, activePass.round);
    } else if (cursor > 0 && messages[cursor - 1]) {
      const msg = messages[cursor - 1];
      const sender = msg.sender_id;
      const other = activeAgentList.find((a) => a.id !== sender && nodePositions[a.id]);
      if (other) triggerPass(sender, other.id, msg.round_num);
    } else if (communicationPasses.length > 0) {
      const p = communicationPasses[0];
      triggerPass(p.from, p.to, p.round);
    }
  };

  // Current active pass trajectory
  const currentPassData = useMemo(() => {
    if (!activePass || !nodePositions[activePass.from] || !nodePositions[activePass.to]) {
      return null;
    }
    const from = nodePositions[activePass.from];
    const to = nodePositions[activePass.to];
    const d = getCurvedPath(from.x, from.y, to.x, to.y, 0.22);
    return { from, to, d };
  }, [activePass, nodePositions]);

  return (
    <div className="relative w-full rounded-2xl bg-[#080d19] border border-white/[0.08] p-4 shadow-2xl flex flex-col space-y-3 overflow-hidden select-none">
      {/* Top Header matching Image #1 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] font-semibold tracking-wider text-[#00f59b] uppercase">
            NETWORKX GRAPH ROUTING • ROUND {activeRound === -1 ? 'ALL' : activeRound}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* On-Demand Replay Pass Button */}
          <button
            type="button"
            onClick={handleReplayPass}
            className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10.5px] font-mono text-[#00f59b] bg-[#00f59b]/10 hover:bg-[#00f59b]/20 border border-[#00f59b]/35 transition-all active:scale-95 cursor-pointer"
            title="Replay tactical pass between active agents"
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            <span>{passAnimActive ? 'PASSING...' : 'REPLAY PASS'}</span>
          </button>
          {/* Consensus Pill */}
          <div className="flex items-center px-3 py-0.5 rounded-full bg-[#00f59b]/10 border border-[#00f59b]/40">
            <span className="font-mono text-[11px] font-bold text-[#00f59b]">
              Consensus: {consensus}%
            </span>
          </div>
        </div>
      </div>

      {/* Main Title matching Image #1 */}
      <div className="flex items-baseline justify-between">
        <h3 className="text-[17px] font-bold text-white tracking-tight">
          Agent Communication Graph
        </h3>
        <span className="text-[11px] text-neutral-400 font-mono">
          {passAnimActive && activePass ? (
            <span className="text-[#00f59b] font-medium transition-all">
              ⚡ Pass: {nodePositions[activePass.from]?.name} ➔ {nodePositions[activePass.to]?.name}
            </span>
          ) : ballPossessor && nodePositions[ballPossessor] ? (
            <span className="text-[#38bdf8] font-medium transition-all">
              ⚽ Ball at {nodePositions[ballPossessor]?.name}
            </span>
          ) : (
            'Tactical passing lanes live • On-demand pass on next/prev'
          )}
        </span>
      </div>

      {/* Football Pitch Container */}
      <div className="relative w-full rounded-xl overflow-hidden bg-[#040810] border border-[#00f59b]/25 shadow-inner">
        <svg
          viewBox={`0 0 ${PITCH_WIDTH} ${PITCH_HEIGHT}`}
          className="w-full h-auto block"
          role="img"
          aria-label="Agent Communication Graph showing conversation passing on football pitch"
        >
          <defs>
            {/* Glow Filter */}
            <filter id="pitch-glow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="3.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            {/* Ball Glow Filter */}
            <filter id="ball-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="glow" />
              <feMerge>
                <feMergeNode in="glow" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            {/* Subtle Pitch Grass Gradient */}
            <linearGradient id="pitch-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#050a14" />
              <stop offset="50%" stopColor="#040810" />
              <stop offset="100%" stopColor="#060c18" />
            </linearGradient>
          </defs>

          {/* Pitch Grass Surface */}
          <rect x="0" y="0" width={PITCH_WIDTH} height={PITCH_HEIGHT} fill="url(#pitch-gradient)" />

          {/* Subtle Vertical Stripes */}
          {Array.from({ length: 10 }).map((_, i) => (
            <rect
              key={i}
              x={(i * PITCH_WIDTH) / 10}
              y="0"
              width={PITCH_WIDTH / 10}
              height={PITCH_HEIGHT}
              fill="#00f59b"
              opacity={i % 2 === 0 ? 0.015 : 0.005}
            />
          ))}

          {/* Tactical Pitch Markings (Emerald #00f59b outline as in Image #1) */}
          <g fill="none" stroke="#00f59b" strokeWidth="1.2" strokeOpacity="0.45">
            {/* Outer Boundary with margin */}
            <rect x="18" y="16" width={PITCH_WIDTH - 36} height={PITCH_HEIGHT - 32} rx="6" />

            {/* Half-Way Line */}
            <line x1={PITCH_WIDTH / 2} y1="16" x2={PITCH_WIDTH / 2} y2={PITCH_HEIGHT - 16} />

            {/* Center Circle */}
            <circle cx={PITCH_WIDTH / 2} cy={PITCH_HEIGHT / 2} r="46" />
            <circle cx={PITCH_WIDTH / 2} cy={PITCH_HEIGHT / 2} r="2" fill="#00f59b" fillOpacity="0.7" />

            {/* Left Penalty Box & Goal Area */}
            <rect x="18" y="86" width="76" height={PITCH_HEIGHT - 172} />
            <rect x="18" y="140" width="28" height="100" />
            <circle cx="70" cy={PITCH_HEIGHT / 2} r="1.5" fill="#00f59b" />
            <path d={`M 94,${PITCH_HEIGHT / 2 - 28} A 36,36 0 0 1 94,${PITCH_HEIGHT / 2 + 28}`} />

            {/* Right Penalty Box & Goal Area */}
            <rect x={PITCH_WIDTH - 94} y="86" width="76" height={PITCH_HEIGHT - 172} />
            <rect x={PITCH_WIDTH - 46} y="140" width="28" height="100" />
            <circle cx={PITCH_WIDTH - 70} cy={PITCH_HEIGHT / 2} r="1.5" fill="#00f59b" />
            <path d={`M ${PITCH_WIDTH - 94},${PITCH_HEIGHT / 2 - 28} A 36,36 0 0 0 ${PITCH_WIDTH - 94},${PITCH_HEIGHT / 2 + 28}`} />
          </g>

          {/* Background Communication Lanes (Static/Faint) */}
          {communicationPasses.map((p, idx) => {
            const from = nodePositions[p.from];
            const to = nodePositions[p.to];
            if (!from || !to) return null;
            const isHovered = hoveredAgentId === p.from || hoveredAgentId === p.to;
            const isCurrentPass = activePass && activePass.from === p.from && activePass.to === p.to;
            const d = getCurvedPath(from.x, from.y, to.x, to.y, idx % 2 === 0 ? 0.16 : -0.16);

            return (
              <g key={`pass-lane-${idx}`}>
                <path
                  d={d}
                  fill="none"
                  stroke={from.color}
                  strokeWidth={isCurrentPass ? 2.5 : isHovered ? 2 : 1}
                  strokeOpacity={isCurrentPass ? 0.75 : isHovered ? 0.45 : 0.14}
                  strokeDasharray={isCurrentPass ? 'none' : '4 6'}
                  filter={isCurrentPass ? 'url(#pitch-glow)' : undefined}
                />
              </g>
            );
          })}

          {/* Active Passing Ball Animation (Triggered On-Demand) */}
          {passAnimActive && currentPassData && (
            <g key={`active-ball-${passKey}-${activePass?.from}-${activePass?.to}`}>
              {/* Glowing animated trajectory path */}
              <path
                id="active-pass-arc"
                d={currentPassData.d}
                fill="none"
                stroke={currentPassData.from.color}
                strokeWidth="2.8"
                strokeOpacity="0.9"
                filter="url(#pitch-glow)"
              />
              {/* Traveling Glowing Soccer Ball */}
              <circle r="4.8" fill="#ffffff" filter="url(#ball-glow)">
                <animateMotion
                  dur="1.5s"
                  repeatCount="1"
                  fill="freeze"
                  path={currentPassData.d}
                />
              </circle>
              {/* Trailing luminous particle */}
              <circle r="2.8" fill={currentPassData.from.color} opacity="0.85">
                <animateMotion
                  dur="1.5s"
                  begin="0.08s"
                  repeatCount="1"
                  fill="freeze"
                  path={currentPassData.d}
                />
              </circle>
            </g>
          )}

          {/* Resting Ball when Idle at Possessor Node */}
          {!passAnimActive && ballPossessor && nodePositions[ballPossessor] && (
            <g
              key={`resting-ball-${ballPossessor}`}
              transform={`translate(${nodePositions[ballPossessor].x + 13},${nodePositions[ballPossessor].y - 12})`}
            >
              <circle r="7.5" fill="none" stroke="#00f59b" strokeWidth="1" strokeDasharray="2 2" opacity="0.65" />
              <circle r="4.2" fill="#ffffff" stroke="#00f59b" strokeWidth="1.2" filter="url(#ball-glow)" />
              <circle r="1.5" fill="#040810" />
            </g>
          )}

          {/* Resting Ball at Pitch Center when at Kickoff (cursor == 0) */}
          {!passAnimActive && !ballPossessor && (
            <g transform={`translate(${PITCH_WIDTH / 2},${PITCH_HEIGHT / 2})`}>
              <circle r="4" fill="#ffffff" stroke="#00f59b" strokeWidth="1.2" opacity="0.85" filter="url(#ball-glow)" />
              <circle r="1.2" fill="#040810" />
            </g>
          )}

          {/* Agent Nodes on Pitch */}
          {Object.values(nodePositions).map((n) => {
            const isHovered = hoveredAgentId === n.id;
            const isSender = activePass && activePass.from === n.id;
            const isReceiver = activePass && activePass.to === n.id;
            const isFocused = isHovered || isSender || isReceiver;

            return (
              <g
                key={n.id}
                transform={`translate(${n.x},${n.y})`}
                className="cursor-pointer transition-transform duration-200"
                onMouseEnter={() => setHoveredAgentId(n.id)}
                onMouseLeave={() => setHoveredAgentId(null)}
                onClick={() => onSelectAgent && onSelectAgent(n.id)}
              >
                {/* Active halo ring if on the ball */}
                {(isSender || isReceiver) && (
                  <circle
                    r="21"
                    fill="none"
                    stroke={n.color}
                    strokeWidth="1.5"
                    strokeOpacity="0.7"
                    className="animate-ping"
                  />
                )}

                {/* Agent Node Circle with Letter (exact style as Image #1) */}
                <circle
                  r={isFocused ? 14 : 12.5}
                  fill="#060c18"
                  stroke={n.color}
                  strokeWidth={isFocused ? 2.5 : 1.8}
                  filter={isFocused ? 'url(#pitch-glow)' : undefined}
                />

                {/* Inner Letter matching Image #1 (e.g. 'F' or 'A') */}
                <text
                  textAnchor="middle"
                  dy="4.2"
                  fill={n.color}
                  fontSize={isFocused ? "11.5" : "10"}
                  fontWeight="bold"
                  fontFamily="system-ui, sans-serif"
                  pointerEvents="none"
                >
                  {n.initial}
                </text>

                {/* Label Underneath Node matching Image #1 */}
                <text
                  textAnchor="middle"
                  y="24"
                  fill="#e2e8f0"
                  fillOpacity={isFocused ? 1 : 0.75}
                  fontSize="9.5"
                  fontWeight={isFocused ? "600" : "500"}
                  fontFamily="system-ui, sans-serif"
                  className="tracking-tight"
                >
                  {n.name}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend at the bottom matching Image #1 */}
      <div className="flex items-center justify-center gap-x-4 gap-y-2 flex-wrap pt-1 px-1">
        {activeAgentList.map((a) => (
          <div
            key={a.id}
            className={`flex items-center gap-1.5 cursor-pointer transition-opacity ${
              hoveredAgentId && hoveredAgentId !== a.id ? 'opacity-35' : 'opacity-90 hover:opacity-100'
            }`}
            onMouseEnter={() => setHoveredAgentId(a.id)}
            onMouseLeave={() => setHoveredAgentId(null)}
            onClick={() => onSelectAgent && onSelectAgent(a.id)}
          >
            <span
              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{
                backgroundColor: a.color,
                boxShadow: hoveredAgentId === a.id ? `0 0 8px ${a.color}` : 'none',
              }}
            ></span>
            <span className="text-[11.5px] text-neutral-300 font-medium whitespace-nowrap">
              {a.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
