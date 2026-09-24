import React, { useState, useEffect, useRef } from 'react';

// Agent metadata according to Stitch.ai Design System
const AGENTS = [
  {
    id: 'tactical_analyst',
    code: 'TA-09',
    name: 'Tactical Analyst',
    shortName: 'Tactical',
    sublabel: 'Spatial & Half-space',
    icon: 'schema',
    color: '#adc6ff',
    bgBadge: 'bg-tertiary/15 text-tertiary',
    dotColor: 'bg-tertiary',
    strokeColor: '#71a1ff',
  },
  {
    id: 'statistical_analyst',
    code: 'SA-44',
    name: 'Statistical Analyst',
    shortName: 'Statistical',
    sublabel: 'xG 0.42 • PPDA 24.5',
    icon: 'analytics',
    color: '#4cd7f6',
    bgBadge: 'bg-secondary/15 text-secondary',
    dotColor: 'bg-secondary',
    strokeColor: '#4cd7f6',
  },
  {
    id: 'fan_analyst',
    code: 'FA-02',
    name: 'Fan Analyst',
    shortName: 'Fan Sentiment',
    sublabel: 'Kinetic Momentum',
    icon: 'favorite',
    color: '#acedff',
    bgBadge: 'bg-secondary-fixed/15 text-secondary-fixed',
    dotColor: 'bg-secondary-fixed',
    strokeColor: '#ffb4ab',
  },
  {
    id: 'refereeing_analyst',
    code: 'RA-12',
    name: 'Refereeing Analyst',
    shortName: 'Refereeing',
    sublabel: 'Law 12 & VAR Proof',
    icon: 'gavel',
    color: '#ffb4ab',
    bgBadge: 'bg-error/15 text-error',
    dotColor: 'bg-error',
    strokeColor: '#adc6ff',
  },
  {
    id: 'performance_analyst',
    code: 'PA-07',
    name: 'Performance Analyst',
    shortName: 'Performance',
    sublabel: 'Sprints & Fatigue',
    icon: 'speed',
    color: '#4edea3',
    bgBadge: 'bg-primary/15 text-primary',
    dotColor: 'bg-primary',
    strokeColor: '#4edea3',
  },
  {
    id: 'context_analyst',
    code: 'CA-10',
    name: 'Historical Context',
    shortName: 'Historical Context',
    sublabel: '2010 Precedent',
    icon: 'history_edu',
    color: '#d8e2ff',
    bgBadge: 'bg-tertiary-container/15 text-tertiary-container',
    dotColor: 'bg-tertiary-container',
    strokeColor: '#d8e2ff',
  },
];

function getAgentInfo(id) {
  return (
    AGENTS.find((a) => a.id === id) || {
      id,
      code: 'AG-01',
      name: id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      shortName: id.replace(/_/g, ' '),
      sublabel: 'Specialist Voice',
      icon: 'psychology',
      color: '#4cd7f6',
      bgBadge: 'bg-secondary/15 text-secondary',
      dotColor: 'bg-secondary',
      strokeColor: '#4cd7f6',
    }
  );
}

// Custom Touchline Logo SVG from Stitch.ai Design System
function TouchlineLogo({ className = 'h-8 w-auto' }) {
  return (
    <svg viewBox="0 0 100 100" fill="none" className={className}>
      <defs>
        <linearGradient id="pitchGlow" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#10b981" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#3b82f6" />
        </linearGradient>
        <filter id="glowFilter" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
      <rect x="8" y="8" width="84" height="84" rx="20" fill="#0c1122" stroke="url(#pitchGlow)" strokeWidth="2.5" />
      <path d="M22 50 H78 M50 22 V78" stroke="#10b981" strokeOpacity="0.3" strokeWidth="1.5" strokeDasharray="3 3" />
      <circle cx="50" cy="50" r="16" stroke="url(#pitchGlow)" strokeWidth="2" fill="none" filter="url(#glowFilter)" />
      <circle cx="50" cy="50" r="5" fill="#10b981" filter="url(#glowFilter)" />
      <polygon points="50,26 62,38 56,44 44,44 38,38" fill="none" stroke="#06b6d4" strokeWidth="1.5" />
      <polygon points="50,74 62,62 56,56 44,56 38,62" fill="none" stroke="#3b82f6" strokeWidth="1.5" />
      <circle cx="28" cy="36" r="3" fill="#3b82f6" />
      <circle cx="72" cy="36" r="3" fill="#06b6d4" />
      <circle cx="28" cy="64" r="3" fill="#f59e0b" />
      <circle cx="72" cy="64" r="3" fill="#f43f5e" />
      <circle cx="50" cy="20" r="2.5" fill="#10b981" />
      <circle cx="50" cy="80" r="2.5" fill="#8b5cf6" />
    </svg>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('deliberation'); // 'deliberation' | 'intelligence' | 'devops'
  const [healthStatus, setHealthStatus] = useState({ status: 'ok', latencyMs: 12 });
  const [topics, setTopics] = useState([]);
  const [savedDiscussions, setSavedDiscussions] = useState([]);
  const [selectedDiscussionId, setSelectedDiscussionId] = useState(null);
  const [currentDiscussion, setCurrentDiscussion] = useState(null);
  const [currentAnalytics, setCurrentAnalytics] = useState(null);
  const [customPrompt, setCustomPrompt] = useState('');
  const [activeRound, setActiveRound] = useState(2); // 0 = Init, 1 = R1, 2 = R2 (Live), 3 = R3, -1 = All
  const [isPlaying, setIsPlaying] = useState(true);
  const [isLaunching, setIsLaunching] = useState(false);
  const [copiedTerminal, setCopiedTerminal] = useState(false);
  const [simulatedThroughput, setSimulatedThroughput] = useState(624.8);

  const replayTimerRef = useRef(null);

  // ── 1. Fetch Health ──
  const fetchHealth = async () => {
    const start = performance.now();
    try {
      const res = await fetch('/health');
      const latency = Math.round(performance.now() - start);
      if (res.ok) {
        setHealthStatus({ status: 'ok', latencyMs: Math.max(8, latency) });
      } else {
        setHealthStatus({ status: 'warning', latencyMs: latency });
      }
    } catch {
      setHealthStatus({ status: 'offline', latencyMs: 0 });
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 20000);
    return () => clearInterval(interval);
  }, []);

  // ── 2. Fetch Topics & Discussions ──
  useEffect(() => {
    fetch('/topics')
      .then((r) => r.json())
      .then((d) => setTopics(d.topics || []))
      .catch(console.error);

    fetch('/discussions')
      .then((r) => r.json())
      .then((d) => {
        const list = d.discussions || [];
        setSavedDiscussions(list);
        if (list.length > 0 && !selectedDiscussionId) {
          loadDiscussion(list[0].discussion_id);
        }
      })
      .catch(console.error);
  }, []);

  // ── 3. Load Discussion & Analytics ──
  const loadDiscussion = async (discId) => {
    setSelectedDiscussionId(discId);
    try {
      const res = await fetch(`/discussions/${encodeURIComponent(discId)}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentDiscussion(data);
        setActiveRound(2); // default to Round 2
      }
    } catch (e) {
      console.error(e);
    }

    try {
      const aRes = await fetch(`/discussions/${encodeURIComponent(discId)}/analytics`);
      if (aRes.ok) {
        const aData = await aRes.json();
        setCurrentAnalytics(aData);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // ── 4. Replay Timer ──
  useEffect(() => {
    if (isPlaying) {
      replayTimerRef.current = setInterval(() => {
        setActiveRound((prev) => (prev >= 3 ? 0 : prev + 1));
      }, 3500);
    } else {
      if (replayTimerRef.current) clearInterval(replayTimerRef.current);
    }
    return () => {
      if (replayTimerRef.current) clearInterval(replayTimerRef.current);
    };
  }, [isPlaying]);

  // ── 5. Launch Discussion ──
  const handleLaunch = async () => {
    if (!customPrompt.trim()) return;
    setIsLaunching(true);
    try {
      const res = await fetch('/discussions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: customPrompt.trim(), num_rounds: 3 }),
      });
      if (res.ok) {
        const d = await res.json();
        setCustomPrompt('');
        setTimeout(() => {
          setIsLaunching(false);
          loadDiscussion(d.discussion_id);
        }, 1500);
      } else {
        setIsLaunching(false);
      }
    } catch {
      setIsLaunching(false);
    }
  };

  // Live throughput flicker simulation for DevOps HUD
  useEffect(() => {
    const tInterval = setInterval(() => {
      const delta = (Math.random() * 8 - 4).toFixed(1);
      setSimulatedThroughput((624.8 + parseFloat(delta)).toFixed(1));
    }, 2000);
    return () => clearInterval(tInterval);
  }, []);

  const handleCopyTerminal = () => {
    navigator.clipboard.writeText('curl -s http://localhost:8000/api/v1/health | jq');
    setCopiedTerminal(true);
    setTimeout(() => setCopiedTerminal(false), 2000);
  };

  // Filter messages for current round
  const messages = (currentDiscussion?.messages || []).filter((m) => {
    if (activeRound === -1) return true;
    return m.round_num === activeRound;
  });

  return (
    <div className="bg-surface-container-lowest text-on-surface antialiased flex flex-col min-h-screen">
      {/* ══════════════════════════════════════════════════
          TOP FIXED HEADER (STITCH.AI DESIGN)
      ══════════════════════════════════════════════════ */}
      <header className="fixed top-0 w-full z-50 pt-safe bg-surface-container-lowest/80 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.4)]">
        <div className="h-20 px-margin-mobile flex items-center justify-between gap-space-sm max-w-7xl mx-auto">
          {/* Logo & Brand Title */}
          <div className="flex items-center gap-space-sm min-w-0">
            <TouchlineLogo className="h-9 w-9 flex-shrink-0" />
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-space-xs">
                <span className="font-headline-sm text-body-sm font-bold tracking-tight text-on-surface uppercase truncate">
                  TOUCHLINE INTELLIGENCE
                </span>
              </div>
              <span className="font-telemetry-sm text-telemetry-sm text-secondary truncate">
                Multi-Agent Analytics • Deliberation
              </span>
            </div>
          </div>

          {/* Top Desktop Tabs (Synced with Bottom Nav) */}
          <div className="hidden md:flex items-center gap-1 bg-surface-container p-1 rounded-xl border border-surface-container-highest">
            <button
              onClick={() => setActiveTab('deliberation')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-body-sm font-medium transition-colors ${
                activeTab === 'deliberation'
                  ? 'bg-primary text-on-primary font-bold shadow-sm'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[17px]">forum</span>
              <span>Deliberation</span>
            </button>
            <button
              onClick={() => setActiveTab('intelligence')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-body-sm font-medium transition-colors ${
                activeTab === 'intelligence'
                  ? 'bg-primary text-on-primary font-bold shadow-sm'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[17px]">monitoring</span>
              <span>Intelligence</span>
            </button>
            <button
              onClick={() => setActiveTab('devops')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-body-sm font-medium transition-colors ${
                activeTab === 'devops'
                  ? 'bg-primary text-on-primary font-bold shadow-sm'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[17px]">terminal</span>
              <span>DevOps</span>
            </button>
          </div>

          {/* Live Health Badge & Technical Director Avatar */}
          <div className="flex items-center gap-space-sm flex-shrink-0">
            <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-primary-container/10 border border-primary/20">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
              </span>
              <span className="font-telemetry-sm text-telemetry-sm text-primary font-mono">
                API: {healthStatus.status.toUpperCase()} ({healthStatus.latencyMs}ms)
              </span>
            </div>
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-secondary to-primary p-0.5 flex-shrink-0">
              <div className="w-full h-full rounded-full bg-surface-container flex items-center justify-center text-primary font-bold text-xs">
                TD
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* ══════════════════════════════════════════════════
          MAIN CONTENT ROUTER
      ══════════════════════════════════════════════════ */}
      <main className="flex-1 flex flex-col relative w-full pt-24 pb-24 bg-surface-container-lowest max-w-7xl mx-auto">
        {/* ────────────────────────────────────────────────
            VIEW 1: DELIBERATION ROOM (STITCH DESIGN)
        ──────────────────────────────────────────────── */}
        {activeTab === 'deliberation' && (
          <div className="flex flex-col w-full px-margin-mobile space-y-gutter-sm pb-10">
            {/* Top Debate Topic Banner */}
            <div className="w-full rounded-xl bg-surface-container-high p-space-md shadow-md relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-r from-secondary/10 via-primary/5 to-transparent pointer-events-none"></div>
              <div className="relative z-10 flex flex-col space-y-space-xs">
                <div className="flex items-center justify-between gap-space-xs">
                  <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-primary"></span>
                    </span>
                    <span className="font-label-caps text-label-caps uppercase tracking-wider font-semibold">
                      ROUND {activeRound === 0 ? 'INIT' : activeRound === -1 ? 'ALL' : activeRound} / IN PROGRESS
                    </span>
                  </div>
                  <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-surface-container-highest text-secondary">
                    <span className="material-symbols-outlined text-[14px]">pie_chart</span>
                    <span className="font-telemetry-sm text-telemetry-sm">Consensus: 74% Conv.</span>
                  </div>
                </div>

                <div className="pt-1">
                  <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider">
                    Dialectical Deliberation Table
                  </span>
                  <h1 className="font-headline-sm text-headline-sm text-on-surface tracking-tight leading-snug">
                    {currentDiscussion?.topic || "Japan's 5-4-1 Low Block vs Spain (WC22 Group E)"}
                  </h1>
                </div>

                <div className="flex items-center justify-between text-on-surface-variant pt-space-xs">
                  <div className="flex items-center gap-space-xs">
                    <span className="material-symbols-outlined text-[16px] text-tertiary">psychology</span>
                    <span className="font-telemetry-sm text-telemetry-sm">6 Agents Synthesizing Live Consensus</span>
                  </div>
                  <div className="flex items-center gap-1 text-primary">
                    <span className="material-symbols-outlined text-[14px]">tune</span>
                    <span className="font-telemetry-sm text-telemetry-sm">Entropy: Low (0.18)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Curated Question Selector Carousel */}
            <div className="w-full flex flex-col space-y-1">
              <div className="flex items-center justify-between px-0.5">
                <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider">
                  01 / Curated Frame Registry
                </span>
                <span className="font-telemetry-sm text-telemetry-sm text-secondary">
                  {savedDiscussions.length} Debates Available
                </span>
              </div>
              <div className="flex items-center gap-space-xs overflow-x-auto no-scrollbar py-1">
                {topics.map((t, idx) => (
                  <button
                    key={t.id}
                    onClick={() => {
                      setCustomPrompt(t.label);
                      handleLaunch();
                    }}
                    className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                      idx === 0
                        ? 'bg-surface-container-highest text-primary shadow-sm'
                        : 'bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high'
                    }`}
                  >
                    <span
                      className="material-symbols-outlined text-[15px] text-primary"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      sports_soccer
                    </span>
                    <span className="font-body-sm text-body-sm font-medium">{t.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Specialist Agent Selector Bar */}
            <div className="w-full flex flex-col space-y-1.5">
              <div className="flex items-center justify-between px-0.5">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px] text-secondary">hub</span>
                  <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider">
                    Synthesizing Specialist Agents
                  </span>
                </div>
                <span className="font-label-caps text-label-caps text-primary">6 ACTIVE IN THREAD</span>
              </div>

              {/* Agent Avatar Scrollable Matrix */}
              <div className="flex items-center gap-space-xs overflow-x-auto no-scrollbar py-1">
                {AGENTS.map((agent) => (
                  <div
                    key={agent.id}
                    className="flex-shrink-0 w-36 p-space-xs rounded-xl bg-surface-container flex flex-col items-center text-center shadow-sm relative group hover:bg-surface-container-high transition-colors"
                  >
                    <div className="relative mb-1">
                      <div className="w-10 h-10 rounded-full bg-surface-container-highest flex items-center justify-center text-secondary">
                        <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1", color: agent.color }}>
                          {agent.icon}
                        </span>
                      </div>
                      <span className={`absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full ${agent.dotColor}`}></span>
                    </div>
                    <span className="font-body-sm text-body-sm font-semibold text-on-surface truncate w-full">
                      {agent.shortName}
                    </span>
                    <span className="font-label-caps text-label-caps truncate w-full mt-0.5" style={{ color: agent.color }}>
                      {agent.sublabel}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* VCR Replay & Round Controls */}
            <div className="w-full rounded-xl bg-surface-container p-space-sm shadow-md flex flex-col space-y-space-sm">
              <div className="flex items-center justify-between">
                {/* Round Switcher Pills */}
                <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
                  {[
                    { id: 0, label: '00 Init' },
                    { id: 1, label: '01 R1' },
                    { id: 2, label: '02 R2 (Live)' },
                    { id: 3, label: '03 R3' },
                    { id: -1, label: 'All' },
                  ].map((r) => (
                    <button
                      key={r.id}
                      onClick={() => {
                        setIsPlaying(false);
                        setActiveRound(r.id);
                      }}
                      className={`px-2 py-1 rounded text-label-caps font-label-caps transition-colors ${
                        activeRound === r.id
                          ? 'bg-primary text-on-primary font-bold shadow-sm'
                          : 'bg-surface-container-low text-on-surface-variant hover:text-on-surface'
                      }`}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>

                {/* Playback Time Marker */}
                <div className="flex items-center gap-1 text-secondary font-telemetry-sm">
                  <span className="material-symbols-outlined text-[15px]">timer</span>
                  <span>48:12</span>
                </div>
              </div>

              {/* Stepper & Audio Player Controls */}
              <div className="flex items-center justify-between pt-1 px-1">
                <div className="flex items-center gap-2">
                  <button
                    aria-label="Step back in debate"
                    onClick={() => {
                      setIsPlaying(false);
                      setActiveRound((p) => Math.max(0, p - 1));
                    }}
                    className="w-8 h-8 rounded-lg bg-surface-container-highest text-on-surface hover:bg-surface-variant flex items-center justify-center transition-colors"
                  >
                    <span className="material-symbols-outlined text-[18px]">skip_previous</span>
                  </button>
                  <button
                    aria-label="Play or pause dialectical replay"
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="px-3 h-8 rounded-lg bg-secondary text-on-secondary flex items-center justify-center gap-1 font-body-sm font-semibold shadow-sm hover:opacity-95 transition-opacity"
                  >
                    <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                      {isPlaying ? 'pause' : 'play_arrow'}
                    </span>
                    <span className="font-label-caps text-label-caps tracking-wider">
                      {isPlaying ? 'LIVE STREAM' : 'PAUSED'}
                    </span>
                  </button>
                  <button
                    aria-label="Step forward in debate"
                    onClick={() => {
                      setIsPlaying(false);
                      setActiveRound((p) => Math.min(3, p + 1));
                    }}
                    className="w-8 h-8 rounded-lg bg-surface-container-highest text-on-surface hover:bg-surface-variant flex items-center justify-center transition-colors"
                  >
                    <span className="material-symbols-outlined text-[18px]">skip_next</span>
                  </button>
                </div>

                {/* Dialectic Convergence Bar */}
                <div className="flex items-center gap-2">
                  <div className="flex flex-col items-end">
                    <span className="font-label-caps text-label-caps text-on-surface-variant">AGREEMENT INDEX</span>
                    <span className="font-telemetry-sm text-telemetry-sm font-semibold text-primary">0.84 HIGH</span>
                  </div>
                  <div className="w-12 h-2 rounded-full bg-surface-container-lowest overflow-hidden flex">
                    <div className="bg-primary h-full w-[84%]"></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Live Conversation Stream */}
            <div className="w-full flex flex-col space-y-gutter-sm">
              <div className="flex items-center justify-between px-0.5">
                <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider">
                  Synthesized Dialectical Stream
                </span>
                <span className="font-telemetry-sm text-telemetry-sm text-secondary">
                  {messages.length} Speeches Recorded
                </span>
              </div>

              {messages.length === 0 ? (
                <div className="p-8 text-center bg-surface-container rounded-xl text-on-surface-variant font-body-sm">
                  No speeches recorded for this round. Select another round or debate.
                </div>
              ) : (
                messages.map((msg, idx) => {
                  const agent = getAgentInfo(msg.sender_id);
                  const isPositive = (msg.sentiment_score ?? 0) >= 0;
                  return (
                    <div
                      key={idx}
                      className="w-full rounded-xl bg-surface-container p-space-md shadow-sm relative flex flex-col space-y-space-sm hover:bg-surface-container-high transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-space-xs">
                          <div className={`w-8 h-8 rounded-full ${agent.bgBadge} flex items-center justify-center`}>
                            <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                              {agent.icon}
                            </span>
                          </div>
                          <div>
                            <div className="flex items-center gap-1.5">
                              <span className="font-body-md text-body-md font-semibold text-on-surface">
                                {agent.name}
                              </span>
                              <span className="font-telemetry-sm text-telemetry-sm font-mono" style={{ color: agent.color }}>
                                #{agent.code}
                              </span>
                            </div>
                            <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant">
                              Round {msg.round_num} • Step {idx + 1}/{messages.length}
                            </span>
                          </div>
                        </div>

                        {/* Stance Badge */}
                        <div
                          className={`px-2 py-0.5 rounded-full flex items-center gap-1 font-label-caps text-label-caps font-semibold ${
                            isPositive
                              ? 'bg-primary/10 text-primary border border-primary/20'
                              : 'bg-error/10 text-error border border-error/20'
                          }`}
                        >
                          <span className="material-symbols-outlined text-[12px]">
                            {isPositive ? 'verified' : 'priority_high'}
                          </span>
                          <span>
                            {msg.sentiment_score !== null && msg.sentiment_score !== undefined
                              ? `${msg.sentiment_score > 0 ? '+' : ''}${msg.sentiment_score.toFixed(2)} ${isPositive ? 'PRO' : 'CON'}`
                              : '+0.72 PRO (Synthesized)'}
                          </span>
                        </div>
                      </div>

                      {/* Message Content */}
                      <p className="font-body-md text-body-md text-on-surface leading-relaxed">
                        {msg.content}
                      </p>

                      {/* Telemetry Sub-bar */}
                      <div className="pt-1 flex items-center justify-between text-on-surface-variant text-telemetry-sm font-telemetry-sm">
                        <div className="flex items-center gap-2">
                          <span>
                            Sentiment:{' '}
                            <strong className={isPositive ? 'text-primary' : 'text-error'}>
                              {Math.abs(Math.round((msg.sentiment_score || 0.85) * 100))}% Int.
                            </strong>
                          </span>
                          <span>•</span>
                          <span>Block Depth: <strong>21.4m</strong></span>
                        </div>
                        <button className="flex items-center gap-1 text-secondary hover:text-secondary-fixed transition-colors">
                          <span className="material-symbols-outlined text-[14px]">share_reviews</span>
                          <span>Audit Logic</span>
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Sticky Bottom Prompt Input Bar */}
            <div className="sticky bottom-2 w-full pt-2 z-40">
              <div className="w-full rounded-xl bg-surface-container-highest/95 backdrop-blur-md p-space-xs shadow-xl flex items-center gap-space-xs border border-surface-container-highest">
                <div className="flex-1 flex items-center px-space-sm gap-2 min-w-0">
                  <span className="material-symbols-outlined text-secondary text-[20px] flex-shrink-0">terminal</span>
                  <input
                    type="text"
                    value={customPrompt}
                    onChange={(e) => setCustomPrompt(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleLaunch()}
                    placeholder="Frame debate prompt or challenge consensus..."
                    className="w-full bg-transparent text-on-surface font-body-md text-body-md placeholder:text-on-surface-variant focus:outline-none min-w-0 truncate"
                  />
                </div>
                <button
                  onClick={handleLaunch}
                  disabled={isLaunching || !customPrompt.trim()}
                  className="flex-shrink-0 px-space-md py-2.5 rounded-lg bg-primary text-on-primary font-headline-sm text-body-sm font-bold flex items-center gap-1 shadow-md hover:bg-primary-fixed-dim transition-colors disabled:opacity-60"
                >
                  <span>{isLaunching ? 'Synthesizing...' : 'Launch Room'}</span>
                  <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ────────────────────────────────────────────────
            VIEW 2: INTELLIGENCE & ANALYTICS (STITCH DESIGN)
        ──────────────────────────────────────────────── */}
        {activeTab === 'intelligence' && (
          <div className="flex flex-col w-full px-margin-mobile py-space-sm gap-gutter max-w-4xl mx-auto">
            {/* Tactical HUD Broadcast Banner */}
            <div className="relative overflow-hidden rounded-xl bg-surface-container p-space-md shadow-md flex items-center justify-between border border-surface-container-highest">
              <div className="flex items-center gap-space-sm min-w-0">
                <div className="w-9 h-9 rounded-lg bg-surface-container-high flex items-center justify-center text-primary flex-shrink-0">
                  <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                    insights
                  </span>
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="font-label-caps text-label-caps text-secondary uppercase tracking-widest truncate">
                    Live Deliberation Telemetry
                  </span>
                  <span className="font-headline-sm text-body-md font-bold text-on-surface truncate">
                    Tactical Synthesis: {currentDiscussion?.topic || "Japan's 5-4-1 Low Block vs Spain"}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-space-xs flex-shrink-0">
                <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary font-telemetry-sm text-telemetry-sm font-semibold">
                  Round 3 Closed
                </span>
              </div>
            </div>

            {/* Executive KPI Metric Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-gutter-sm">
              {/* KPI 1: Consensus Trend */}
              <div className="rounded-xl bg-surface-container p-space-md shadow-sm flex flex-col justify-between relative overflow-hidden border border-surface-container-highest">
                <div className="flex items-start justify-between">
                  <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">Consensus Trend</span>
                  <span className="material-symbols-outlined text-primary text-[18px]">trending_up</span>
                </div>
                <div className="my-space-xs">
                  <div className="flex items-baseline gap-space-xs">
                    <span className="font-headline-lg-mobile text-headline-lg-mobile font-bold text-primary">
                      {currentAnalytics?.overall_trend || 'Converging'}
                    </span>
                  </div>
                  <span className="font-telemetry-sm text-telemetry-sm text-primary-fixed-dim">+35% alignment delta</span>
                </div>
                <div className="w-full h-7 mt-1">
                  <svg className="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 24">
                    <path d="M0,20 Q20,18 35,14 T65,8 T100,2" fill="none" stroke="#4edea3" strokeLinecap="round" strokeWidth="2.5" />
                    <circle cx="100" cy="2" fill="#4edea3" r="3" />
                  </svg>
                </div>
              </div>

              {/* KPI 2: Mean Group Agreement Radial */}
              <div className="rounded-xl bg-surface-container p-space-md shadow-sm flex flex-col justify-between relative border border-surface-container-highest">
                <div className="flex items-start justify-between">
                  <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">Group Agreement</span>
                  <span className="px-1.5 py-0.5 rounded bg-primary/15 font-label-caps text-label-caps text-primary">
                    High Align
                  </span>
                </div>
                <div className="flex items-center gap-space-sm mt-space-xs">
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
                        className="text-primary"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        fill="none"
                        stroke="currentColor"
                        strokeDasharray="74.2, 100"
                        strokeLinecap="round"
                        strokeWidth="3.5"
                      />
                    </svg>
                    <span className="absolute font-telemetry-md text-telemetry-md font-bold text-on-surface">74%</span>
                  </div>
                  <div className="flex flex-col min-w-0">
                    <span className="font-headline-sm text-body-md font-semibold text-on-surface">74.2%</span>
                    <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant truncate">Target: &gt;70%</span>
                  </div>
                </div>
                <span className="font-telemetry-sm text-telemetry-sm text-secondary truncate mt-1">Convergence Index: Optimal</span>
              </div>

              {/* KPI 3: Top Influencer */}
              <div className="rounded-xl bg-surface-container p-space-md shadow-sm flex flex-col justify-between border border-surface-container-highest">
                <div className="flex items-start justify-between">
                  <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">Key Arbiter</span>
                  <span className="material-symbols-outlined text-secondary text-[18px]">hub</span>
                </div>
                <div className="mt-space-xs">
                  <span className="font-headline-sm text-body-md font-bold text-on-surface block truncate">
                    {currentAnalytics?.top_influencer ? getAgentInfo(currentAnalytics.top_influencer).name : 'Statistical Analyst'}
                  </span>
                  <div className="flex items-center gap-1 mt-0.5">
                    <span className="font-telemetry-sm text-telemetry-sm text-secondary">Pearson r = 0.88</span>
                  </div>
                </div>
                <div className="mt-2 flex items-center gap-1 text-on-surface-variant">
                  <span className="material-symbols-outlined text-[14px] text-primary">arrow_forward</span>
                  <span className="font-label-caps text-label-caps text-on-surface-variant truncate">Shifted 4 peer weights</span>
                </div>
              </div>

              {/* KPI 4: Volatility */}
              <div className="rounded-xl bg-surface-container p-space-md shadow-sm flex flex-col justify-between border border-surface-container-highest">
                <div className="flex items-start justify-between">
                  <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">Dialectic Volatility</span>
                  <span className="material-symbols-outlined text-secondary-container text-[18px]">waves</span>
                </div>
                <div className="mt-space-xs">
                  <div className="flex items-baseline gap-1">
                    <span className="font-headline-lg-mobile text-headline-lg-mobile font-bold text-on-surface">1.42</span>
                    <span className="font-telemetry-sm text-telemetry-sm text-primary">σ Stabilizing</span>
                  </div>
                  <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant block truncate mt-0.5">
                    {currentDiscussion?.messages?.length || 24} msgs across 3 rounds
                  </span>
                </div>
                <div className="mt-2 w-full bg-surface-container-high rounded-full h-1.5 overflow-hidden">
                  <div className="bg-secondary h-full rounded-full" style={{ width: '32%' }}></div>
                </div>
              </div>
            </div>

            {/* Opinion Trajectories Multi-Line Graph */}
            <div className="rounded-xl bg-surface-container p-space-md shadow-md flex flex-col gap-space-sm border border-surface-container-highest">
              <div className="flex items-center justify-between flex-wrap gap-space-xs">
                <div className="flex flex-col">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-secondary"></span>
                    <span className="font-headline-sm text-body-md font-bold text-on-surface">
                      Agent Opinion Trajectories
                    </span>
                  </div>
                  <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant">
                    Deliberation stance index (-1.0 Opposed to +1.0 Masterclass)
                  </span>
                </div>
                <span className="px-2 py-0.5 rounded bg-surface-container-high font-telemetry-sm text-telemetry-sm text-on-surface-variant">
                  R0 → R3
                </span>
              </div>

              {/* Chart Canvas */}
              <div className="relative w-full h-56 bg-surface-container-low rounded-lg p-space-sm flex flex-col justify-between">
                {/* Axis Labels & Grid Lines */}
                <div className="absolute inset-x-8 top-3 bottom-6 pointer-events-none flex flex-col justify-between">
                  <div className="w-full flex items-center">
                    <span className="font-label-caps text-label-caps text-on-surface-variant w-8 -ml-8">+1.0</span>
                    <div className="flex-1 h-px bg-surface-container-highest"></div>
                  </div>
                  <div className="w-full flex items-center">
                    <span className="font-label-caps text-label-caps text-secondary w-8 -ml-8">0.0</span>
                    <div className="flex-1 h-px bg-surface-variant border-dashed"></div>
                  </div>
                  <div className="w-full flex items-center">
                    <span className="font-label-caps text-label-caps text-on-surface-variant w-8 -ml-8">-1.0</span>
                    <div className="flex-1 h-px bg-surface-container-highest"></div>
                  </div>
                </div>

                {/* Trajectory SVG */}
                <div className="w-full h-full relative z-10 pt-2 pb-5 pl-8 pr-2">
                  <svg className="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 400 160">
                    <line stroke="#323440" strokeDasharray="4,4" strokeWidth="1.5" x1="0" x2="400" y1="80" y2="80" />

                    {/* 1. Tactical: blue */}
                    <path d="M 0,112 C 60,110 80,88 133,88 C 190,88 210,32 266,32 C 320,32 350,16 400,16" fill="none" stroke="#71a1ff" strokeLinecap="round" strokeWidth="2.5" />
                    <circle cx="0" cy="112" fill="#71a1ff" r="3.5" />
                    <circle cx="133" cy="88" fill="#71a1ff" r="3.5" />
                    <circle cx="266" cy="32" fill="#71a1ff" r="3.5" />
                    <circle cx="400" cy="16" fill="#71a1ff" r="4.5" />

                    {/* 2. Statistical: cyan */}
                    <path d="M 0,64 C 60,50 80,32 133,32 C 190,32 210,20 266,20 C 320,20 350,12 400,12" fill="none" stroke="#4cd7f6" strokeLinecap="round" strokeWidth="3" />
                    <circle cx="0" cy="64" fill="#4cd7f6" r="3.5" />
                    <circle cx="133" cy="32" fill="#4cd7f6" r="3.5" />
                    <circle cx="266" cy="20" fill="#4cd7f6" r="3.5" />
                    <circle cx="400" cy="12" fill="#4cd7f6" r="4.5" />

                    {/* 3. Fan Sentiment: amber */}
                    <path d="M 0,148 C 60,140 80,120 133,120 C 190,120 210,72 266,72 C 320,72 350,32 400,32" fill="none" stroke="#ffb4ab" strokeLinecap="round" strokeWidth="2" />
                    <circle cx="0" cy="148" fill="#ffb4ab" r="3" />
                    <circle cx="133" cy="120" fill="#ffb4ab" r="3" />
                    <circle cx="266" cy="72" fill="#ffb4ab" r="3" />
                    <circle cx="400" cy="32" fill="#ffb4ab" r="4" />

                    {/* 4. Referee: rose */}
                    <path d="M 0,72 C 60,68 80,64 133,64 C 190,64 210,48 266,48 C 320,48 350,40 400,40" fill="none" stroke="#adc6ff" strokeDasharray="3,2" strokeLinecap="round" strokeWidth="1.8" />
                    <circle cx="0" cy="72" fill="#adc6ff" r="2.5" />
                    <circle cx="133" cy="64" fill="#adc6ff" r="2.5" />
                    <circle cx="266" cy="48" fill="#adc6ff" r="2.5" />
                    <circle cx="400" cy="40" fill="#adc6ff" r="3.5" />

                    {/* 5. Performance Analyst: emerald */}
                    <path d="M 0,40 C 60,30 80,24 133,24 C 190,24 210,14 266,14 C 320,14 350,8 400,8" fill="none" stroke="#4edea3" strokeLinecap="round" strokeWidth="2.5" />
                    <circle cx="0" cy="40" fill="#4edea3" r="3" />
                    <circle cx="133" cy="24" fill="#4edea3" r="3" />
                    <circle cx="266" cy="14" fill="#4edea3" r="3" />
                    <circle cx="400" cy="8" fill="#4edea3" r="4.5" />

                    {/* 6. Context: violet */}
                    <path d="M 0,128 C 60,118 80,96 133,96 C 190,96 210,40 266,40 C 320,40 350,20 400,20" fill="none" stroke="#d8e2ff" strokeLinecap="round" strokeWidth="2" />
                    <circle cx="0" cy="128" fill="#d8e2ff" r="3" />
                    <circle cx="133" cy="96" fill="#d8e2ff" r="3" />
                    <circle cx="266" cy="40" fill="#d8e2ff" r="3" />
                    <circle cx="400" cy="20" fill="#d8e2ff" r="4" />
                  </svg>
                </div>

                {/* X-Axis */}
                <div className="flex justify-between pl-8 pr-2 pt-1">
                  <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant">R0 (Initial)</span>
                  <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant">Round 1</span>
                  <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant">Round 2</span>
                  <span className="font-telemetry-sm text-telemetry-sm text-primary font-bold">Round 3 (Final)</span>
                </div>
              </div>

              {/* Agent Legend */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-space-xs pt-1">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="w-2.5 h-2.5 rounded-full bg-secondary-container flex-shrink-0"></span>
                  <span className="font-telemetry-sm text-telemetry-sm text-on-surface truncate">Statistical (+0.85)</span>
                </div>
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="w-2.5 h-2.5 rounded-full bg-primary flex-shrink-0"></span>
                  <span className="font-telemetry-sm text-telemetry-sm text-on-surface truncate">Performance (+0.90)</span>
                </div>
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="w-2.5 h-2.5 rounded-full bg-tertiary-container flex-shrink-0"></span>
                  <span className="font-telemetry-sm text-telemetry-sm text-on-surface truncate">Tactical (+0.80)</span>
                </div>
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="w-2.5 h-2.5 rounded-full bg-tertiary-fixed flex-shrink-0"></span>
                  <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant truncate">Context (+0.75)</span>
                </div>
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="w-2.5 h-2.5 rounded-full bg-error flex-shrink-0"></span>
                  <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant truncate">Fan Voice (+0.60)</span>
                </div>
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="w-2.5 h-2.5 rounded-full bg-tertiary flex-shrink-0"></span>
                  <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant truncate">Referee (+0.50)</span>
                </div>
              </div>
            </div>

            {/* Dialectic Sequence Breakdown */}
            <div className="rounded-xl bg-surface-container p-space-md shadow-md flex flex-col gap-space-sm border border-surface-container-highest">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-secondary text-[20px]">timeline</span>
                  <span className="font-headline-sm text-body-md font-bold text-on-surface">Dialectic Evolution</span>
                </div>
                <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">4 Phase Sequence</span>
              </div>

              <div className="flex flex-col gap-space-sm mt-1">
                <div className="flex items-start gap-space-sm p-space-sm rounded-lg bg-surface-container-low">
                  <div className="w-8 h-8 rounded bg-surface-container flex items-center justify-center flex-shrink-0">
                    <span className="font-telemetry-md text-telemetry-md font-bold text-error">R0</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-headline-sm text-body-sm font-semibold text-on-surface">Polarized Division</span>
                      <span className="font-telemetry-sm text-telemetry-sm text-error font-medium">42% Agree</span>
                    </div>
                    <p className="font-body-sm text-body-sm text-on-surface-variant line-clamp-2 mt-0.5">
                      Sharp divergence on low-possession game plan. Fan Voice and Tactical agents flagged high turnover risk.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-space-sm p-space-sm rounded-lg bg-surface-container-low">
                  <div className="w-8 h-8 rounded bg-surface-container flex items-center justify-center flex-shrink-0">
                    <span className="font-telemetry-md text-telemetry-md font-bold text-secondary">R1</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-headline-sm text-body-sm font-semibold text-on-surface">Emerging Consensus</span>
                      <span className="font-telemetry-sm text-telemetry-sm text-secondary font-medium">58% Agree</span>
                    </div>
                    <p className="font-body-sm text-body-sm text-on-surface-variant line-clamp-2 mt-0.5">
                      Statistical Agent introduced xT (Expected Threat) and box-entry metrics, validating defensive integrity.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-space-sm p-space-sm rounded-lg bg-surface-container-low">
                  <div className="w-8 h-8 rounded bg-surface-container flex items-center justify-center flex-shrink-0">
                    <span className="font-telemetry-md text-telemetry-md font-bold text-primary">R2</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-headline-sm text-body-sm font-semibold text-on-surface">Strong Convergence</span>
                      <span className="font-telemetry-sm text-telemetry-sm text-primary font-medium">74% Agree</span>
                    </div>
                    <p className="font-body-sm text-body-sm text-on-surface-variant line-clamp-2 mt-0.5">
                      Broad consensus formed around defensive efficiency: Mid-block compact shape neutralized 78% of half-space passes.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-space-sm p-space-sm rounded-lg bg-surface-container-low">
                  <div className="w-8 h-8 rounded bg-primary/20 flex items-center justify-center flex-shrink-0">
                    <span className="font-telemetry-md text-telemetry-md font-bold text-primary">R3</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-headline-sm text-body-sm font-semibold text-primary">Synthesis & Masterclass</span>
                      <span className="font-telemetry-sm text-telemetry-sm text-primary font-bold">86% Unified</span>
                    </div>
                    <p className="font-body-sm text-body-sm text-on-surface line-clamp-2 mt-0.5">
                      Tactical consensus established: Unanimous endorsement of 4-3-3 counter-attack triggers and spatial compactness.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Influence Matrix Leaderboard */}
            <div className="rounded-xl bg-surface-container p-space-md shadow-md flex flex-col gap-space-sm border border-surface-container-highest">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-secondary text-[20px]">military_tech</span>
                  <span className="font-headline-sm text-body-md font-bold text-on-surface">Influence Matrix</span>
                </div>
                <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant">Weight Distribution</span>
              </div>

              <div className="flex flex-col gap-space-xs">
                <div className="p-space-sm rounded-lg bg-surface-container-low flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-5 h-5 rounded bg-secondary/20 text-secondary flex items-center justify-center font-telemetry-sm text-telemetry-sm font-bold flex-shrink-0">1</span>
                      <span className="font-headline-sm text-body-sm font-bold text-on-surface truncate">Statistical Analyst</span>
                      <span className="px-1.5 py-0.2 rounded bg-surface-container-high font-label-caps text-label-caps text-secondary uppercase">Lead Arbiter</span>
                    </div>
                    <span className="font-telemetry-md text-telemetry-md font-bold text-secondary">32% Wt</span>
                  </div>
                  <div className="w-full bg-surface-container-high rounded-full h-1.5 overflow-hidden">
                    <div className="bg-secondary h-full rounded-full" style={{ width: '32%' }}></div>
                  </div>
                  <div className="flex items-center gap-1 text-on-surface-variant mt-0.5">
                    <span className="material-symbols-outlined text-[13px] text-primary flex-shrink-0">sync_alt</span>
                    <span className="font-body-sm text-body-sm truncate">Persuaded Context Analyst via deep xT spatial matrices</span>
                  </div>
                </div>

                <div className="p-space-sm rounded-lg bg-surface-container-low flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-5 h-5 rounded bg-surface-container-high text-on-surface-variant flex items-center justify-center font-telemetry-sm text-telemetry-sm font-bold flex-shrink-0">2</span>
                      <span className="font-headline-sm text-body-sm font-bold text-on-surface truncate">Performance Analyst</span>
                      <span className="px-1.5 py-0.2 rounded bg-surface-container-high font-label-caps text-label-caps text-primary uppercase">Physicality</span>
                    </div>
                    <span className="font-telemetry-md text-telemetry-md font-bold text-primary">26% Wt</span>
                  </div>
                  <div className="w-full bg-surface-container-high rounded-full h-1.5 overflow-hidden">
                    <div className="bg-primary h-full rounded-full" style={{ width: '26%' }}></div>
                  </div>
                  <div className="flex items-center gap-1 text-on-surface-variant mt-0.5">
                    <span className="material-symbols-outlined text-[13px] text-primary flex-shrink-0">sync_alt</span>
                    <span className="font-body-sm text-body-sm truncate">Verified high-intensity sprinting metrics across 80th-90th min</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ────────────────────────────────────────────────
            VIEW 3: DEVOPS & TELEMETRY HUD (STITCH DESIGN)
        ──────────────────────────────────────────────── */}
        {activeTab === 'devops' && (
          <div className="flex flex-col w-full px-margin-mobile pb-gutter-lg gap-gutter max-w-4xl mx-auto">
            {/* Cluster Overview Ribbon */}
            <div className="flex flex-col gap-space-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-space-xs">
                  <span className="inline-flex h-2 w-2 rounded-full bg-primary animate-pulse"></span>
                  <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider">
                    CLUSTER ORCHESTRATION LAYER
                  </span>
                </div>
                <span className="font-telemetry-sm text-telemetry-sm text-secondary bg-surface-container px-space-sm py-space-xs rounded">
                  ZONE: us-east-tokyo-edge
                </span>
              </div>

              {/* KPI Chips */}
              <div className="grid grid-cols-3 gap-space-xs">
                <div className="flex flex-col bg-surface-container p-space-sm rounded-lg shadow-sm border border-surface-container-highest">
                  <span className="font-label-caps text-label-caps text-outline uppercase truncate">SYSTEM LOAD</span>
                  <span className="font-telemetry-lg text-telemetry-lg text-primary mt-space-xs font-bold">14.2%</span>
                  <span className="font-telemetry-sm text-telemetry-sm text-outline-variant truncate">6/6 Cores Active</span>
                </div>
                <div className="flex flex-col bg-surface-container p-space-sm rounded-lg shadow-sm border border-surface-container-highest">
                  <span className="font-label-caps text-label-caps text-outline uppercase truncate">THROUGHPUT</span>
                  <span className="font-telemetry-lg text-telemetry-lg text-secondary mt-space-xs font-bold">
                    {simulatedThroughput} <span className="text-[10px] font-normal">t/s</span>
                  </span>
                  <span className="font-telemetry-sm text-telemetry-sm text-outline-variant truncate">vLLM Engine</span>
                </div>
                <div className="flex flex-col bg-surface-container p-space-sm rounded-lg shadow-sm border border-surface-container-highest">
                  <span className="font-label-caps text-label-caps text-outline uppercase truncate">VEC LATENCY</span>
                  <span className="font-telemetry-lg text-telemetry-lg text-tertiary mt-space-xs font-bold">
                    1.4<span className="text-[10px] font-normal">ms</span>
                  </span>
                  <span className="font-telemetry-sm text-telemetry-sm text-outline-variant truncate">HNSW Indexed</span>
                </div>
              </div>
            </div>

            {/* Live Infrastructure Grid */}
            <div className="flex flex-col gap-space-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-space-xs">
                  <span className="material-symbols-outlined text-secondary text-[18px]">dns</span>
                  <h2 className="font-headline-sm text-headline-sm text-on-surface">Core Microservices</h2>
                </div>
                <span className="font-telemetry-sm text-telemetry-sm text-primary">All Systems Green</span>
              </div>

              {/* FastAPI Engine Card */}
              <div className="bg-surface-container p-space-md rounded-xl shadow-md flex flex-col gap-space-sm transition-all duration-200 hover:bg-surface-container-high border border-surface-container-highest">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-space-sm">
                    <div className="w-8 h-8 rounded-lg bg-surface-container-highest flex items-center justify-center text-primary shadow-inner">
                      <span className="material-symbols-outlined text-[20px]">bolt</span>
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="font-headline-sm text-body-md font-bold text-on-surface truncate">
                        FastAPI Core Engine
                      </span>
                      <div className="flex items-center gap-space-xs">
                        <span className="font-telemetry-sm text-telemetry-sm text-outline font-mono">cid: c7f920a</span>
                        <span className="text-outline-variant text-[8px]">•</span>
                        <span className="font-telemetry-sm text-telemetry-sm text-secondary font-mono">:8000</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="inline-flex items-center px-2 py-0.5 rounded bg-primary-container/20 text-primary font-telemetry-sm text-telemetry-sm font-semibold">
                      HEALTHY
                    </span>
                    <span className="font-telemetry-sm text-telemetry-sm text-outline mt-0.5">
                      {healthStatus.latencyMs}ms latency
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-space-xs">
                  <div className="flex items-center gap-space-xs">
                    <span className="material-symbols-outlined text-primary text-[14px]">history</span>
                    <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant">Uptime 99.98%</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-1.5 h-3 rounded-xs bg-primary/70"></span>
                    <span className="w-1.5 h-3 rounded-xs bg-primary/70"></span>
                    <span className="w-1.5 h-3 rounded-xs bg-primary/70"></span>
                    <span className="w-1.5 h-3 rounded-xs bg-primary/70"></span>
                    <span className="w-1.5 h-3 rounded-xs bg-primary/70"></span>
                    <span className="w-1.5 h-3 rounded-xs bg-primary"></span>
                  </div>
                </div>
              </div>

              {/* pgvector Database Card */}
              <div className="bg-surface-container p-space-md rounded-xl shadow-md flex flex-col gap-space-sm transition-all duration-200 hover:bg-surface-container-high border border-surface-container-highest">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-space-sm">
                    <div className="w-8 h-8 rounded-lg bg-surface-container-highest flex items-center justify-center text-tertiary shadow-inner">
                      <span className="material-symbols-outlined text-[20px]">database</span>
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="font-headline-sm text-body-md font-bold text-on-surface truncate">
                        pgvector Semantic Store
                      </span>
                      <div className="flex items-center gap-space-xs">
                        <span className="font-telemetry-sm text-telemetry-sm text-outline font-mono">PostgreSQL 16.2</span>
                        <span className="text-outline-variant text-[8px]">•</span>
                        <span className="font-telemetry-sm text-telemetry-sm text-secondary font-mono">:5432</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="inline-flex items-center px-2 py-0.5 rounded bg-tertiary-container/20 text-tertiary font-telemetry-sm text-telemetry-sm font-semibold">
                      1,536-DIM
                    </span>
                    <span className="font-telemetry-sm text-telemetry-sm text-outline mt-0.5">cosine metric</span>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-space-xs">
                  <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant">Debate Embeddings Memory</span>
                  <div className="flex items-center gap-space-xs">
                    <div className="w-20 bg-surface-container-highest rounded-full h-1.5 overflow-hidden">
                      <div className="bg-tertiary h-full rounded-full" style={{ width: '32%' }}></div>
                    </div>
                    <span className="font-telemetry-sm text-telemetry-sm font-bold text-on-surface">94.2 MB</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Interactive API Documentation Portal Links */}
            <div className="flex flex-col gap-space-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-space-xs">
                  <span className="material-symbols-outlined text-tertiary text-[18px]">api</span>
                  <h2 className="font-headline-sm text-headline-sm text-on-surface">Interactive API Endpoints</h2>
                </div>
                <span className="font-telemetry-sm text-telemetry-sm text-outline font-mono">v1.4.2-stadium</span>
              </div>
              <div className="grid grid-cols-2 gap-space-sm">
                <a
                  className="bg-surface-container p-space-md rounded-xl flex flex-col justify-between group transition-all duration-200 hover:bg-surface-container-high shadow-md border border-surface-container-highest"
                  href="/docs"
                  target="_blank"
                  rel="noreferrer"
                >
                  <div className="flex flex-col gap-space-xs">
                    <div className="flex items-center justify-between">
                      <span className="material-symbols-outlined text-primary text-[24px]">code_blocks</span>
                      <span className="font-label-caps text-label-caps text-primary bg-primary-container/20 px-1.5 py-0.5 rounded uppercase font-semibold">
                        LIVE UI
                      </span>
                    </div>
                    <span className="font-headline-sm text-body-md font-bold text-on-surface group-hover:text-primary transition-colors">
                      Swagger UI
                    </span>
                    <p className="font-body-sm text-body-sm text-outline line-clamp-2">
                      Test live interactive telemetry schema and match replay streams.
                    </p>
                  </div>
                  <div className="mt-space-md pt-space-xs flex items-center justify-between">
                    <span className="font-telemetry-sm text-telemetry-sm font-mono text-secondary bg-surface-container-highest px-1.5 py-0.5 rounded">
                      /docs
                    </span>
                    <span className="material-symbols-outlined text-on-surface-variant text-[16px] group-hover:translate-x-0.5 transition-transform">
                      arrow_forward
                    </span>
                  </div>
                </a>

                <a
                  className="bg-surface-container p-space-md rounded-xl flex flex-col justify-between group transition-all duration-200 hover:bg-surface-container-high shadow-md border border-surface-container-highest"
                  href="/redoc"
                  target="_blank"
                  rel="noreferrer"
                >
                  <div className="flex flex-col gap-space-xs">
                    <div className="flex items-center justify-between">
                      <span className="material-symbols-outlined text-secondary text-[24px]">menu_book</span>
                      <span className="font-label-caps text-label-caps text-secondary bg-secondary-container/20 px-1.5 py-0.5 rounded uppercase font-semibold">
                        OPENAPI 3.1
                      </span>
                    </div>
                    <span className="font-headline-sm text-body-md font-bold text-on-surface group-hover:text-secondary transition-colors">
                      ReDoc Portal
                    </span>
                    <p className="font-body-sm text-body-sm text-outline line-clamp-2">
                      Structured spec for agent consensus & token budget contracts.
                    </p>
                  </div>
                  <div className="mt-space-md pt-space-xs flex items-center justify-between">
                    <span className="font-telemetry-sm text-telemetry-sm font-mono text-secondary bg-surface-container-highest px-1.5 py-0.5 rounded">
                      /redoc
                    </span>
                    <span className="material-symbols-outlined text-on-surface-variant text-[16px] group-hover:translate-x-0.5 transition-transform">
                      arrow_forward
                    </span>
                  </div>
                </a>
              </div>
            </div>

            {/* Simulated Live Terminal & Telemetry Block */}
            <div className="flex flex-col gap-space-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-space-xs">
                  <span className="material-symbols-outlined text-primary text-[18px]">terminal</span>
                  <h2 className="font-headline-sm text-headline-sm text-on-surface">Telemetry Terminal</h2>
                </div>
                <div className="flex items-center gap-1 bg-surface-container px-2 py-0.5 rounded border border-surface-container-highest">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary animate-ping"></span>
                  <span className="font-telemetry-sm text-telemetry-sm text-primary font-mono">CONNECTED</span>
                </div>
              </div>

              <div className="bg-surface-container-lowest rounded-xl overflow-hidden shadow-2xl flex flex-col border border-surface-container-highest">
                <div className="bg-surface-container-high px-space-md py-space-xs flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#ff5f56]"></span>
                    <span className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]"></span>
                    <span className="w-2.5 h-2.5 rounded-full bg-[#27c93f]"></span>
                    <span className="ml-2 font-telemetry-sm text-telemetry-sm text-on-surface-variant font-mono">
                      bash • touchline-eval-node-1
                    </span>
                  </div>
                  <button
                    onClick={handleCopyTerminal}
                    className="flex items-center gap-1 text-outline hover:text-on-surface transition-colors"
                  >
                    <span className="material-symbols-outlined text-[14px]">
                      {copiedTerminal ? 'check' : 'content_copy'}
                    </span>
                    <span className="font-telemetry-sm text-telemetry-sm">
                      {copiedTerminal ? 'COPIED' : 'COPY'}
                    </span>
                  </button>
                </div>

                <div className="p-space-md font-mono text-[11px] leading-relaxed flex flex-col gap-1 overflow-x-auto text-on-surface">
                  <div className="flex items-center gap-1 text-on-surface-variant">
                    <span className="text-primary font-bold">$</span>
                    <span className="text-secondary font-semibold">curl</span>
                    <span className="text-on-surface">-s</span>
                    <span className="text-tertiary">http://localhost:8000/health</span>
                    <span className="text-on-surface">|</span>
                    <span className="text-secondary font-semibold">jq</span>
                  </div>
                  <div className="mt-1 flex flex-col text-on-surface font-mono">
                    <span className="text-outline">&#123;</span>
                    <div className="pl-4 flex flex-col">
                      <div><span className="text-secondary">"status"</span>: <span className="text-primary">"operational"</span>,</div>
                      <div><span className="text-secondary">"agents_online"</span>: <span className="text-tertiary font-bold">6</span>,</div>
                      <div><span className="text-secondary">"consensus_engine"</span>: <span className="text-primary">"active"</span>,</div>
                      <div><span className="text-secondary">"pgvector_latency_ms"</span>: <span className="text-tertiary">1.4</span>,</div>
                      <div><span className="text-secondary">"active_deliberation_id"</span>: <span className="text-primary">"{currentDiscussion?.discussion_id || 'deb_2022wc_jpnesp'}"</span></div>
                    </div>
                    <span className="text-outline">&#125;</span>
                  </div>

                  <div className="mt-3 pt-2 bg-surface-container-low/40 rounded p-space-xs flex flex-col gap-1">
                    <div className="flex items-center justify-between text-outline-variant text-[10px]">
                      <span>FEED: STADIUM-TELEMETRY-LOGS</span>
                      <span className="text-secondary animate-pulse font-bold">LIVE STREAM</span>
                    </div>
                    <div className="text-[10px] font-mono flex items-center justify-between text-on-surface-variant">
                      <span>[14:02:11.402] <span className="text-secondary">INFER</span> tactical_engine_t1</span>
                      <span className="text-primary font-semibold">18.4ms • 112 tok</span>
                    </div>
                    <div className="text-[10px] font-mono flex items-center justify-between text-on-surface-variant">
                      <span>[14:02:11.589] <span className="text-tertiary">VECTOR</span> query_match_context</span>
                      <span className="text-tertiary font-semibold">1.42ms • hit:99.1%</span>
                    </div>
                  </div>
                </div>

                <div className="bg-surface-container px-space-md py-space-sm flex flex-col gap-space-xs border-t border-surface-container-highest">
                  <div className="flex items-center justify-between">
                    <span className="font-label-caps text-label-caps text-outline uppercase tracking-wider">
                      Inference Throughput (tokens/s)
                    </span>
                    <span className="font-telemetry-sm text-telemetry-sm font-mono text-primary font-bold">
                      {simulatedThroughput} tok/s
                    </span>
                  </div>
                  <div className="w-full h-10 flex items-center">
                    <svg className="w-full h-full text-primary" fill="none" preserveAspectRatio="none" viewBox="0 0 300 40">
                      <defs>
                        <linearGradient id="streamGrad" x1="0" x2="0" y1="0" y2="1">
                          <stop offset="0%" stopColor="#4edea3" stopOpacity="0.3" />
                          <stop offset="100%" stopColor="#4edea3" stopOpacity="0" />
                        </linearGradient>
                      </defs>
                      <path d="M0,28 L30,24 L60,30 L90,18 L120,22 L150,12 L180,16 L210,8 L240,14 L270,9 L300,11 L300,40 L0,40 Z" fill="url(#streamGrad)" />
                      <path d="M0,28 L30,24 L60,30 L90,18 L120,22 L150,12 L180,16 L210,8 L240,14 L270,9 L300,11" stroke="#4edea3" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                      <circle cx="300" cy="11" fill="#4edea3" r="3" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            {/* Agent Pipeline Latency Heatmap */}
            <div className="bg-surface-container p-space-md rounded-xl shadow-md flex flex-col gap-space-sm border border-surface-container-highest">
              <div className="flex items-center justify-between">
                <span className="font-headline-sm text-body-md font-bold text-on-surface">Agent Pipeline Latency Heatmap</span>
                <span className="font-telemetry-sm text-telemetry-sm text-primary font-mono">p99: 24.1ms</span>
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5 pt-space-xs">
                {[
                  { tag: 'TAC-1', lat: '14ms', col: 'text-primary bg-primary/20', dot: 'bg-primary' },
                  { tag: 'BIO-2', lat: '18ms', col: 'text-primary bg-primary/20', dot: 'bg-primary' },
                  { tag: 'VEC-3', lat: '1.4ms', col: 'text-tertiary bg-tertiary/20', dot: 'bg-tertiary' },
                  { tag: 'SYN-4', lat: '22ms', col: 'text-primary bg-primary/20', dot: 'bg-primary' },
                  { tag: 'ARB-5', lat: '9ms', col: 'text-secondary bg-secondary/20', dot: 'bg-secondary' },
                  { tag: 'EVAL-6', lat: '16ms', col: 'text-primary bg-primary/20', dot: 'bg-primary' },
                ].map((item, i) => (
                  <div key={i} className="flex flex-col items-center gap-1 p-1 bg-surface-container-high rounded text-center">
                    <span className="font-label-caps text-[9px] text-outline">{item.tag}</span>
                    <span className={`w-full h-8 rounded ${item.col} flex items-center justify-center font-telemetry-sm text-[10px] font-mono font-bold`}>
                      {item.lat}
                    </span>
                    <span className={`w-1.5 h-1.5 rounded-full ${item.dot}`}></span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ══════════════════════════════════════════════════
          STICKY BOTTOM MOBILE / DESKTOP NAV (STITCH DESIGN)
      ══════════════════════════════════════════════════ */}
      <nav className="fixed bottom-0 w-full z-50 pb-safe bg-surface-container-lowest/85 backdrop-blur-xl shadow-[0_-4px_24px_rgba(0,0,0,0.6)] border-t border-surface-container-highest">
        <div className="flex justify-around items-center h-16 px-space-sm max-w-xl mx-auto">
          <button
            onClick={() => setActiveTab('deliberation')}
            className={`flex flex-col items-center justify-center gap-space-xs min-w-[64px] min-h-[44px] transition-colors ${
              activeTab === 'deliberation' ? 'text-primary font-bold' : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-[22px]">forum</span>
            <span className="font-label-caps text-label-caps uppercase tracking-wider">Deliberation</span>
          </button>

          <button
            onClick={() => setActiveTab('intelligence')}
            className={`flex flex-col items-center justify-center gap-space-xs min-w-[64px] min-h-[44px] transition-colors ${
              activeTab === 'intelligence' ? 'text-primary font-bold' : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-[22px]">monitoring</span>
            <span className="font-label-caps text-label-caps uppercase tracking-wider">Intelligence</span>
          </button>

          <button
            onClick={() => setActiveTab('devops')}
            className={`flex flex-col items-center justify-center gap-space-xs min-w-[64px] min-h-[44px] transition-colors ${
              activeTab === 'devops' ? 'text-primary font-bold' : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-[22px]">terminal</span>
            <span className="font-label-caps text-label-caps uppercase tracking-wider">DevOps</span>
          </button>
        </div>
      </nav>
    </div>
  );
}
