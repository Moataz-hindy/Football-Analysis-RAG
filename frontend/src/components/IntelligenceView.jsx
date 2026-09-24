import React from 'react';
import { getAgentInfo } from '../constants/agents.js';
import TacticalPitch from './TacticalPitch.jsx';
import OpinionTrajectories from './OpinionTrajectories.jsx';

// Persuasion flow between agents across the debate: [from, to, weight]
const INFLUENCE_LANES = [
  ['statistical_analyst', 'context_analyst', 0.9],
  ['statistical_analyst', 'tactical_analyst', 0.85],
  ['performance_analyst', 'statistical_analyst', 0.75],
  ['statistical_analyst', 'fan_analyst', 0.6],
  ['tactical_analyst', 'fan_analyst', 0.55],
  ['performance_analyst', 'refereeing_analyst', 0.45],
  ['context_analyst', 'refereeing_analyst', 0.35],
];

// Final-round stances, matching the trajectory legend below
const FINAL_STANCES = {
  statistical_analyst: 0.85,
  performance_analyst: 0.9,
  tactical_analyst: 0.8,
  context_analyst: 0.75,
  fan_analyst: 0.6,
  refereeing_analyst: 0.5,
};

export default function IntelligenceView({ currentDiscussion, currentAnalytics }) {
  const keyArbiterId = currentAnalytics?.top_influencer || 'statistical_analyst';

  return (
    <div className="flex flex-col w-full px-4 space-y-4 pt-2">
      {/* Tactical HUD Broadcast Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-[#0d0f18]/90 border border-white/[0.08] p-4 shadow-xl flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-surface-container-high border border-primary/30 flex items-center justify-center text-primary shadow-[0_0_10px_rgba(0,245,155,0.15)] flex-shrink-0">
            <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              insights
            </span>
          </div>
          <div className="flex flex-col min-w-0">
            <span className="font-mono text-[10px] text-secondary tracking-wider uppercase truncate">
              Live Deliberation Telemetry
            </span>
            <span className="font-headline text-[14px] font-bold text-white truncate">
              Tactical Synthesis: {currentDiscussion?.topic || "Japan's 5-4-1 Low Block vs Spain"}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span className="px-2.5 py-0.5 rounded-full bg-primary/10 border border-primary/30 text-primary font-mono text-[10px] font-semibold">
            Round 3 Closed
          </span>
        </div>
      </div>

      {/* Executive KPI Metric Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* KPI 1: Consensus Trend */}
        <div style={{ animationDelay: '0ms' }} className="metric-tile card-enter rounded-2xl bg-[#0d0f18]/90 border border-white/[0.08] p-4 shadow-md flex flex-col justify-between relative overflow-hidden">
          <div className="flex items-start justify-between">
            <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider">
              Consensus Trend
            </span>
            <span className="material-symbols-outlined text-primary text-[18px]">trending_up</span>
          </div>
          <div className="my-2">
            <span className="font-headline text-[22px] font-bold text-primary block">
              {currentAnalytics?.overall_trend || 'Converging'}
            </span>
            <span className="font-mono text-[11px] text-primary/80">+35% alignment delta</span>
          </div>
          <div className="w-full h-7 mt-1">
            <svg className="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 24">
              <path className="path-draw" pathLength="1" d="M0,20 Q20,18 35,14 T65,8 T100,2" fill="none" stroke="#00f59b" strokeLinecap="round" strokeWidth="2.5" />
              <circle className="fade-in-late" cx="100" cy="2" fill="#00f59b" r="3" />
            </svg>
          </div>
        </div>

        {/* KPI 2: Mean Group Agreement Radial */}
        <div style={{ animationDelay: '60ms' }} className="metric-tile card-enter rounded-2xl bg-[#0d0f18]/90 border border-white/[0.08] p-4 shadow-md flex flex-col justify-between relative">
          <div className="flex items-start justify-between">
            <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider">
              Group Agreement
            </span>
            <span className="px-2 py-0.5 rounded bg-primary/10 border border-primary/30 font-mono text-[10px] text-primary">
              High Align
            </span>
          </div>
          <div className="flex items-center gap-3 mt-2">
            <div className="relative w-14 h-14 flex items-center justify-center flex-shrink-0">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                <path
                  className="text-surface-container-highest"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3.5"
                />
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="currentColor"
                  strokeDasharray="74.2, 100"
                  className="text-primary gauge-sweep"
                  strokeLinecap="round"
                  strokeWidth="3.5"
                />
              </svg>
              <span className="absolute font-mono text-[12px] font-bold text-white">74%</span>
            </div>
            <div className="flex flex-col min-w-0">
              <span className="font-headline text-[15px] font-semibold text-white">74.2%</span>
              <span className="font-mono text-[11px] text-on-surface-variant truncate">Target: &gt;70%</span>
            </div>
          </div>
          <span className="font-mono text-[10px] text-secondary truncate mt-1">Convergence Index: Optimal</span>
        </div>

        {/* KPI 3: Top Influencer */}
        <div style={{ animationDelay: '120ms' }} className="metric-tile card-enter rounded-2xl bg-[#0d0f18]/90 border border-white/[0.08] p-4 shadow-md flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider">Key Arbiter</span>
            <span className="material-symbols-outlined text-secondary text-[18px]">hub</span>
          </div>
          <div className="mt-2">
            <span className="font-headline text-[14px] font-bold text-white block truncate">
              {currentAnalytics?.top_influencer ? getAgentInfo(currentAnalytics.top_influencer).name : 'Statistical Analyst'}
            </span>
            <div className="flex items-center gap-1 mt-0.5">
              <span className="font-mono text-[11px] text-secondary">Pearson r = 0.88</span>
            </div>
          </div>
          <div className="mt-2 flex items-center gap-1 text-on-surface-variant text-[11px]">
            <span className="material-symbols-outlined text-[14px] text-primary">arrow_forward</span>
            <span className="font-mono text-[10px] text-on-surface-variant truncate">Shifted 4 peer weights</span>
          </div>
        </div>

        {/* KPI 4: Volatility */}
        <div style={{ animationDelay: '180ms' }} className="metric-tile card-enter rounded-2xl bg-[#0d0f18]/90 border border-white/[0.08] p-4 shadow-md flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider">
              Dialectic Volatility
            </span>
            <span className="material-symbols-outlined text-secondary text-[18px]">waves</span>
          </div>
          <div className="mt-2">
            <div className="flex items-baseline gap-1.5">
              <span className="font-headline text-[22px] font-bold text-white">1.42</span>
              <span className="font-mono text-[10px] text-primary font-medium">σ Stabilizing</span>
            </div>
            <span className="font-mono text-[10px] text-on-surface-variant block truncate mt-0.5">
              {currentDiscussion?.messages?.length || 24} msgs across 3 rounds
            </span>
          </div>
          <div className="mt-2 w-full bg-surface-container-high rounded-full h-1.5 overflow-hidden">
            <div className="bar-grow bg-secondary h-full rounded-full" style={{ width: '32%' }}></div>
          </div>
        </div>
      </div>

      {/* Influence Network Pitch */}
      <div className="rounded-2xl bg-[#0d0f18]/90 border border-white/[0.08] p-4 shadow-xl flex flex-col space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_#00f59b]"></span>
              <span className="font-headline text-[14px] font-bold text-white">Influence Network</span>
            </div>
            <span className="font-mono text-[10px] text-on-surface-variant">
              Lane weight = persuasion flow between agents • orbit marks the key arbiter
            </span>
          </div>
          <span className="px-2.5 py-0.5 rounded-full bg-surface-container-high border border-white/[0.06] font-mono text-[10px] text-on-surface-variant">
            Final shape (R3)
          </span>
        </div>
        <TacticalPitch lanes={INFLUENCE_LANES} focusId={keyArbiterId} stances={FINAL_STANCES} />
      </div>

      {/* Opinion Trajectories — small multiples, one panel per agent */}
      <OpinionTrajectories analytics={currentAnalytics} />

      {/* Dialectic Sequence Breakdown */}
      <div className="rounded-2xl bg-[#0d0f18]/90 border border-white/[0.08] p-4 shadow-xl flex flex-col space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-outlined text-secondary text-[20px]">timeline</span>
            <span className="font-headline text-[14px] font-bold text-white">Dialectic Evolution</span>
          </div>
          <span className="font-mono text-[10px] text-on-surface-variant uppercase">4 Phase Sequence</span>
        </div>

        <div className="flex flex-col gap-2 mt-1">
          <div style={{ animationDelay: '0ms' }} className="card-enter transition-all duration-200 hover:translate-x-0.5 hover:bg-surface-container-high flex items-start gap-3 p-3 rounded-xl bg-surface-container border border-white/[0.04]">
            <div className="w-8 h-8 rounded-lg bg-[#06070a] border border-error/30 flex items-center justify-center flex-shrink-0">
              <span className="font-mono text-[11px] font-bold text-error">R0</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-1">
                <span className="font-headline text-[13px] font-semibold text-white">Polarized Division</span>
                <span className="font-mono text-[10px] text-error font-medium">42% Agree</span>
              </div>
              <p className="font-sans text-[12px] text-on-surface-variant line-clamp-2 mt-0.5">
                Sharp divergence on low-possession game plan. Fan Voice and Tactical agents flagged high systemic turnover risk.
              </p>
            </div>
          </div>

          <div style={{ animationDelay: '70ms' }} className="card-enter transition-all duration-200 hover:translate-x-0.5 hover:bg-surface-container-high flex items-start gap-3 p-3 rounded-xl bg-surface-container border border-white/[0.04]">
            <div className="w-8 h-8 rounded-lg bg-[#06070a] border border-secondary/30 flex items-center justify-center flex-shrink-0">
              <span className="font-mono text-[11px] font-bold text-secondary">R1</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-1">
                <span className="font-headline text-[13px] font-semibold text-white">Emerging Consensus</span>
                <span className="font-mono text-[10px] text-secondary font-medium">58% Agree</span>
              </div>
              <p className="font-sans text-[12px] text-on-surface-variant line-clamp-2 mt-0.5">
                Statistical Agent introduced xT (Expected Threat) and box-entry data, validating tactical sustainability under counter-pressure.
              </p>
            </div>
          </div>

          <div style={{ animationDelay: '140ms' }} className="card-enter transition-all duration-200 hover:translate-x-0.5 hover:bg-surface-container-high flex items-start gap-3 p-3 rounded-xl bg-surface-container border border-white/[0.04]">
            <div className="w-8 h-8 rounded-lg bg-[#06070a] border border-primary/30 flex items-center justify-center flex-shrink-0">
              <span className="font-mono text-[11px] font-bold text-primary">R2</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-1">
                <span className="font-headline text-[13px] font-semibold text-white">Strong Convergence</span>
                <span className="font-mono text-[10px] text-primary font-medium">74% Agree</span>
              </div>
              <p className="font-sans text-[12px] text-on-surface-variant line-clamp-2 mt-0.5">
                Broad coalition formed around defensive efficiency: Mid-block compact shape neutralized 78% of half-space incursions.
              </p>
            </div>
          </div>

          <div style={{ animationDelay: '210ms' }} className="card-enter transition-all duration-200 hover:translate-x-0.5 hover:bg-surface-container-high flex items-start gap-3 p-3 rounded-xl bg-surface-container border border-primary/30">
            <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0">
              <span className="font-mono text-[11px] font-bold text-primary">R3</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-1">
                <span className="font-headline text-[13px] font-semibold text-primary">Synthesis & Masterclass</span>
                <span className="font-mono text-[10px] text-primary font-bold">86% Unified</span>
              </div>
              <p className="font-sans text-[12px] text-white line-clamp-2 mt-0.5">
                Actionable tactical consensus established: Unanimous endorsement of 4-3-3 transition triggers and overload protection.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Influence Matrix Leaderboard */}
      <div className="rounded-2xl bg-[#0d0f18]/90 border border-white/[0.08] p-4 shadow-xl flex flex-col space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-outlined text-secondary text-[20px]">military_tech</span>
            <span className="font-headline text-[14px] font-bold text-white">Influence Matrix</span>
          </div>
          <span className="font-mono text-[10px] text-on-surface-variant">Weight Distribution</span>
        </div>

        <div className="flex flex-col gap-2">
          <div style={{ animationDelay: '0ms' }} className="card-enter transition-all duration-200 hover:bg-surface-container-high hover:border-white/[0.1] p-3 rounded-xl bg-surface-container border border-white/[0.04] flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-5 h-5 rounded bg-secondary/20 text-secondary flex items-center justify-center font-mono text-[10px] font-bold flex-shrink-0">1</span>
                <span className="font-headline text-[13px] font-bold text-white truncate">Statistical Analyst</span>
                <span className="px-1.5 py-0.5 rounded bg-surface-container-high font-mono text-[9px] text-secondary uppercase">Lead Arbiter</span>
              </div>
              <span className="font-mono text-[12px] font-bold text-secondary">32% Wt</span>
            </div>
            <div className="w-full bg-surface-container-high rounded-full h-1.5 overflow-hidden">
              <div className="bar-grow bg-secondary h-full rounded-full" style={{ width: '32%' }}></div>
            </div>
            <div className="flex items-center gap-1 text-on-surface-variant mt-0.5 font-sans text-[11px]">
              <span className="material-symbols-outlined text-[13px] text-primary flex-shrink-0">sync_alt</span>
              <span className="truncate">Persuaded Context Analyst via deep xT spatial matrices</span>
            </div>
          </div>

          <div style={{ animationDelay: '70ms' }} className="card-enter transition-all duration-200 hover:bg-surface-container-high hover:border-white/[0.1] p-3 rounded-xl bg-surface-container border border-white/[0.04] flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-5 h-5 rounded bg-surface-container-high text-on-surface-variant flex items-center justify-center font-mono text-[10px] font-bold flex-shrink-0">2</span>
                <span className="font-headline text-[13px] font-bold text-white truncate">Performance Analyst</span>
                <span className="px-1.5 py-0.5 rounded bg-surface-container-high font-mono text-[9px] text-primary uppercase">Physicality</span>
              </div>
              <span className="font-mono text-[12px] font-bold text-primary">26% Wt</span>
            </div>
            <div className="w-full bg-surface-container-high rounded-full h-1.5 overflow-hidden">
              <div className="bar-grow bg-primary h-full rounded-full" style={{ width: '26%' }}></div>
            </div>
            <div className="flex items-center gap-1 text-on-surface-variant mt-0.5 font-sans text-[11px]">
              <span className="material-symbols-outlined text-[13px] text-primary flex-shrink-0">sync_alt</span>
              <span className="truncate">Verified high-intensity sprinting metrics across 80th-90th min</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
