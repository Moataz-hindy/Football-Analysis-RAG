import React, { useState, useEffect } from 'react';
import AgentCommunicationPitch from './AgentCommunicationPitch';

/**
 * Command-Center Landing Page with Agent Communication Pitch hero.
 *
 * Hero specifications:
 * - Live AgentCommunicationPitch preview: 6 specialist agents, autoplaying
 *   sample passes (cursor stepped every 2.5s; pinned under reduced motion).
 * - Telemetry chip row under the pitch (xT, Block Depth, Passing Centrality).
 * - Live status topbar (FastAPI 8000, pgvector 1024-D, 6 specialist agents).
 * - Hero action suite: Initialize Workspace, Sign In, Quick Demo (Marwan - Scout).
 * - Deliberation simulator preview with consensus meter.
 * - Interactive Persona Profile Matrix.
 * - Multi-tenant security & architecture guarantee.
 * - Fully accessible with prefers-reduced-motion respect.
 */

const PROFILES_DATA = [
  {
    id: 'scout',
    name: 'Scout',
    badge: 'TALENT INTELLIGENCE',
    color: '#00f59b',
    icon: 'ph ph-binoculars',
    focus: 'Physical Ceilings & Transfer Valuation',
    headline: 'Executive Scouting Dossiers & 99th-Percentile Comps',
    description: 'Generates comprehensive player recruitment dossiers comparing physical attributes, tactical ceiling, and market transfer valuation metrics against peer percentiles.',
    kpis: ['98% Sprint Recovery Index', 'Top-5 League Peer Comp', 'Contract Value Delta: +$14M'],
  },
  {
    id: 'analyst',
    name: 'Tactical Analyst',
    badge: 'TACTICAL MATRIX',
    color: '#00d2ff',
    icon: 'ph ph-chart-line-up',
    focus: 'Expected Threat (xT) & Field Tilt',
    headline: 'Spatial Dominance & Markov Chain Passing Flows',
    description: 'Deconstructs spatial control, progressive carrying corridors, PPDA pressure metrics, and Markov-chain transition efficiencies across 90 minutes.',
    kpis: ['Field Tilt: 68.4%', 'Central PPDA: 7.2', 'xT Added/90: +0.64'],
  },
  {
    id: 'coach',
    name: 'Head Coach',
    badge: 'GAME MODEL',
    color: '#fb7185',
    icon: 'ph ph-strategy',
    focus: 'Block Spacing & Rest Defense',
    headline: 'Low-Block Infiltration & Transition Triggers',
    description: 'Pinpoints defensive line compression, counter-pressing traps, and overload-to-isolate mechanisms to unlock stubborn deep-block formations.',
    kpis: ['Block Spacing: 14.8m', 'Rest-Defense 3+2 Shape', 'Counter-Press Regain: 4.2s'],
  },
  {
    id: 'researcher',
    name: 'Researcher',
    badge: 'EVIDENCE RIGOR',
    color: '#a78bfa',
    icon: 'ph ph-brain',
    focus: 'Counterfactual Ablation & Citations',
    headline: 'Grounding Verification & Multi-Match Hypotheses',
    description: 'Validates agent deliberations against strict pgvector semantic chunks, performing counterfactual scenario ablations with verbatim tactical evidence.',
    kpis: ['100% Verbatim Citation', 'Zero Hallucination Anchor', '1024-D Vector Proximity'],
  },
  {
    id: 'fan',
    name: 'Passionate Fan',
    badge: 'NARRATIVE PULSE',
    color: '#fbbf24',
    icon: 'ph ph-flame',
    focus: 'Historical Rivalries & Momentums',
    headline: 'Clutch Performance & Dramatic Narrative Currents',
    description: 'Captures the emotional resonance, refereeing controversies, folklore narratives, and psychological turning points that define football heritage.',
    kpis: ['Momentum Shift Index: 89', 'Crowd Decibel Proxy', 'Historical Rivalry Weight'],
  },
];

// Static hero roster for the Agent Communication Pitch preview.
const HERO_AGENTS = [
  { id: 'tactical_analyst', name: 'Tactical', color: '#10b981' },
  { id: 'statistical_analyst', name: 'Statistical', color: '#38bdf8' },
  { id: 'performance_analyst', name: 'Performance', color: '#f43f5e' },
  { id: 'fan_analyst', name: 'Fan', color: '#ec4899' },
  { id: 'refereeing_analyst', name: 'Refereeing', color: '#f59e0b' },
  { id: 'context_analyst', name: 'Context', color: '#a78bfa' },
];

// Sample deliberation messages driving the landing autoplay (cursor 0 → 6).
const HERO_MESSAGES = [
  {
    round_num: 1,
    sender_id: 'tactical_analyst',
    recipient_ids: ['statistical_analyst'],
    content: 'Japan compresses into a 5-4-1 low block, conceding the flanks to force Spain wide.',
  },
  {
    round_num: 1,
    sender_id: 'statistical_analyst',
    recipient_ids: ['performance_analyst'],
    content: 'Spain generated 0.94 xT per width inversion, so wide overloads dominate their build-up.',
  },
  {
    round_num: 1,
    sender_id: 'performance_analyst',
    recipient_ids: ['fan_analyst'],
    content: 'Sprint-recovery data shows the wing-backs cannot sustain 18.2m block depth for a full match.',
  },
  {
    round_num: 1,
    sender_id: 'fan_analyst',
    recipient_ids: ['refereeing_analyst'],
    content: 'Fans expect a siege; sustained box pressure usually drags penalties out of deep blocks.',
  },
  {
    round_num: 1,
    sender_id: 'refereeing_analyst',
    recipient_ids: ['context_analyst'],
    content: 'Handball and holding calls rise sharply when defenders defend the box that deep.',
  },
  {
    round_num: 1,
    sender_id: 'context_analyst',
    recipient_ids: ['tactical_analyst'],
    content: 'Japan held a similar block against Spain in 2022 and won 2-1 on a counter and a set piece.',
  },
];

export default function LandingPage({
  onGetStarted,
  onSignIn,
  onExploreDemo,
  onDemoLogin,
}) {
  const [activeProfileTab, setActiveProfileTab] = useState('scout');
  const [simActiveTab, setSimActiveTab] = useState('dialogue');

  // Hero pitch autoplay: step the message cursor 0 → 6 every 2.5s (landing-only motion).
  const [pitchCursor, setPitchCursor] = useState(0);
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setPitchCursor(HERO_MESSAGES.length);
      return;
    }
    const timer = setInterval(() => {
      setPitchCursor((c) => (c >= HERO_MESSAGES.length ? 0 : c + 1));
    }, 2500);
    return () => clearInterval(timer);
  }, []);

  const selectedProfile = PROFILES_DATA.find((p) => p.id === activeProfileTab) || PROFILES_DATA[0];

  return (
    <div
      className="min-h-screen bg-[#040711] text-neutral-100 flex flex-col relative overflow-hidden font-sans selection:bg-[#00f59b]/30 selection:text-white"
    >
      {/* Background Ambient Glows */}
      <div className="absolute top-0 left-1/4 w-[680px] h-[680px] bg-gradient-to-br from-[#00f59b]/12 via-[#00d2ff]/8 to-transparent rounded-full blur-[160px] pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-5 w-[600px] h-[600px] bg-gradient-to-tl from-[#a78bfa]/12 via-[#00f59b]/6 to-transparent rounded-full blur-[170px] pointer-events-none"></div>

      {/* Cybernetic Tactical Pitch Grid Pattern */}
      <div
        className="absolute inset-0 opacity-[0.038] pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(to right, #00f59b 1px, transparent 1px), linear-gradient(to bottom, #00f59b 1px, transparent 1px)',
          backgroundSize: '44px 44px',
        }}
      ></div>

      {/* Live System Status Topbar */}
      <div className="relative z-30 bg-[#060a17]/95 border-b border-white/[0.07] px-6 py-2">
        <div className="max-w-7xl mx-auto flex items-center justify-between flex-wrap gap-2 text-[11px] font-mono">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-[#00f59b]">
              <span className="w-2 h-2 rounded-full bg-[#00f59b] animate-ping inline-block"></span>
              <span className="font-bold">FASTAPI :8000 LIVE</span>
            </span>
            <span className="text-neutral-600 hidden sm:inline">•</span>
            <span className="text-[#38bdf8] hidden sm:inline">PGVECTOR 1024-D EMBEDDINGS READY</span>
            <span className="text-neutral-600 hidden md:inline">•</span>
            <span className="text-neutral-400 hidden md:inline">6 SPECIALIST AGENTS ONLINE</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-neutral-400">TENANT ISOLATED: RLS SECURED</span>
            <span className="px-2 py-0.5 rounded bg-[#00f59b]/10 border border-[#00f59b]/30 text-[#00f59b] font-semibold text-[10px]">
              V2.4 TACTICAL
            </span>
          </div>
        </div>
      </div>


      {/* Hero Section */}
      <section className="relative z-10 max-w-7xl mx-auto w-full px-6 pt-12 pb-20 flex flex-col justify-center">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Column: Value Proposition & Hero Actions */}
          <div className="lg:col-span-7 flex flex-col space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#00f59b]/10 border border-[#00f59b]/35 w-fit">
              <span className="w-2 h-2 rounded-full bg-[#00f59b] animate-ping"></span>
              <span className="text-[11.5px] font-mono font-semibold tracking-wider text-[#00f59b] uppercase">
                6 Specialist Autonomous Personas • NetworkX Passing Pitch
              </span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.12]">
              Command multi-agent football debates on a{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00f59b] via-[#38bdf8] to-[#a78bfa]">
                live tactical pitch
              </span>
              .
            </h1>

            <p className="text-base sm:text-lg text-neutral-300 leading-relaxed max-w-2xl font-normal">
              Autonomous specialist personas clash over match tactics, grounded in pgvector 1024-D match embeddings.
              Arguments map dynamically as football passes across the pitch, tailored to your personal scouting profile.
            </p>

            {/* Action Suite */}
            <div className="flex items-center gap-3.5 flex-wrap pt-2">
              <button
                type="button"
                onClick={onGetStarted}
                className="px-7 py-3.5 rounded-xl text-[14.5px] font-bold bg-[#00f59b] text-black shadow-[0_0_26px_rgba(0,245,155,0.45)] hover:shadow-[0_0_38px_rgba(0,245,155,0.7)] hover:bg-[#34d399] transition-all flex items-center gap-2.5 active:scale-95 cursor-pointer"
              >
                <span>Initialize Workspace</span>
                <i className="ph ph-arrow-right font-bold text-base"></i>
              </button>

              <button
                type="button"
                onClick={onDemoLogin || onExploreDemo}
                className="px-6 py-3.5 rounded-xl text-[14px] font-medium bg-[#38bdf8]/10 hover:bg-[#38bdf8]/20 border border-[#38bdf8]/40 text-[#38bdf8] transition-all flex items-center gap-2 backdrop-blur-md cursor-pointer active:scale-95"
              >
                <i className="ph ph-lightning text-lg text-[#38bdf8]"></i>
                <span>Quick Demo (Marwan - Scout)</span>
              </button>

              <button
                type="button"
                onClick={onSignIn}
                className="px-5 py-3.5 rounded-xl text-[14px] font-medium bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-neutral-200 transition-all flex items-center gap-2 cursor-pointer"
              >
                <i className="ph ph-sign-in text-lg text-neutral-400"></i>
                <span>Sign In</span>
              </button>
            </div>

            {/* Micro Feature Badges */}
            <div className="pt-6 grid grid-cols-3 gap-4 border-t border-white/[0.08] max-w-lg">
              <div>
                <div className="font-mono text-xl font-bold text-[#00f59b]">6 Agents</div>
                <div className="text-[12px] text-neutral-400">Specialist Deliberation Roster</div>
              </div>
              <div>
                <div className="font-mono text-xl font-bold text-[#38bdf8]">1024-D</div>
                <div className="text-[12px] text-neutral-400">pgvector Semantic RAG</div>
              </div>
              <div>
                <div className="font-mono text-xl font-bold text-[#a78bfa]">NetworkX</div>
                <div className="text-[12px] text-neutral-400">Tactical Pitch Passing Graph</div>
              </div>
            </div>
          </div>

          {/* Right Column: Live Agent Communication Pitch */}
          <div className="lg:col-span-5 flex flex-col items-stretch space-y-4 select-none">
            <AgentCommunicationPitch
              agents={HERO_AGENTS}
              messages={HERO_MESSAGES}
              activeRound={-1}
              consensus={76}
              cursor={pitchCursor}
              playing={false}
            />
            {/* Telemetry chips row under the pitch card */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-[#09101d]/90 border border-[#00f59b]/40 px-3 py-2 rounded-xl">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#00f59b] animate-ping"></span>
                  <span className="font-mono text-[11px] font-bold text-[#00f59b]">xT 0.94</span>
                </div>
                <div className="text-[10px] text-neutral-300 font-mono mt-0.5">Central Overload</div>
              </div>
              <div className="bg-[#09101d]/90 border border-[#00d2ff]/40 px-3 py-2 rounded-xl">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#00d2ff]"></span>
                  <span className="font-mono text-[11px] font-bold text-[#00d2ff]">Block Depth 18.2m</span>
                </div>
                <div className="text-[10px] text-neutral-300 font-mono mt-0.5">Japan 5-4-1 Low Block</div>
              </div>
              <div className="bg-[#09101d]/90 border border-purple-500/40 px-3 py-2 rounded-xl">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                  <span className="font-mono text-[11px] font-bold text-purple-300">Centrality 88%</span>
                </div>
                <div className="text-[10px] text-neutral-300 font-mono mt-0.5">Flank Isolation</div>
              </div>
            </div>
          </div>
        </div>

        {/* Interactive Deliberation Simulator Preview Section */}
        <div className="mt-20 rounded-2xl bg-[#080d19]/90 border border-white/[0.08] p-6 lg:p-8 backdrop-blur-xl shadow-2xl">
          <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-white/[0.08] gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[11.5px] font-bold tracking-wider text-[#00f59b] uppercase">
                  SIMULATED ARENA DELIBERATION
                </span>
                <span className="px-2 py-0.5 rounded-full bg-white/[0.06] text-[10.5px] font-mono text-neutral-400">
                  ROUND 1 ARGUMENT CLASH
                </span>
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight mt-1">
                Argentina vs France 2022 • Tactical Neutralization of Tchouaméni
              </h2>
            </div>

            {/* Consensus Meter */}
            <div className="flex items-center gap-3 bg-[#040810] px-4 py-2.5 rounded-xl border border-white/[0.08]">
              <div className="flex flex-col">
                <span className="text-[10.5px] font-mono text-neutral-400 uppercase">Agent Alignment</span>
                <span className="font-mono text-lg font-bold text-[#00f59b]">76% Consensus</span>
              </div>
              <div className="w-24 h-2.5 bg-white/[0.08] rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#00f59b] to-[#00d2ff] w-[76%] rounded-full shadow-[0_0_10px_#00f59b]"></div>
              </div>
            </div>
          </div>

          {/* Dialogue Clash Demonstration */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6">
            {/* Speaker 1: Tactical Analyst */}
            <div className="rounded-xl bg-[#050a14] border border-[#10b981]/30 p-5 flex flex-col space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-full bg-[#10b981]/15 border border-[#10b981]/50 flex items-center justify-center text-[12px] font-bold text-[#10b981]">
                    T
                  </div>
                  <div>
                    <div className="text-[13.5px] font-bold text-white">Tactical Coach</div>
                    <div className="text-[10.5px] text-neutral-400 font-mono">Structural Strategy</div>
                  </div>
                </div>
                <span className="text-[10.5px] font-mono px-2 py-0.5 rounded bg-[#10b981]/10 text-[#10b981] border border-[#10b981]/30">
                  ROUND 1
                </span>
              </div>
              <p className="text-[13px] text-neutral-300 leading-relaxed">
                "Argentina's staggered 4-3-3 press severed France's central pivot through Tchouaméni in the first 45 minutes.
                By having Mac Allister shadow him on build-up while Di María pinned Koundé wide, Argentina isolated the French midfield and generated a +0.42 xT overload down the left channel."
              </p>
              <div className="pt-2 flex items-center gap-2 text-[11px] font-mono text-[#10b981]">
                <i className="ph ph-check-circle"></i>
                <span>Grounded in Tactical Pass Map & Lineup Data</span>
              </div>
            </div>

            {/* Speaker 2: Statistical Analyst */}
            <div className="rounded-xl bg-[#050a14] border border-[#00d2ff]/30 p-5 flex flex-col space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-full bg-[#00d2ff]/15 border border-[#00d2ff]/50 flex items-center justify-center text-[12px] font-bold text-[#00d2ff]">
                    S
                  </div>
                  <div>
                    <div className="text-[13.5px] font-bold text-white">Statistical Analyst</div>
                    <div className="text-[10.5px] text-neutral-400 font-mono">Empirical Verification</div>
                  </div>
                </div>
                <span className="text-[10.5px] font-mono px-2 py-0.5 rounded bg-[#00d2ff]/10 text-[#00d2ff] border border-[#00d2ff]/30">
                  COUNTER-POINT
                </span>
              </div>
              <p className="text-[13px] text-neutral-300 leading-relaxed">
                "Empirical data confirms the structural asphyxiation. Tchouaméni recorded only 19 touches in the first half with 0 progressive passes into zone 14. France's overall pass completion dropped to 64% in their own third, with their progressive carry distance reduced by 58% compared to the semi-final."
              </p>
              <div className="pt-2 flex items-center gap-2 text-[11px] font-mono text-[#00d2ff]">
                <i className="ph ph-chart-bar"></i>
                <span>1024-D Vector Match Chunk Proximity 0.912</span>
              </div>
            </div>
          </div>
        </div>

        {/* Personalized Profile Matrix Section */}
        <section className="mt-20 pt-10 border-t border-white/[0.08]">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <span className="font-mono text-[11.5px] font-bold tracking-wider text-[#00f59b] uppercase">
              PERSONALIZED SCOUTING MATRICES
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mt-1">
              Analytical lenses tuned to your football domain
            </h2>
            <p className="text-sm text-neutral-400 mt-2">
              Select your persona profile to adapt the deliberation depth, metric vocabulary, and executive scouting output.
            </p>
          </div>

          {/* Persona Switcher Tabs */}
          <div className="flex items-center justify-center gap-2 flex-wrap pb-8">
            {PROFILES_DATA.map((p) => {
              const active = p.id === activeProfileTab;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setActiveProfileTab(p.id)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-[13px] font-medium transition-all cursor-pointer ${
                    active
                      ? 'bg-white/[0.1] text-white border border-white/[0.2] shadow-lg'
                      : 'bg-white/[0.03] text-neutral-400 border border-transparent hover:text-white hover:bg-white/[0.06]'
                  }`}
                  style={active ? { borderColor: `${p.color}60` } : {}}
                >
                  <i className={`${p.icon} text-base`} style={{ color: p.color }}></i>
                  <span>{p.name}</span>
                </button>
              );
            })}
          </div>

          {/* Selected Profile Showcase Card */}
          <div className="max-w-4xl mx-auto rounded-2xl bg-[#080d19] border border-white/[0.09] p-6 sm:p-8 relative overflow-hidden shadow-2xl">
            <div
              className="absolute top-0 right-0 w-80 h-80 rounded-full blur-[100px] pointer-events-none opacity-20"
              style={{ backgroundColor: selectedProfile.color }}
            ></div>

            <div className="relative z-10 flex flex-col md:flex-row md:items-start justify-between gap-6">
              <div className="flex-1 space-y-4">
                <div className="flex items-center gap-2.5">
                  <span
                    className="px-2.5 py-0.5 rounded-full font-mono text-[10.5px] font-bold uppercase tracking-wider"
                    style={{
                      backgroundColor: `${selectedProfile.color}15`,
                      color: selectedProfile.color,
                      border: `1px solid ${selectedProfile.color}40`,
                    }}
                  >
                    {selectedProfile.badge}
                  </span>
                  <span className="text-neutral-400 text-[12px] font-mono">
                    Focus: {selectedProfile.focus}
                  </span>
                </div>

                <h3 className="text-xl sm:text-2xl font-bold text-white">
                  {selectedProfile.headline}
                </h3>

                <p className="text-sm text-neutral-300 leading-relaxed">
                  {selectedProfile.description}
                </p>

                {/* Key KPIs */}
                <div className="flex items-center gap-3 flex-wrap pt-2">
                  {selectedProfile.kpis.map((kpi, idx) => (
                    <div
                      key={idx}
                      className="px-3 py-1.5 rounded-lg bg-[#040810] border border-white/[0.08] text-[12px] font-mono text-neutral-200"
                    >
                      {kpi}
                    </div>
                  ))}
                </div>
              </div>

              <div className="md:w-64 flex flex-col justify-between p-5 rounded-xl bg-[#040810] border border-white/[0.08] space-y-4">
                <div className="text-[12px] font-mono text-neutral-400">
                  READY-TO-USE PRESET
                </div>
                <div className="text-sm font-semibold text-white">
                  Seed Account Available:
                  <div className="text-[#00f59b] font-mono text-[12px] mt-1">marwan@football.ai</div>
                </div>
                <button
                  type="button"
                  onClick={onDemoLogin || onExploreDemo}
                  className="w-full py-2.5 rounded-lg text-[12.5px] font-bold font-mono text-black transition-all hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
                  style={{ backgroundColor: selectedProfile.color }}
                >
                  LOAD {selectedProfile.name.toUpperCase()} DEMO
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Grid Section */}
        <section className="mt-20 pt-10 border-t border-white/[0.08]">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Card 1 */}
            <div className="rounded-2xl bg-[#080d19]/80 border border-white/[0.08] p-6 flex flex-col space-y-3 hover:border-[#00f59b]/40 transition-all group">
              <div className="w-10 h-10 rounded-xl bg-[#00f59b]/10 border border-[#00f59b]/30 flex items-center justify-center text-[#00f59b] group-hover:scale-110 transition-transform">
                <i className="ph ph-strategy text-xl"></i>
              </div>
              <h3 className="text-lg font-bold text-white">On-Demand Tactical Pitch Passing</h3>
              <p className="text-sm text-neutral-400 leading-relaxed">
                Watch arguments materialize as actual tactical passes across the pitch. Every click of Next or Previous drives a single, physics-modeled trajectory from speaker to recipient.
              </p>
            </div>

            {/* Card 2 */}
            <div className="rounded-2xl bg-[#080d19]/80 border border-white/[0.08] p-6 flex flex-col space-y-3 hover:border-[#00d2ff]/40 transition-all group">
              <div className="w-10 h-10 rounded-xl bg-[#00d2ff]/10 border border-[#00d2ff]/30 flex items-center justify-center text-[#00d2ff] group-hover:scale-110 transition-transform">
                <i className="ph ph-database text-xl"></i>
              </div>
              <h3 className="text-lg font-bold text-white">pgvector Semantic Match Memory</h3>
              <p className="text-sm text-neutral-400 leading-relaxed">
                Indexed in 1024-dimensional vector space. Retrieves exact tactical sequence moments, player tracking metrics, and historical matches with zero hallucination.
              </p>
            </div>

            {/* Card 3 */}
            <div className="rounded-2xl bg-[#080d19]/80 border border-white/[0.08] p-6 flex flex-col space-y-3 hover:border-purple-400/40 transition-all group">
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 group-hover:scale-110 transition-transform">
                <i className="ph ph-shield-check text-xl"></i>
              </div>
              <h3 className="text-lg font-bold text-white">Multi-Tenant Isolation & Zero Leakage</h3>
              <p className="text-sm text-neutral-400 leading-relaxed">
                Strict server-side tenant isolation guarantees each organization's scouting notes, custom persona prompts, and discussion histories remain strictly confidential.
              </p>
            </div>
          </div>
        </section>
      </section>

      {/* Embedded CSS Keyframes for Animations */}
      <style>{`
        @media (prefers-reduced-motion: reduce) {
          .animate-pulse, .animate-ping {
            animation: none !important;
          }
        }
      `}</style>
    </div>
  );
}
