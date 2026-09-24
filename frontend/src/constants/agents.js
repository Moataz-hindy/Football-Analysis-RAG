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
    textColor: 'text-primary',
    border: 'border-primary/30 hover:border-primary/60',
    shadow: 'shadow-[0_0_8px_rgba(0,245,155,0.2)]',
    dot: 'bg-primary',
    subtextColor: 'text-primary/80',
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
    textColor: 'text-secondary',
    border: 'border-secondary/30 hover:border-secondary/60',
    shadow: 'shadow-[0_0_8px_rgba(0,210,255,0.2)]',
    dot: 'bg-secondary',
    subtextColor: 'text-secondary/80',
    strokeColor: '#00d2ff',
  },
  {
    id: 'fan_analyst',
    code: 'FA-02',
    name: 'Fan Analyst',
    shortName: 'Fan Sentiment',
    sublabel: 'Kinetic Surge',
    icon: 'favorite',
    color: '#a5e7ff',
    textColor: 'text-secondary-fixed',
    border: 'border-white/[0.08] hover:border-white/[0.2]',
    shadow: '',
    dot: 'bg-secondary-fixed',
    subtextColor: 'text-secondary-fixed/80',
    strokeColor: '#a5e7ff',
  },
  {
    id: 'refereeing_analyst',
    code: 'RA-12',
    name: 'Refereeing Analyst',
    shortName: 'Refereeing',
    sublabel: 'Law 12 VAR',
    icon: 'gavel',
    color: '#ffb4ab',
    textColor: 'text-error',
    border: 'border-white/[0.08] hover:border-white/[0.2]',
    shadow: '',
    dot: 'bg-error',
    subtextColor: 'text-error/80',
    strokeColor: '#ffb4ab',
  },
  {
    id: 'performance_analyst',
    code: 'PA-07',
    name: 'Performance Analyst',
    shortName: 'Performance',
    sublabel: 'Fatigue Index',
    icon: 'speed',
    color: '#00e38f',
    textColor: 'text-primary-fixed-dim',
    border: 'border-white/[0.08] hover:border-white/[0.2]',
    shadow: '',
    dot: 'bg-primary-fixed-dim',
    subtextColor: 'text-primary-fixed-dim/80',
    strokeColor: '#00e38f',
  },
  {
    id: 'context_analyst',
    code: 'CA-10',
    name: 'Historical Context',
    shortName: 'Historical',
    sublabel: '2010 Precedent',
    icon: 'history_edu',
    color: '#c0c1ff',
    textColor: 'text-tertiary',
    border: 'border-white/[0.08] hover:border-white/[0.2]',
    shadow: '',
    dot: 'bg-tertiary',
    subtextColor: 'text-tertiary/80',
    strokeColor: '#c0c1ff',
  },
];

export function getAgentInfo(id) {
  return (
    AGENTS.find((a) => a.id === id) || {
      id,
      code: 'AG-01',
      name: id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      shortName: id.replace(/_/g, ' '),
      sublabel: 'Specialist Voice',
      icon: 'psychology',
      color: '#00d2ff',
      textColor: 'text-secondary',
      border: 'border-secondary/30 hover:border-secondary/60',
      shadow: 'shadow-[0_0_8px_rgba(0,210,255,0.2)]',
      dot: 'bg-secondary',
      subtextColor: 'text-secondary/80',
      strokeColor: '#00d2ff',
    }
  );
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
