import React, { useState, useEffect, useRef, useMemo } from 'react';
import LandingPage from './components/LandingPage';
import MarkdownPreview from './components/MarkdownPreview';
import AgentCommunicationPitch from './components/AgentCommunicationPitch';
import AuthModal from './components/AuthModal';
import OnboardingModal from './components/OnboardingModal';
import ProfileModal from './components/ProfileModal';
import PersonaManagerModal from './components/PersonaManagerModal';
// Agent order the 2-6 agent presets draw from; mirrors the backend roster.
const AGENT_ROSTER = [
  'tactical_analyst',
  'statistical_analyst',
  'performance_analyst',
  'context_analyst',
  'refereeing_analyst',
  'fan_analyst',
];

// Specialist agent registry with distinct, high-contrast, obsidian-neon colors
export const AGENT_DISTINCT_COLORS = {
  tactical_analyst: '#00f59b',    // Neon Emerald Green
  performance_analyst: '#f43f5e', // Coral Crimson Rose
  statistical_analyst: '#00d2ff', // Electric Cyan Blue
  fan_analyst: '#fbbf24',         // Golden Amber Yellow
  refereeing_analyst: '#a855f7',  // Vivid Neon Purple
  context_analyst: '#fb923c',     // Warm Tangerine Orange
  arg_coach: '#00f59b',
  arg_fan: '#00d2ff',
  arg_pundit: '#38bdf8',
  france_coach: '#f43f5e',
  france_fan: '#fbbf24',
  france_pundit: '#a855f7',
};

export const DISTINCT_PALETTE = [
  '#00f59b', // 0: Neon Emerald Green (Tactical Analyst)
  '#00d2ff', // 1: Electric Cyan Blue (Statistical Analyst)
  '#f43f5e', // 2: Coral Crimson Rose (Performance Analyst)
  '#fbbf24', // 3: Golden Amber Yellow (Fan Sentiment)
  '#a855f7', // 4: Vivid Neon Purple (Refereeing Analyst)
  '#fb923c', // 5: Warm Tangerine Orange (Historical Context)
  '#38bdf8', // 6: Sky Cyan
  '#ec4899', // 7: Hot Magenta Pink
  '#34d399', // 8: Mint Green
  '#818cf8', // 9: Indigo Blue
  '#f97316', // 10: Bright Orange
  '#06b6d4', // 11: Deep Cyan
  '#e11d48', // 12: Ruby Rose
  '#10b981', // 13: Emerald
  '#8b5cf6', // 14: Violet
  '#f59e0b', // 15: Amber Gold
];

export const CUSTOM_PERSONAS_CACHE = {};

export function buildDebateColorMap(allAgents = []) {
  const colorMap = {};
  const usedColors = new Set();

  if (!Array.isArray(allAgents) || allAgents.length === 0) {
    return colorMap;
  }

  // Pass 1: Give signature colors to known standard agents
  allAgents.forEach((a) => {
    const id = typeof a === 'string' ? a : (a?.agent_id || a?.id || '');
    const cleanId = String(id).toLowerCase();
    if (AGENT_DISTINCT_COLORS[cleanId]) {
      const sigColor = AGENT_DISTINCT_COLORS[cleanId];
      colorMap[id] = sigColor;
      colorMap[cleanId] = sigColor;
      usedColors.add(sigColor.toLowerCase());
    }
  });

  // Pass 2: Custom personas with an explicit distinct color that is not yet taken
  allAgents.forEach((a) => {
    const id = typeof a === 'string' ? a : (a?.agent_id || a?.id || '');
    const cleanId = String(id).toLowerCase();
    if (colorMap[id] || colorMap[cleanId]) return;

    const cached = CUSTOM_PERSONAS_CACHE[id] || CUSTOM_PERSONAS_CACHE[cleanId];
    const candidate = (typeof a === 'object' && a?.color) || cached?.color;
    if (candidate && candidate.startsWith('#')) {
      const candLower = candidate.toLowerCase();
      if (!usedColors.has(candLower) && candLower !== '#00f59b' && candLower !== '#a78bfa' && candLower !== '#c084fc' && candLower !== '#818cf8') {
        colorMap[id] = candidate;
        colorMap[cleanId] = candidate;
        usedColors.add(candLower);
      }
    }
  });

  // Pass 3: For any remaining agents (custom personas or dynamic agents), allocate next unused color from DISTINCT_PALETTE
  let paletteIdx = 0;
  allAgents.forEach((a) => {
    const id = typeof a === 'string' ? a : (a?.agent_id || a?.id || '');
    const cleanId = String(id).toLowerCase();
    if (colorMap[id] || colorMap[cleanId]) return;

    while (paletteIdx < DISTINCT_PALETTE.length && usedColors.has(DISTINCT_PALETTE[paletteIdx].toLowerCase())) {
      paletteIdx++;
    }
    const color = paletteIdx < DISTINCT_PALETTE.length
      ? DISTINCT_PALETTE[paletteIdx]
      : DISTINCT_PALETTE[paletteIdx % DISTINCT_PALETTE.length];

    colorMap[id] = color;
    colorMap[cleanId] = color;
    usedColors.add(color.toLowerCase());
    paletteIdx++;
  });

  return colorMap;
}

export function getDistinctAgentColor(id, index = null, fallback = null) {
  const cleanId = String(id || '').toLowerCase();

  // 1. Signature distinct color for known analyst roles
  if (cleanId && AGENT_DISTINCT_COLORS[cleanId]) {
    return AGENT_DISTINCT_COLORS[cleanId];
  }

  // 2. Explicit custom color (if not legacy monochrome camp green/purple)
  if (fallback && fallback.startsWith('#') && fallback !== '#00f59b' && fallback !== '#a78bfa' && fallback !== '#c084fc' && fallback !== '#818cf8') {
    return fallback;
  }

  // 3. Sequential index mapping ensures every agent in a match gets a different color
  if (typeof index === 'number' && index >= 0) {
    return DISTINCT_PALETTE[index % DISTINCT_PALETTE.length];
  }

  // 4. Fallback deterministic hash (offset by 6 for custom personas to avoid colliding with default 6)
  let hash = 0;
  for (let i = 0; i < cleanId.length; i++) {
    hash = (hash << 5) - hash + cleanId.charCodeAt(i);
    hash |= 0;
  }
  const offset = 6 + (Math.abs(hash) % (DISTINCT_PALETTE.length - 6));
  return DISTINCT_PALETTE[offset];
}

const AGENTS = {
  tactical_analyst: {
    id: 'tactical_analyst',
    name: 'Tactical Analyst',
    focus: 'Half-space & Spatial',
    icon: 'ph ph-strategy',
    color: '#00f59b',
  },
  statistical_analyst: {
    id: 'statistical_analyst',
    name: 'Statistical Analyst',
    focus: 'xG & PPDA',
    icon: 'ph ph-chart-line-up',
    color: '#00d2ff',
  },
  performance_analyst: {
    id: 'performance_analyst',
    name: 'Performance Analyst',
    focus: 'Fatigue & Sprints',
    icon: 'ph ph-heartbeat',
    color: '#f43f5e',
  },
  fan_analyst: {
    id: 'fan_analyst',
    name: 'Fan Sentiment',
    focus: 'Momentum & Psychological Surge',
    icon: 'ph ph-users-three',
    color: '#fbbf24',
  },
  refereeing_analyst: {
    id: 'refereeing_analyst',
    name: 'Refereeing Analyst',
    focus: 'Law 12 & VAR',
    icon: 'ph ph-flag',
    color: '#a855f7',
  },
  context_analyst: {
    id: 'context_analyst',
    name: 'Historical Context',
    focus: 'Precedents',
    icon: 'ph ph-books',
    color: '#fb923c',
  },
};

// Agents that take part in a run started with the selected count.
function rosterAgents(numAgents) {
  const ids = AGENT_ROSTER.slice(0, numAgents);
  const colorMap = buildDebateColorMap(ids);
  return ids
    .map((id) => ({
      ...AGENTS[id],
      agent_id: id,
      color: colorMap[id] || AGENTS[id]?.color || '#00f59b',
    }))
    .filter((agent) => agent.id);
}

export function registerCustomPersona(persona) {
  if (persona && persona.id) {
    const id = persona.id;
    const cleanId = String(id).toLowerCase();
    if (!persona.color || persona.color === '#00f59b' || persona.color === '#a78bfa' || persona.color === '#c084fc' || persona.color === '#818cf8') {
      let hash = 0;
      for (let i = 0; i < cleanId.length; i++) {
        hash = (hash << 5) - hash + cleanId.charCodeAt(i);
        hash |= 0;
      }
      const colorIdx = 6 + (Math.abs(hash) % (DISTINCT_PALETTE.length - 6));
      persona.color = DISTINCT_PALETTE[colorIdx];
    }
    CUSTOM_PERSONAS_CACHE[id] = persona;
    CUSTOM_PERSONAS_CACHE[cleanId] = persona;
  }
}

function getAgentInfo(id, meta = null, allAgents = []) {
  if (!id) {
    return {
      id: 'agent',
      name: 'Specialist Voice',
      focus: 'Tactical Analyst',
      icon: 'ph ph-user',
      color: '#00f59b',
      camp: '',
    };
  }

  // If agent metadata is already in allAgents list
  if (!meta && Array.isArray(allAgents)) {
    meta = allAgents.find((a) => (a.agent_id || a.id || a) === id);
  }

  const cleanId = String(id).toLowerCase();
  const staticAgent = AGENTS[id];
  const cachedCustom = CUSTOM_PERSONAS_CACHE[id] || CUSTOM_PERSONAS_CACHE[cleanId];

  // Identify Camp and Team Name
  let campName = meta?.camp || '';
  let teamName = '';

  const idParts = id.split('_');
  if (idParts.length > 1) {
    const rawTeam = idParts.slice(0, -1).join(' ');
    teamName = rawTeam.replace(/\b\w/g, (c) => c.toUpperCase());
  }

  // Determine Agent's Unique Distinct Color via collision-free debate map
  let assignedColor = null;
  const effectiveAgents = Array.isArray(allAgents) && allAgents.length > 0
    ? allAgents
    : (Array.isArray(meta?.allAgents) && meta.allAgents.length > 0 ? meta.allAgents : null);

  if (effectiveAgents) {
    const debateColors = buildDebateColorMap(effectiveAgents);
    assignedColor = debateColors[id] || debateColors[cleanId];
  }

  if (!assignedColor) {
    let agentIndex = -1;
    if (effectiveAgents) {
      agentIndex = effectiveAgents.findIndex((a) => (a.agent_id || a.id || a) === id);
    }
    if (agentIndex < 0) agentIndex = AGENT_ROSTER.indexOf(cleanId);
    assignedColor = getDistinctAgentColor(id, agentIndex >= 0 ? agentIndex : null, meta?.color || cachedCustom?.color);
  }

  // 1. Direct static lookup with consistent distinct color
  if (staticAgent) {
    return {
      ...staticAgent,
      camp: campName,
      color: assignedColor,
      focus: campName ? `${campName} • ${staticAgent.focus}` : staticAgent.focus,
    };
  }

  // 2. Cached custom / AI persona with consistent distinct color
  if (cachedCustom) {
    return {
      id,
      name: cachedCustom.name || id,
      focus: campName ? `${campName} • ${cachedCustom.field || 'Specialist Analyst'}` : (cachedCustom.field || 'Specialist Analyst'),
      icon: cachedCustom.icon || 'ph ph-sparkle',
      color: assignedColor,
      camp: campName,
    };
  }

  // 3. Dynamic / LLM generated persona
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
    color: assignedColor,
    camp: campName || teamName,
  };
}

// SVG math helpers for trajectories
const X = (i) => 40 + i * (580 / 3);
const Y = (v) => 130 - v * 110;
// Skip null (unclassified) stance points; draw only measured segments.
const smoothPath = (pts) => {
  const measured = pts
    .map((v, i) => ({ v, i }))
    .filter(({ v }) => v != null);
  return measured
    .map(({ v, i }, k) => {
      if (k === 0) return `M${X(i)},${Y(v)}`;
      const prev = measured[k - 1];
      const mx = (X(prev.i) + X(i)) / 2;
      return `C${mx},${Y(prev.v)} ${mx},${Y(v)} ${X(i)},${Y(v)}`;
    })
    .join(' ');
};

// ── Multi-page URL routing ───────────────────────────────────────────────────
// Every top-level view is a real page: /, /arena, /history, /intel, /devops.
// FastAPI serves the matching built HTML document (arena.html, …) for those
// paths and mounts the bundle at /app, so deep links survive a hard refresh.
const PAGE_TAB_SLUGS = ['arena', 'history', 'intel', 'devops'];

// Extra slugs accepted in the URL, e.g. /intelligence or /deliberation.
const TAB_SLUG_ALIASES = {
  index: 'landing',
  home: 'landing',
  deliberation: 'arena',
  intelligence: 'intel',
  analytics: 'intel',
};

/** Mount prefix the app is currently served under ('/app' or ''). */
function routeBasePath() {
  const path = window.location.pathname || '/';
  return path === '/app' || path.startsWith('/app/') ? '/app' : '';
}

/** Map a URL pathname onto one of the five page tabs (default: landing). */
function tabFromPathname(pathname) {
  const segments = String(pathname || '/').toLowerCase().split('/').filter(Boolean);
  const leaf = (segments[0] === 'app' ? segments[1] : segments[0]) || '';
  const slug = leaf.replace(/\.html$/, '');
  if (!slug) return 'landing';
  const resolved = TAB_SLUG_ALIASES[slug] || slug;
  return PAGE_TAB_SLUGS.includes(resolved) ? resolved : 'landing';
}

/** Canonical URL path for a tab, honouring the active mount prefix. */
function pathForTab(tabId) {
  const base = routeBasePath();
  return tabId === 'landing' ? `${base}/` : `${base}/${tabId}`;
}

/** Query parameters carried by the current URL. */
function currentQueryParams() {
  const params = {};
  new URLSearchParams(window.location.search).forEach((value, key) => {
    params[key] = value;
  });
  return params;
}

export default function App() {
  const [isAdmin, setIsAdmin] = useState(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      if (params.get('admin') === 'false' || params.get('admin') === '0') {
        localStorage.removeItem('football_rag_admin');
        return false;
      }
      if (params.get('admin') === 'true' || params.get('admin') === '1') {
        localStorage.setItem('football_rag_admin', 'true');
        return true;
      }
      return localStorage.getItem('football_rag_admin') === 'true';
    } catch {
      return false;
    }
  });

  // Multi-Tenant Platform & Persona State (Strict Landing-First Auth Gating)
  const [token, setToken] = useState(() => {
    try {
      return localStorage.getItem('touchline_token') || null;
    } catch {
      return null;
    }
  });
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);

  const [tab, setTab] = useState(() => {
    try {
      const storedToken = localStorage.getItem('touchline_token');
      if (!storedToken) return 'landing';
      const params = new URLSearchParams(window.location.search);
      if (params.get('admin') === 'true' || params.get('admin') === '1') {
        return 'devops';
      }
      // Deep links such as /history or /arena decide the initial page.
      return tabFromPathname(window.location.pathname);
    } catch (_) {
      return 'landing';
    }
  });

  const isAuthenticated = Boolean(user && token);
  const [activePassEvent, setActivePassEvent] = useState(null);

  // Client-side navigation: keeps the URL bar, the History API and `tab` in sync.
  const navigateTo = (tabId, queryParams = null) => {
    const params = new URLSearchParams();
    if (queryParams) {
      Object.entries(queryParams).forEach(([key, value]) => {
        if (value === undefined || value === null || value === '') return;
        params.set(key, String(value));
      });
    }
    const search = params.toString();
    const url = `${pathForTab(tabId)}${search ? `?${search}` : ''}`;
    const current = `${window.location.pathname}${window.location.search}`;
    if (url !== current) window.history.pushState({ tab: tabId }, '', url);
    setTab(tabId);
  };

  const [query, setQuery] = useState('');
  const queryInputRef = useRef(null);

  // Auto-resize discussion topic text box to dynamically adapt to text length
  useEffect(() => {
    if (queryInputRef.current) {
      queryInputRef.current.style.height = 'auto';
      const scrollH = queryInputRef.current.scrollHeight;
      queryInputRef.current.style.height = `${Math.max(48, Math.min(scrollH, 300))}px`;
    }
  }, [query]);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [searchHistory, setSearchHistory] = useState('');
  const [hoverAgent, setHoverAgent] = useState(null);
  const [copied, setCopied] = useState(false);
  const [selectedRounds, setSelectedRounds] = useState(3);

  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');
  const [onboardingModalOpen, setOnboardingModalOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [personaManagerModalOpen, setPersonaManagerModalOpen] = useState(false);
  const [selectedAgentCount, setSelectedAgentCount] = useState(6);
  const [personaMode, setPersonaMode] = useState('custom'); // 'dynamic' | 'custom'
  const [campAPersonaIds, setCampAPersonaIds] = useState([
    'tactical_analyst',
    'statistical_analyst',
    'fan_analyst',
  ]);
  const [campBPersonaIds, setCampBPersonaIds] = useState([
    'refereeing_analyst',
    'performance_analyst',
    'context_analyst',
  ]);
  const selectedPersonaIds = useMemo(
    () => [...campAPersonaIds, ...campBPersonaIds],
    [campAPersonaIds, campBPersonaIds]
  );

  const [customPersonasVersion, setCustomPersonasVersion] = useState(0);

  const registerCustomPersonas = (list) => {
    if (!Array.isArray(list)) return;
    list.forEach(registerCustomPersona);
    setCustomPersonasVersion((v) => v + 1);
  };

  const handleAssignPersonaToCamp = (persona, camp) => {
    if (persona && persona.id) {
      registerCustomPersona(persona);
      setCustomPersonasVersion((v) => v + 1);
    }
    const pid = persona.id;
    setPersonaMode('custom');
    if (campAPersonaIds.includes(pid) || campBPersonaIds.includes(pid)) return;
    if (selectedPersonaIds.length >= 6) {
      alert('Maximum 6 personas can be selected for a deliberation.');
      return;
    }
    if (camp === 'B') {
      setCampBPersonaIds((prev) => [...prev, pid]);
    } else {
      setCampAPersonaIds((prev) => [...prev, pid]);
    }
  };

  const handleMovePersonaCamp = (persona, targetCamp) => {
    const pid = persona.id;
    if (targetCamp === 'B') {
      if (campAPersonaIds.length <= 1) {
        alert('Camp A must retain at least 1 agent.');
        return;
      }
      setCampAPersonaIds((prev) => prev.filter((id) => id !== pid));
      setCampBPersonaIds((prev) => (prev.includes(pid) ? prev : [...prev, pid]));
    } else {
      if (campBPersonaIds.length <= 1) {
        alert('Camp B must retain at least 1 agent.');
        return;
      }
      setCampBPersonaIds((prev) => prev.filter((id) => id !== pid));
      setCampAPersonaIds((prev) => (prev.includes(pid) ? prev : [...prev, pid]));
    }
  };

  const handleRemovePersonaFromArena = (persona) => {
    const pid = persona.id;
    if (selectedPersonaIds.length <= 2) {
      alert('A deliberation requires at least 2 active personas in total.');
      return;
    }
    if (campAPersonaIds.includes(pid)) {
      if (campAPersonaIds.length <= 1) {
        alert('Camp A must retain at least 1 agent.');
        return;
      }
      setCampAPersonaIds((prev) => prev.filter((id) => id !== pid));
    } else if (campBPersonaIds.includes(pid)) {
      if (campBPersonaIds.length <= 1) {
        alert('Camp B must retain at least 1 agent.');
        return;
      }
      setCampBPersonaIds((prev) => prev.filter((id) => id !== pid));
    }
  };

  const handleTogglePersonaForArena = (persona) => {
    if (persona && persona.id) {
      registerCustomPersona(persona);
      setCustomPersonasVersion((v) => v + 1);
    }
    const pid = persona.id;
    setPersonaMode('custom');
    if (campAPersonaIds.includes(pid) || campBPersonaIds.includes(pid)) {
      handleRemovePersonaFromArena(persona);
    } else {
      if (campAPersonaIds.length <= campBPersonaIds.length) {
        handleAssignPersonaToCamp(persona, 'A');
      } else {
        handleAssignPersonaToCamp(persona, 'B');
      }
    }
  };

  // Pre-load custom personas so their human names appear on arena roster chips
  useEffect(() => {
    const activeTok = token || localStorage.getItem('touchline_token');
    if (!activeTok) return;
    fetch('/profile/personas', {
      headers: { Authorization: `Bearer ${activeTok}` },
    })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        if (Array.isArray(data)) {
          data.forEach(registerCustomPersona);
          setCustomPersonasVersion((v) => v + 1);
        }
      })
      .catch(() => {});
  }, [token]);

  // Redirect to landing page whenever not authenticated (and normalise the URL)
  useEffect(() => {
    if (token) return;
    if (tab === 'landing' && window.location.pathname === pathForTab('landing')) return;
    navigateTo('landing');
  }, [token, tab]);

  // Session Restoration from touchline_token
  useEffect(() => {
    const fetchMe = async () => {
      const activeTok = token || localStorage.getItem('touchline_token');
      if (!activeTok) {
        setUser(null);
        setProfile(null);
        return;
      }
      try {
        const res = await fetch('/auth/me', {
          headers: { Authorization: `Bearer ${activeTok}` },
        });
        if (res.ok) {
          const data = await res.json();
          setUser(data.user);
          setProfile(data.profile);
        } else {
          localStorage.removeItem('touchline_token');
          setToken(null);
          setUser(null);
          setProfile(null);
          navigateTo('landing');
        }
      } catch (err) {
        console.error('Session restoration notice:', err);
      }
    };
    fetchMe();
  }, [token]);

  // Instant Demo Login (Marwan - Scout Profile)
  const handleDemoLogin = async () => {
    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'marwan@football.ai', password: 'password123' }),
      });
      if (res.ok) {
        const data = await res.json();
        localStorage.setItem('touchline_token', data.token);
        setToken(data.token);
        setUser(data.user);
        setProfile(data.profile);
        navigateTo('arena');
        return;
      }
    } catch (err) {
      console.warn('Demo login API fallback:', err);
    }
    // Fallback if backend auth service is offline or in mock
    const fallbackToken = 'demo-session-token-marwan';
    localStorage.setItem('touchline_token', fallbackToken);
    setToken(fallbackToken);
    setUser({ id: 'usr-demo-marwan', email: 'marwan@football.ai', display_name: 'Marwan' });
    setProfile({
      id: 'prof-demo-marwan',
      display_name: 'Marwan',
      profile_type: 'scout',
      football_focus: 'Player Recruitment & Positional Profiling',
      experience_level: 'Professional',
      preferred_analysis_style: 'Statistical & Quantitative',
      preferred_report_type: 'Scout Report',
      favorite_teams: ['Argentina', 'Manchester City', 'Arsenal'],
      favorite_competitions: ['FIFA World Cup', 'UEFA Champions League'],
    });
    navigateTo('arena');
  };

  const handleLogout = async () => {
    try {
      if (token) {
        await fetch('/auth/logout', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    } catch (_) {}
    localStorage.removeItem('touchline_token');
    setToken(null);
    setUser(null);
    setProfile(null);
    setProfileModalOpen(false);
    navigateTo('landing');
  };

  // On-Demand Tactical Pass Trigger helper for step navigation
  const triggerPassForCursor = (nextCursor, msgsArray) => {
    const list = msgsArray || currentDiscussion?.messages || [];
    if (nextCursor <= 0 || !list || list.length === 0) {
      setActivePassEvent(null);
      return;
    }
    const currentMsg = list[nextCursor - 1];
    if (!currentMsg) return;

    let fromId = null;
    let toId = null;

    if (Array.isArray(currentMsg.recipient_ids) && currentMsg.recipient_ids.length > 0) {
      fromId = currentMsg.sender_id;
      toId = currentMsg.recipient_ids[0];
    } else if (nextCursor > 1 && list[nextCursor - 2]) {
      fromId = list[nextCursor - 2].sender_id;
      toId = currentMsg.sender_id;
    } else {
      fromId = currentMsg.sender_id;
      const agents = currentDiscussion?.agents || [];
      const other = agents.find((a) => (a.id || a.agent_id) !== fromId);
      if (other) toId = other.id || other.agent_id;
    }

    if (fromId && toId && fromId !== toId) {
      setActivePassEvent({
        from: fromId,
        to: toId,
        timestamp: Date.now(),
        round: currentMsg.round_num,
      });
    }
  };

  // Live Backend State
  const [healthStatus, setHealthStatus] = useState({ status: 'ok', latencyMs: 12 });
  const [topicsList, setTopicsList] = useState([]);
  const [savedDiscussions, setSavedDiscussions] = useState([]);
  const [currentDiscussion, setCurrentDiscussion] = useState(null);
  const [currentDiscussionStatus, setCurrentDiscussionStatus] = useState('unknown');
  const [discussionLoadError, setDiscussionLoadError] = useState(null);
  const [currentAnalytics, setCurrentAnalytics] = useState(null);
  const [causalCache, setCausalCache] = useState({});
  const [isComputingCausal, setIsComputingCausal] = useState(false);
  const [causalError, setCausalError] = useState(null);
  const [expandedExchanges, setExpandedExchanges] = useState(false);

  // LLM Executive Synthesis & Agent Commentary State
  const [synthesisCache, setSynthesisCache] = useState({});
  const [isComputingSynthesis, setIsComputingSynthesis] = useState(false);
  const [synthesisError, setSynthesisError] = useState(null);

  // Strategic Advisor & Executive Decision State
  const [advisorCache, setAdvisorCache] = useState({});
  const [isComputingAdvisor, setIsComputingAdvisor] = useState(false);
  const [advisorError, setAdvisorError] = useState(null);

  // Real-time Execution State
  const [isStarting, setIsStarting] = useState(false);
  const [progressStatus, setProgressStatus] = useState('');
  const [currentDiscussionId, setCurrentDiscussionId] = useState(null);

  const timerRef = useRef(null);
  const pollTimerRef = useRef(null);
  const discussionLoadRef = useRef(0);
  const discussionRunRef = useRef(0);
  // Number of transcript messages already shown; used to keep live-follow on
  // the newest message without yanking a reader who scrubbed back.
  const liveLengthRef = useRef(0);

  // Browser back/forward buttons re-derive the active page from the URL.
  useEffect(() => {
    const onPopState = () => {
      const nextTab = tabFromPathname(window.location.pathname);
      setTab(nextTab);
      const requestedId = new URLSearchParams(window.location.search).get('id');
      if (nextTab === 'arena' && requestedId && requestedId !== currentDiscussionId) {
        loadDiscussionById(requestedId);
      }
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [currentDiscussionId]);

  // Sync causal cache when discussion analytics loads
  React.useEffect(() => {
    if (currentDiscussionId && currentAnalytics?.causal_influence) {
      setCausalCache((prev) => ({
        ...prev,
        [currentDiscussionId]: currentAnalytics.causal_influence,
      }));
    }
  }, [currentDiscussionId, currentAnalytics]);

  const activeCausalData = currentDiscussionId
    ? (causalCache[currentDiscussionId] || currentAnalytics?.causal_influence)
    : null;

  // Ensure non-admin users cannot access devops tab
  React.useEffect(() => {
    if (tab === 'devops' && !isAdmin) {
      navigateTo('arena');
    }
  }, [tab, isAdmin]);

  const handleRunCausalAnalysis = async () => {
    if (!currentDiscussionId || isComputingCausal) return;
    setIsComputingCausal(true);
    setCausalError(null);
    try {
      const res = await fetch(`/discussions/${encodeURIComponent(currentDiscussionId)}/causal-analysis`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
      const data = await res.json();
      setCausalCache((prev) => ({ ...prev, [currentDiscussionId]: data }));
      setCurrentAnalytics((prev) => (prev ? { ...prev, causal_influence: data } : prev));
    } catch (err) {
      console.error('Causal counterfactual failed:', err);
      setCausalError(err.message || 'Counterfactual analysis failed.');
    } finally {
      setIsComputingCausal(false);
    }
  };

  const activeSynthesisData = currentDiscussionId ? synthesisCache[currentDiscussionId] : null;

  const handleFetchSynthesis = async (force = false) => {
    if (!currentDiscussionId || isComputingSynthesis) return;
    if (!force && synthesisCache[currentDiscussionId]) return;

    setIsComputingSynthesis(true);
    setSynthesisError(null);
    try {
      const res = await fetch(`/discussions/${encodeURIComponent(currentDiscussionId)}/synthesis`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
      const data = await res.json();
      setSynthesisCache((prev) => ({ ...prev, [currentDiscussionId]: data }));
    } catch (err) {
      console.error('Synthesis generation failed:', err);
      setSynthesisError(err.message || 'Failed to generate tactical synthesis.');
    } finally {
      setIsComputingSynthesis(false);
    }
  };

  const activeAdvisorData = currentDiscussionId ? advisorCache[currentDiscussionId] : null;

  const handleFetchAdvisor = async (force = false) => {
    if (!currentDiscussionId || isComputingAdvisor) return;
    if (!force && advisorCache[currentDiscussionId]) return;

    setIsComputingAdvisor(true);
    setAdvisorError(null);
    try {
      const res = await fetch(`/discussions/${encodeURIComponent(currentDiscussionId)}/advisor`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
      const data = await res.json();
      setAdvisorCache((prev) => ({ ...prev, [currentDiscussionId]: data }));
    } catch (err) {
      console.error('Advisor decision generation failed:', err);
      setAdvisorError(err.message || 'Failed to generate strategic advisor decision.');
    } finally {
      setIsComputingAdvisor(false);
    }
  };

  // Auto-fetch advisor decision when viewing a completed discussion if not yet cached
  React.useEffect(() => {
    if (currentDiscussionId && !advisorCache[currentDiscussionId] && !isComputingAdvisor) {
      handleFetchAdvisor(false);
    }
  }, [currentDiscussionId]);

  // Auto-fetch synthesis when opening the Intelligence tab if not already cached
  React.useEffect(() => {
    if (tab === 'intel' && currentDiscussionId && !synthesisCache[currentDiscussionId] && !isComputingSynthesis) {
      handleFetchSynthesis(false);
    }
  }, [tab, currentDiscussionId]);

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
    let cancelled = false;
    const generation = discussionRunRef.current;
    fetch('/topics')
      .then((r) => r.json())
      .then((d) => { if (!cancelled) setTopicsList(d.topics || []); })
      .catch(console.error);

    refreshDiscussionsList().then(() => {
      if (cancelled || generation !== discussionRunRef.current) return;
      // The Arena starts empty: a saved record is only opened when the URL
      // explicitly asks for it (?id=…), never by silently picking a recent one.
      const requestedId = new URLSearchParams(window.location.search).get('id');
      if (!requestedId || !localStorage.getItem('touchline_token')) return;
      loadDiscussionById(requestedId);
    });
    return () => { cancelled = true; };
  }, []);

  // 3. Load Discussion by ID
  const loadDiscussionById = async (discId, knownStatus = null) => {
    pause();
    if (!knownStatus) {
      discussionRunRef.current += 1;
      clearTimeout(pollTimerRef.current);
      setIsStarting(false);
    }
    const generation = ++discussionLoadRef.current;
    setCurrentDiscussionId(discId);
    setCurrentDiscussion(null);
    setCurrentAnalytics(null);
    setDiscussionLoadError(null);
    setCurrentDiscussionStatus(knownStatus || 'checking');
    const base = `/discussions/${encodeURIComponent(discId)}`;
    const read = async (url) => {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Could not load discussion (HTTP ${response.status}).`);
      return response.json();
    };
    const completion = knownStatus ? Promise.resolve({ status: knownStatus })
      : read(`${base}/status`).catch((error) => {
        console.error(error);
        return { status: 'unknown' };
      });
    // Read the transcript after completion is confirmed. A concurrent read
    // could otherwise return the last checkpoint just before the final save.
    // Loading another record invalidates both pending paths together.
    await Promise.allSettled([
      completion.then(async (record) => {
        const data = await read(base);
        if (generation !== discussionLoadRef.current) return;
        setCurrentDiscussion(data);
        const loadedCount = (data.messages || []).length;
        setCursor(loadedCount);
        liveLengthRef.current = loadedCount;
        setCurrentDiscussionStatus(record.status || 'unknown');
      }).catch(async (error) => {
        if (generation === discussionLoadRef.current) {
          setCurrentDiscussionStatus('unknown');
          // Never silently substitute a different record: surface the failure.
          await refreshDiscussionsList();
          setDiscussionLoadError(error.message);
        }
        console.error(error);
      }),
      completion.then(async () => {
        const response = await fetch(`${base}/analytics`, { signal: AbortSignal.timeout(120000) });
        if (!response.ok) throw new Error(`Could not load analytics (HTTP ${response.status}).`);
        return response.json();
      }).then((data) => {
        if (generation === discussionLoadRef.current) setCurrentAnalytics(data);
      }).catch(console.error),
    ]);
  };

  // Reopening an unfinished record keeps streaming its transcript: the worker
  // checkpoints after every agent turn, so the page must re-read the record
  // instead of only watching its status until a manual reload.
  useEffect(() => {
    if (isStarting) return undefined;
    if (!currentDiscussionId || !currentDiscussion
      || !['running', 'queued', 'unknown'].includes(currentDiscussionStatus)) return undefined;
    let cancelled = false;
    let timer;
    const controller = new AbortController();
    const checkStatus = async () => {
      try {
        const response = await fetch(`/discussions/${encodeURIComponent(currentDiscussionId)}/status`, { signal: controller.signal });
        if (response.ok) {
          const data = await response.json();
          if (cancelled) return;
          if (['completed', 'failed'].includes(data.status)) {
            await loadDiscussionById(currentDiscussionId, data.status);
            return;
          }

          const transcriptResponse = await fetch(`/discussions/${encodeURIComponent(currentDiscussionId)}`, { signal: controller.signal });
          if (cancelled) return;
          if (transcriptResponse.ok) {
            const transcript = await transcriptResponse.json();
            if (cancelled) return;
            const incoming = Array.isArray(transcript.messages) ? transcript.messages.length : 0;
            if (incoming > 0) {
              // Capture the previous length before scheduling: the updater runs
              // later, when the ref already holds the new value.
              const previousLength = liveLengthRef.current;
              liveLengthRef.current = incoming;
              setCurrentDiscussion(transcript);
              setCursor((prev) => (prev >= previousLength ? incoming : prev));
            }
          }
        }
      } catch (error) {
        if (!cancelled) console.error('Discussion status check:', error);
      }
      if (!cancelled) timer = setTimeout(checkStatus, 2500);
    };
    timer = setTimeout(checkStatus, 2500);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      controller.abort();
    };
  }, [currentDiscussionId, currentDiscussionStatus, currentDiscussion, isStarting]);

  // 4. Play / Pause Stepper
  const play = () => {
    clearInterval(timerRef.current);
    const msgsList = currentDiscussion?.messages || [];
    if (!msgsList.length) return;
    if (cursor >= msgsList.length) {
      setCursor(0);
      triggerPassForCursor(0, msgsList);
    }
    setPlaying(true);

    timerRef.current = setInterval(() => {
      setCursor((prev) => {
        const next = prev + 1;
        triggerPassForCursor(next, msgsList);
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
    clearInterval(timerRef.current);
    setPlaying(false);
  };

  useEffect(() => {
    return () => {
      clearInterval(timerRef.current);
      clearTimeout(pollTimerRef.current);
      discussionLoadRef.current += 1;
      discussionRunRef.current += 1;
    };
  }, []);

  // 5. Start Real Multi-Agent Deliberation with Polling
  const handleStart = async (overridePrompt) => {
    const prompt = (overridePrompt || query).trim();
    if (!prompt) return;

    pause();
    const generation = ++discussionRunRef.current;
    discussionLoadRef.current += 1;
    clearTimeout(pollTimerRef.current);
    setIsStarting(true);
    setCurrentDiscussion(null);
    setDiscussionLoadError(null);
    setCurrentDiscussionId(null);
    setCurrentDiscussionStatus('running');
    setCurrentAnalytics(null);
    setProgressStatus(
      personaMode === 'dynamic'
        ? `Generating dynamic ${selectedAgentCount} polarized personas via LLM and initializing RAG retrieval...`
        : `Initializing ${selectedPersonaIds.length} specialist personas and querying RAG embeddings...`
    );
    navigateTo('arena');

    try {
      const res = await fetch('/discussions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: prompt,
          num_rounds: selectedRounds,
          num_agents: personaMode === 'dynamic' ? selectedAgentCount : selectedPersonaIds.length,
          dynamic_personas: personaMode === 'dynamic',
          persona_ids: personaMode === 'custom' ? selectedPersonaIds : null,
          camp_a_ids: personaMode === 'custom' ? campAPersonaIds : null,
          camp_b_ids: personaMode === 'custom' ? campBPersonaIds : null,
        }),
        signal: AbortSignal.timeout(30000),
      });

      if (generation !== discussionRunRef.current) return;

      if (!res.ok) {
        setIsStarting(false);
        let detail = `the API answered HTTP ${res.status}.`;
        try {
          const failure = await res.json();
          if (failure && typeof failure.detail === 'string' && failure.detail) detail = failure.detail;
        } catch {
          // Non-JSON error body: keep the status-code message.
        }
        alert(`Could not start discussion: ${detail}`);
        return;
      }

      const d = await res.json();
      if (generation !== discussionRunRef.current) return;
      const discId = d.discussion_id;
      setQuery('');
      setCurrentDiscussionId(discId);
      setCursor(0);
      // Render the Arena shell immediately so the pitch and the message stream
      // are on screen before the first agent has spoken.
      setCurrentDiscussion({
        discussion_id: discId,
        topic: prompt,
        messages: [],
        num_rounds: selectedRounds,
        agents: personaMode === 'custom'
          ? [
              ...campAPersonaIds.map((id) => {
                const info = getAgentInfo(id, { camp: 'Camp A' }, selectedPersonaIds);
                return { agent_id: id, name: info.name, role: info.focus, focus: info.focus, camp: 'Camp A', color: info.color };
              }),
              ...campBPersonaIds.map((id) => {
                const info = getAgentInfo(id, { camp: 'Camp B' }, selectedPersonaIds);
                return { agent_id: id, name: info.name, role: info.focus, focus: info.focus, camp: 'Camp B', color: info.color };
              }),
            ]
          : rosterAgents(selectedAgentCount),
      });

      // Begin polling the background discussion worker
      const pollDiscussion = async () => {
        if (generation !== discussionRunRef.current) return;
        try {
          const sRes = await fetch(`/discussions/${encodeURIComponent(discId)}/status`);
          if (generation !== discussionRunRef.current) return;
          const sData = sRes.ok ? await sRes.json() : { status: 'unknown' };
          if (generation !== discussionRunRef.current) return;

          // Live transcript: the worker checkpoints messages while it runs, so
          // re-read the record on every poll and stream whatever exists yet.
          const tRes = await fetch(`/discussions/${encodeURIComponent(discId)}`);
          if (generation !== discussionRunRef.current) return;
          if (tRes.ok) {
            const transcript = await tRes.json();
            if (generation !== discussionRunRef.current) return;
            if (Array.isArray(transcript.messages) && transcript.messages.length > 0) {
              const incoming = transcript.messages.length;
              const previousLength = liveLengthRef.current;
              liveLengthRef.current = incoming;
              setCurrentDiscussion(transcript);
              // Stream new turns in place; keep a scrubbed-back cursor stable.
              setCursor((prev) => (prev >= previousLength ? incoming : prev));
            }
          }

          if (sData.status === 'completed') {
            setProgressStatus('All rounds finished. Loading the completed deliberation…');
            await refreshDiscussionsList();
            if (generation !== discussionRunRef.current) return;
            await loadDiscussionById(discId, 'completed');
            if (generation !== discussionRunRef.current) return;
            // Finished record becomes deep-linkable: a refresh reopens it.
            navigateTo('arena', { id: discId });
            if (generation === discussionRunRef.current) setIsStarting(false);
            return;
          } else if (sData.status === 'running') {
            if (sData.current_round === 0) {
              setProgressStatus('Specialist analysts formulating opening stances from match knowledge base...');
            } else {
              setProgressStatus(
                `Round ${sData.current_round || 1} of ${sData.total_rounds || 3}: Opposing camps cross-examining arguments & evidence...`
              );
            }
          } else if (sData.status === 'failed') {
            setIsStarting(false);
            setProgressStatus('');
            const list = await refreshDiscussionsList();
            if (generation !== discussionRunRef.current) return;
            const hasRecord = list.find((x) => x.discussion_id === discId && x.num_messages > 0);
            if (hasRecord) {
              await loadDiscussionById(discId, 'failed');
            } else {
              // No transcript was persisted: report the failure instead of
              // silently opening some other, unrelated saved discussion.
              setCurrentDiscussion(null);
              setCurrentDiscussionStatus('unknown');
              setDiscussionLoadError(sData.message || 'Discussion execution encountered an issue. Check server logs.');
            }
            return;
          }
        } catch (pollErr) {
          console.error('Polling error:', pollErr);
        }

        if (generation === discussionRunRef.current) {
          pollTimerRef.current = setTimeout(pollDiscussion, 2500);
        }
      };
      pollTimerRef.current = setTimeout(pollDiscussion, 2500);
    } catch (err) {
      console.error('Launch error:', err);
      if (generation === discussionRunRef.current) {
        setIsStarting(false);
        alert(`Could not start discussion: ${err?.message || 'the API is unreachable.'}`);
      }
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
  const activeRound = currentMsg?.round_num != null ? currentMsg.round_num : 1;
  const activeRoundAgreement = currentAnalytics?.agreement?.find((r) => r.round_num === activeRound);

  // Available Rounds (always includes 0 for opening statements, up to total rounds)
  const totalRounds = React.useMemo(() => {
    if (currentDiscussion?.num_rounds) return currentDiscussion.num_rounds;
    if (rawMsgs.length > 0) {
      const maxR = Math.max(...rawMsgs.map((m) => m.round_num ?? 0));
      return Math.max(2, maxR);
    }
    return 3;
  }, [currentDiscussion, rawMsgs]);

  const availableRounds = React.useMemo(() => {
    return Array.from({ length: totalRounds + 1 }, (_, i) => i);
  }, [totalRounds]);

  // Dynamic Tactical Alignment per Round (derives from LLM agreement, trajectories, sentiments, or live message text)
  const getRoundAlignment = React.useCallback(
    (roundNum) => {
      // While generating a debate or when none is selected or no messages yet, consensus is '--'
      if (isStarting || currentDiscussionStatus === 'running' || !currentDiscussion || rawMsgs.length === 0) {
        return null;
      }

      // 1. Backend calculated round agreement score
      const match = currentAnalytics?.agreement?.find((r) => r.round_num === roundNum);
      if (match?.agreement_score != null) {
        return Math.round(match.agreement_score * 100);
      }

      // 2. Trajectories pairwise stance distance for this round
      if (currentAnalytics?.opinion_trajectories && Object.keys(currentAnalytics.opinion_trajectories).length > 0) {
        const stances = [];
        for (const pts of Object.values(currentAnalytics.opinion_trajectories)) {
          const pt = pts.find((p) => p.round_num === roundNum);
          if (pt?.stance_value != null) {
            stances.push(pt.stance_value);
          }
        }
        if (stances.length >= 2) {
          let sumDist = 0;
          let pairs = 0;
          for (let i = 0; i < stances.length; i++) {
            for (let j = i + 1; j < stances.length; j++) {
              sumDist += Math.abs(stances[i] - stances[j]);
              pairs++;
            }
          }
          const meanDist = sumDist / pairs;
          return Math.round(Math.max(0.1, Math.min(0.98, 1.0 - (meanDist / 2.0))) * 100);
        }
      }

      // 3. Message sentiments for this round
      const roundSentiments = (currentAnalytics?.sentiment || [])
        .filter((s) => s.round_num === roundNum && s.sentiment_score != null)
        .map((s) => s.sentiment_score);
      if (roundSentiments.length >= 2) {
        let sumDist = 0;
        let pairs = 0;
        for (let i = 0; i < roundSentiments.length; i++) {
          for (let j = i + 1; j < roundSentiments.length; j++) {
            sumDist += Math.abs(roundSentiments[i] - roundSentiments[j]);
            pairs++;
          }
        }
        const meanDist = sumDist / pairs;
        return Math.round(Math.max(0.15, Math.min(0.95, 1.0 - (meanDist / 2.0))) * 100);
      }

      // 4. Live lexical polarity variance from actual messages in this round
      const msgsInRound = rawMsgs.filter((m) => (m.round_num ?? 1) === roundNum);
      if (msgsInRound.length >= 2) {
        const agentScores = msgsInRound.map((m) => {
          const text = (m.text || m.reasoning || m.raw_text || '').toLowerCase();
          const posMatches = (text.match(/\b(agree|concede|effective|sustainable|superior|compact|correct|align|valid|synergy|masterclass)\b/g) || []).length;
          const negMatches = (text.match(/\b(disagree|flaw|reckless|vulnerable|burnout|chaos|exposed|negligence|gamble|collapse|false)\b/g) || []).length;
          const total = posMatches + negMatches;
          return total > 0 ? (posMatches - negMatches) / total : 0;
        });
        let sumDist = 0;
        let pairs = 0;
        for (let i = 0; i < agentScores.length; i++) {
          for (let j = i + 1; j < agentScores.length; j++) {
            sumDist += Math.abs(agentScores[i] - agentScores[j]);
            pairs++;
          }
        }
        const meanDist = pairs > 0 ? sumDist / pairs : 0.6;
        return Math.round(Math.max(0.2, Math.min(0.92, 1.0 - (meanDist / 2.0))) * 100);
      }

      return null;
    },
    [isStarting, currentDiscussionStatus, currentDiscussion, currentAnalytics, rawMsgs]
  );

  // Dynamic round tactical alignment (per round in Arena & Intelligence):
  const roundAlignment = getRoundAlignment(activeRound);

  // Dynamic consensus (overall discussion average across rounds):
  const consensus = React.useMemo(() => {
    if (isStarting || currentDiscussionStatus === 'running' || !currentDiscussion || rawMsgs.length === 0) {
      return null;
    }
    if (currentAnalytics?.mean_agreement != null) {
      return Math.round(currentAnalytics.mean_agreement * 100);
    }
    if (currentAnalytics?.consensus_score != null) {
      return Math.round(currentAnalytics.consensus_score * 100);
    }
    const roundScores = availableRounds
      .filter((r) => r > 0)
      .map((r) => getRoundAlignment(r))
      .filter((s) => s != null && s > 0);
    return roundScores.length > 0
      ? Math.round(roundScores.reduce((a, b) => a + b, 0) / roundScores.length)
      : null;
  }, [isStarting, currentDiscussionStatus, currentDiscussion, rawMsgs, currentAnalytics, availableRounds, getRoundAlignment]);

  const nextAgentId = cursor < rawMsgs.length ? rawMsgs[cursor]?.sender_id : null;
  const lastAgentId = cursor > 0 ? rawMsgs[cursor - 1]?.sender_id : null;
  const spokenSet = new Set(rawMsgs.slice(0, cursor).map((m) => m.sender_id));

  // Unified, authoritative debate roster for color and agent info resolution.
  // Resilient against initial stale roster states while dynamic personas are generating.
  const debateAgentRoster = React.useMemo(() => {
    if (currentDiscussion?.agents && currentDiscussion.agents.length > 0) {
      const sampleId = currentDiscussion.agents[0]?.agent_id || currentDiscussion.agents[0]?.id;
      if (currentAnalytics?.opinion_trajectories && sampleId && !currentAnalytics.opinion_trajectories[sampleId]) {
        return Object.keys(currentAnalytics.opinion_trajectories);
      }
      return currentDiscussion.agents;
    }
    if (currentAnalytics?.opinion_trajectories && Object.keys(currentAnalytics.opinion_trajectories).length > 0) {
      return Object.keys(currentAnalytics.opinion_trajectories);
    }
    if (currentAnalytics?.influence && currentAnalytics.influence.length > 0) {
      return currentAnalytics.influence.map((inf) => inf.agent_id);
    }
    return null;
  }, [currentDiscussion, currentAnalytics]);

  // Dynamic Active Agent List
  const activeAgents = (debateAgentRoster && debateAgentRoster.length > 0)
    ? debateAgentRoster.map((ag) => {
        const aid = typeof ag === 'string' ? ag : (ag?.agent_id || ag?.id);
        const meta = typeof ag === 'object' ? ag : null;
        return getAgentInfo(aid, meta, debateAgentRoster);
      })
    : Object.values(AGENTS);

  // Trajectories Data (Real analytics only; no fabricated camp-decay series).
  const derivedTrajectories = React.useMemo(() => {
    if (currentAnalytics?.opinion_trajectories && Object.keys(currentAnalytics.opinion_trajectories).length > 0) {
      const res = {};
      let hasValidPoints = false;
      for (const [aid, points] of Object.entries(currentAnalytics.opinion_trajectories)) {
        res[aid] = points.map((p) => p.stance_value ?? null);
        if (points.some((p) => p.stance_value != null && p.stance_value !== 0)) {
          hasValidPoints = true;
        }
      }
      if (hasValidPoints) {
        return res;
      }
    }
    return null;
  }, [currentAnalytics, currentDiscussion]);

  // Influence Data (Real analytics only; no fabricated share percentages).
  const derivedInfluence = React.useMemo(() => {
    if (currentAnalytics?.influence && currentAnalytics.influence.length > 0) {
      const valid = currentAnalytics.influence.filter((inf) => inf.influence_score != null);
      if (valid.length > 0) {
        const total = valid.reduce((sum, item) => sum + Math.abs(item.influence_score), 0) || 1;
        return valid
          .map((inf) => ({
            id: inf.agent_id,
            pct: Math.round((Math.abs(inf.influence_score) / total) * 100),
          }))
          .sort((a, b) => b.pct - a.pct);
      }
    }
    return null;
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
            maxWidth: (!isAuthenticated || tab === 'landing') ? '1360px' : '1120px',
            width: '100%',
            margin: '0 auto',
            padding: (!isAuthenticated || tab === 'landing') ? '14px 32px' : '14px 24px',
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
                Multi-Agent Football Deliberation
              </span>
            </div>
          </div>

          {/* Navigation & Controls: Strict Auth Gating */}
          {isAuthenticated ? (
            <>
              {/* Navigation Tabs (Landing, Arena, History, Intelligence, DevOps for Admin) */}
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
                  { id: 'landing', label: 'Landing', icon: 'ph ph-house' },
                  { id: 'arena', label: 'Arena', icon: 'ph ph-chats-teardrop' },
                  { id: 'history', label: 'History', icon: 'ph ph-clock-counter-clockwise' },
                  { id: 'intel', label: 'Intelligence', icon: 'ph ph-chart-polar' },
                  ...(isAdmin ? [{ id: 'devops', label: 'DevOps', icon: 'ph ph-cpu', badge: 'Admin' }] : []),
                ].map((t) => {
                  const on = tab === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => navigateTo(t.id)}
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
                      {t.badge && (
                        <span
                          style={{
                            padding: '1px 5px',
                            borderRadius: '999px',
                            background: 'color-mix(in srgb, var(--color-accent) 25%, transparent)',
                            color: 'var(--color-accent-300)',
                            fontSize: '9px',
                            fontWeight: 700,
                            letterSpacing: '0.04em',
                          }}
                        >
                          {t.badge}
                        </span>
                      )}
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

              {/* Persona Roster & Profile Identity Tag */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  onClick={() => setPersonaManagerModalOpen(true)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '7px 12px',
                    borderRadius: 'var(--radius-md)',
                    background: 'color-mix(in srgb, var(--color-surface) 55%, transparent)',
                    border: '1px solid var(--color-divider)',
                    color: 'var(--color-neutral-300)',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all .15s ease',
                  }}
                  title="Manage and create AI specialist personas"
                >
                  <i className="ph ph-users-three" style={{ fontSize: '15px', color: 'var(--color-accent)' }}></i>
                  <span>Personas</span>
                </button>

                {profile && (
                  <button
                    onClick={() => setProfileModalOpen(true)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '6px 12px',
                      borderRadius: 'var(--radius-md)',
                      background: 'color-mix(in srgb, var(--color-accent) 12%, transparent)',
                      border: '1px solid color-mix(in srgb, var(--color-accent) 35%, transparent)',
                      cursor: 'pointer',
                      transition: 'all .15s ease',
                    }}
                    title="Click to view & edit Profile, Memory & Reports"
                  >
                    <div
                      style={{
                        width: '22px',
                        height: '22px',
                        borderRadius: '50%',
                        background: 'var(--color-accent)',
                        color: '#000',
                        display: 'grid',
                        placeItems: 'center',
                        fontSize: '11px',
                        fontWeight: 700,
                      }}
                    >
                      {profile.display_name?.[0]?.toUpperCase() || 'U'}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', lineHeight: 1.1 }}>
                      <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-neutral-100)' }}>
                        {profile.display_name.toUpperCase()}
                      </span>
                      <span style={{ fontSize: '9.5px', color: 'var(--color-accent-300)', fontWeight: 600, letterSpacing: '0.04em' }}>
                        {profile.profile_type?.toUpperCase()} PROFILE
                      </span>
                    </div>
                  </button>
                )}
              </div>
            </>
          ) : (
            /* Unauthenticated Header State: Nav tabs, Personas, Profile are completely hidden */
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: 'auto' }}>
              <button
                type="button"
                onClick={handleDemoLogin}
                className="btn btn-ghost"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  fontSize: '12.5px',
                  color: 'var(--color-accent-200)',
                  border: '1px solid color-mix(in srgb, var(--color-accent) 30%, transparent)',
                  borderRadius: 'var(--radius-md)',
                  background: 'color-mix(in srgb, var(--color-accent) 8%, transparent)',
                  cursor: 'pointer',
                }}
              >
                <i className="ph ph-lightning" style={{ fontSize: '14px' }}></i>
                <span>Quick Demo</span>
              </button>
              <button
                type="button"
                onClick={() => { setAuthModalMode('login'); setAuthModalOpen(true); }}
                className="btn btn-ghost"
                style={{ padding: '6px 14px', fontSize: '13px', color: 'var(--color-neutral-300)', cursor: 'pointer' }}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => { setAuthModalMode('register'); setAuthModalOpen(true); }}
                className="btn btn-primary"
                style={{ padding: '6px 16px', fontSize: '13px', cursor: 'pointer' }}
              >
                Get Started
              </button>
            </div>
          )}

          {/* Live System Status Pill */}
          <div
            title={`System operational · ${healthStatus.latencyMs}ms latency`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: '999px',
              border: '1px solid color-mix(in srgb, var(--color-accent) 25%, transparent)',
              background: 'color-mix(in srgb, var(--color-accent) 8%, transparent)',
              fontSize: '12px',
              fontWeight: 500,
              color: healthStatus.status === 'ok' ? 'var(--color-accent-200)' : 'var(--color-neutral-400)',
              letterSpacing: '0.01em',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: healthStatus.status === 'ok' ? 'var(--color-accent)' : '#f59e0b',
                boxShadow: healthStatus.status === 'ok' ? '0 0 6px var(--color-accent)' : 'none',
              }}
            ></span>
            {healthStatus.status === 'ok' ? (isAdmin ? `Live · ${healthStatus.latencyMs}ms` : 'Live') : 'Offline'}
          </div>
        </div>
      </header>

      {/* ══════════════════════════════════════════════════
          MAIN CONTENT AREA
      ══════════════════════════════════════════════════ */}
      {(!isAuthenticated || tab === 'landing') ? (
        <main style={{ width: '100%', margin: 0, padding: 0 }}>
          {/* ────────────────────────────────────────────────
              TAB 0: FUTURISTIC LANDING PAGE WITH ANIMATED FOOTBALL HERO
          ──────────────────────────────────────────────── */}
          <LandingPage
            onGetStarted={() => {
              setAuthModalMode('register');
              setAuthModalOpen(true);
            }}
            onSignIn={() => {
              setAuthModalMode('login');
              setAuthModalOpen(true);
            }}
            onExploreDemo={handleDemoLogin}
            onDemoLogin={handleDemoLogin}
          />
        </main>
      ) : (
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
                Specialist agents debate your question round by round, grounded in the evidence they retrieve.
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
              {/* Persona Deliberation Mode Switch */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'inline-flex', padding: '3px', borderRadius: 'var(--radius-md)', background: 'color-mix(in srgb, var(--color-bg) 75%, transparent)', border: '1px solid var(--color-divider)' }}>
                  <button
                    type="button"
                    onClick={() => setPersonaMode('dynamic')}
                    style={{
                      padding: '6px 14px',
                      borderRadius: 'calc(var(--radius-md) - 2px)',
                      border: 0,
                      background: personaMode === 'dynamic' ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.3) 0%, rgba(139, 92, 246, 0.4) 100%)' : 'transparent',
                      color: personaMode === 'dynamic' ? '#c084fc' : 'var(--color-neutral-400)',
                      font: '600 12.5px var(--font-body)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      boxShadow: personaMode === 'dynamic' ? '0 0 14px rgba(168, 85, 247, 0.35)' : 'none',
                      transition: 'all 0.18s ease',
                    }}
                  >
                    <i className="ph ph-sparkle" style={{ fontSize: '15px' }}></i>
                    Dynamic ({selectedAgentCount} Agents, AI-Polarized)
                  </button>
                  <button
                    type="button"
                    onClick={() => setPersonaMode('custom')}
                    style={{
                      padding: '6px 14px',
                      borderRadius: 'calc(var(--radius-md) - 2px)',
                      border: 0,
                      background: personaMode === 'custom' ? 'color-mix(in srgb, var(--color-accent) 20%, transparent)' : 'transparent',
                      color: personaMode === 'custom' ? 'var(--color-accent-100)' : 'var(--color-neutral-400)',
                      font: '600 12.5px var(--font-body)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      boxShadow: personaMode === 'custom' ? '0 0 14px color-mix(in srgb, var(--color-accent) 30%, transparent)' : 'none',
                      transition: 'all 0.18s ease',
                    }}
                  >
                    <i className="ph ph-users-three" style={{ fontSize: '15px' }}></i>
                    Curated Roster ({selectedPersonaIds.length}/6 Personas)
                  </button>
                </div>

                {personaMode === 'custom' ? (
                  <button
                    type="button"
                    onClick={() => setPersonaManagerModalOpen(true)}
                    className="btn btn-ghost"
                    style={{
                      fontSize: '12px',
                      padding: '5px 12px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-divider)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      color: 'var(--color-accent)',
                      cursor: 'pointer',
                    }}
                  >
                    <i className="ph ph-sliders-horizontal" style={{ fontSize: '14px' }}></i>
                    Manage Specialist Roster (Min 2, Max 6)
                  </button>
                ) : (
                  <span style={{ fontSize: '12px', color: '#c084fc', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <i className="ph ph-sparkle" style={{ fontSize: '14px' }}></i>
                    Generates {selectedAgentCount} match-specific personas dynamically across opposing camps
                  </span>
                )}
              </div>

              {/* Curated Dual-Camp Assignment Dashboard (Mode 2) */}
              {personaMode === 'custom' && (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                    gap: '12px',
                    padding: '8px 0 12px 0',
                    alignItems: 'stretch',
                  }}
                >
                  {/* CAMP A CONTAINER */}
                  <div
                    style={{
                      background: 'linear-gradient(135deg, rgba(0, 245, 155, 0.06) 0%, rgba(6, 10, 18, 0.85) 100%)',
                      border: '1px solid rgba(0, 245, 155, 0.3)',
                      borderRadius: 'var(--radius-lg)',
                      padding: '12px 14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px',
                      boxShadow: '0 4px 20px rgba(0, 245, 155, 0.08)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                          style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: '#00f59b',
                            boxShadow: '0 0 10px #00f59b',
                          }}
                        />
                        <span style={{ fontSize: '12px', fontWeight: 700, color: '#00f59b', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                          Camp A • Thesis / Left Pitch
                        </span>
                        <span
                          style={{
                            fontSize: '10.5px',
                            fontFamily: 'monospace',
                            padding: '1px 7px',
                            borderRadius: '999px',
                            background: 'rgba(0, 245, 155, 0.15)',
                            color: '#00f59b',
                            border: '1px solid rgba(0, 245, 155, 0.3)',
                          }}
                        >
                          {campAPersonaIds.length} {campAPersonaIds.length === 1 ? 'agent' : 'agents'}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setPersonaManagerModalOpen(true)}
                        style={{
                          background: 'transparent',
                          border: '1px dashed rgba(0, 245, 155, 0.5)',
                          color: '#00f59b',
                          fontSize: '11px',
                          padding: '2px 8px',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                        title="Add specialist persona to Camp A"
                      >
                        <i className="ph ph-plus" style={{ fontSize: '11px' }}></i>
                        Add
                      </button>
                    </div>

                    {/* Agent Chips in Camp A */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {campAPersonaIds.map((pid) => {
                        const info = getAgentInfo(pid, { camp: 'Camp A' }, selectedPersonaIds);
                        return (
                          <div
                            key={pid}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '4px 10px',
                              borderRadius: '8px',
                              background: 'rgba(0, 245, 155, 0.08)',
                              border: '1px solid rgba(0, 245, 155, 0.25)',
                              fontSize: '11.5px',
                              color: '#f1f5f9',
                            }}
                          >
                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: info.color }}></span>
                            <span style={{ fontWeight: 500 }}>{info.name}</span>

                            {/* Move to Camp B Button */}
                            <button
                              type="button"
                              onClick={() => handleMovePersonaCamp({ id: pid }, 'B')}
                              disabled={campAPersonaIds.length <= 1}
                              title={campAPersonaIds.length <= 1 ? 'Camp A must have at least 1 agent' : 'Move to Camp B'}
                              style={{
                                background: 'rgba(192, 132, 252, 0.15)',
                                border: '1px solid rgba(192, 132, 252, 0.35)',
                                color: '#c084fc',
                                borderRadius: '4px',
                                padding: '1px 5px',
                                fontSize: '10px',
                                cursor: campAPersonaIds.length <= 1 ? 'not-allowed' : 'pointer',
                                opacity: campAPersonaIds.length <= 1 ? 0.4 : 1,
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '2px',
                                marginLeft: '2px',
                              }}
                            >
                              ⇄ B
                            </button>

                            {/* Remove Button */}
                            {selectedPersonaIds.length > 2 && campAPersonaIds.length > 1 && (
                              <button
                                type="button"
                                onClick={() => handleRemovePersonaFromArena({ id: pid })}
                                title={`Remove ${info.name}`}
                                style={{
                                  background: 'transparent',
                                  border: 0,
                                  color: 'var(--color-neutral-400)',
                                  cursor: 'pointer',
                                  padding: '0 2px',
                                  fontSize: '13px',
                                  lineHeight: 1,
                                }}
                              >
                                ×
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* CAMP B CONTAINER */}
                  <div
                    style={{
                      background: 'linear-gradient(135deg, rgba(192, 132, 252, 0.06) 0%, rgba(6, 10, 18, 0.85) 100%)',
                      border: '1px solid rgba(192, 132, 252, 0.3)',
                      borderRadius: 'var(--radius-lg)',
                      padding: '12px 14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px',
                      boxShadow: '0 4px 20px rgba(192, 132, 252, 0.08)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                          style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: '#c084fc',
                            boxShadow: '0 0 10px #c084fc',
                          }}
                        />
                        <span style={{ fontSize: '12px', fontWeight: 700, color: '#c084fc', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                          Camp B • Counter / Right Pitch
                        </span>
                        <span
                          style={{
                            fontSize: '10.5px',
                            fontFamily: 'monospace',
                            padding: '1px 7px',
                            borderRadius: '999px',
                            background: 'rgba(192, 132, 252, 0.15)',
                            color: '#c084fc',
                            border: '1px solid rgba(192, 132, 252, 0.3)',
                          }}
                        >
                          {campBPersonaIds.length} {campBPersonaIds.length === 1 ? 'agent' : 'agents'}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setPersonaManagerModalOpen(true)}
                        style={{
                          background: 'transparent',
                          border: '1px dashed rgba(192, 132, 252, 0.5)',
                          color: '#c084fc',
                          fontSize: '11px',
                          padding: '2px 8px',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                        title="Add specialist persona to Camp B"
                      >
                        <i className="ph ph-plus" style={{ fontSize: '11px' }}></i>
                        Add
                      </button>
                    </div>

                    {/* Agent Chips in Camp B */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {campBPersonaIds.map((pid) => {
                        const info = getAgentInfo(pid, { camp: 'Camp B' }, selectedPersonaIds);
                        return (
                          <div
                            key={pid}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '4px 10px',
                              borderRadius: '8px',
                              background: 'rgba(192, 132, 252, 0.08)',
                              border: '1px solid rgba(192, 132, 252, 0.25)',
                              fontSize: '11.5px',
                              color: '#f1f5f9',
                            }}
                          >
                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: info.color }}></span>
                            <span style={{ fontWeight: 500 }}>{info.name}</span>

                            {/* Move to Camp A Button */}
                            <button
                              type="button"
                              onClick={() => handleMovePersonaCamp({ id: pid }, 'A')}
                              disabled={campBPersonaIds.length <= 1}
                              title={campBPersonaIds.length <= 1 ? 'Camp B must have at least 1 agent' : 'Move to Camp A'}
                              style={{
                                background: 'rgba(0, 245, 155, 0.15)',
                                border: '1px solid rgba(0, 245, 155, 0.35)',
                                color: '#00f59b',
                                borderRadius: '4px',
                                padding: '1px 5px',
                                fontSize: '10px',
                                cursor: campBPersonaIds.length <= 1 ? 'not-allowed' : 'pointer',
                                opacity: campBPersonaIds.length <= 1 ? 0.4 : 1,
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '2px',
                                marginLeft: '2px',
                              }}
                            >
                              ⇄ A
                            </button>

                            {/* Remove Button */}
                            {selectedPersonaIds.length > 2 && campBPersonaIds.length > 1 && (
                              <button
                                type="button"
                                onClick={() => handleRemovePersonaFromArena({ id: pid })}
                                title={`Remove ${info.name}`}
                                style={{
                                  background: 'transparent',
                                  border: 0,
                                  color: 'var(--color-neutral-400)',
                                  cursor: 'pointer',
                                  padding: '0 2px',
                                  fontSize: '13px',
                                  lineHeight: 1,
                                }}
                              >
                                ×
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
              <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div
                  style={{
                    flex: '1 1 360px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    padding: '0 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'color-mix(in srgb, var(--color-bg) 70%, transparent)',
                    border: '1px solid var(--color-divider)',
                    minWidth: 0,
                    minHeight: '50px',
                    boxShadow: query.trim() ? '0 0 14px color-mix(in srgb, var(--color-accent) 20%, transparent)' : 'none',
                    transition: 'border-color 0.18s ease, box-shadow 0.18s ease',
                  }}
                >
                  <i
                    className="ph ph-magnifying-glass"
                    style={{
                      fontSize: '18px',
                      color: 'var(--color-neutral-500)',
                      marginTop: '15px',
                      flexShrink: 0,
                    }}
                  />
                  <textarea
                    ref={queryInputRef}
                    rows={1}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleStart();
                      }
                    }}
                    placeholder="Enter any match or tactical question to deliberate... (e.g. Argentina vs France 2022 Final)"
                    style={{
                      flex: 1,
                      minWidth: 0,
                      minHeight: '48px',
                      maxHeight: '300px',
                      border: 0,
                      outline: 0,
                      background: 'transparent',
                      color: 'var(--color-neutral-100)',
                      font: '400 15px var(--font-body)',
                      resize: 'none',
                      overflowY: 'auto',
                      lineHeight: '1.5',
                      padding: '13px 0',
                      boxSizing: 'border-box',
                    }}
                  />
                  {query && (
                    <button
                      type="button"
                      onClick={() => setQuery('')}
                      title="Clear topic"
                      style={{
                        background: 'transparent',
                        border: 0,
                        color: 'var(--color-neutral-400)',
                        cursor: 'pointer',
                        padding: '14px 0 0 0',
                        fontSize: '16px',
                        lineHeight: 1,
                        flexShrink: 0,
                      }}
                    >
                      <i className="ph ph-x-circle"></i>
                    </button>
                  )}
                </div>
                {/* Rounds Dropdown Selector */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '0 14px',
                    height: '50px',
                    borderRadius: 'var(--radius-md)',
                    background: 'color-mix(in srgb, var(--color-bg) 70%, transparent)',
                    border: '1px solid var(--color-divider)',
                    flexShrink: 0,
                  }}
                >
                  <i className="ph ph-arrows-clockwise" style={{ fontSize: '16px', color: 'var(--color-accent)' }}></i>
                  <span style={{ fontSize: '12px', color: 'var(--color-neutral-400)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
                    Rounds:
                  </span>
                  <select
                    value={selectedRounds}
                    onChange={(e) => setSelectedRounds(Number(e.target.value))}
                    disabled={isStarting}
                    aria-label="Select number of deliberation rounds"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      outline: 'none',
                      color: 'var(--color-neutral-100)',
                      font: '600 13px var(--font-body)',
                      cursor: 'pointer',
                      padding: '4px 6px 4px 2px',
                    }}
                  >
                    <option value={2} style={{ background: '#0c1224', color: '#f1f5f9' }}>2 Rounds</option>
                    <option value={3} style={{ background: '#0c1224', color: '#f1f5f9' }}>3 Rounds (Default)</option>
                    <option value={4} style={{ background: '#0c1224', color: '#f1f5f9' }}>4 Rounds</option>
                    <option value={5} style={{ background: '#0c1224', color: '#f1f5f9' }}>5 Rounds</option>
                  </select>
                </div>
                {/* Agent Count Selector in Dynamic Mode OR Roster Status in Curated Mode */}
                {personaMode === 'dynamic' ? (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '0 12px',
                      height: '50px',
                      borderRadius: 'var(--radius-md)',
                      background: 'color-mix(in srgb, var(--color-bg) 70%, transparent)',
                      border: '1px solid rgba(168, 85, 247, 0.4)',
                      flexShrink: 0,
                    }}
                  >
                    <i className="ph ph-sparkle" style={{ fontSize: '16px', color: '#c084fc' }}></i>
                    <span style={{ fontSize: '12px', color: '#c084fc', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
                      Agents:
                    </span>
                    <select
                      value={selectedAgentCount}
                      onChange={(e) => setSelectedAgentCount(Number(e.target.value))}
                      disabled={isStarting}
                      aria-label="Select number of agents in dynamic deliberation"
                      style={{
                        background: 'transparent',
                        border: 'none',
                        outline: 'none',
                        color: 'var(--color-neutral-100)',
                        font: '600 13px var(--font-body)',
                        cursor: 'pointer',
                        padding: '4px 6px 4px 2px',
                      }}
                    >
                      <option value={2} style={{ background: '#0c1224', color: '#f1f5f9' }}>2 Agents (1v1 Clash)</option>
                      <option value={3} style={{ background: '#0c1224', color: '#f1f5f9' }}>3 Agents (Triad)</option>
                      <option value={4} style={{ background: '#0c1224', color: '#f1f5f9' }}>4 Agents (2v2 Tactical Box)</option>
                      <option value={5} style={{ background: '#0c1224', color: '#f1f5f9' }}>5 Agents</option>
                      <option value={6} style={{ background: '#0c1224', color: '#f1f5f9' }}>6 Agents (Full Pitch 3v3)</option>
                    </select>
                  </div>
                ) : (
                  <div
                    onClick={() => setPersonaManagerModalOpen(true)}
                    title="Click to manage active roster personas (Min 2, Max 6)"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '0 12px',
                      height: '50px',
                      borderRadius: 'var(--radius-md)',
                      background: 'color-mix(in srgb, var(--color-bg) 70%, transparent)',
                      border: '1px solid var(--color-divider)',
                      flexShrink: 0,
                      cursor: 'pointer',
                    }}
                  >
                    <i className="ph ph-users" style={{ fontSize: '16px', color: 'var(--color-accent)' }}></i>
                    <span style={{ fontSize: '12px', color: 'var(--color-neutral-400)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
                      Roster:
                    </span>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-neutral-100)' }}>
                      {selectedPersonaIds.length}/6 (A:{campAPersonaIds.length} | B:{campBPersonaIds.length})
                    </span>
                  </div>
                )}
                <button
                  className="btn btn-primary"
                  onClick={() => handleStart()}
                  disabled={
                    isStarting ||
                    !query.trim() ||
                    (personaMode === 'custom' && (
                      campAPersonaIds.length < 1 ||
                      campBPersonaIds.length < 1 ||
                      selectedPersonaIds.length < 2 ||
                      selectedPersonaIds.length > 6
                    ))
                  }
                  title={
                    personaMode === 'custom' && campAPersonaIds.length < 1
                      ? 'Camp A must have at least 1 agent'
                      : personaMode === 'custom' && campBPersonaIds.length < 1
                      ? 'Camp B must have at least 1 agent'
                      : personaMode === 'custom' && selectedPersonaIds.length < 2
                      ? 'Please select at least 2 personas for deliberation'
                      : personaMode === 'custom' && selectedPersonaIds.length > 6
                      ? 'Maximum 6 personas allowed for deliberation'
                      : undefined
                  }
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
                  Agents are querying evidence and cross-examining arguments.
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
                      {currentDiscussionStatus === 'completed' ? 'Completed deliberation' : 'Active deliberation'}
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
                          {roundAlignment != null ? `${roundAlignment}%` : '--'}
                        </span>{' '}
                        Consensus
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)', fontVariantNumeric: 'tabular-nums' }}>
                        {cursor === 0 ? 'Awaiting opening statements' : activeRound === 0 ? 'Round 0 (Opening Statements)' : `Round ${activeRound} of ${currentDiscussion.num_rounds || totalRounds}`}
                      </span>
                    </div>
                    <div style={{ height: '6px', borderRadius: '999px', background: 'var(--color-neutral-900)', overflow: 'hidden' }}>
                      <div
                        style={{
                          height: '100%',
                          width: roundAlignment != null ? `${roundAlignment}%` : '0%',
                          borderRadius: '999px',
                          background: 'linear-gradient(90deg, var(--color-accent-700), var(--color-accent))',
                          boxShadow: roundAlignment != null ? '0 0 12px var(--color-accent)' : 'none',
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

                {/* Football Pitch Agent Communication Graph (Image #1) */}
                <AgentCommunicationPitch
                  agents={debateAgentRoster || currentDiscussion?.agents || activeAgents}
                  messages={rawMsgs}
                  activeRound={activeRound}
                  consensus={roundAlignment ?? '--'}
                  cursor={cursor}
                  playing={playing}
                  activePassEvent={activePassEvent}
                  onSelectAgent={(aid) => setHoverAgent(aid)}
                />

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
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {availableRounds.map((r) => {
                      const on = cursor > 0 && r === activeRound;
                      return (
                        <button
                          key={r}
                          onClick={() => {
                            pause();
                            const next = rawMsgs.filter((m) => m.round_num <= r).length;
                            setCursor(next);
                            triggerPassForCursor(next);
                          }}
                          style={{
                            padding: '7px 14px',
                            borderRadius: 'var(--radius-md)',
                            border: on ? '1px solid var(--color-accent)' : '1px solid var(--color-divider)',
                            background: on ? 'color-mix(in srgb, var(--color-accent) 14%, transparent)' : 'transparent',
                            color: on ? 'var(--color-accent-100)' : 'var(--color-neutral-400)',
                            font: '500 13px var(--font-body)',
                            cursor: 'pointer',
                            transition: 'all 0.15s ease',
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
                        setCursor((c) => {
                          const next = Math.max(0, c - 1);
                          triggerPassForCursor(next);
                          return next;
                        });
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
                        setCursor((c) => {
                          const next = Math.min(rawMsgs.length, c + 1);
                          triggerPassForCursor(next);
                          return next;
                        });
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
                    const agent = getAgentInfo(m.sender_id, null, debateAgentRoster || currentDiscussion?.agents);
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
                              <span style={{ fontSize: '12px', color: 'var(--color-neutral-600)', fontVariantNumeric: 'tabular-nums', marginLeft: 'auto' }}>
                                Round {m.round_num}
                              </span>
                            </div>
                            <MarkdownPreview
                              content={m.content}
                              style={{ margin: 0, fontSize: '14.5px', lineHeight: 1.6, textWrap: 'pretty' }}
                            />
                          </div>
                        </article>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {!currentDiscussion && currentDiscussionStatus === 'checking' && (
              <p role="status" style={{ color: 'var(--color-neutral-400)' }}>Loading discussion and checking completion…</p>
            )}

            {discussionLoadError && (
              <div
                role="alert"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '12px 18px',
                  borderRadius: 'var(--radius-md)',
                  background: 'color-mix(in srgb, #f43f5e 12%, transparent)',
                  border: '1px solid color-mix(in srgb, #f43f5e 35%, transparent)',
                  color: '#fda4af',
                  fontSize: '13px',
                }}
              >
                <i className="ph ph-warning-circle" style={{ fontSize: '18px', color: '#f43f5e' }}></i>
                <span>{discussionLoadError}</span>
              </div>
            )}

            {/* Empty state when no debate has run yet and not starting */}
            {!currentDiscussion && !isStarting && !discussionLoadError && currentDiscussionStatus !== 'checking' && (
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
                    Arena Command Ready
                  </h3>
                  <p style={{ margin: 0, fontSize: '14.5px', color: 'var(--color-neutral-400)', lineHeight: 1.5 }}>
                    Enter a fixture, match question or debate thesis in the command bar above — or pick one of the
                    tactical briefings below. Six autonomous specialist agents will query live match evidence,
                    cross-examine opposing viewpoints and calculate consensus.
                  </p>
                </div>

                {/* Suggested tactical briefings — fill the query input */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', justifyContent: 'center', maxWidth: '820px' }}>
                  {[
                    'Germany vs Japan 2022 tactical breakdown',
                    'Argentina vs France 2022 Final',
                    'Arsenal clinical striker January transfer',
                  ].map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => setQuery(suggestion)}
                      title={`Load "${suggestion}" into the command bar`}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '9px 15px',
                        borderRadius: '999px',
                        background: 'color-mix(in srgb, var(--color-accent) 8%, transparent)',
                        border: '1px solid color-mix(in srgb, var(--color-accent) 32%, transparent)',
                        color: 'var(--color-accent-100)',
                        font: '500 13px var(--font-body)',
                        cursor: 'pointer',
                        transition: 'all .15s ease',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'color-mix(in srgb, var(--color-accent) 18%, transparent)';
                        e.currentTarget.style.borderColor = 'var(--color-accent)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'color-mix(in srgb, var(--color-accent) 8%, transparent)';
                        e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--color-accent) 32%, transparent)';
                      }}
                    >
                      <i className="ph ph-lightning" style={{ fontSize: '14px' }}></i>
                      {suggestion}
                    </button>
                  ))}
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
        {isAuthenticated && tab === 'history' && (
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
                    {h.status === 'queued' ? (
                      <span
                        className="tag"
                        style={{
                          color: 'var(--color-accent-300, #38bdf8)',
                          borderColor: 'var(--color-accent-400, #0284c7)',
                          background: 'color-mix(in srgb, var(--color-accent, #0284c7) 15%, transparent)',
                        }}
                      >
                        Queued in Worker
                      </span>
                    ) : h.status === 'running' ? (
                      <span
                        className="tag"
                        style={{
                          color: '#4ade80',
                          borderColor: '#22c55e',
                          background: 'color-mix(in srgb, #22c55e 15%, transparent)',
                        }}
                      >
                        Deliberating Live
                      </span>
                    ) : (h.num_messages === 0 || h.status === 'failed') ? (
                      <span
                        className="tag"
                        style={{
                          color: 'var(--color-amber-300, #fbbf24)',
                          borderColor: 'var(--color-amber-400, #f59e0b)',
                          background: 'color-mix(in srgb, var(--color-amber-500, #f59e0b) 12%, transparent)',
                        }}
                      >
                        Failed / No messages recorded
                      </span>
                    ) : null}
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
                  {(h.status === 'queued' || h.status === 'running') ? (
                    <button
                      className="btn btn-primary"
                      onClick={() => {
                        loadDiscussionById(h.discussion_id);
                        navigateTo('arena', { id: h.discussion_id });
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }}
                      style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '7px' }}
                    >
                      <i className="ph ph-broadcast" style={{ fontSize: '15px' }}></i>
                      Watch Live
                    </button>
                  ) : (h.num_messages === 0 || h.status === 'failed') ? (
                    <button
                      className="btn"
                      onClick={() => {
                        setQuery(h.topic);
                        navigateTo('arena');
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }}
                      style={{
                        marginTop: 'auto',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '7px',
                        background: 'var(--color-amber-500, #f59e0b)',
                        color: '#1a1a1a',
                      }}
                    >
                      <i className="ph ph-arrow-clockwise" style={{ fontSize: '15px' }}></i>
                      Retry Topic
                    </button>
                  ) : (
                    <button
                      className="btn btn-primary"
                      onClick={() => {
                        loadDiscussionById(h.discussion_id);
                        navigateTo('arena', { id: h.discussion_id });
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }}
                      style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '7px' }}
                    >
                      <i className="ph ph-arrow-counter-clockwise" style={{ fontSize: '15px' }}></i>
                      Resume / Replay
                    </button>
                  )}
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
        {isAuthenticated && tab === 'intel' && (
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
                  <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <span style={{ fontSize: '42px', fontWeight: 600, letterSpacing: '-0.03em', color: 'var(--color-accent-200)', fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
                        {roundAlignment != null ? `${roundAlignment}%` : '--'}
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--color-neutral-400)' }}>
                        Round {activeRound} Consensus
                      </span>
                    </div>
                    <div style={{ width: '1px', height: '38px', background: 'var(--color-divider)' }}></div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <span style={{ fontSize: '28px', fontWeight: 600, letterSpacing: '-0.02em', color: 'var(--color-accent-300)', fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
                        {consensus != null ? `${consensus}%` : '--'}
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)' }}>
                        Overall Consensus
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <span style={{ fontSize: '12px', color: 'var(--color-neutral-500)' }}>
                      Executive Deliberation Summary
                    </span>
                    <p style={{ margin: 0, fontSize: '15px', lineHeight: 1.6, color: 'var(--color-neutral-200)', textWrap: 'pretty' }}>
                      {activeSynthesisData?.tactical_verdict
                        ? activeSynthesisData.tactical_verdict
                        : (currentAnalytics?.overall_trend && currentAnalytics.overall_trend !== 'Insufficient Data'
                          ? `Trend: ${currentAnalytics.overall_trend}. Top influential arbiter: ${getAgentInfo(currentAnalytics.top_influencer, null, debateAgentRoster || currentDiscussion?.agents).name}.`
                          : `Deliberation on "${currentDiscussion.topic}" synthesized across ${rawMsgs.length} messages with active perspective convergence.`)}
                    </p>
                  </div>
                </div>

                {/* ─── STRATEGIC ADVISOR LLM & DECISION DOSSIER ─── */}
                <div
                  style={{
                    padding: '24px',
                    borderRadius: 'var(--radius-lg)',
                    background: 'radial-gradient(ellipse at top left, color-mix(in srgb, var(--color-accent) 12%, transparent), color-mix(in srgb, var(--color-surface) 60%, transparent) 70%)',
                    backdropFilter: 'blur(24px)',
                    WebkitBackdropFilter: 'blur(24px)',
                    border: '1px solid color-mix(in srgb, var(--color-accent) 35%, var(--color-divider))',
                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.35)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '20px',
                  }}
                >
                  {/* Header Bar */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div
                        style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: '8px',
                          background: 'color-mix(in srgb, var(--color-accent) 20%, transparent)',
                          border: '1px solid color-mix(in srgb, var(--color-accent) 50%, transparent)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'var(--color-accent-300)',
                        }}
                      >
                        <i className="ph ph-gavel" style={{ fontSize: '20px' }}></i>
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <h3 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: '18px', color: 'var(--color-neutral-100)', letterSpacing: '-0.01em' }}>
                            Strategic Advisor Decision Dossier
                          </h3>
                          <span
                            style={{
                              fontSize: '10.5px',
                              padding: '2px 8px',
                              borderRadius: '999px',
                              background: 'color-mix(in srgb, var(--color-accent) 20%, transparent)',
                              color: 'var(--color-accent-300)',
                              border: '1px solid color-mix(in srgb, var(--color-accent) 40%, transparent)',
                              fontWeight: 700,
                              letterSpacing: '0.04em',
                              textTransform: 'uppercase',
                            }}
                          >
                            {activeAdvisorData?.topic_type || 'EXECUTIVE ARBITER'}
                          </span>
                        </div>
                        <span style={{ fontSize: '12px', color: 'var(--color-neutral-400)' }}>
                          Authoritative technical ruling and actionable execution plan for "{currentDiscussion.topic}"
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleFetchAdvisor(true)}
                      disabled={isComputingAdvisor}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '7px 14px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid color-mix(in srgb, var(--color-accent) 30%, var(--color-divider))',
                        background: 'color-mix(in srgb, var(--color-surface) 80%, transparent)',
                        color: 'var(--color-neutral-200)',
                        fontSize: '12px',
                        fontWeight: 600,
                        cursor: isComputingAdvisor ? 'not-allowed' : 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <i className={isComputingAdvisor ? 'ph ph-spinner ph-spin' : 'ph ph-arrows-clockwise'} style={{ fontSize: '14px', color: 'var(--color-accent-300)' }}></i>
                      {isComputingAdvisor ? 'Adjudicating Debate...' : 'Re-Evaluate Ruling'}
                    </button>
                  </div>

                  {isComputingAdvisor && !activeAdvisorData ? (
                    <div style={{ padding: '36px', textAlign: 'center', color: 'var(--color-neutral-400)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                      <i className="ph ph-spinner ph-spin" style={{ fontSize: '28px', color: 'var(--color-accent-300)' }}></i>
                      <span style={{ fontSize: '14px' }}>Evaluating conflicting peer arguments, stress-testing evidence, and formulating final decision...</span>
                    </div>
                  ) : activeAdvisorData ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                      {/* Hero Ruling Card */}
                      <div
                        style={{
                          padding: '20px',
                          borderRadius: 'var(--radius-md)',
                          background: 'linear-gradient(135deg, color-mix(in srgb, var(--color-accent) 14%, transparent), color-mix(in srgb, var(--color-surface) 80%, transparent))',
                          border: '1px solid color-mix(in srgb, var(--color-accent) 45%, transparent)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '12px',
                          boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.08)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span
                              style={{
                                fontSize: '12px',
                                fontWeight: 800,
                                letterSpacing: '0.08em',
                                padding: '4px 10px',
                                borderRadius: '6px',
                                background: 'var(--color-accent)',
                                color: '#002511',
                                textTransform: 'uppercase',
                              }}
                            >
                              {activeAdvisorData.verdict_badge || 'BINDING RULING'}
                            </span>
                            <span style={{ fontSize: '13px', color: 'var(--color-neutral-300)', fontWeight: 500 }}>
                              Definitive Technical Verdict
                            </span>
                          </div>
                          {activeAdvisorData.confidence_score != null && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--color-neutral-400)' }}>
                              <span>Decision Confidence:</span>
                              <strong style={{ color: 'var(--color-accent-300)', fontVariantNumeric: 'tabular-nums' }}>
                                {Math.round(activeAdvisorData.confidence_score * 100)}%
                              </strong>
                            </div>
                          )}
                        </div>

                        <p style={{ margin: 0, fontSize: '16px', fontWeight: 600, lineHeight: 1.55, color: 'var(--color-neutral-100)', letterSpacing: '-0.01em' }}>
                          "{activeAdvisorData.definitive_ruling}"
                        </p>
                      </div>

                      {/* Deciding Factor */}
                      {activeAdvisorData.deciding_factor && (
                        <div
                          style={{
                            padding: '14px 18px',
                            borderRadius: 'var(--radius-md)',
                            background: 'rgba(255, 255, 255, 0.02)',
                            border: '1px solid var(--color-divider)',
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: '12px',
                          }}
                        >
                          <div style={{ padding: '6px', borderRadius: '6px', background: 'rgba(251, 191, 36, 0.15)', color: '#fbbf24', marginTop: '2px' }}>
                            <i className="ph ph-lightning" style={{ fontSize: '16px' }}></i>
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.06em', color: '#fbbf24', textTransform: 'uppercase' }}>
                              Core Deciding Factor
                            </span>
                            <span style={{ fontSize: '13.5px', color: 'var(--color-neutral-200)', lineHeight: 1.5 }}>
                              {activeAdvisorData.deciding_factor}
                            </span>
                          </div>
                        </div>
                      )}

                      {/* 3-Step Action Plan */}
                      {activeAdvisorData.action_plan?.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <i className="ph ph-check-square-offset" style={{ fontSize: '16px', color: 'var(--color-accent-300)' }}></i>
                            <span style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.04em', color: 'var(--color-neutral-200)', textTransform: 'uppercase' }}>
                              Actionable Directives (Execution Protocol)
                            </span>
                          </div>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: '10px' }}>
                            {activeAdvisorData.action_plan.map((step, idx) => (
                              <div
                                key={idx}
                                style={{
                                  padding: '14px 16px',
                                  borderRadius: 'var(--radius-md)',
                                  background: 'color-mix(in srgb, var(--color-surface) 75%, transparent)',
                                  border: '1px solid var(--color-divider)',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '8px',
                                }}
                              >
                                <span style={{ fontSize: '12px', fontWeight: 800, color: 'var(--color-accent-300)', fontFamily: 'var(--font-heading)' }}>
                                  DIRECTIVE {String(idx + 1).padStart(2, '0')}
                                </span>
                                <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.5, color: 'var(--color-neutral-300)' }}>
                                  {step.replace(/^\d+\.\s*/, '')}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Risk & Mitigation Dual Grid */}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: '12px' }}>
                        {activeAdvisorData.primary_risk && (
                          <div
                            style={{
                              padding: '14px 16px',
                              borderRadius: 'var(--radius-md)',
                              background: 'rgba(244, 63, 94, 0.05)',
                              border: '1px solid rgba(244, 63, 94, 0.25)',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '6px',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f43f5e', fontSize: '11.5px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                              <i className="ph ph-warning-circle" style={{ fontSize: '14px' }}></i>
                              Primary Strategic Risk
                            </div>
                            <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-neutral-300)', lineHeight: 1.5 }}>
                              {activeAdvisorData.primary_risk}
                            </p>
                          </div>
                        )}

                        {activeAdvisorData.mitigation_strategy && (
                          <div
                            style={{
                              padding: '14px 16px',
                              borderRadius: 'var(--radius-md)',
                              background: 'color-mix(in srgb, var(--color-accent) 6%, transparent)',
                              border: '1px solid color-mix(in srgb, var(--color-accent) 30%, transparent)',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '6px',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--color-accent-300)', fontSize: '11.5px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                              <i className="ph ph-shield-check" style={{ fontSize: '14px' }}></i>
                              Mitigation & Safeguard
                            </div>
                            <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-neutral-300)', lineHeight: 1.5 }}>
                              {activeAdvisorData.mitigation_strategy}
                            </p>
                          </div>
                        )}
                      </div>

                      {/* Stakeholder Impact Strip */}
                      {activeAdvisorData.stakeholder_impacts && (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))', gap: '10px', paddingTop: '4px' }}>
                          {activeAdvisorData.stakeholder_impacts.sporting_impact && (
                            <div style={{ padding: '10px 14px', borderRadius: '6px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--color-divider)' }}>
                              <span style={{ fontSize: '11px', color: 'var(--color-neutral-500)', textTransform: 'uppercase', fontWeight: 600 }}>On-Pitch Tactical</span>
                              <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: 'var(--color-neutral-300)', lineHeight: 1.4 }}>{activeAdvisorData.stakeholder_impacts.sporting_impact}</p>
                            </div>
                          )}
                          {activeAdvisorData.stakeholder_impacts.squad_impact && (
                            <div style={{ padding: '10px 14px', borderRadius: '6px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--color-divider)' }}>
                              <span style={{ fontSize: '11px', color: 'var(--color-neutral-500)', textTransform: 'uppercase', fontWeight: 600 }}>Squad & Hierarchy</span>
                              <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: 'var(--color-neutral-300)', lineHeight: 1.4 }}>{activeAdvisorData.stakeholder_impacts.squad_impact}</p>
                            </div>
                          )}
                          {activeAdvisorData.stakeholder_impacts.strategic_impact && (
                            <div style={{ padding: '10px 14px', borderRadius: '6px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--color-divider)' }}>
                              <span style={{ fontSize: '11px', color: 'var(--color-neutral-500)', textTransform: 'uppercase', fontWeight: 600 }}>Institutional / Legacy</span>
                              <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: 'var(--color-neutral-300)', lineHeight: 1.4 }}>{activeAdvisorData.stakeholder_impacts.strategic_impact}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-neutral-500)' }}>
                      <span>No strategic advisor ruling has been computed for this deliberation yet. Click "Re-Evaluate Ruling" above to generate.</span>
                    </div>
                  )}
                </div>

                {/* ─── LLM EXECUTIVE SYNTHESIS & AGENT DOSSIERS ─── */}
                <div
                  style={{
                    padding: '24px',
                    borderRadius: 'var(--radius-lg)',
                    background: 'color-mix(in srgb, var(--color-surface) 50%, transparent)',
                    backdropFilter: 'blur(24px)',
                    WebkitBackdropFilter: 'blur(24px)',
                    border: '1px solid color-mix(in srgb, var(--color-accent) 28%, var(--color-divider))',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '20px',
                  }}
                >
                  {/* Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <i className="ph ph-sparkle" style={{ fontSize: '20px', color: 'var(--color-accent-300)' }}></i>
                      <h3 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: '18px', color: 'var(--color-neutral-100)' }}>
                        Executive Tactical Synthesis & Agent Evaluations
                      </h3>
                      <span
                        style={{
                          fontSize: '11px',
                          padding: '2px 8px',
                          borderRadius: '999px',
                          background: 'color-mix(in srgb, var(--color-accent) 15%, transparent)',
                          color: 'var(--color-accent-300)',
                          border: '1px solid color-mix(in srgb, var(--color-accent) 30%, transparent)',
                          fontWeight: 600,
                        }}
                      >
                        LLM ARBITER
                      </span>
                    </div>

                    <button
                      onClick={() => handleFetchSynthesis(true)}
                      disabled={isComputingSynthesis}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 12px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--color-divider)',
                        background: 'color-mix(in srgb, var(--color-surface) 70%, transparent)',
                        color: 'var(--color-neutral-300)',
                        fontSize: '12px',
                        fontWeight: 500,
                        cursor: isComputingSynthesis ? 'not-allowed' : 'pointer',
                      }}
                    >
                      <i className={isComputingSynthesis ? 'ph ph-spinner ph-spin' : 'ph ph-arrows-clockwise'} style={{ fontSize: '13px' }}></i>
                      {isComputingSynthesis ? 'Analyzing Debate...' : 'Refresh Synthesis'}
                    </button>
                  </div>

                  {isComputingSynthesis && !activeSynthesisData ? (
                    <div style={{ padding: '36px', textAlign: 'center', color: 'var(--color-neutral-400)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
                      <i className="ph ph-spinner ph-spin" style={{ fontSize: '24px', color: 'var(--color-accent)' }}></i>
                      <span>Synthesizing debate dynamics and drafting agent evaluations...</span>
                    </div>
                  ) : activeSynthesisData ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                      {/* Tactical Verdict Box */}
                      <div
                        style={{
                          padding: '16px 20px',
                          borderRadius: 'var(--radius-md)',
                          background: 'color-mix(in srgb, var(--color-accent) 10%, transparent)',
                          borderLeft: '4px solid var(--color-accent)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px',
                        }}
                      >
                        <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.06em', color: 'var(--color-accent-300)', textTransform: 'uppercase' }}>
                          Tactical Verdict
                        </span>
                        <p style={{ margin: 0, fontSize: '15px', fontWeight: 500, lineHeight: 1.5, color: 'var(--color-neutral-100)' }}>
                          "{activeSynthesisData.tactical_verdict}"
                        </p>
                      </div>

                      {/* Narrative Summary */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-neutral-400)' }}>
                          Executive Narrative
                        </span>
                        <div style={{ fontSize: '14px', lineHeight: 1.7, color: 'var(--color-neutral-300)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          {activeSynthesisData.executive_summary?.split('\n\n').map((para, i) => (
                            <p key={i} style={{ margin: 0 }}>{para}</p>
                          ))}
                        </div>
                      </div>

                      {/* Key Tactical Findings */}
                      {activeSynthesisData.key_findings?.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-neutral-400)' }}>
                            Key Tactical Findings
                          </span>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: '8px' }}>
                            {activeSynthesisData.key_findings.map((f, i) => (
                              <div
                                key={i}
                                style={{
                                  padding: '10px 14px',
                                  borderRadius: 'var(--radius-md)',
                                  background: 'color-mix(in srgb, var(--color-surface) 40%, transparent)',
                                  border: '1px solid var(--color-divider)',
                                  fontSize: '13px',
                                  lineHeight: 1.5,
                                  color: 'var(--color-neutral-300)',
                                  display: 'flex',
                                  alignItems: 'flex-start',
                                  gap: '8px',
                                }}
                              >
                                <i className="ph ph-check-circle" style={{ fontSize: '15px', color: 'var(--color-accent)', marginTop: '2px', flexShrink: 0 }}></i>
                                <span>{f}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Agent Evaluation Dossiers Grid */}
                      {activeSynthesisData.agent_evaluations?.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '6px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-neutral-300)' }}>
                              Agent Deliberation Scorecards & Peer Commentary
                            </span>
                            <span style={{ fontSize: '11px', color: 'var(--color-neutral-500)' }}>
                              {activeSynthesisData.agent_evaluations.length} Agents Evaluated
                            </span>
                          </div>

                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))', gap: '12px' }}>
                            {activeSynthesisData.agent_evaluations.map((evalItem) => {
                              const aInfo = getAgentInfo(evalItem.agent_id, null, debateAgentRoster || currentDiscussion?.agents);
                              const rating = evalItem.performance_rating || 'Analytical';

                              let badgeBg = 'color-mix(in srgb, var(--color-accent) 15%, transparent)';
                              let badgeColor = 'var(--color-accent-300)';
                              if (rating === 'Influential') {
                                badgeBg = 'rgba(167, 139, 250, 0.15)';
                                badgeColor = '#c4b5fd';
                              } else if (rating === 'Adaptive') {
                                badgeBg = 'rgba(56, 189, 248, 0.15)';
                                badgeColor = '#7dd3fc';
                              } else if (rating === 'Dogmatic') {
                                badgeBg = 'rgba(244, 63, 94, 0.15)';
                                badgeColor = '#fda4af';
                              } else if (rating === 'Pragmatic') {
                                badgeBg = 'rgba(251, 191, 36, 0.15)';
                                badgeColor = '#fde68a';
                              }

                              return (
                                <div
                                  key={evalItem.agent_id}
                                  style={{
                                    padding: '16px',
                                    borderRadius: 'var(--radius-md)',
                                    background: 'color-mix(in srgb, var(--color-surface) 60%, transparent)',
                                    border: '1px solid var(--color-divider)',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: '12px',
                                  }}
                                >
                                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                                      <div
                                        style={{
                                          width: '28px',
                                          height: '28px',
                                          borderRadius: '50%',
                                          background: aInfo.color,
                                          color: '#000',
                                          display: 'flex',
                                          alignItems: 'center',
                                          justifyContent: 'center',
                                          fontSize: '12px',
                                          fontWeight: 700,
                                        }}
                                      >
                                        {aInfo.name[0]}
                                      </div>
                                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                                        <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-neutral-100)' }}>
                                          {aInfo.name}
                                        </span>
                                        <span style={{ fontSize: '11px', color: 'var(--color-neutral-500)' }}>
                                          {aInfo.role}
                                        </span>
                                      </div>
                                    </div>
                                    <span
                                      style={{
                                        padding: '2px 8px',
                                        borderRadius: '999px',
                                        background: badgeBg,
                                        color: badgeColor,
                                        fontSize: '11px',
                                        fontWeight: 600,
                                      }}
                                    >
                                      {rating}
                                    </span>
                                  </div>

                                  <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.6, color: 'var(--color-neutral-300)' }}>
                                    {evalItem.commentary}
                                  </p>

                                  {evalItem.key_contribution && (
                                    <div
                                      style={{
                                        marginTop: 'auto',
                                        padding: '8px 10px',
                                        borderRadius: 'var(--radius-sm)',
                                        background: 'color-mix(in srgb, var(--color-surface) 35%, transparent)',
                                        border: '1px solid var(--color-divider)',
                                        fontSize: '11px',
                                        lineHeight: 1.4,
                                        color: 'var(--color-neutral-400)',
                                      }}
                                    >
                                      <strong style={{ color: 'var(--color-accent-300)' }}>Key Contribution: </strong>
                                      {evalItem.key_contribution}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-neutral-400)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                      <p style={{ margin: 0, fontSize: '13px' }}>
                        No executive synthesis generated yet for this debate.
                      </p>
                      <button
                        onClick={() => handleFetchSynthesis(true)}
                        className="btn btn-primary"
                        style={{ fontSize: '12px', padding: '6px 14px' }}
                      >
                        <i className="ph ph-sparkle"></i> Generate Tactical Synthesis
                      </button>
                    </div>
                  )}
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
                      {derivedTrajectories ? Object.entries(derivedTrajectories).map(([id, pts]) => {
                        const isHovered = hoverAgent === id;
                        const opacity = hoverAgent && !isHovered ? 0.18 : 1;
                        const strokeWidth = isHovered ? 3.5 : 2;
                        const a = getAgentInfo(id, null, debateAgentRoster || currentDiscussion?.agents);
                        const measuredPts = pts.filter((v) => v != null);
                        const lastPt = measuredPts[measuredPts.length - 1];
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
                            {lastPt != null && (
                              <circle cx="620" cy={Y(lastPt)} r="3.5" fill={a.color} opacity={opacity} />
                            )}
                          </g>
                        );
                      }) : (
                        <text x="330" y="150" textAnchor="middle" fontSize="13" fill="var(--color-neutral-500)">
                          Stances not yet scored for this discussion
                        </text>
                      )}
                    </svg>

                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      {derivedTrajectories ? Object.keys(derivedTrajectories).map((id) => {
                        const a = getAgentInfo(id, null, debateAgentRoster || currentDiscussion?.agents);
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
                      }) : null}
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
                    {derivedInfluence ? derivedInfluence.map((f, i) => {
                      const agent = getAgentInfo(f.id, null, debateAgentRoster || currentDiscussion?.agents);
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
                    }) : (
                      <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-neutral-500)' }}>
                        Influence scores need stance movement across consecutive rounds — none measurable yet for this discussion.
                      </p>
                    )}
                  </div>
                </div>

                {/* Causal Counterfactual Ablation (LLM Judge) */}
                <div
                  style={{
                    padding: '24px',
                    borderRadius: 'var(--radius-lg)',
                    background: 'color-mix(in srgb, var(--color-surface) 48%, transparent)',
                    backdropFilter: 'blur(24px)',
                    WebkitBackdropFilter: 'blur(24px)',
                    border: '1px solid color-mix(in srgb, var(--color-accent) 30%, var(--color-divider))',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '20px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <h3 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: '18px', color: 'var(--color-neutral-100)' }}>
                          Causal Counterfactual Analysis
                        </h3>
                        <span
                          style={{
                            fontSize: '11px',
                            padding: '2px 8px',
                            borderRadius: '999px',
                            background: 'color-mix(in srgb, var(--color-accent) 15%, transparent)',
                            color: 'var(--color-accent-300)',
                            border: '1px solid color-mix(in srgb, var(--color-accent) 30%, transparent)',
                            fontWeight: 500,
                          }}
                        >
                          LLM-as-a-Judge Ablation
                        </span>
                      </div>
                      <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-neutral-400)', maxWidth: '640px', lineHeight: 1.5 }}>
                        Simulates counterfactual silence (¬A) across directed peer exchanges to determine if an agent genuinely caused peer stance movement or if the shift was baseline drift.
                      </p>
                    </div>

                    <div>
                      {activeCausalData && (activeCausalData.evaluated_exchanges_count || 0) > 0 ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 14px', borderRadius: '999px', background: 'rgba(34, 197, 94, 0.12)', border: '1px solid rgba(34, 197, 94, 0.3)' }}>
                          <i className="ph ph-check-circle" style={{ color: '#4ade80', fontSize: '16px' }}></i>
                          <span style={{ fontSize: '12px', fontWeight: 600, color: '#4ade80' }}>Cached & Verified (No Rerun)</span>
                        </div>
                      ) : (
                        <button
                          onClick={handleRunCausalAnalysis}
                          disabled={isComputingCausal}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '9px 18px',
                            borderRadius: 'var(--radius-md)',
                            background: 'linear-gradient(135deg, var(--color-accent-700), var(--color-accent))',
                            color: '#fff',
                            fontWeight: 600,
                            fontSize: '13px',
                            border: 'none',
                            cursor: isComputingCausal ? 'not-allowed' : 'pointer',
                            opacity: isComputingCausal ? 0.7 : 1,
                            boxShadow: '0 0 16px color-mix(in srgb, var(--color-accent) 40%, transparent)',
                            transition: 'all .2s ease',
                          }}
                        >
                          {isComputingCausal ? (
                            <>
                              <i className="ph ph-spinner ph-spin" style={{ fontSize: '16px' }}></i>
                              Evaluating Exchanges (LLM Judge)...
                            </>
                          ) : (
                            <>
                              <i className="ph ph-lightning" style={{ fontSize: '16px' }}></i>
                              Run Causal Counterfactual Analysis
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>

                  {causalError && (
                    <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#f87171', fontSize: '13px' }}>
                      {causalError}
                    </div>
                  )}

                  {activeCausalData ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                      {/* Metrics Banner */}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                        <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--color-divider)' }}>
                          <span style={{ fontSize: '11px', color: 'var(--color-neutral-500)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Top Causal Arbiter</span>
                          <div style={{ marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-neutral-100)' }}>
                              {getAgentInfo(activeCausalData.top_causal_influencer, null, debateAgentRoster || currentDiscussion?.agents).name}
                            </span>
                          </div>
                        </div>
                        <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--color-divider)' }}>
                          <span style={{ fontSize: '11px', color: 'var(--color-neutral-500)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Exchanges Evaluated</span>
                          <div style={{ marginTop: '4px', fontSize: '16px', fontWeight: 600, color: 'var(--color-neutral-100)' }}>
                            {activeCausalData.evaluated_exchanges_count || 0} directed exchanges
                          </div>
                        </div>
                        <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--color-divider)' }}>
                          <span style={{ fontSize: '11px', color: 'var(--color-neutral-500)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Evaluation Metric</span>
                          <div style={{ marginTop: '4px', fontSize: '13px', fontWeight: 500, color: 'var(--color-accent-300)' }}>
                            Treatment Effect τ = |S_factual - S_¬A|
                          </div>
                        </div>
                      </div>

                      {/* Agents Causal Impact List */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--color-neutral-300)' }}>
                          Causal Persuasion Index (Ablation Score)
                        </h4>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
                          {Object.entries(activeCausalData.agent_causal_influences || {}).map(([aid, info]) => {
                            const agent = getAgentInfo(aid, null, debateAgentRoster || currentDiscussion?.agents);
                            const score = info.causal_score != null ? info.causal_score : 0;
                            const isTop = aid === activeCausalData.top_causal_influencer && info.causal_score != null;
                            return (
                              <div
                                key={aid}
                                style={{
                                  padding: '14px',
                                  borderRadius: 'var(--radius-md)',
                                  background: isTop ? 'color-mix(in srgb, var(--color-accent) 10%, transparent)' : 'rgba(255, 255, 255, 0.02)',
                                  border: isTop ? '1px solid color-mix(in srgb, var(--color-accent) 40%, transparent)' : '1px solid var(--color-divider)',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '8px',
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <i className={agent.icon} style={{ fontSize: '16px', color: agent.color }}></i>
                                    <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--color-neutral-100)' }}>{agent.name}</span>
                                  </div>
                                  <span style={{ fontSize: '11px', padding: '2px 7px', borderRadius: '4px', background: 'rgba(255, 255, 255, 0.06)', color: 'var(--color-neutral-300)' }}>
                                    {info.causal_classification || 'Untested'}
                                  </span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', color: 'var(--color-neutral-400)' }}>
                                  <span>Causal Shift τ: <strong style={{ color: 'var(--color-neutral-100)' }}>{info.causal_score != null ? `+${info.causal_score.toFixed(4)}` : 'not evaluated'}</strong></span>
                                  <span>{info.exchange_count} exchanges</span>
                                </div>
                                <div style={{ height: '4px', borderRadius: '999px', background: 'var(--color-neutral-900)', overflow: 'hidden' }}>
                                  <div style={{ height: '100%', width: `${Math.min(100, (score / 0.1) * 100)}%`, background: agent.color, borderRadius: '999px' }}></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Sample Counterfactual Exchanges */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--color-neutral-300)' }}>
                            Peer Exchanges Evaluated by LLM Judge
                          </h4>
                          <button
                            onClick={() => setExpandedExchanges(!expandedExchanges)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--color-accent-300)',
                              fontSize: '12px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            {expandedExchanges ? 'Show Fewer' : 'Show All Judgments'}
                            <i className={`ph ${expandedExchanges ? 'ph-caret-up' : 'ph-caret-down'}`}></i>
                          </button>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {Object.entries(activeCausalData.agent_causal_influences || {})
                            .flatMap(([senderId, info]) => (info.exchanges || []).map((ex) => ({ ...ex, sender_id: senderId })))
                            .filter((ex) => ex.causal_shift > 0 || expandedExchanges)
                            .slice(0, expandedExchanges ? 20 : 3)
                            .map((ex, idx) => {
                              const sender = getAgentInfo(ex.sender_id, null, debateAgentRoster || currentDiscussion?.agents);
                              const recipient = getAgentInfo(ex.recipient_id, null, debateAgentRoster || currentDiscussion?.agents);
                              return (
                                <div
                                  key={idx}
                                  style={{
                                    padding: '12px 14px',
                                    borderRadius: 'var(--radius-md)',
                                    background: 'rgba(255, 255, 255, 0.02)',
                                    border: '1px solid var(--color-divider)',
                                    fontSize: '12px',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: '6px',
                                  }}
                                >
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <span style={{ fontWeight: 600, color: sender.color }}>{sender.name}</span>
                                      <i className="ph ph-arrow-right" style={{ color: 'var(--color-neutral-600)', fontSize: '11px' }}></i>
                                      <span style={{ fontWeight: 600, color: recipient.color }}>{recipient.name}</span>
                                      <span style={{ color: 'var(--color-neutral-500)' }}>· Round {ex.round_num}</span>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                      <span>Factual: <strong style={{ color: 'var(--color-neutral-200)' }}>{ex.factual_stance != null ? ex.factual_stance.toFixed(2) : 'N/A'}</strong></span>
                                      <span>Without Sender: <strong style={{ color: 'var(--color-neutral-400)' }}>{ex.counterfactual_stance != null ? ex.counterfactual_stance.toFixed(2) : 'N/A'}</strong></span>
                                      <span style={{ padding: '2px 6px', borderRadius: '4px', background: ex.causal_shift > 0.02 ? 'rgba(34, 197, 94, 0.15)' : 'rgba(255, 255, 255, 0.05)', color: ex.causal_shift > 0.02 ? '#4ade80' : 'var(--color-neutral-400)', fontWeight: 600 }}>
                                        Δ {ex.causal_shift != null ? ex.causal_shift.toFixed(3) : '0.000'}
                                      </span>
                                    </div>
                                  </div>
                                  {ex.attribution_rationale && (
                                    <div style={{ color: 'var(--color-neutral-300)', fontStyle: 'italic', fontSize: '12px' }}>
                                      "{ex.attribution_rationale}"
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div
                      style={{
                        padding: '24px',
                        borderRadius: 'var(--radius-md)',
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px dashed var(--color-divider)',
                        textAlign: 'center',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '10px',
                      }}
                    >
                      <i className="ph ph-cpu" style={{ fontSize: '28px', color: 'var(--color-neutral-500)' }}></i>
                      <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-neutral-400)', maxWidth: '480px' }}>
                        Counterfactual ablation has not been run for this debate yet. Click the button above to execute the LLM judge across all {currentDiscussion.messages?.length || 0} messages. Once evaluated, results are permanently cached.
                      </p>
                    </div>
                  )}
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
            TAB 4: DEVOPS (SYSTEM HEALTH & TERMINAL - ADMIN ONLY)
        ──────────────────────────────────────────────── */}
        {isAuthenticated && tab === 'devops' && isAdmin && (
          <section style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <h1 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: '32px', letterSpacing: '-0.02em', color: 'var(--color-neutral-100)' }}>
                    DevOps
                  </h1>
                  <span
                    style={{
                      fontSize: '11px',
                      padding: '2px 8px',
                      borderRadius: '999px',
                      background: 'color-mix(in srgb, var(--color-accent) 20%, transparent)',
                      color: 'var(--color-accent-300)',
                      border: '1px solid color-mix(in srgb, var(--color-accent) 40%, transparent)',
                      fontWeight: 700,
                      letterSpacing: '0.04em',
                    }}
                  >
                    ADMIN ONLY
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: '15px', color: 'var(--color-neutral-400)' }}>
                  Internal system diagnostics and health observability.
                </p>
              </div>
              <button
                onClick={() => {
                  try {
                    localStorage.removeItem('football_rag_admin');
                    const url = new URL(window.location.href);
                    url.searchParams.delete('admin');
                    window.history.replaceState({}, '', url.toString());
                  } catch (_) {}
                  setIsAdmin(false);
                  navigateTo('arena');
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '7px 14px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-divider)',
                  background: 'color-mix(in srgb, var(--color-surface) 60%, transparent)',
                  color: 'var(--color-neutral-300)',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 500,
                }}
              >
                <i className="ph ph-sign-out" style={{ fontSize: '14px' }}></i>
                Exit Admin Mode
              </button>
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
      )}

      {/* ══════════════════════════════════════════════════
          MULTI-TENANT PLATFORM MODALS (AUTH, ONBOARDING, PROFILE, PERSONAS)
      ══════════════════════════════════════════════════ */}
      <AuthModal
        isOpen={authModalOpen}
        initialMode={authModalMode}
        onClose={() => setAuthModalOpen(false)}
        onLoginSuccess={(data) => {
          setToken(data.token);
          setUser(data.user);
          setProfile(data.profile);
          navigateTo('arena');
        }}
        onRegisterSuccess={(data) => {
          setToken(data.token);
          setUser(data.user);
          setProfile(data.profile);
          setOnboardingModalOpen(true);
        }}
      />

      <OnboardingModal
        isOpen={onboardingModalOpen}
        profile={profile}
        token={token}
        onClose={() => setOnboardingModalOpen(false)}
        onComplete={(updatedProfile) => {
          setProfile(updatedProfile);
          setOnboardingModalOpen(false);
          navigateTo('arena');
        }}
      />

      <ProfileModal
        isOpen={profileModalOpen}
        profile={profile}
        user={user}
        token={token}
        onClose={() => setProfileModalOpen(false)}
        onUpdateProfile={(updated) => setProfile(updated)}
        onLogout={handleLogout}
      />

      <PersonaManagerModal
        isOpen={personaManagerModalOpen}
        token={token}
        onClose={() => setPersonaManagerModalOpen(false)}
        campAPersonaIds={campAPersonaIds}
        campBPersonaIds={campBPersonaIds}
        onAssignPersonaToCamp={handleAssignPersonaToCamp}
        onMovePersonaCamp={handleMovePersonaCamp}
        onRemovePersonaFromArena={handleRemovePersonaFromArena}
        onPersonasLoaded={registerCustomPersonas}
      />
    </div>
  );
}
