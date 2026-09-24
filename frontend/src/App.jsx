import React, { useState, useEffect, useRef } from 'react';

// Agent configuration from Claude Nocturne design
const AGENTS = {
  tactical_analyst: {
    id: 'tactical_analyst',
    name: 'Tactical Analyst',
    focus: 'Half-space & Spatial',
    icon: 'ph ph-strategy',
    color: 'var(--color-accent)',
  },
  statistical_analyst: {
    id: 'statistical_analyst',
    name: 'Statistical Analyst',
    focus: 'xG & PPDA',
    icon: 'ph ph-chart-line-up',
    color: 'var(--color-accent-300)',
  },
  fan_analyst: {
    id: 'fan_analyst',
    name: 'Fan Sentiment',
    focus: 'Momentum & Psychological Surge',
    icon: 'ph ph-users-three',
    color: 'var(--color-neutral-300)',
  },
  refereeing_analyst: {
    id: 'refereeing_analyst',
    name: 'Refereeing Analyst',
    focus: 'Law 12 & VAR',
    icon: 'ph ph-flag',
    color: 'var(--color-neutral-400)',
  },
  performance_analyst: {
    id: 'performance_analyst',
    name: 'Performance Analyst',
    focus: 'Fatigue & Sprints',
    icon: 'ph ph-heartbeat',
    color: 'var(--color-accent-700)',
  },
  context_analyst: {
    id: 'context_analyst',
    name: 'Historical Context',
    focus: 'Precedents',
    icon: 'ph ph-books',
    color: 'var(--color-neutral-500)',
  },
};

function getAgentInfo(id) {
  if (AGENTS[id]) return AGENTS[id];
  const cleanId = id?.toLowerCase() || '';
  if (cleanId.includes('tact')) return AGENTS.tactical_analyst;
  if (cleanId.includes('stat')) return AGENTS.statistical_analyst;
  if (cleanId.includes('fan')) return AGENTS.fan_analyst;
  if (cleanId.includes('ref')) return AGENTS.refereeing_analyst;
  if (cleanId.includes('perf')) return AGENTS.performance_analyst;
  if (cleanId.includes('hist') || cleanId.includes('cont')) return AGENTS.context_analyst;

  return {
    id,
    name: id ? id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : 'Specialist Voice',
    focus: 'Tactical Ensemble',
    icon: 'ph ph-user',
    color: 'var(--color-accent-300)',
  };
}

// Curated default debates from Claude Nocturne design
const DEFAULT_HISTORY = [
  {
    discussion_id: 'wc22_jpn_esp',
    topic: "Japan's 5-4-1 low block vs Spain — can it hold for 90 minutes?",
    created_at: 'Sep 24, 2026 · 21:14',
    consensus: 91,
    msgs: 9,
    tags: ['Japan', 'Spain', 'World Cup'],
  },
  {
    discussion_id: 'epl_ars_mci',
    topic: 'Arsenal high-press vs City: who wins the first-phase battle?',
    created_at: 'Sep 22, 2026 · 18:02',
    consensus: 86,
    msgs: 18,
    tags: ['Arsenal', 'Man City', 'Premier League'],
  },
  {
    discussion_id: 'wc22_fra_arg',
    topic: 'France 2022 Final xG — was Argentina’s win deserved?',
    created_at: 'Sep 18, 2026 · 10:47',
    consensus: 73,
    msgs: 21,
    tags: ['France', 'Argentina', 'World Cup'],
  },
  {
    discussion_id: 'bun_bay_b04',
    topic: 'Tuchel’s back-three setup vs Leverkusen wing-backs',
    created_at: 'Sep 14, 2026 · 16:30',
    consensus: 82,
    msgs: 15,
    tags: ['Bayern', 'Leverkusen', 'Bundesliga'],
  },
  {
    discussion_id: 'ucl_int_rma',
    topic: 'Inter’s 3-5-2 rest defence against Madrid transitions',
    created_at: 'Sep 08, 2026 · 20:55',
    consensus: 68,
    msgs: 24,
    tags: ['Inter', 'Real Madrid', 'Champions League'],
  },
  {
    discussion_id: 'epl_bha_liv',
    topic: 'Brighton build-up vs Liverpool’s mid-block trap',
    created_at: 'Aug 28, 2026 · 12:10',
    consensus: 79,
    msgs: 12,
    tags: ['Brighton', 'Liverpool', 'Premier League'],
  },
];

// Fallback synthetic messages if discussion is initializing
const DEFAULT_MSGS = [
  {
    round_num: 1,
    sender_id: 'tactical_analyst',
    sentiment_score: 0.72,
    content:
      "Japan's back five is compressing the half-spaces well — Pedri receives with his back to goal 70% of the time. The block works as long as the wing-backs aren't dragged out by Spain's overlapping full-backs.",
    tele: [
      { k: 'Block Depth', v: '21.4m' },
      { k: 'Half-space entries', v: '4' },
    ],
  },
  {
    round_num: 1,
    sender_id: 'statistical_analyst',
    sentiment_score: -0.4,
    content:
      'The numbers disagree with the eye test. Spain have generated 1.62 xG from cut-backs alone, and a PPDA of 18.3 means Japan are letting Spain circulate unchallenged.',
    tele: [
      { k: 'xG against', v: '1.62' },
      { k: 'PPDA', v: '18.3' },
    ],
  },
  {
    round_num: 1,
    sender_id: 'performance_analyst',
    sentiment_score: -0.25,
    content:
      "Japan's midfield three have covered 4.1km more than Spain's in the first half. Sprint counts are already dropping — the block will stretch after the 65th minute.",
    tele: [
      { k: 'Distance delta', v: '+4.1km' },
      { k: 'Sprints', v: '−18%' },
    ],
  },
  {
    round_num: 2,
    sender_id: 'context_analyst',
    sentiment_score: 0.55,
    content:
      'Precedent favours Japan. In 2022 they beat Germany and Spain from a deep block, then switched to a front-foot press after the break — the low block was a phase, not the plan.',
    tele: [
      { k: 'Precedents', v: '3' },
      { k: 'Win rate', v: '67%' },
    ],
  },
  {
    round_num: 2,
    sender_id: 'refereeing_analyst',
    sentiment_score: 0.1,
    content:
      "Deep blocks invite contact in the box. Two of Spain's penalty shouts came from wing-back recovery runs — under Law 12, Japan are one mistimed challenge from conceding.",
    tele: [
      { k: 'VAR reviews', v: '2' },
      { k: 'Fouls in box', v: '3' },
    ],
  },
  {
    round_num: 2,
    sender_id: 'fan_analyst',
    sentiment_score: 0.64,
    content:
      'Momentum shifted when Japan went direct. Sentiment surged 22 points in five minutes — this squad feeds off defending as a collective.',
    tele: [
      { k: 'Sentiment', v: '88%' },
      { k: 'Surge', v: '+22' },
    ],
  },
  {
    round_num: 3,
    sender_id: 'statistical_analyst',
    sentiment_score: 0.31,
    content:
      "Revised: once Japan drop the line 3m deeper, Spain's cut-back xG falls to 0.08 per entry. The block can hold — if it stays compact under 25m.",
    tele: [
      { k: 'xG per entry', v: '0.08' },
      { k: 'Block Depth', v: '18.2m' },
    ],
  },
  {
    round_num: 3,
    sender_id: 'performance_analyst',
    sentiment_score: 0.2,
    content:
      'Agreed, with one condition: fresh wing-backs by the hour. Substitution timing is the whole plan.',
    tele: [{ k: 'Sub window', v: "58–62'" }],
  },
  {
    round_num: 3,
    sender_id: 'tactical_analyst',
    sentiment_score: 0.81,
    content:
      "Consensus position: the 5-4-1 holds for 60 minutes, then transitions to a 5-2-3 counter-press with fresh wide legs. Spain's possession becomes the trap.",
    tele: [
      { k: 'Alignment', v: '91%' },
      { k: 'Transition trigger', v: "60'" },
    ],
  },
];

// SVG math helpers for trajectories
const X = (i) => 40 + i * (580 / 3);
const Y = (v) => 130 - v * 110;
const smoothPath = (pts) =>
  pts
    .map((v, i) =>
      i === 0
        ? `M${X(0)},${Y(v)}`
        : `C${(X(i - 1) + X(i)) / 2},${Y(pts[i - 1])} ${(X(i - 1) + X(i)) / 2},${Y(v)} ${X(i)},${Y(v)}`
    )
    .join(' ');

export default function App() {
  const [tab, setTab] = useState('arena'); // 'arena' | 'history' | 'intel' | 'devops'
  const [query, setQuery] = useState('');
  const [topic, setTopic] = useState(DEFAULT_HISTORY[0].topic);
  const [cursor, setCursor] = useState(6);
  const [playing, setPlaying] = useState(false);
  const [searchHistory, setSearchHistory] = useState('');
  const [hoverAgent, setHoverAgent] = useState(null);
  const [copied, setCopied] = useState(false);

  // Live Backend State
  const [healthStatus, setHealthStatus] = useState({ status: 'ok', latencyMs: 12 });
  const [topicsList, setTopicsList] = useState([]);
  const [savedDiscussions, setSavedDiscussions] = useState([]);
  const [currentDiscussion, setCurrentDiscussion] = useState(null);
  const [currentAnalytics, setCurrentAnalytics] = useState(null);
  const [isStarting, setIsStarting] = useState(false);

  const timerRef = useRef(null);

  // 1. Live Health Check
  const fetchHealth = async () => {
    const start = performance.now();
    try {
      const res = await fetch('/health');
      const latency = Math.round(performance.now() - start);
      if (res.ok) {
        setHealthStatus({ status: 'ok', latencyMs: Math.max(6, latency) });
      } else {
        setHealthStatus({ status: 'warn', latencyMs: latency });
      }
    } catch {
      setHealthStatus({ status: 'offline', latencyMs: 0 });
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 25000);
    return () => clearInterval(interval);
  }, []);

  // 2. Fetch Topics & Saved Discussions
  useEffect(() => {
    fetch('/topics')
      .then((r) => r.json())
      .then((d) => setTopicsList(d.topics || []))
      .catch(console.error);

    fetch('/discussions')
      .then((r) => r.json())
      .then((d) => {
        const list = d.discussions || [];
        setSavedDiscussions(list);
        if (list.length > 0) {
          loadDiscussionById(list[0].discussion_id);
        }
      })
      .catch(console.error);
  }, []);

  // 3. Load Discussion by ID
  const loadDiscussionById = async (discId) => {
    pause();
    try {
      const res = await fetch(`/discussions/${encodeURIComponent(discId)}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentDiscussion(data);
        setTopic(data.topic);
        const total = (data.messages || []).length;
        setCursor(total > 0 ? total : 6);
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

  // 4. Play / Pause Streaming Stepper
  const play = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    const msgsList = currentDiscussion?.messages?.length ? currentDiscussion.messages : DEFAULT_MSGS;
    if (cursor >= msgsList.length) setCursor(0);
    setPlaying(true);

    timerRef.current = setInterval(() => {
      setCursor((prev) => {
        const next = prev + 1;
        if (next >= msgsList.length) {
          clearInterval(timerRef.current);
          setPlaying(false);
          return msgsList.length;
        }
        return next;
      });
    }, 1800);
  };

  const pause = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setPlaying(false);
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // 5. Start New Deliberation
  const handleStart = async (customText) => {
    const prompt = (customText || query || topic).trim();
    if (!prompt) return;
    pause();
    setIsStarting(true);
    setTopic(prompt);
    setTab('arena');
    setCursor(0);

    try {
      const res = await fetch('/discussions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: prompt, num_rounds: 3 }),
      });
      if (res.ok) {
        const d = await res.json();
        setQuery('');
        setTimeout(() => {
          setIsStarting(false);
          loadDiscussionById(d.discussion_id);
          play();
        }, 1200);
      } else {
        setIsStarting(false);
        play();
      }
    } catch {
      setIsStarting(false);
      play();
    }
  };

  // Copy Terminal Command
  const handleCopy = () => {
    navigator.clipboard?.writeText('curl http://localhost:8000/health | jq');
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  // Compute Active Messages & Consensus
  const rawMsgs = currentDiscussion?.messages?.length ? currentDiscussion.messages : DEFAULT_MSGS;
  const currentMsg = cursor > 0 && cursor <= rawMsgs.length ? rawMsgs[cursor - 1] : rawMsgs[0];
  const activeRound = currentMsg?.round_num || 1;
  const consensusList = [54, 78, 91];
  const consensus = cursor === 0 ? 0 : consensusList[activeRound - 1] || 85;

  const nextAgentId = cursor < rawMsgs.length ? rawMsgs[cursor]?.sender_id : null;
  const lastAgentId = cursor > 0 ? rawMsgs[cursor - 1]?.sender_id : null;
  const spokenSet = new Set(rawMsgs.slice(0, cursor).map((m) => m.sender_id));

  // Trajectories Data
  const trajectories = {
    tactical_analyst: [0.4, 0.72, 0.75, 0.81],
    statistical_analyst: [-0.2, -0.4, -0.1, 0.31],
    fan_analyst: [0.5, 0.6, 0.64, 0.7],
    refereeing_analyst: [0, -0.1, 0.1, 0.15],
    performance_analyst: [0, -0.25, -0.1, 0.2],
    context_analyst: [0.3, 0.4, 0.55, 0.6],
  };

  // Influence Data
  const influence = [
    { id: 'tactical_analyst', pct: 34 },
    { id: 'statistical_analyst', pct: 24 },
    { id: 'context_analyst', pct: 16 },
    { id: 'fan_analyst', pct: 12 },
    { id: 'performance_analyst', pct: 9 },
    { id: 'refereeing_analyst', pct: 5 },
  ];

  // Combined History List (Live + Default Curated)
  const combinedHistory = [
    ...savedDiscussions.map((d) => ({
      discussion_id: d.discussion_id,
      topic: d.topic,
      created_at: new Date(d.created_at || Date.now()).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }),
      consensus: 88,
      msgs: d.message_count || 18,
      tags: ['Live Debate', 'Analyzed'],
    })),
    ...DEFAULT_HISTORY.filter(
      (dh) => !savedDiscussions.some((sd) => sd.topic.toLowerCase() === dh.topic.toLowerCase())
    ),
  ];

  // Filtered History
  const qSearch = searchHistory.trim().toLowerCase();
  const filteredHistory = combinedHistory.filter(
    (h) => !qSearch || `${h.topic} ${h.tags.join(' ')} ${h.created_at}`.toLowerCase().includes(qSearch)
  );

  return (
    <div
      style={{
        position: 'relative',
        minHeight: '100vh',
        overflowX: 'hidden',
        background:
          'radial-gradient(900px 520px at 12% -8%, color-mix(in srgb, var(--color-accent) 22%, transparent), transparent 70%), radial-gradient(760px 480px at 96% 4%, color-mix(in srgb, var(--color-accent-700) 30%, transparent), transparent 70%), linear-gradient(180deg, var(--color-bg), color-mix(in srgb, var(--color-bg) 80%, black))',
      }}
    >
      {/* ══════════════════════════════════════════════════
          TOP FROSTED HEADER (CLAUDE NOCTURNE DESIGN)
      ══════════════════════════════════════════════════ */}
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 20,
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          background: 'color-mix(in srgb, var(--color-bg) 62%, transparent)',
          borderBottom: '1px solid var(--color-divider)',
        }}
      >
        <div
          style={{
            maxWidth: '1120px',
            margin: '0 auto',
            padding: '14px 24px',
            display: 'flex',
            alignItems: 'center',
            gap: '24px',
            flexWrap: 'wrap',
          }}
        >
          {/* Logo & Platform Name */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-accent)',
                display: 'grid',
                placeItems: 'center',
                color: 'var(--color-accent-300)',
                boxShadow: '0 0 18px color-mix(in srgb, var(--color-accent) 35%, transparent)',
              }}
            >
              <i className="ph ph-soccer-ball" style={{ fontSize: '19px' }}></i>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
              <span
                style={{
                  fontFamily: 'var(--font-heading)',
                  fontWeight: 600,
                  fontSize: '15px',
                  color: 'var(--color-neutral-100)',
                  letterSpacing: '-0.01em',
                }}
              >
                Touchline Intelligence
              </span>
              <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)' }}>
                Multi-Agent Tactical Deliberation
              </span>
            </div>
          </div>

          {/* Navigation Tabs (Arena, History, Intelligence, DevOps) */}
          <nav
            style={{
              display: 'flex',
              gap: '4px',
              padding: '4px',
              borderRadius: 'var(--radius-lg)',
              background: 'color-mix(in srgb, var(--color-surface) 55%, transparent)',
              border: '1px solid var(--color-divider)',
              marginLeft: 'auto',
            }}
          >
            {[
              { id: 'arena', label: 'Arena', icon: 'ph ph-chats-teardrop' },
              { id: 'history', label: 'History', icon: 'ph ph-clock-counter-clockwise' },
              { id: 'intel', label: 'Intelligence', icon: 'ph ph-chart-polar' },
              { id: 'devops', label: 'DevOps', icon: 'ph ph-cpu' },
            ].map((t) => {
              const on = tab === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '7px',
                    padding: '7px 14px',
                    borderRadius: 'var(--radius-md)',
                    border: on ? '1px solid color-mix(in srgb, var(--color-accent) 55%, transparent)' : '1px solid transparent',
                    background: on ? 'color-mix(in srgb, var(--color-accent) 14%, transparent)' : 'transparent',
                    color: on ? 'var(--color-accent-100)' : 'var(--color-neutral-400)',
                    font: '500 13px var(--font-body)',
                    cursor: 'pointer',
                    transition: 'all .15s ease',
                  }}
                >
                  <i className={t.icon} style={{ fontSize: '15px' }}></i>
                  {t.label}
                </button>
              );
            })}
          </nav>

          {/* Live API Latency Badge */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '7px',
              padding: '5px 11px',
              borderRadius: '999px',
              border: '1px solid var(--color-divider)',
              fontSize: '12px',
              color: 'var(--color-neutral-400)',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: 'var(--color-accent)',
                boxShadow: '0 0 8px var(--color-accent)',
              }}
            ></span>
            API: {healthStatus.status.toUpperCase()} ({healthStatus.latencyMs}ms)
          </div>
        </div>
      </header>

      {/* ══════════════════════════════════════════════════
          MAIN CONTENT AREA
      ══════════════════════════════════════════════════ */}
      <main style={{ maxWidth: '1120px', margin: '0 auto', padding: '40px 24px 80px' }}>
        {/* ────────────────────────────────────────────────
            TAB 1: ARENA (DELIBERATION ROOM)
        ──────────────────────────────────────────────── */}
        {tab === 'arena' && (
          <section style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
            {/* Hero Heading */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxWidth: '720px' }}>
              <h1
                style={{
                  margin: 0,
                  fontFamily: 'var(--font-heading)',
                  fontWeight: 600,
                  fontSize: 'clamp(28px, 4vw, 40px)',
                  lineHeight: 1.1,
                  letterSpacing: '-0.02em',
                  color: 'var(--color-neutral-100)',
                  textWrap: 'balance',
                }}
              >
                Six specialist agents debate your tactical question — and converge on an answer.
              </h1>
              <p
                style={{
                  margin: 0,
                  fontSize: '15px',
                  lineHeight: 1.55,
                  color: 'var(--color-neutral-400)',
                  textWrap: 'pretty',
                }}
              >
                Ask about a match, a system or a matchup. Watch the argument unfold round by round.
              </p>
            </div>

            {/* Glassmorphic Command Input Bar */}
            <div
              style={{
                padding: '18px',
                borderRadius: 'var(--radius-lg)',
                background: 'color-mix(in srgb, var(--color-surface) 60%, transparent)',
                backdropFilter: 'blur(24px)',
                WebkitBackdropFilter: 'blur(24px)',
                border: '1px solid color-mix(in srgb, var(--color-accent) 40%, var(--color-divider))',
                boxShadow:
                  '0 0 0 4px color-mix(in srgb, var(--color-accent) 7%, transparent), 0 18px 48px rgba(0,0,0,.45)',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                <div
                  style={{
                    flex: '1 1 320px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '0 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'color-mix(in srgb, var(--color-bg) 70%, transparent)',
                    border: '1px solid var(--color-divider)',
                    minWidth: 0,
                  }}
                >
                  <i className="ph ph-magnifying-glass" style={{ fontSize: '18px', color: 'var(--color-neutral-500)' }}></i>
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleStart()}
                    placeholder="Ask tactical question or analyze match... (e.g. Japan's 5-4-1 low block vs Spain)"
                    style={{
                      flex: 1,
                      minWidth: 0,
                      height: '48px',
                      border: 0,
                      outline: 0,
                      background: 'transparent',
                      color: 'var(--color-neutral-100)',
                      font: '400 15px var(--font-body)',
                    }}
                  />
                </div>
                <button
                  className="btn btn-primary"
                  onClick={() => handleStart()}
                  disabled={isStarting}
                  style={{
                    height: '50px',
                    padding: '0 22px',
                    fontSize: '14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    boxShadow: '0 0 22px color-mix(in srgb, var(--color-accent) 30%, transparent)',
                  }}
                >
                  <i className="ph ph-play-circle" style={{ fontSize: '18px' }}></i>
                  {isStarting ? 'Synthesizing...' : 'Start Deliberation'}
                </button>
              </div>

              {/* Try Quick-Start Chips */}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)', marginRight: '4px' }}>Try</span>
                {(topicsList.length > 0
                  ? topicsList.slice(0, 3).map((t) => t.label)
                  : ['Arsenal high-press vs City', 'Japan 5-4-1 vs Spain', 'Tuchel setup vs Leverkusen']
                ).map((label, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setQuery(label);
                      handleStart(label);
                    }}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '999px',
                      border: '1px solid var(--color-divider)',
                      background: 'transparent',
                      color: 'var(--color-neutral-300)',
                      font: '500 12.5px var(--font-body)',
                      cursor: 'pointer',
                      transition: 'all .15s ease',
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Active Deliberation Glass Container */}
            <div
              style={{
                padding: '22px',
                borderRadius: 'var(--radius-lg)',
                background: 'color-mix(in srgb, var(--color-surface) 45%, transparent)',
                backdropFilter: 'blur(24px)',
                WebkitBackdropFilter: 'blur(24px)',
                border: '1px solid var(--color-divider)',
                display: 'flex',
                flexDirection: 'column',
                gap: '22px',
              }}
            >
              {/* Header & Alignment Bar */}
              <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: 0, flex: '1 1 360px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span
                      style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        background: 'var(--color-accent)',
                        animation: 'tiPulse 1.6s infinite',
                      }}
                    ></span>
                    Active deliberation
                  </span>
                  <h2
                    style={{
                      margin: 0,
                      fontFamily: 'var(--font-heading)',
                      fontWeight: 600,
                      fontSize: '22px',
                      lineHeight: 1.25,
                      color: 'var(--color-neutral-100)',
                      textWrap: 'pretty',
                    }}
                  >
                    {topic}
                  </h2>
                </div>

                <div style={{ flex: '0 1 320px', display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '240px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '12px' }}>
                    <span style={{ fontSize: '13px', color: 'var(--color-neutral-300)' }}>
                      <span
                        style={{
                          fontSize: '22px',
                          fontWeight: 600,
                          color: 'var(--color-accent-200)',
                          fontVariantNumeric: 'tabular-nums',
                        }}
                      >
                        {consensus}%
                      </span>{' '}
                      Tactical Alignment
                    </span>
                    <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)', fontVariantNumeric: 'tabular-nums' }}>
                      {cursor === 0 ? 'Awaiting opening statements' : `Round ${activeRound} of 3`}
                    </span>
                  </div>
                  <div style={{ height: '6px', borderRadius: '999px', background: 'var(--color-neutral-900)', overflow: 'hidden' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${consensus}%`,
                        borderRadius: '999px',
                        background: 'linear-gradient(90deg, var(--color-accent-700), var(--color-accent))',
                        boxShadow: '0 0 12px var(--color-accent)',
                        transition: 'width .6s ease',
                      }}
                    ></div>
                  </div>
                </div>
              </div>

              {/* Specialist Agent Matrix Chips */}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {Object.entries(AGENTS).map(([id, a]) => {
                  const speaking = playing ? id === nextAgentId : id === lastAgentId;
                  const done = spokenSet.has(id);
                  return (
                    <div
                      key={id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '9px',
                        padding: '8px 12px 8px 10px',
                        borderRadius: 'var(--radius-md)',
                        border: speaking
                          ? '1px solid color-mix(in srgb, var(--color-accent) 55%, transparent)'
                          : '1px solid var(--color-divider)',
                        background: speaking
                          ? 'color-mix(in srgb, var(--color-accent) 10%, transparent)'
                          : 'color-mix(in srgb, var(--color-surface) 40%, transparent)',
                        transition: 'all .2s ease',
                      }}
                    >
                      <span
                        style={{
                          width: '8px',
                          height: '8px',
                          borderRadius: '50%',
                          background: speaking ? 'var(--color-accent)' : done ? 'var(--color-accent-700)' : 'var(--color-neutral-700)',
                          boxShadow: speaking ? '0 0 10px var(--color-accent)' : 'none',
                          flexShrink: 0,
                        }}
                      ></span>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
                        <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-neutral-100)' }}>
                          {a.name}
                        </span>
                        <span style={{ fontSize: '11.5px', color: 'var(--color-neutral-500)' }}>{a.focus}</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Stepper Bar & Round Controls */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  flexWrap: 'wrap',
                  padding: '10px',
                  borderRadius: 'var(--radius-md)',
                  background: 'color-mix(in srgb, var(--color-bg) 55%, transparent)',
                  border: '1px solid var(--color-divider)',
                }}
              >
                <div style={{ display: 'flex', gap: '4px' }}>
                  {[1, 2, 3].map((r) => {
                    const on = cursor > 0 && r === activeRound;
                    return (
                      <button
                        key={r}
                        onClick={() => {
                          pause();
                          setCursor(rawMsgs.filter((m) => m.round_num <= r).length);
                        }}
                        style={{
                          padding: '7px 14px',
                          borderRadius: 'var(--radius-md)',
                          border: on ? '1px solid var(--color-accent)' : '1px solid var(--color-divider)',
                          background: on ? 'color-mix(in srgb, var(--color-accent) 14%, transparent)' : 'transparent',
                          color: on ? 'var(--color-accent-100)' : 'var(--color-neutral-400)',
                          font: '500 13px var(--font-body)',
                          cursor: 'pointer',
                        }}
                      >
                        Round {r}
                      </button>
                    );
                  })}
                </div>

                <div style={{ display: 'flex', gap: '6px', marginLeft: 'auto', alignItems: 'center' }}>
                  <button
                    className="btn btn-ghost btn-icon"
                    onClick={() => {
                      pause();
                      setCursor((c) => Math.max(0, c - 1));
                    }}
                    aria-label="Previous message"
                  >
                    <i className="ph ph-skip-back" style={{ fontSize: '17px' }}></i>
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={() => (playing ? pause() : play())}
                    style={{ display: 'flex', alignItems: 'center', gap: '7px', minWidth: '132px', justifyContent: 'center' }}
                  >
                    <i className={playing ? 'ph ph-pause' : 'ph ph-play'} style={{ fontSize: '16px' }}></i>
                    {playing ? 'Pause' : 'Play Live'}
                  </button>
                  <button
                    className="btn btn-ghost btn-icon"
                    onClick={() => {
                      pause();
                      setCursor((c) => Math.min(rawMsgs.length, c + 1));
                    }}
                    aria-label="Next message"
                  >
                    <i className="ph ph-skip-forward" style={{ fontSize: '17px' }}></i>
                  </button>
                  <span
                    style={{
                      fontSize: '12px',
                      color: 'var(--color-neutral-500)',
                      fontVariantNumeric: 'tabular-nums',
                      minWidth: '48px',
                      textAlign: 'right',
                    }}
                  >
                    {cursor}/{rawMsgs.length}
                  </span>
                </div>
              </div>

              {/* Synthesized Dialogue Stream */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {cursor === 0 && !playing && (
                  <div
                    style={{
                      padding: '36px 20px',
                      textAlign: 'center',
                      color: 'var(--color-neutral-500)',
                      fontSize: '14px',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '8px',
                    }}
                  >
                    <i className="ph ph-chats-circle" style={{ fontSize: '28px', color: 'var(--color-neutral-600)' }}></i>
                    Press Play Live to stream opening statements.
                  </div>
                )}

                {rawMsgs.slice(0, cursor).map((m, idx) => {
                  const agent = getAgentInfo(m.sender_id);
                  const isPro = (m.sentiment_score ?? 0) >= 0;
                  const roundStart = idx === 0 || rawMsgs[idx - 1]?.round_num !== m.round_num;

                  return (
                    <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {roundStart && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12px', color: 'var(--color-neutral-500)', paddingTop: '6px' }}>
                          <span>Round {m.round_num}</span>
                          <span style={{ flex: 1, height: '1px', background: 'linear-gradient(90deg, var(--color-divider), transparent)' }}></span>
                        </div>
                      )}
                      <article style={{ display: 'flex', gap: '14px', animation: 'tiIn .45s ease both' }}>
                        <div
                          style={{
                            width: '38px',
                            height: '38px',
                            flexShrink: 0,
                            borderRadius: '50%',
                            display: 'grid',
                            placeItems: 'center',
                            background: 'var(--color-accent-900)',
                            border: '1px solid var(--color-accent-800)',
                            color: 'var(--color-accent-300)',
                          }}
                        >
                          <i className={agent.icon} style={{ fontSize: '18px' }}></i>
                        </div>
                        <div
                          style={{
                            flex: 1,
                            minWidth: 0,
                            padding: '14px 16px',
                            borderRadius: '4px var(--radius-lg) var(--radius-lg) var(--radius-lg)',
                            background: 'color-mix(in srgb, var(--color-surface) 70%, transparent)',
                            border: '1px solid var(--color-divider)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '9px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                            <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-neutral-100)' }}>
                              {agent.name}
                            </span>
                            <span style={{ fontSize: '12px', color: 'var(--color-neutral-600)', fontVariantNumeric: 'tabular-nums' }}>
                              21:{String(14 + idx).padStart(2, '0')}:{String((idx * 17) % 60).padStart(2, '0')}
                            </span>
                            <span
                              style={{
                                marginLeft: 'auto',
                                padding: '3px 9px',
                                borderRadius: '999px',
                                fontSize: '11.5px',
                                fontWeight: 600,
                                fontVariantNumeric: 'tabular-nums',
                                border: isPro
                                  ? '1px solid color-mix(in srgb, var(--color-accent) 50%, transparent)'
                                  : '1px solid var(--color-neutral-600)',
                                background: isPro
                                  ? 'color-mix(in srgb, var(--color-accent) 14%, transparent)'
                                  : 'transparent',
                                color: isPro ? 'var(--color-accent-200)' : 'var(--color-neutral-300)',
                              }}
                            >
                              {isPro ? '+' : '−'}
                              {Math.abs(m.sentiment_score ?? 0.72).toFixed(2)} {isPro ? 'PRO' : 'CON'}
                            </span>
                          </div>
                          <p style={{ margin: 0, fontSize: '14.5px', lineHeight: 1.6, color: 'var(--color-neutral-300)', textWrap: 'pretty' }}>
                            {m.content}
                          </p>
                          <div style={{ display: 'flex', gap: '18px', flexWrap: 'wrap', paddingTop: '8px', borderTop: '1px solid color-mix(in srgb, var(--color-text) 7%, transparent)' }}>
                            {(m.tele || [
                              { k: 'Sentiment', v: `${Math.round(Math.abs(m.sentiment_score ?? 0.8) * 100)}%` },
                              { k: 'Block Depth', v: '21.4m' },
                            ]).map((t, ti) => (
                              <span key={ti} style={{ fontSize: '12px', color: 'var(--color-neutral-500)', fontVariantNumeric: 'tabular-nums' }}>
                                {t.k}: <span style={{ color: 'var(--color-neutral-300)' }}>{t.v}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      </article>
                    </div>
                  );
                })}

                {playing && nextAgentId && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingLeft: '52px', fontSize: '13px', color: 'var(--color-neutral-500)' }}>
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--color-accent)', animation: 'tiPulse 1s infinite' }}></span>
                    {getAgentInfo(nextAgentId).name} is composing…
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* ────────────────────────────────────────────────
            TAB 2: HISTORY (DEDICATED CONVERSATION ARCHIVE)
        ──────────────────────────────────────────────── */}
        {tab === 'history' && (
          <section style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <h1 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: '32px', letterSpacing: '-0.02em', color: 'var(--color-neutral-100)' }}>
                History
              </h1>
              <p style={{ margin: 0, fontSize: '15px', color: 'var(--color-neutral-400)' }}>
                Every past deliberation. Resume one to replay it in the Arena.
              </p>
            </div>

            {/* Filter Search Bar */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '0 14px',
                maxWidth: '520px',
                borderRadius: 'var(--radius-md)',
                background: 'color-mix(in srgb, var(--color-surface) 60%, transparent)',
                border: '1px solid var(--color-divider)',
              }}
            >
              <i className="ph ph-magnifying-glass" style={{ fontSize: '17px', color: 'var(--color-neutral-500)' }}></i>
              <input
                value={searchHistory}
                onChange={(e) => setSearchHistory(e.target.value)}
                placeholder="Filter by team, tournament or date"
                style={{
                  flex: 1,
                  minWidth: 0,
                  height: '44px',
                  border: 0,
                  outline: 0,
                  background: 'transparent',
                  color: 'var(--color-neutral-100)',
                  font: '400 14px var(--font-body)',
                }}
              />
              <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)', fontVariantNumeric: 'tabular-nums' }}>
                {filteredHistory.length} of {combinedHistory.length}
              </span>
            </div>

            {/* History Cards Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))', gap: '14px' }}>
              {filteredHistory.map((h, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '18px',
                    borderRadius: 'var(--radius-lg)',
                    background: 'color-mix(in srgb, var(--color-surface) 50%, transparent)',
                    backdropFilter: 'blur(24px)',
                    WebkitBackdropFilter: 'blur(24px)',
                    border: '1px solid var(--color-divider)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '14px',
                    transition: 'border-color .15s ease',
                  }}
                >
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {h.tags.map((tg, tgi) => (
                      <span key={tgi} className="tag tag-neutral">
                        {tg}
                      </span>
                    ))}
                  </div>
                  <h3
                    style={{
                      margin: 0,
                      fontFamily: 'var(--font-heading)',
                      fontWeight: 600,
                      fontSize: '16px',
                      lineHeight: 1.35,
                      color: 'var(--color-neutral-100)',
                      textWrap: 'pretty',
                    }}
                  >
                    {h.topic}
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12.5px', color: 'var(--color-neutral-500)', fontVariantNumeric: 'tabular-nums' }}>
                    <span>{h.created_at}</span>
                    <span>
                      <span style={{ color: 'var(--color-accent-300)' }}>{h.consensus}% Consensus Reached</span> • {h.msgs} messages
                    </span>
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={() => {
                      if (h.discussion_id && savedDiscussions.some((d) => d.discussion_id === h.discussion_id)) {
                        loadDiscussionById(h.discussion_id);
                      } else {
                        setTopic(h.topic);
                        setCursor(0);
                      }
                      setTab('arena');
                      setTimeout(play, 600);
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '7px' }}
                  >
                    <i className="ph ph-arrow-counter-clockwise" style={{ fontSize: '15px' }}></i>
                    Resume / Replay
                  </button>
                </div>
              ))}
            </div>

            {filteredHistory.length === 0 && (
              <p style={{ margin: 0, color: 'var(--color-neutral-500)', fontSize: '14px' }}>
                No deliberations match that search.
              </p>
            )}
          </section>
        )}

        {/* ────────────────────────────────────────────────
            TAB 3: INTELLIGENCE (ANALYTICS DASHBOARD)
        ──────────────────────────────────────────────── */}
        {tab === 'intel' && (
          <section style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <h1 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: '32px', letterSpacing: '-0.02em', color: 'var(--color-neutral-100)' }}>
                Intelligence
              </h1>
              <p style={{ margin: 0, fontSize: '15px', color: 'var(--color-neutral-400)' }}>{topic}</p>
            </div>

            {/* Executive Consensus Card */}
            <div
              style={{
                padding: '22px',
                borderRadius: 'var(--radius-lg)',
                background: 'color-mix(in srgb, var(--color-surface) 55%, transparent)',
                backdropFilter: 'blur(24px)',
                WebkitBackdropFilter: 'blur(24px)',
                border: '1px solid color-mix(in srgb, var(--color-accent) 35%, var(--color-divider))',
                display: 'grid',
                gridTemplateColumns: 'auto minmax(0, 1fr)',
                gap: '24px',
                alignItems: 'center',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontSize: '44px', fontWeight: 600, letterSpacing: '-0.03em', color: 'var(--color-accent-200)', fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
                  91%
                </span>
                <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)' }}>Final alignment · Round 3</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)' }}>Executive consensus</span>
                <p style={{ margin: 0, fontSize: '15px', lineHeight: 1.6, color: 'var(--color-neutral-200)', textWrap: 'pretty' }}>
                  The 5-4-1 holds for roughly 60 minutes if the line sits under 25m. Fresh wing-backs at 58–62' let Japan switch to a 5-2-3 counter-press — Spain's possession becomes the trap. The Statistical Analyst moved furthest, from −0.40 to +0.31.
                </p>
              </div>
            </div>

            {/* Opinion Trajectories & Influence Leaderboard */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: '14px' }}>
              {/* Trajectories Graph */}
              <div
                style={{
                  padding: '20px',
                  borderRadius: 'var(--radius-lg)',
                  background: 'color-mix(in srgb, var(--color-surface) 45%, transparent)',
                  border: '1px solid var(--color-divider)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '14px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '12px', flexWrap: 'wrap' }}>
                  <h3 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: '16px', color: 'var(--color-neutral-100)' }}>
                    Opinion trajectories
                  </h3>
                  <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)' }}>Stance −1 CON → +1 PRO</span>
                </div>

                <svg viewBox="0 0 640 280" style={{ width: '100%', height: 'auto', display: 'block' }}>
                  {[1, 0.5, 0, -0.5, -1].map((v) => (
                    <g key={v}>
                      <line x1="40" x2="620" y1={Y(v)} y2={Y(v)} stroke="var(--color-neutral-800)" strokeDasharray={v === 0 ? '0' : '3 5'} />
                      <text x="30" y={Y(v) + 4} textAnchor="end" fontSize="11" fill="var(--color-neutral-600)">
                        {v > 0 ? `+${v}` : String(v)}
                      </text>
                    </g>
                  ))}
                  {[0, 1, 2, 3].map((i) => (
                    <text key={i} x={X(i)} y="272" textAnchor="middle" fontSize="11" fill="var(--color-neutral-500)">
                      R{i}
                    </text>
                  ))}
                  {Object.entries(trajectories).map(([id, pts]) => {
                    const isHovered = hoverAgent === id;
                    const opacity = hoverAgent && !isHovered ? 0.18 : 1;
                    const strokeWidth = isHovered ? 3.5 : 2;
                    return (
                      <g key={id}>
                        <path
                          d={smoothPath(pts)}
                          fill="none"
                          stroke={AGENTS[id].color}
                          strokeWidth={strokeWidth}
                          strokeLinecap="round"
                          opacity={opacity}
                          style={{ transition: 'opacity .2s, stroke-width .2s' }}
                        />
                        <circle cx="620" cy={Y(pts[3])} r="3.5" fill={AGENTS[id].color} opacity={opacity} />
                      </g>
                    );
                  })}
                </svg>

                {/* Legend Chips with Hover Filter */}
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {Object.entries(AGENTS).map(([id, a]) => (
                    <button
                      key={id}
                      onMouseEnter={() => setHoverAgent(id)}
                      onMouseLeave={() => setHoverAgent(null)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '4px 9px',
                        borderRadius: '999px',
                        border: '1px solid var(--color-divider)',
                        background: 'transparent',
                        color: 'var(--color-neutral-300)',
                        font: '500 12px var(--font-body)',
                        cursor: 'default',
                      }}
                    >
                      <span style={{ width: '10px', height: '3px', borderRadius: '2px', background: a.color }}></span>
                      {a.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Agent Influence Leaderboard */}
              <div
                style={{
                  padding: '20px',
                  borderRadius: 'var(--radius-lg)',
                  background: 'color-mix(in srgb, var(--color-surface) 45%, transparent)',
                  border: '1px solid var(--color-divider)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '12px' }}>
                  <h3 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: '16px', color: 'var(--color-neutral-100)' }}>
                    Agent influence
                  </h3>
                  <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)' }}>Share of consensus shift</span>
                </div>
                {influence.map((f, i) => {
                  const agent = AGENTS[f.id];
                  return (
                    <div key={f.id} style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px' }}>
                        <span style={{ width: '18px', color: 'var(--color-neutral-600)', fontVariantNumeric: 'tabular-nums' }}>
                          {i + 1}
                        </span>
                        <i className={agent.icon} style={{ fontSize: '15px', color: 'var(--color-neutral-400)' }}></i>
                        <span style={{ color: 'var(--color-neutral-200)', flex: 1 }}>{agent.name}</span>
                        <span style={{ color: 'var(--color-neutral-300)', fontVariantNumeric: 'tabular-nums' }}>{f.pct}%</span>
                      </div>
                      <div style={{ height: '5px', marginLeft: '28px', borderRadius: '999px', background: 'var(--color-neutral-900)', overflow: 'hidden' }}>
                        <div
                          style={{
                            height: '100%',
                            width: `${(f.pct / 34) * 100}%`,
                            borderRadius: '999px',
                            background: i === 0 ? 'linear-gradient(90deg, var(--color-accent-700), var(--color-accent))' : 'var(--color-neutral-600)',
                          }}
                        ></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        )}

        {/* ────────────────────────────────────────────────
            TAB 4: DEVOPS (SYSTEM HEALTH & TERMINAL)
        ──────────────────────────────────────────────── */}
        {tab === 'devops' && (
          <section style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <h1 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: '32px', letterSpacing: '-0.02em', color: 'var(--color-neutral-100)' }}>
                DevOps
              </h1>
              <p style={{ margin: 0, fontSize: '15px', color: 'var(--color-neutral-400)' }}>
                System health for the deliberation engine.
              </p>
            </div>

            {/* Microservices Cards Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', gap: '14px' }}>
              {[
                { name: 'FastAPI', icon: 'ph ph-lightning', metric: ':8000', sub: 'REST gateway · 12ms p50' },
                { name: 'pgvector', icon: 'ph ph-database', metric: ':5432', sub: 'Postgres 16 · embeddings store' },
                { name: 'Vector search', icon: 'ph ph-graph', metric: '1.4ms', sub: 'Median similarity query latency' },
              ].map((s, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '18px',
                    borderRadius: 'var(--radius-lg)',
                    background: 'color-mix(in srgb, var(--color-surface) 50%, transparent)',
                    backdropFilter: 'blur(24px)',
                    WebkitBackdropFilter: 'blur(24px)',
                    border: '1px solid var(--color-divider)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <i className={s.icon} style={{ fontSize: '20px', color: 'var(--color-neutral-300)' }}></i>
                    <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-neutral-100)', flex: 1 }}>{s.name}</span>
                    <span className="tag tag-accent" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--color-accent)', boxShadow: '0 0 6px var(--color-accent)' }}></span>
                      Healthy
                    </span>
                  </div>
                  <span style={{ fontSize: '28px', fontWeight: 600, letterSpacing: '-0.02em', color: 'var(--color-neutral-100)', fontVariantNumeric: 'tabular-nums' }}>
                    {s.metric}
                  </span>
                  <span style={{ fontSize: '12.5px', color: 'var(--color-neutral-500)' }}>{s.sub}</span>
                </div>
              ))}
            </div>

            {/* Health Check Terminal Box */}
            <div style={{ borderRadius: 'var(--radius-lg)', background: 'color-mix(in srgb, var(--color-bg) 80%, black)', border: '1px solid var(--color-divider)', overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px', borderBottom: '1px solid var(--color-divider)' }}>
                <i className="ph ph-terminal-window" style={{ fontSize: '16px', color: 'var(--color-neutral-500)' }}></i>
                <span style={{ fontSize: '12.5px', color: 'var(--color-neutral-400)', flex: 1 }}>Health check</span>
                <button className="btn btn-ghost" onClick={handleCopy} style={{ display: 'flex', alignItems: 'center', gap: '6px', height: '30px', fontSize: '12.5px' }}>
                  <i className={copied ? 'ph ph-check' : 'ph ph-copy'} style={{ fontSize: '14px' }}></i>
                  {copied ? 'Copied' : 'Copy command'}
                </button>
              </div>
              <pre style={{ margin: 0, padding: '18px', font: "400 13px/1.7 ui-monospace, 'SF Mono', Menlo, monospace", color: 'var(--color-neutral-300)', overflowX: 'auto' }}>
                <span style={{ color: 'var(--color-accent-300)' }}>$</span> curl http://localhost:8000/health | jq{'\n'}
                <span style={{ color: 'var(--color-neutral-500)' }}>{'{'}{'\n'}</span>
                {'  '}<span style={{ color: 'var(--color-accent-200)' }}>"status"</span>: "ok",{'\n'}
                {'  '}<span style={{ color: 'var(--color-accent-200)' }}>"api"</span>: {'{'} "service": "fastapi", "port": 8000, "latency_ms": {healthStatus.latencyMs} {'}'},{'\n'}
                {'  '}<span style={{ color: 'var(--color-accent-200)' }}>"db"</span>: {'{'} "service": "pgvector", "port": 5432, "vector_latency_ms": 1.4 {'}'},{'\n'}
                {'  '}<span style={{ color: 'var(--color-accent-200)' }}>"agents_online"</span>: 6{'\n'}
                <span style={{ color: 'var(--color-neutral-500)' }}>{'}'}</span>
              </pre>
            </div>

            {/* Swagger & ReDoc API Links */}
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <a className="btn btn-secondary" href="/docs" target="_blank" rel="noreferrer" style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                <i className="ph ph-book-open" style={{ fontSize: '15px' }}></i>Swagger UI · /docs
              </a>
              <a className="btn btn-secondary" href="/redoc" target="_blank" rel="noreferrer" style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                <i className="ph ph-file-text" style={{ fontSize: '15px' }}></i>ReDoc · /redoc
              </a>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
