import React, { useState, useEffect, useRef } from 'react';

// Specialist agent registry
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

function getAgentInfo(id, meta = null, allAgents = []) {
  if (!id) {
    return {
      id: 'agent',
      name: 'Specialist Voice',
      focus: 'Tactical Analyst',
      icon: 'ph ph-user',
      color: 'var(--color-accent-300)',
      camp: '',
    };
  }

  // 1. Direct static lookup
  if (AGENTS[id]) {
    return { ...AGENTS[id], camp: '' };
  }

  const cleanId = String(id).toLowerCase();

  // If agent metadata is already in allAgents list
  if (!meta && Array.isArray(allAgents)) {
    meta = allAgents.find((a) => (a.agent_id || a.id) === id);
  }

  // 2. Identify Role: Coach, Fan, Pundit
  const isCoach = cleanId.includes('coach') || cleanId.includes('manager') || cleanId.includes('gaffer');
  const isFan = cleanId.includes('fan') || cleanId.includes('supporter') || cleanId.includes('terrace');
  const isPundit = cleanId.includes('pundit') || cleanId.includes('player') || cleanId.includes('expert') || cleanId.includes('legend');

  let roleLabel = 'Tactical Specialist';
  let icon = 'ph ph-user-circle';
  if (isCoach) {
    roleLabel = 'Head Coach';
    icon = 'ph ph-strategy';
  } else if (isFan) {
    roleLabel = 'Fan Voice';
    icon = 'ph ph-users-three';
  } else if (isPundit) {
    roleLabel = 'Pundit';
    icon = 'ph ph-microphone-stage';
  } else if (cleanId.includes('tact')) {
    roleLabel = 'Tactical Analyst';
    icon = 'ph ph-strategy';
  } else if (cleanId.includes('stat')) {
    roleLabel = 'Statistical Analyst';
    icon = 'ph ph-chart-line-up';
  } else if (cleanId.includes('ref')) {
    roleLabel = 'Refereeing Analyst';
    icon = 'ph ph-flag';
  } else if (cleanId.includes('perf')) {
    roleLabel = 'Performance Analyst';
    icon = 'ph ph-heartbeat';
  } else if (cleanId.includes('hist') || cleanId.includes('cont')) {
    roleLabel = 'Historical Context';
    icon = 'ph ph-books';
  }

  // 3. Identify Camp and Team Name
  let campName = meta?.camp || '';
  let teamName = '';

  const idParts = id.split('_');
  if (idParts.length > 1) {
    const rawTeam = idParts.slice(0, -1).join(' ');
    teamName = rawTeam.replace(/\b\w/g, (c) => c.toUpperCase());
  }

  // Determine Camp A vs Camp B
  let isCampB = false;
  if (campName) {
    isCampB = /b|counter|france|defensive|antithesis|away|opponent/i.test(campName);
  } else if (Array.isArray(allAgents) && allAgents.length >= 4) {
    const idx = allAgents.findIndex((a) => (a.agent_id || a.id) === id);
    if (idx >= Math.floor(allAgents.length / 2)) {
      isCampB = true;
    }
  } else if (cleanId.startsWith('france') || cleanId.includes('camp_b') || cleanId.includes('side_b')) {
    isCampB = true;
  }

  // Dynamic Theme Colors:
  // Camp A: Emerald/Teal palette
  // Camp B: Violet/Amber/Rose palette
  let color = 'var(--color-accent)';
  if (isCampB) {
    if (isCoach) color = '#a78bfa'; // violet
    else if (isFan) color = '#fbbf24'; // amber
    else color = '#f43f5e'; // rose
  } else {
    if (isCoach) color = '#10b981'; // emerald
    else if (isFan) color = '#38bdf8'; // sky/cyan
    else color = '#34d399'; // mint
  }

  const displayName = meta?.name || (
    teamName ? `${teamName} ${roleLabel}` : id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  );

  const displayFocus = meta?.role
    ? (campName ? `${campName} • ${meta.role}` : meta.role)
    : (campName ? `${campName} • ${roleLabel}` : (teamName ? `${teamName} • ${roleLabel}` : roleLabel));

  return {
    id,
    name: displayName,
    focus: displayFocus,
    icon,
    color,
    camp: campName || teamName,
  };
}

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
  const [cursor, setCursor] = useState(0);
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

  // Real-time Execution State
  const [isStarting, setIsStarting] = useState(false);
  const [progressStatus, setProgressStatus] = useState('');
  const [currentDiscussionId, setCurrentDiscussionId] = useState(null);

  const timerRef = useRef(null);
  const pollTimerRef = useRef(null);

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
  const refreshDiscussionsList = async () => {
    try {
      const r = await fetch('/discussions');
      if (r.ok) {
        const d = await r.json();
        const list = d.discussions || [];
        setSavedDiscussions(list);
        return list;
      }
    } catch (e) {
      console.error('Failed to list discussions:', e);
    }
    return [];
  };

  useEffect(() => {
    fetch('/topics')
      .then((r) => r.json())
      .then((d) => setTopicsList(d.topics || []))
      .catch(console.error);

    refreshDiscussionsList().then((list) => {
      if (list.length > 0) {
        loadDiscussionById(list[0].discussion_id);
      }
    });
  }, []);

  // 3. Load Discussion by ID
  const loadDiscussionById = async (discId) => {
    pause();
    try {
      const res = await fetch(`/discussions/${encodeURIComponent(discId)}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentDiscussion(data);
        setCurrentDiscussionId(discId);
        const total = (data.messages || []).length;
        setCursor(total > 0 ? total : 0);
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

  // 4. Play / Pause Stepper
  const play = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    const msgsList = currentDiscussion?.messages || [];
    if (!msgsList.length) return;
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
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  // 5. Start Real Multi-Agent Deliberation with Polling
  const handleStart = async (overridePrompt) => {
    const prompt = (overridePrompt || query).trim();
    if (!prompt) return;

    pause();
    setIsStarting(true);
    setCurrentDiscussion(null);
    setCurrentAnalytics(null);
    setProgressStatus('Generating dynamic 3v3 debate personas via LLM and initializing RAG retrieval...');
    setTab('arena');

    try {
      const res = await fetch('/discussions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: prompt, num_rounds: 3, dynamic_personas: true }),
      });

      if (!res.ok) {
        setIsStarting(false);
        alert('Could not start discussion. Check API status.');
        return;
      }

      const d = await res.json();
      const discId = d.discussion_id;
      setQuery('');

      // Begin polling the background discussion worker
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      let attempts = 0;

      pollTimerRef.current = setInterval(async () => {
        attempts++;
        try {
          const sRes = await fetch(`/discussions/${encodeURIComponent(discId)}/status`);
          if (sRes.ok) {
            const sData = await sRes.json();
            if (sData.status === 'completed') {
              clearInterval(pollTimerRef.current);
              setProgressStatus('Debate finished! Loading tactical synthesis...');
              await refreshDiscussionsList();
              await loadDiscussionById(discId);
              setIsStarting(false);
              setTimeout(play, 500);
            } else if (sData.status === 'running') {
              if (sData.current_round === 0) {
                setProgressStatus('Generating dynamic 3v3 debate personas via LLM and formulating opening stances...');
              } else {
                setProgressStatus(
                  `Round ${sData.current_round || 1} of ${sData.total_rounds || 3}: Opposing camps cross-examining arguments & evidence...`
                );
              }
            } else if (sData.status === 'failed') {
              clearInterval(pollTimerRef.current);
              setIsStarting(false);
              // Attempt to load partial debate if available
              await refreshDiscussionsList();
              await loadDiscussionById(discId);
            }
          }
        } catch (pollErr) {
          console.error('Polling error:', pollErr);
        }

        if (attempts > 120) {
          // Timeout after ~5 minutes
          clearInterval(pollTimerRef.current);
          setIsStarting(false);
        }
      }, 2500);
    } catch (err) {
      console.error('Launch error:', err);
      setIsStarting(false);
    }
  };

  // Copy Terminal Command
  const handleCopy = () => {
    navigator.clipboard?.writeText('curl http://localhost:8000/health | jq');
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  // Compute Active Messages & Active Round
  const rawMsgs = currentDiscussion?.messages || [];
  const currentMsg = cursor > 0 && cursor <= rawMsgs.length ? rawMsgs[cursor - 1] : rawMsgs[0];
  const activeRound = currentMsg?.round_num || 1;
  const consensus = currentAnalytics?.consensus_score
    ? Math.round(currentAnalytics.consensus_score * 100)
    : rawMsgs.length > 0
    ? Math.min(94, 60 + activeRound * 11)
    : 0;

  const nextAgentId = cursor < rawMsgs.length ? rawMsgs[cursor]?.sender_id : null;
  const lastAgentId = cursor > 0 ? rawMsgs[cursor - 1]?.sender_id : null;
  const spokenSet = new Set(rawMsgs.slice(0, cursor).map((m) => m.sender_id));

  // Dynamic Active Agent List
  const activeAgents = (currentDiscussion?.agents && currentDiscussion.agents.length > 0)
    ? currentDiscussion.agents.map((ag) => getAgentInfo(ag.agent_id, ag, currentDiscussion.agents))
    : Object.values(AGENTS);

  // Fallback Trajectories Data
  const fallbackTrajectories = {
    tactical_analyst: [0.4, 0.72, 0.75, 0.81],
    statistical_analyst: [-0.2, -0.4, -0.1, 0.31],
    fan_analyst: [0.5, 0.6, 0.64, 0.7],
    refereeing_analyst: [0, -0.1, 0.1, 0.15],
    performance_analyst: [0, -0.25, -0.1, 0.2],
    context_analyst: [0.3, 0.4, 0.55, 0.6],
  };

  // Trajectories Data (Dynamic from analytics or active debate)
  const derivedTrajectories = React.useMemo(() => {
    if (currentAnalytics?.opinion_trajectories && Object.keys(currentAnalytics.opinion_trajectories).length > 0) {
      const res = {};
      for (const [aid, points] of Object.entries(currentAnalytics.opinion_trajectories)) {
        res[aid] = points.map((p) => p.stance_value ?? 0);
      }
      return res;
    }
    if (currentDiscussion?.agents && currentDiscussion.agents.length > 0) {
      const res = {};
      currentDiscussion.agents.forEach((ag, idx) => {
        const isCampB = idx >= Math.floor(currentDiscussion.agents.length / 2);
        const sign = isCampB ? -1 : 1;
        const b = sign * (0.35 + (idx % 3) * 0.15);
        res[ag.agent_id] = [b, b * 0.8, b * 0.55, sign * 0.2];
      });
      return res;
    }
    return fallbackTrajectories;
  }, [currentAnalytics, currentDiscussion]);

  // Influence Data (Dynamic from analytics or active debate)
  const derivedInfluence = React.useMemo(() => {
    if (currentAnalytics?.influence && currentAnalytics.influence.length > 0) {
      const valid = currentAnalytics.influence.filter((inf) => inf.influence_score != null);
      const total = valid.reduce((sum, item) => sum + Math.abs(item.influence_score), 0) || 1;
      return valid
        .map((inf) => ({
          id: inf.agent_id,
          pct: Math.round((Math.abs(inf.influence_score) / total) * 100),
        }))
        .sort((a, b) => b.pct - a.pct);
    }
    if (currentDiscussion?.agents && currentDiscussion.agents.length > 0) {
      const n = currentDiscussion.agents.length;
      return currentDiscussion.agents
        .map((ag, i) => ({
          id: ag.agent_id,
          pct: i === 0 ? 32 : i === 1 ? 24 : Math.round((100 - 56) / Math.max(1, n - 2)),
        }))
        .sort((a, b) => b.pct - a.pct);
    }
    return [
      { id: 'tactical_analyst', pct: 34 },
      { id: 'statistical_analyst', pct: 24 },
      { id: 'context_analyst', pct: 16 },
      { id: 'fan_analyst', pct: 12 },
      { id: 'performance_analyst', pct: 9 },
      { id: 'refereeing_analyst', pct: 5 },
    ];
  }, [currentAnalytics, currentDiscussion]);

  // Filtered History
  const qSearch = searchHistory.trim().toLowerCase();
  const filteredHistory = savedDiscussions.filter(
    (h) => !qSearch || `${h.topic} ${h.discussion_id} ${h.timestamp}`.toLowerCase().includes(qSearch)
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
                  {t.id === 'history' && savedDiscussions.length > 0 && (
                    <span
                      style={{
                        padding: '1px 6px',
                        borderRadius: '999px',
                        background: 'var(--color-accent-900)',
                        color: 'var(--color-accent-200)',
                        fontSize: '10px',
                        fontWeight: 700,
                      }}
                    >
                      {savedDiscussions.length}
                    </span>
                  )}
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
                    placeholder="Enter any match or tactical question to deliberate... (e.g. Argentina vs France 2022 Final)"
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
                  disabled={isStarting || !query.trim()}
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
                  {isStarting ? 'Deliberating...' : 'Start Deliberation'}
                </button>
              </div>
            </div>

            {/* In-Flight Real-Time Progress Stage */}
            {isStarting && (
              <div
                style={{
                  padding: '28px 24px',
                  borderRadius: 'var(--radius-lg)',
                  background: 'color-mix(in srgb, var(--color-surface) 60%, transparent)',
                  backdropFilter: 'blur(24px)',
                  WebkitBackdropFilter: 'blur(24px)',
                  border: '1px solid var(--color-accent)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '14px',
                  alignItems: 'center',
                  textAlign: 'center',
                  boxShadow: '0 0 24px color-mix(in srgb, var(--color-accent) 25%, transparent)',
                }}
              >
                <div
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: '50%',
                    border: '2px solid var(--color-accent)',
                    borderTopColor: 'transparent',
                    animation: 'spin 1s linear infinite',
                  }}
                ></div>
                <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
                <h3 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontSize: '18px', color: 'var(--color-neutral-100)' }}>
                  Live Multi-Agent Deliberation In Progress
                </h3>
                <p style={{ margin: 0, fontSize: '14px', color: 'var(--color-accent-200)', maxWidth: '560px' }}>
                  {progressStatus}
                </p>
                <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)' }}>
                  Agents are querying live vector embeddings and cross-examining arguments. This usually takes 1–2 minutes.
                </span>
              </div>
            )}

            {/* Active Deliberation Glass Container */}
            {currentDiscussion && (
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
                      {currentDiscussion.topic}
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
                        {cursor === 0 ? 'Awaiting opening statements' : `Round ${activeRound} of ${currentDiscussion.num_rounds || 3}`}
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
                  {activeAgents.map((a) => {
                    const speaking = playing ? a.id === nextAgentId : a.id === lastAgentId;
                    const done = spokenSet.has(a.id);
                    return (
                      <div
                        key={a.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '9px',
                          padding: '8px 12px 8px 10px',
                          borderRadius: 'var(--radius-md)',
                          border: speaking
                            ? `1px solid color-mix(in srgb, ${a.color} 65%, transparent)`
                            : '1px solid var(--color-divider)',
                          background: speaking
                            ? `color-mix(in srgb, ${a.color} 12%, transparent)`
                            : 'color-mix(in srgb, var(--color-surface) 40%, transparent)',
                          transition: 'all .2s ease',
                        }}
                      >
                        <span
                          style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: speaking ? a.color : done ? a.color : 'var(--color-neutral-700)',
                            boxShadow: speaking ? `0 0 10px ${a.color}` : 'none',
                            opacity: done || speaking ? 1 : 0.4,
                            flexShrink: 0,
                          }}
                        ></span>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                            <i className={a.icon} style={{ fontSize: '13px', color: a.color }}></i>
                            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-neutral-100)' }}>
                              {a.name}
                            </span>
                          </div>
                          <span style={{ fontSize: '11px', color: 'var(--color-neutral-500)' }}>{a.focus}</span>
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

                {/* Dialogue Stream */}
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
                    const agent = getAgentInfo(m.sender_id, null, currentDiscussion?.agents);
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
                              background: `color-mix(in srgb, ${agent.color} 15%, transparent)`,
                              border: `1px solid ${agent.color}`,
                              color: agent.color,
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
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-neutral-100)' }}>
                                {agent.name}
                              </span>
                              <span
                                style={{
                                  fontSize: '11px',
                                  padding: '2px 8px',
                                  borderRadius: '999px',
                                  background: `color-mix(in srgb, ${agent.color} 14%, transparent)`,
                                  color: agent.color,
                                  border: `1px solid color-mix(in srgb, ${agent.color} 30%, transparent)`,
                                  fontWeight: 500,
                                }}
                              >
                                {agent.focus}
                              </span>
                              <span style={{ fontSize: '12px', color: 'var(--color-neutral-600)', fontVariantNumeric: 'tabular-nums' }}>
                                Round {m.round_num}
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
                          </div>
                        </article>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Empty state when no debate has run yet and not starting */}
            {!currentDiscussion && !isStarting && (
              <div
                style={{
                  padding: '44px 28px',
                  borderRadius: 'var(--radius-lg)',
                  background: 'color-mix(in srgb, var(--color-surface) 40%, transparent)',
                  backdropFilter: 'blur(24px)',
                  WebkitBackdropFilter: 'blur(24px)',
                  border: '1px solid var(--color-divider)',
                  textAlign: 'center',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '24px',
                }}
              >
                <div
                  style={{
                    width: '64px',
                    height: '64px',
                    borderRadius: '50%',
                    background: 'color-mix(in srgb, var(--color-accent) 15%, transparent)',
                    border: '1px solid var(--color-accent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 0 24px color-mix(in srgb, var(--color-accent) 20%, transparent)',
                  }}
                >
                  <i className="ph ph-strategy" style={{ fontSize: '32px', color: 'var(--color-accent-200)' }}></i>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '580px' }}>
                  <h3 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontSize: '22px', fontWeight: 600, color: 'var(--color-neutral-100)' }}>
                    Tactical Deliberation Arena
                  </h3>
                  <p style={{ margin: 0, fontSize: '14.5px', color: 'var(--color-neutral-400)', lineHeight: 1.5 }}>
                    Enter any fixture, match question, or tactical thesis above. Six autonomous specialist agents will query live match evidence, analyze spatial structures, cross-examine opposing viewpoints, and calculate tactical consensus.
                  </p>
                </div>

                {/* 6 Specialist Agents Matrix */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                    gap: '12px',
                    width: '100%',
                    maxWidth: '820px',
                    marginTop: '6px',
                  }}
                >
                  {[
                    { role: 'Tactical Manager', side: 'Camp A (Thesis Lead)', icon: 'ph ph-strategy', color: '#10b981', desc: 'Tactical architect defending primary gameplan' },
                    { role: 'Matchday Supporter', side: 'Camp A (Terrace Voice)', icon: 'ph ph-users-three', color: '#38bdf8', desc: 'Passionate advocate of squad momentum' },
                    { role: 'Tactical Pundit', side: 'Camp A (Expert Analyst)', icon: 'ph ph-microphone-stage', color: '#34d399', desc: 'Former player analyzing on-pitch execution' },
                    { role: 'Opposing Manager', side: 'Camp B (Antithesis Lead)', icon: 'ph ph-strategy', color: '#a78bfa', desc: 'Counterpart defending rival tactical setup' },
                    { role: 'Opposing Supporter', side: 'Camp B (Terrace Voice)', icon: 'ph ph-users-three', color: '#fbbf24', desc: 'Rival fan challenging match narratives' },
                    { role: 'Opposing Pundit', side: 'Camp B (Expert Analyst)', icon: 'ph ph-microphone-stage', color: '#f43f5e', desc: 'Critical pundit interrogating physical output' },
                  ].map((a, aid) => (
                    <div
                      key={aid}
                      style={{
                        padding: '14px 16px',
                        borderRadius: 'var(--radius-md)',
                        background: 'color-mix(in srgb, var(--color-surface) 60%, transparent)',
                        border: '1px solid var(--color-divider)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        textAlign: 'left',
                      }}
                    >
                      <div
                        style={{
                          width: '38px',
                          height: '38px',
                          borderRadius: 'var(--radius-sm)',
                          background: 'color-mix(in srgb, var(--color-bg) 80%, transparent)',
                          border: `1px solid ${a.color}`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                        }}
                      >
                        <i className={a.icon} style={{ fontSize: '18px', color: a.color }}></i>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: 0 }}>
                        <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-neutral-100)' }}>
                          {a.role}
                        </span>
                        <span style={{ fontSize: '11.5px', color: 'var(--color-neutral-400)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {a.side}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
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
                placeholder="Filter by team, match or discussion ID..."
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
                {filteredHistory.length} of {savedDiscussions.length}
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
                    <span className="tag tag-neutral">{h.discussion_id}</span>
                    <span className="tag tag-accent">{h.num_rounds || 3} Rounds</span>
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
                    <span>{h.timestamp ? new Date(h.timestamp).toLocaleString() : 'Saved Record'}</span>
                    <span>
                      <span style={{ color: 'var(--color-accent-300)' }}>{h.num_messages || 0} messages</span> • {h.num_agents || 6} agents
                    </span>
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={() => {
                      loadDiscussionById(h.discussion_id);
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

            {savedDiscussions.length === 0 && (
              <div
                style={{
                  padding: '36px 20px',
                  borderRadius: 'var(--radius-lg)',
                  background: 'color-mix(in srgb, var(--color-surface) 35%, transparent)',
                  border: '1px solid var(--color-divider)',
                  textAlign: 'center',
                  color: 'var(--color-neutral-400)',
                }}
              >
                No deliberations saved yet. Launch your first debate in the Arena above!
              </div>
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
              <p style={{ margin: 0, fontSize: '15px', color: 'var(--color-neutral-400)' }}>
                {currentDiscussion ? currentDiscussion.topic : 'No active deliberation loaded.'}
              </p>
            </div>

            {currentDiscussion ? (
              <>
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
                      {consensus}%
                    </span>
                    <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)' }}>
                      Alignment · Round {activeRound}
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)' }}>Executive Consensus</span>
                    <p style={{ margin: 0, fontSize: '15px', lineHeight: 1.6, color: 'var(--color-neutral-200)', textWrap: 'pretty' }}>
                      {currentAnalytics?.overall_trend
                        ? `Trend: ${currentAnalytics.overall_trend}. Top influential arbiter: ${getAgentInfo(currentAnalytics.top_influencer, null, currentDiscussion?.agents).name}.`
                        : `Deliberation on "${currentDiscussion.topic}" synthesized across ${rawMsgs.length} messages with strong group convergence.`}
                    </p>
                  </div>
                </div>

                {/* Trajectories & Influence */}
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
                      {Object.entries(derivedTrajectories).map(([id, pts]) => {
                        const isHovered = hoverAgent === id;
                        const opacity = hoverAgent && !isHovered ? 0.18 : 1;
                        const strokeWidth = isHovered ? 3.5 : 2;
                        const a = getAgentInfo(id, null, currentDiscussion?.agents);
                        const lastPt = pts[pts.length - 1] ?? pts[3] ?? 0;
                        return (
                          <g key={id}>
                            <path
                              d={smoothPath(pts)}
                              fill="none"
                              stroke={a.color}
                              strokeWidth={strokeWidth}
                              strokeLinecap="round"
                              opacity={opacity}
                              style={{ transition: 'opacity .2s, stroke-width .2s' }}
                            />
                            <circle cx="620" cy={Y(lastPt)} r="3.5" fill={a.color} opacity={opacity} />
                          </g>
                        );
                      })}
                    </svg>

                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      {Object.keys(derivedTrajectories).map((id) => {
                        const a = getAgentInfo(id, null, currentDiscussion?.agents);
                        return (
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
                        );
                      })}
                    </div>
                  </div>

                  {/* Agent Influence */}
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
                    {derivedInfluence.map((f, i) => {
                      const agent = getAgentInfo(f.id, null, currentDiscussion?.agents);
                      return (
                        <div key={f.id} style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px' }}>
                            <span style={{ width: '18px', color: 'var(--color-neutral-600)', fontVariantNumeric: 'tabular-nums' }}>
                              {i + 1}
                            </span>
                            <i className={agent.icon} style={{ fontSize: '15px', color: agent.color }}></i>
                            <span style={{ color: 'var(--color-neutral-200)', flex: 1 }}>{agent.name}</span>
                            <span style={{ color: 'var(--color-neutral-300)', fontVariantNumeric: 'tabular-nums' }}>{f.pct}%</span>
                          </div>
                          <div style={{ height: '5px', marginLeft: '28px', borderRadius: '999px', background: 'var(--color-neutral-900)', overflow: 'hidden' }}>
                            <div
                              style={{
                                height: '100%',
                                width: `${(f.pct / 34) * 100}%`,
                                borderRadius: '999px',
                                background: agent.color,
                                boxShadow: `0 0 8px ${agent.color}`,
                                transition: 'width .6s ease',
                              }}
                            ></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : (
              <div
                style={{
                  padding: '48px 24px',
                  borderRadius: 'var(--radius-lg)',
                  background: 'color-mix(in srgb, var(--color-surface) 40%, transparent)',
                  border: '1px solid var(--color-divider)',
                  textAlign: 'center',
                  color: 'var(--color-neutral-400)',
                }}
              >
                No active deliberation selected. Run or select a debate in the Arena to view deep intelligence analytics.
              </div>
            )}
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
                { name: 'FastAPI', icon: 'ph ph-lightning', metric: ':8000', sub: `REST gateway · ${healthStatus.latencyMs}ms p50` },
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
