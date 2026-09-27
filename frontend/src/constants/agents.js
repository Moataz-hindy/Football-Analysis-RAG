// Agent metadata according to Stitch.ai Obsidian Neon Design System
export const AGENTS = [
  {
    id: 'tactical_analyst',
    code: 'TA-09',
    name: 'Tactical Analyst',
    shortName: 'Tactical',
    sublabel: 'Half-space Sync',
    icon: 'schema',
    color: '#00f59b',
    textColor: 'text-[#00f59b]',
    border: 'border-[#00f59b]/30 hover:border-[#00f59b]/60',
    shadow: 'shadow-[0_0_8px_rgba(0,245,155,0.2)]',
    dot: 'bg-[#00f59b]',
    subtextColor: 'text-[#00f59b]/80',
    strokeColor: '#00f59b',
  },
  {
    id: 'statistical_analyst',
    code: 'SA-44',
    name: 'Statistical Analyst',
    shortName: 'Statistical',
    sublabel: 'xG 0.42 • PPDA',
    icon: 'analytics',
    color: '#00d2ff',
    textColor: 'text-[#00d2ff]',
    border: 'border-[#00d2ff]/30 hover:border-[#00d2ff]/60',
    shadow: 'shadow-[0_0_8px_rgba(0,210,255,0.2)]',
    dot: 'bg-[#00d2ff]',
    subtextColor: 'text-[#00d2ff]/80',
    strokeColor: '#00d2ff',
  },
  {
    id: 'performance_analyst',
    code: 'PA-07',
    name: 'Performance Analyst',
    shortName: 'Performance',
    sublabel: 'Fatigue Index',
    icon: 'speed',
    color: '#f43f5e',
    textColor: 'text-[#f43f5e]',
    border: 'border-[#f43f5e]/30 hover:border-[#f43f5e]/60',
    shadow: 'shadow-[0_0_8px_rgba(244,63,94,0.2)]',
    dot: 'bg-[#f43f5e]',
    subtextColor: 'text-[#f43f5e]/80',
    strokeColor: '#f43f5e',
  },
  {
    id: 'fan_analyst',
    code: 'FA-02',
    name: 'Fan Analyst',
    shortName: 'Fan Sentiment',
    sublabel: 'Kinetic Surge',
    icon: 'favorite',
    color: '#fbbf24',
    textColor: 'text-[#fbbf24]',
    border: 'border-[#fbbf24]/30 hover:border-[#fbbf24]/60',
    shadow: 'shadow-[0_0_8px_rgba(251,191,36,0.2)]',
    dot: 'bg-[#fbbf24]',
    subtextColor: 'text-[#fbbf24]/80',
    strokeColor: '#fbbf24',
  },
  {
    id: 'refereeing_analyst',
    code: 'RA-12',
    name: 'Refereeing Analyst',
    shortName: 'Refereeing',
    sublabel: 'Law 12 VAR',
    icon: 'gavel',
    color: '#a855f7',
    textColor: 'text-[#a855f7]',
    border: 'border-[#a855f7]/30 hover:border-[#a855f7]/60',
    shadow: 'shadow-[0_0_8px_rgba(168,85,247,0.2)]',
    dot: 'bg-[#a855f7]',
    subtextColor: 'text-[#a855f7]/80',
    strokeColor: '#a855f7',
  },
  {
    id: 'context_analyst',
    code: 'CA-10',
    name: 'Historical Context',
    shortName: 'Historical',
    sublabel: '2010 Precedent',
    icon: 'history_edu',
    color: '#fb923c',
    textColor: 'text-[#fb923c]',
    border: 'border-[#fb923c]/30 hover:border-[#fb923c]/60',
    shadow: 'shadow-[0_0_8px_rgba(251,146,60,0.2)]',
    dot: 'bg-[#fb923c]',
    subtextColor: 'text-[#fb923c]/80',
    strokeColor: '#fb923c',
  },
];

export const AGENT_DISTINCT_COLORS = {
  tactical_analyst: '#00f59b',    // Neon Emerald Green
  statistical_analyst: '#00d2ff', // Electric Cyan Blue
  performance_analyst: '#f43f5e', // Coral Crimson Rose
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

    const candidate = typeof a === 'object' ? a?.color : null;
    if (candidate && candidate.startsWith('#')) {
      const candLower = candidate.toLowerCase();
      if (!usedColors.has(candLower) && candLower !== '#00f59b' && candLower !== '#a78bfa' && candLower !== '#c084fc' && candLower !== '#818cf8') {
        colorMap[id] = candidate;
        colorMap[cleanId] = candidate;
        usedColors.add(candLower);
      }
    }
  });

  // Pass 3: Allocate next unused color from DISTINCT_PALETTE
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

export function getAgentInfo(id, meta = null, allAgents = []) {
  const cleanId = String(id || '').toLowerCase();
  const staticFound = AGENTS.find((a) => a.id === id || a.id === cleanId);

  // If allAgents provided, determine color via collision-free debate color map
  let assignedColor = null;
  const effectiveAgents = Array.isArray(allAgents) && allAgents.length > 0
    ? allAgents
    : (Array.isArray(meta?.allAgents) && meta.allAgents.length > 0 ? meta.allAgents : null);

  if (effectiveAgents) {
    const debateColors = buildDebateColorMap(effectiveAgents);
    assignedColor = debateColors[id] || debateColors[cleanId];
  }

  if (!assignedColor) {
    if (AGENT_DISTINCT_COLORS[cleanId]) {
      assignedColor = AGENT_DISTINCT_COLORS[cleanId];
    } else {
      let hash = 0;
      for (let i = 0; i < cleanId.length; i++) {
        hash = (hash << 5) - hash + cleanId.charCodeAt(i);
        hash |= 0;
      }
      const offset = 6 + (Math.abs(hash) % (DISTINCT_PALETTE.length - 6));
      assignedColor = DISTINCT_PALETTE[offset];
    }
  }

  if (staticFound) {
    return {
      ...staticFound,
      color: assignedColor || staticFound.color,
      strokeColor: assignedColor || staticFound.strokeColor,
    };
  }

  return {
    id,
    code: 'AG-01',
    name: cleanId.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    shortName: cleanId.replace(/_/g, ' '),
    sublabel: 'Specialist Voice',
    icon: 'psychology',
    color: assignedColor,
    textColor: `text-[${assignedColor}]`,
    border: `border-[${assignedColor}]/30 hover:border-[${assignedColor}]/60`,
    shadow: `shadow-[0_0_8px_${assignedColor}33]`,
    dot: `bg-[${assignedColor}]`,
    subtextColor: `text-[${assignedColor}]/80`,
    strokeColor: assignedColor,
  };
}

// Primary navigation tabs, shared by the desktop header switcher and the bottom nav
export const TABS = [
  { id: 'deliberation', label: 'Deliberation', icon: 'forum' },
  { id: 'history', label: 'History', icon: 'history_toggle_off' },
  { id: 'intelligence', label: 'Intelligence', icon: 'insights' },
  { id: 'devops', label: 'DevOps', icon: 'terminal' },
];

// Pitch coordinates (680x440 viewBox, attacking left → right) for each specialist agent
export const PITCH_POSITIONS = {
  context_analyst: { x: 118, y: 220, role: 'Sweeper' },
  refereeing_analyst: { x: 228, y: 336, role: 'Left CB' },
  performance_analyst: { x: 228, y: 104, role: 'Right CB' },
  statistical_analyst: { x: 342, y: 220, role: 'Regista' },
  tactical_analyst: { x: 486, y: 138, role: 'Half-space 8' },
  fan_analyst: { x: 494, y: 306, role: 'Inverted 10' },
};

// Default passing lanes between agents: [from, to, weight 0..1]
export const DEFAULT_LANES = [
  ['context_analyst', 'performance_analyst', 0.55],
  ['context_analyst', 'refereeing_analyst', 0.45],
  ['performance_analyst', 'statistical_analyst', 0.7],
  ['refereeing_analyst', 'statistical_analyst', 0.5],
  ['statistical_analyst', 'tactical_analyst', 0.95],
  ['statistical_analyst', 'fan_analyst', 0.6],
  ['tactical_analyst', 'fan_analyst', 0.75],
  ['performance_analyst', 'tactical_analyst', 0.4],
];
