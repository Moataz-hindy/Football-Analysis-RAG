import React, { useState } from 'react';

/**
 * Profile Onboarding Modal: Configure your football intelligence workspace.
 *
 * Implements Feature Group C from the master specification:
 * - Data-driven profile types (Scout, Researcher, Fan, Analyst, Coach, Custom)
 * - Establishes football focus, experience level, analysis style, and favorite teams
 * - Informs the underlying agent architecture
 */

const PROFILE_TYPES = [
  {
    id: 'scout',
    name: 'Football Scout',
    icon: 'ph ph-binoculars',
    color: '#00f59b',
    tagline: 'Talent Identification & Recruitment Analytics',
    desc: 'Focuses on player attributes, tactical role suitability, athletic ceiling, and recruitment context.',
  },
  {
    id: 'researcher',
    name: 'Football Researcher',
    icon: 'ph ph-books',
    color: '#38bdf8',
    tagline: 'Methodology, Peer Evidence & Critical Comparison',
    desc: 'Demands rigorous empirical evidence, primary citations, uncertainty estimates, and sample size validation.',
  },
  {
    id: 'fan',
    name: 'Football Fan',
    icon: 'ph ph-users-three',
    color: '#ec4899',
    tagline: 'Passion, Momentum & Match Story',
    desc: 'Focuses on psychological momentum, dramatic turning points, accessible explanations, and terrace emotion.',
  },
  {
    id: 'analyst',
    name: 'Football Analyst',
    icon: 'ph ph-chart-line-up',
    color: '#00d2ff',
    tagline: 'Spatial Formations & Expected Threat',
    desc: 'Examines game models: pressing structures, half-space manipulation, defensive block heights, and xG flow.',
  },
  {
    id: 'coach',
    name: 'Coach / Technical Staff',
    icon: 'ph ph-strategy',
    color: '#fb7185',
    tagline: 'Match Preparation & Tactical Counter-Moves',
    desc: 'Focuses on actionable coaching interventions, opponent weaknesses, rest defense stability, and subs.',
  },
  {
    id: 'custom',
    name: 'Custom Profile',
    icon: 'ph ph-sparkle',
    color: '#a78bfa',
    tagline: 'Bespoke Analytical Matrix',
    desc: 'Personalized hybrid combination of custom metrics, special focus areas, and flexible reporting.',
  },
];

export default function OnboardingModal({
  isOpen,
  profile,
  token,
  onComplete,
}) {
  const [selectedType, setSelectedType] = useState(profile?.profile_type || 'scout');
  const [footballFocus, setFootballFocus] = useState(profile?.football_focus || 'Player Recruitment & Positional Profiling');
  const [experienceLevel, setExperienceLevel] = useState(profile?.experience_level || 'Professional');
  const [analysisStyle, setAnalysisStyle] = useState(profile?.preferred_analysis_style || 'Statistical & Quantitative');
  const [favTeams, setFavTeams] = useState(profile?.favorite_teams?.join(', ') || 'Argentina, Manchester City, Arsenal');
  const [favComps, setFavComps] = useState(profile?.favorite_competitions?.join(', ') || 'UEFA Champions League, FIFA World Cup, Premier League');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleFinish = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const teamsList = favTeams.split(',').map((t) => t.trim()).filter(Boolean);
    const compsList = favComps.split(',').map((c) => c.trim()).filter(Boolean);

    try {
      const res = await fetch('/profile', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token || localStorage.getItem('touchline_token')}`,
        },
        body: JSON.stringify({
          profile_type: selectedType,
          football_focus: footballFocus.trim(),
          experience_level: experienceLevel,
          preferred_analysis_style: analysisStyle,
          favorite_teams: teamsList,
          favorite_competitions: compsList,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to update profile.');
      }
      if (onComplete) {
        onComplete(data);
      }
    } catch (err) {
      setError(err.message || 'Onboarding error.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-lg animate-fadeIn overflow-y-auto">
      <div className="relative w-full max-w-2xl rounded-2xl bg-[#0c1220] border border-white/[0.1] shadow-2xl p-6 sm:p-8 flex flex-col space-y-6 my-8">
        {/* Header */}
        <div className="flex flex-col space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#00f59b] shadow-[0_0_8px_#00f59b]"></span>
            <span className="font-mono text-[11px] font-bold text-[#00f59b] uppercase tracking-wider">
              Profile Calibration
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Configure your football intelligence workspace
          </h2>
          <p className="text-sm text-neutral-400">
            Tell the agents your analytical role. This adapts discussion priority, depth, and report formats.
          </p>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/15 border border-red-500/40 text-red-200 text-xs font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleFinish} className="flex flex-col space-y-6">
          {/* Step 1: Select Profile Type */}
          <div className="flex flex-col space-y-3">
            <label className="text-xs font-bold text-neutral-300 uppercase tracking-wider font-mono">
              Step 1: Choose Your Primary Role
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {PROFILE_TYPES.map((pt) => {
                const isSelected = selectedType === pt.id;
                return (
                  <div
                    key={pt.id}
                    onClick={() => setSelectedType(pt.id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col space-y-1.5 ${
                      isSelected
                        ? 'bg-[#00f59b]/15 border-[#00f59b] shadow-[0_0_16px_rgba(0,245,155,0.25)]'
                        : 'bg-white/[0.03] border-white/[0.08] hover:border-white/[0.2] hover:bg-white/[0.05]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <i className={`${pt.icon} text-lg`} style={{ color: pt.color }}></i>
                        <span className="text-sm font-bold text-white">{pt.name}</span>
                      </div>
                      {isSelected && (
                        <span className="w-2 h-2 rounded-full bg-[#00f59b] shadow-[0_0_6px_#00f59b]"></span>
                      )}
                    </div>
                    <span className="text-[11px] text-neutral-400 leading-tight">{pt.desc}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Step 2: Specific Analytical Focus & Style */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex flex-col space-y-1.5">
              <label className="text-xs font-semibold text-neutral-300">Football Focus</label>
              <input
                type="text"
                required
                value={footballFocus}
                onChange={(e) => setFootballFocus(e.target.value)}
                placeholder="e.g. U21 Recruitment & Spatial Carry"
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#00f59b]"
              />
            </div>

            <div className="flex flex-col space-y-1.5">
              <label className="text-xs font-semibold text-neutral-300">Analysis Style</label>
              <select
                value={analysisStyle}
                onChange={(e) => setAnalysisStyle(e.target.value)}
                className="w-full px-3 py-2.5 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#00f59b]"
              >
                <option value="Statistical & Quantitative">Statistical & Quantitative</option>
                <option value="Deep Tactical & Spatial">Deep Tactical & Spatial</option>
                <option value="Narrative & Storytelling">Narrative & Storytelling</option>
                <option value="Concise Executive Summary">Concise Executive Summary</option>
              </select>
            </div>
          </div>

          {/* Step 3: Teams & Competitions */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex flex-col space-y-1.5">
              <label className="text-xs font-semibold text-neutral-300">Favorite / Monitored Teams</label>
              <input
                type="text"
                value={favTeams}
                onChange={(e) => setFavTeams(e.target.value)}
                placeholder="Comma-separated: Argentina, Arsenal..."
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#00f59b]"
              />
            </div>

            <div className="flex flex-col space-y-1.5">
              <label className="text-xs font-semibold text-neutral-300">Primary Competitions</label>
              <input
                type="text"
                value={favComps}
                onChange={(e) => setFavComps(e.target.value)}
                placeholder="Comma-separated: Champions League..."
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#00f59b]"
              />
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 rounded-xl bg-gradient-to-r from-[#00f59b] to-[#00d2ff] text-black font-bold text-sm shadow-[0_0_24px_rgba(0,245,155,0.4)] hover:shadow-[0_0_36px_rgba(0,245,155,0.6)] transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 mt-4"
          >
            {loading ? 'Saving Workspace Preferences...' : 'Launch Personalized Workspace'}
          </button>
        </form>
      </div>
    </div>
  );
}
