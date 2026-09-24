import React, { useState } from 'react';
import { AGENTS, getAgentInfo } from '../constants/agents.js';
import SpeechCard from './SpeechCard.jsx';
import TacticalPitch from './TacticalPitch.jsx';

// Fallback Stitch mock speeches shown until live messages are loaded
const MOCK_SPEECHES = [
  {
    key: 'mock-tactical',
    agent: getAgentInfo('tactical_analyst'),
    stance: 0.72,
    meta: '12:44:02 UTC • Step 14/22',
    badge: { icon: 'verified', label: '+0.72 PRO (Masterclass)', className: 'bg-primary/10 border border-primary/30 text-primary' },
    content:
      'スペインのポゼッション (82.3%) against our compact 5-4-1 forced horizontal circulation. Notice Morata being starved of central penetrative passing lanes; our defensive line compressed the vertical pitch space to just 18.2 meters between lines.',
    stats: [
      { label: 'Sentiment', value: '88% Int.', className: 'text-primary' },
      { label: 'Block Depth', value: '21.4m' },
    ],
    action: { icon: 'share_reviews', label: 'Audit Logic' },
  },
  {
    key: 'mock-statistical',
    agent: getAgentInfo('statistical_analyst'),
    stance: 0.81,
    meta: '12:44:18 UTC • Step 15/22',
    badge: { icon: 'query_stats', label: '+0.81 PRO (Quantified)', className: 'bg-secondary/10 border border-secondary/30 text-secondary' },
    content:
      'xG conceded was merely 0.68 excluding the Morata header. Expected Threat (xT) conceded fell 64% after switching from 4-2-3-1. Spain completed over 1,000 passes, but only 4.2% penetrated into the penalty box.',
    stats: [
      { label: 'Sentiment', value: '94% Int.', className: 'text-secondary' },
      { label: 'Delta xG', value: '-1.50' },
    ],
    action: { icon: 'scatter_plot', label: 'Inspect Vectors' },
  },
  {
    key: 'mock-fan',
    agent: getAgentInfo('fan_analyst'),
    stance: 0.55,
    meta: '12:44:31 UTC • Step 16/22',
    badge: {
      icon: 'local_fire_department',
      label: '+0.55 PRO (Kinetic)',
      className: 'bg-surface-container-highest border border-white/[0.08] text-secondary-fixed',
    },
    content:
      'The sheer psychological collapse of Spain when Doan struck! Numbers do not capture the stadium atmosphere shifting; Spain started playing with paralyzed hesitation the second the second ball hit the net!',
    stats: [
      { label: 'Decibel', value: '104dB', className: 'text-secondary-fixed' },
      { label: 'Heart Rate', value: '162bpm' },
    ],
    action: { icon: 'graphic_eq', label: 'Acoustic Sync' },
  },
];

function toSpeech(msg, idx, total) {
  const agent = getAgentInfo(msg.sender_id);
  const hasScore = msg.sentiment_score !== null && msg.sentiment_score !== undefined;
  const isPositive = (msg.sentiment_score ?? 0) >= 0;
  return {
    key: `${msg.sender_id}-${msg.round_num}-${idx}`,
    agent,
    stance: hasScore ? msg.sentiment_score : null,
    meta: `Round ${msg.round_num} • Step ${idx + 1}/${total}`,
    badge: {
      icon: isPositive ? 'verified' : 'priority_high',
      label: hasScore
        ? `${msg.sentiment_score > 0 ? '+' : ''}${msg.sentiment_score.toFixed(2)} ${isPositive ? 'PRO' : 'CON'}`
        : '+0.72 PRO (Synthesized)',
      className: isPositive
        ? 'bg-primary/10 border border-primary/30 text-primary'
        : 'bg-error/10 border border-error/30 text-error',
    },
    content: msg.content,
    stats: [
      {
        label: 'Sentiment',
        value: `${Math.abs(Math.round((msg.sentiment_score || 0.85) * 100))}% Int.`,
        className: isPositive ? 'text-primary' : 'text-error',
      },
      { label: 'Block Depth', value: '21.4m' },
    ],
    action: { icon: 'share_reviews', label: 'Audit Logic' },
  };
}

export default function DeliberationView({
  topics,
  currentDiscussion,
  currentAnalytics,
  messages,
  customPrompt,
  setCustomPrompt,
  handleLaunch,
  isLaunching,
  activeRound,
  setActiveRound,
  isPlaying,
  setIsPlaying,
}) {
  // Shared hover state between the agent selector, the pitch and the speech cards
  const [hoveredAgent, setHoveredAgent] = useState(null);

  const speeches = messages.length === 0 ? MOCK_SPEECHES : messages.map((m, i) => toSpeech(m, i, messages.length));
  const speakingIds = [...new Set(speeches.map((s) => s.agent.id))];
  // Latest stance per agent in the current round, surfaced in the pitch tooltip
  const stances = Object.fromEntries(
    speeches.filter((s) => typeof s.stance === 'number').map((s) => [s.agent.id, s.stance])
  );

  return (
    <div className="flex flex-col w-full px-4 space-y-4 pt-2">
      {/* Active Debate Hero Banner */}
      <div className="w-full rounded-2xl bg-[#0d0f18]/90 border border-white/[0.08] p-4 relative overflow-hidden shadow-2xl backdrop-blur-md">
        {/* Ambient kinetic gradient corner */}
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-gradient-to-br from-primary/15 via-secondary/10 to-transparent blur-2xl pointer-events-none"></div>
        <div className="relative z-10 flex flex-col space-y-3">
          {/* Top Badges */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-primary/10 border border-primary/30 text-primary">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-primary"></span>
              </span>
              <span className="font-mono text-[9px] uppercase tracking-wider font-semibold">
                ROUND{' '}
                <span key={activeRound} className="inline-block fade-swap">
                  {activeRound === 0 ? 'INIT' : activeRound === -1 ? 'ALL' : activeRound}
                </span>{' '}
                / IN PROGRESS
              </span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-surface-container-highest/80 border border-secondary/25 text-secondary">
              <span className="material-symbols-outlined text-[13px]">pie_chart</span>
              <span className="font-mono text-[10px] font-medium tracking-tight">
                Consensus: {Math.round((currentAnalytics?.consensus_score || 0.68) * 100)}% Conv.
              </span>
            </div>
          </div>

          {/* Main Debate Header */}
          <div>
            <span className="font-mono text-[10px] text-on-surface-variant tracking-wider uppercase">
              Dialectical Deliberation Table
            </span>
            <h1 className="font-headline text-[19px] sm:text-[21px] font-bold text-white tracking-tight leading-snug mt-0.5">
              {currentDiscussion?.topic || "Japan's 5-4-1 Low Block vs Spain"}{' '}
              <span className="text-secondary font-mono text-[14px] font-normal">(WC22 Group E)</span>
            </h1>
          </div>

          {/* Meta Footnote */}
          <div className="flex items-center justify-between pt-1 border-t border-white/[0.06] text-[11px]">
            <div className="flex items-center gap-1.5 text-on-surface-variant">
              <span className="material-symbols-outlined text-[15px] text-tertiary">psychology</span>
              <span className="font-mono text-[10px]">6 Agents Synthesizing Live</span>
            </div>
            <div className="flex items-center gap-1 text-primary">
              <span className="material-symbols-outlined text-[14px]">tune</span>
              <span className="font-mono text-[10px] font-medium">Entropy: Low (0.18)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Curated Frame Registry */}
      <div className="w-full flex flex-col space-y-2">
        <div className="flex items-center justify-between px-0.5">
          <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider">
            01 / Curated Frame Registry
          </span>
          <span className="font-mono text-[10px] text-secondary font-medium">
            {topics.length || 3} Pinned Debates
          </span>
        </div>
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-0.5">
          {topics.length > 0 ? (
            topics.map((t, idx) => {
              const isSelected = currentDiscussion?.topic === t.label;
              return (
                <button
                  key={t.id}
                  onClick={() => {
                    setCustomPrompt(t.label);
                    handleLaunch(t.label);
                  }}
                  className={`flex-shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all duration-200 active:scale-95 ${
                    isSelected || (idx === 0 && !currentDiscussion)
                      ? 'bg-surface-container-high border border-primary/40 text-primary shadow-[0_0_12px_rgba(0,245,155,0.08)]'
                      : 'bg-[#0d0f18] border border-white/[0.06] text-on-surface-variant hover:text-white hover:border-white/[0.12]'
                  }`}
                >
                  <span
                    className="material-symbols-outlined text-[15px] text-primary"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    {idx === 0 ? 'check_circle' : idx === 1 ? 'sports_soccer' : 'tactic'}
                  </span>
                  <span className="font-sans text-[12px] font-semibold">{t.label}</span>
                </button>
              );
            })
          ) : (
            <>
              <button className="flex-shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-high border border-primary/40 text-primary shadow-[0_0_12px_rgba(0,245,155,0.08)]">
                <span className="material-symbols-outlined text-[15px] text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>
                  check_circle
                </span>
                <span className="font-sans text-[12px] font-semibold">Japan 5-4-1 vs Spain</span>
              </button>
              <button className="flex-shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0d0f18] border border-white/[0.06] text-on-surface-variant hover:text-white hover:border-white/[0.12] transition-colors">
                <span className="material-symbols-outlined text-[15px] text-secondary">sports_soccer</span>
                <span className="font-sans text-[12px]">France 2022 Final xG</span>
              </button>
              <button className="flex-shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0d0f18] border border-white/[0.06] text-on-surface-variant hover:text-white hover:border-white/[0.12] transition-colors">
                <span className="material-symbols-outlined text-[15px]">tactic</span>
                <span className="font-sans text-[12px]">Tuchel Setup vs Leverkusen</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Specialist Agent Selector Matrix */}
      <div className="w-full flex flex-col space-y-2">
        <div className="flex items-center justify-between px-0.5">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px] text-secondary">hub</span>
            <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider">
              Synthesizing Specialist Agents
            </span>
          </div>
          <span className="font-mono text-[10px] text-primary font-semibold">6 ACTIVE</span>
        </div>
        <div className="flex items-center gap-2.5 overflow-x-auto no-scrollbar py-0.5">
          {AGENTS.map((agent) => (
            <div
              key={agent.id}
              onMouseEnter={() => setHoveredAgent(agent.id)}
              onMouseLeave={() => setHoveredAgent(null)}
              className={`flex-shrink-0 w-32 p-2.5 rounded-xl bg-[#0d0f18] border ${agent.border} flex flex-col items-center text-center shadow-sm relative group transition-all duration-200 hover:-translate-y-0.5 ${
                hoveredAgent === agent.id ? '-translate-y-0.5 bg-surface-container' : ''
              } ${hoveredAgent && hoveredAgent !== agent.id ? 'opacity-50' : ''}`}
              style={
                hoveredAgent === agent.id
                  ? { borderColor: `${agent.strokeColor}99`, boxShadow: `0 0 16px ${agent.strokeColor}26` }
                  : undefined
              }
            >
              <div className="relative mb-1">
                <div
                  className={`w-9 h-9 rounded-lg bg-surface-container-high border border-white/[0.08] flex items-center justify-center ${agent.textColor} ${agent.shadow} transition-transform duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] group-hover:scale-110`}
                >
                  <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                    {agent.icon}
                  </span>
                </div>
                <span className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full ${agent.dot} ring-2 ring-[#0d0f18] ${speakingIds.includes(agent.id) ? 'animate-pulse' : ''}`}></span>
              </div>
              <span className="font-headline text-[12px] font-bold text-white truncate w-full">
                {agent.shortName}
              </span>
              <span className={`font-mono text-[9px] ${agent.subtextColor} truncate w-full mt-0.5`}>
                {agent.sublabel}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Live Tactical Pitch */}
      <div className="w-full rounded-2xl bg-[#0d0f18]/90 border border-white/[0.08] p-3.5 shadow-xl flex flex-col space-y-3">
        <div className="flex items-center justify-between px-0.5">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px] text-primary">stadium</span>
            <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider">
              Deliberation Shape • Passing Lanes
            </span>
          </div>
          <span key={activeRound} className="fade-swap font-mono text-[10px] text-secondary font-medium">
            {speakingIds.length} on the ball
          </span>
        </div>
        <TacticalPitch
          activeAgentIds={speakingIds}
          highlightId={hoveredAgent}
          onHighlight={setHoveredAgent}
          stances={stances}
        />
      </div>

      {/* VCR Replay & Round Controller */}
      <div className="w-full rounded-2xl bg-[#0d0f18] border border-white/[0.08] p-3.5 shadow-xl flex flex-col space-y-3">
        <div className="flex items-center justify-between">
          {/* Step Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
            {[
              { id: 0, label: '00 Init' },
              { id: 1, label: '01 R1' },
              { id: 2, label: '02 R2 (Live)' },
              { id: 3, label: '03 R3' },
              { id: -1, label: 'All' },
            ].map((r) => (
              <button
                key={r.id}
                onClick={() => setActiveRound(r.id)}
                className={`px-2.5 py-1 rounded-md font-mono text-[10px] transition-all duration-200 active:scale-95 ${
                  activeRound === r.id
                    ? 'bg-primary text-on-primary font-bold shadow-[0_0_12px_rgba(0,245,155,0.4)]'
                    : 'bg-surface-container-high border border-white/[0.04] text-on-surface-variant hover:text-white'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
          {/* Timecode */}
          <div className="flex items-center gap-1.5 text-secondary font-mono text-[12px] font-semibold flex-shrink-0">
            <span className="material-symbols-outlined text-[15px]">timer</span>
            <span>48:12</span>
          </div>
        </div>

        {/* Playback Actions & Agreement Gauge */}
        <div className="flex items-center justify-between pt-1 border-t border-white/[0.06]">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveRound((prev) => (prev <= 0 ? 3 : prev - 1))}
              aria-label="Step back"
              className="w-8 h-8 rounded-lg bg-surface-container-high border border-white/[0.06] text-on-surface-variant hover:text-white hover:border-white/[0.14] active:scale-90 flex items-center justify-center transition-all"
            >
              <span className="material-symbols-outlined text-[16px]">skip_previous</span>
            </button>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              aria-label="Play/Pause stream"
              className="px-3.5 h-8 rounded-lg bg-secondary text-on-primary font-mono text-[11px] font-bold flex items-center gap-1.5 shadow-[0_0_12px_rgba(0,210,255,0.35)] hover:opacity-95 hover:shadow-[0_0_18px_rgba(0,210,255,0.55)] active:scale-95 transition-all"
            >
              <span
                className="material-symbols-outlined text-[16px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                {isPlaying ? 'pause' : 'play_arrow'}
              </span>
              <span>{isPlaying ? 'LIVE STREAM' : 'PAUSED'}</span>
            </button>
            <button
              onClick={() => setActiveRound((prev) => (prev >= 3 ? 0 : prev + 1))}
              aria-label="Step forward"
              className="w-8 h-8 rounded-lg bg-surface-container-high border border-white/[0.06] text-on-surface-variant hover:text-white hover:border-white/[0.14] active:scale-90 flex items-center justify-center transition-all"
            >
              <span className="material-symbols-outlined text-[16px]">skip_next</span>
            </button>
          </div>

          {/* Agreement Gauge */}
          <div className="flex items-center gap-2">
            <div className="flex flex-col items-end">
              <span className="font-mono text-[9px] text-on-surface-variant tracking-wider uppercase">
                AGREEMENT INDEX
              </span>
              <span className="font-mono text-[11px] font-bold text-primary">0.84 HIGH</span>
            </div>
            <div className="w-14 h-2 rounded-full bg-surface-container-lowest border border-white/[0.06] overflow-hidden flex">
              <div className="bar-grow bg-gradient-to-r from-secondary to-primary h-full w-[84%] shadow-[0_0_8px_#00f59b]"></div>
            </div>
          </div>
        </div>
      </div>

      {/* Synthesized Dialectical Stream */}
      <div className="w-full flex flex-col space-y-3 pt-1">
        <div className="flex items-center justify-between px-0.5">
          <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider">
            Synthesized Dialectical Stream
          </span>
          <span key={`${activeRound}-${speeches.length}`} className="fade-swap font-mono text-[10px] text-secondary font-medium">
            {messages.length || 3} Speeches Recorded
          </span>
        </div>

        {speeches.map(({ key, ...speech }, idx) => (
          <SpeechCard key={`${activeRound}-${key}`} index={idx} onHover={setHoveredAgent} {...speech} />
        ))}
      </div>

      {/* STICKY BOTTOM INPUT FOR DEBATE CHALLENGE */}
      <div className="sticky bottom-20 w-full pt-1 z-40">
        <div className="w-full rounded-2xl bg-[#131622]/95 backdrop-blur-xl border border-white/[0.1] p-1.5 shadow-[0_8px_32px_rgba(0,0,0,0.8)] flex items-center gap-2 transition-all duration-200 focus-within:border-secondary/50 focus-within:shadow-[0_8px_32px_rgba(0,0,0,0.8),0_0_0_3px_rgba(0,210,255,0.12)]">
          <div className="flex-1 flex items-center px-2.5 gap-2 min-w-0">
            <span className="material-symbols-outlined text-secondary text-[18px] flex-shrink-0">terminal</span>
            <input
              type="text"
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleLaunch()}
              placeholder="Frame debate prompt or challenge consensus..."
              className="w-full bg-transparent text-white font-sans text-[13px] placeholder:text-on-surface-variant focus:outline-none min-w-0 truncate py-1.5"
            />
          </div>
          <button
            onClick={() => handleLaunch()}
            disabled={isLaunching || !customPrompt.trim()}
            className="group/launch flex-shrink-0 px-3.5 py-2 rounded-xl bg-primary text-on-primary font-headline text-[12px] font-bold flex items-center gap-1.5 shadow-[0_0_16px_rgba(0,245,155,0.4)] hover:bg-primary-fixed-dim active:scale-95 transition-all disabled:opacity-60 disabled:active:scale-100"
          >
            <span>{isLaunching ? 'Synthesizing...' : 'Launch Room'}</span>
            <span
              className={`material-symbols-outlined text-[15px] transition-transform duration-200 group-hover/launch:translate-x-0.5 ${
                isLaunching ? 'animate-pulse' : ''
              }`}
            >
              arrow_forward
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}
