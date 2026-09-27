import React, { useState, useEffect } from 'react';

/**
 * Persona Manager Modal: System Personas, Custom Personas & AI Generation.
 *
 * Implements Feature Group F from the master specification:
 * - View protected system personas
 * - Create custom personas manually (+ Create Persona)
 * - Generate personas using AI (Create with AI)
 * - Manage & select personas for arena deliberations
 */

const PERSONA_FIELDS = [
  'Tactical Analysis',
  'Scouting & Recruitment',
  'Statistics & Analytics',
  'Physical & Performance',
  'Refereeing & Laws',
  'Historical Context',
  'Fan & Media Narrative',
  'Player Development',
  'Custom Analytical Field',
];

export default function PersonaManagerModal({
  isOpen,
  token,
  onClose,
  onSelectPersonaForArena,
}) {
  const [personas, setPersonas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('all'); // 'all', 'create_manual', 'create_ai'
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Manual Creation State
  const [manualName, setManualName] = useState('');
  const [manualField, setManualField] = useState('Tactical Analysis');
  const [manualSpecs, setManualSpecs] = useState('');

  // AI Generation State
  const [aiField, setAiField] = useState('Scouting & Recruitment');
  const [aiCount, setAiCount] = useState(2);
  const [aiDesc, setAiDesc] = useState('');
  const [aiGenerating, setAiGenerating] = useState(false);

  const fetchPersonas = async () => {
    setLoading(true);
    try {
      const res = await fetch('/profile/personas', {
        headers: {
          Authorization: `Bearer ${token || localStorage.getItem('touchline_token')}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setPersonas(data);
      }
    } catch (err) {
      console.error('Failed to fetch personas:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchPersonas();
      setError(null);
      setSuccessMsg(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleManualCreate = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await fetch('/profile/personas', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token || localStorage.getItem('touchline_token')}`,
        },
        body: JSON.stringify({
          name: manualName.trim(),
          field: manualField,
          specifications: manualSpecs.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Creation failed.');
      setSuccessMsg(`Created persona "${data.name}" successfully!`);
      setManualName('');
      setManualSpecs('');
      setActiveTab('all');
      fetchPersonas();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleAiGenerate = async (e) => {
    e.preventDefault();
    setError(null);
    setAiGenerating(true);
    try {
      const res = await fetch('/profile/personas/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token || localStorage.getItem('touchline_token')}`,
        },
        body: JSON.stringify({
          field: aiField,
          count: Number(aiCount),
          description: aiDesc.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'AI generation failed.');
      setSuccessMsg(`Generated ${data.length} personas successfully!`);
      setAiDesc('');
      setActiveTab('all');
      fetchPersonas();
    } catch (err) {
      setError(err.message);
    } finally {
      setAiGenerating(false);
    }
  };

  const handleDelete = async (personaId) => {
    if (!confirm('Are you sure you want to delete this custom persona?')) return;
    try {
      const res = await fetch(`/profile/personas/${personaId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token || localStorage.getItem('touchline_token')}`,
        },
      });
      if (res.ok) {
        fetchPersonas();
      } else {
        const d = await res.json();
        alert(d.detail || 'Delete failed.');
      }
    } catch (err) {
      alert('Delete error: ' + err.message);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-lg animate-fadeIn overflow-y-auto">
      <div className="relative w-full max-w-4xl rounded-2xl bg-[#0c1220] border border-white/[0.1] shadow-2xl p-6 sm:p-8 flex flex-col space-y-6 my-8 max-h-[90vh] overflow-y-auto">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-neutral-400 hover:text-white transition-colors"
        >
          <i className="ph ph-x text-xl"></i>
        </button>

        {/* Header */}
        <div className="flex flex-col space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#00f59b] shadow-[0_0_8px_#00f59b]"></span>
            <span className="font-mono text-[11px] font-bold text-[#00f59b] uppercase tracking-wider">
              Persona Architecture
            </span>
          </div>
          <div className="flex items-center justify-between flex-wrap gap-4">
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Specialist Agent Roster
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => { setActiveTab('create_manual'); setError(null); }}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  activeTab === 'create_manual'
                    ? 'bg-[#00f59b] text-black font-bold shadow-[0_0_12px_rgba(0,245,155,0.4)]'
                    : 'bg-white/[0.05] text-white hover:bg-white/[0.1] border border-white/[0.08]'
                }`}
              >
                <i className="ph ph-plus-circle font-bold"></i>
                <span>+ Create Persona</span>
              </button>
              <button
                onClick={() => { setActiveTab('create_ai'); setError(null); }}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  activeTab === 'create_ai'
                    ? 'bg-purple-500 text-white font-bold shadow-[0_0_12px_rgba(168,85,247,0.4)]'
                    : 'bg-purple-500/10 text-purple-300 hover:bg-purple-500/20 border border-purple-500/30'
                }`}
              >
                <i className="ph ph-sparkle text-sm"></i>
                <span>Create with AI</span>
              </button>
            </div>
          </div>
        </div>

        {/* Alerts */}
        {error && (
          <div className="p-3 rounded-lg bg-red-500/15 border border-red-500/40 text-red-200 text-xs font-medium">
            {error}
          </div>
        )}
        {successMsg && (
          <div className="p-3 rounded-lg bg-[#00f59b]/15 border border-[#00f59b]/40 text-[#00f59b] text-xs font-medium">
            {successMsg}
          </div>
        )}

        {/* ── Mode 1: Manual Persona Creation Form ── */}
        {activeTab === 'create_manual' && (
          <form onSubmit={handleManualCreate} className="p-5 rounded-xl bg-white/[0.02] border border-white/[0.08] flex flex-col space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <i className="ph ph-user-plus text-[#00f59b]"></i>
                Manual Persona Configuration
              </h3>
              <button type="button" onClick={() => setActiveTab('all')} className="text-xs text-neutral-400 hover:text-white">
                Back to Roster
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col space-y-1.5">
                <label className="text-xs font-semibold text-neutral-300">Persona Name</label>
                <input
                  type="text"
                  required
                  value={manualName}
                  onChange={(e) => setManualName(e.target.value)}
                  placeholder="e.g. Opposition Rest-Defense Scout"
                  className="w-full px-3.5 py-2 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#00f59b]"
                />
              </div>
              <div className="flex flex-col space-y-1.5">
                <label className="text-xs font-semibold text-neutral-300">Persona Field</label>
                <select
                  value={manualField}
                  onChange={(e) => setManualField(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#00f59b]"
                >
                  {PERSONA_FIELDS.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex flex-col space-y-1.5">
              <label className="text-xs font-semibold text-neutral-300">Persona Specifications</label>
              <textarea
                rows={4}
                required
                value={manualSpecs}
                onChange={(e) => setManualSpecs(e.target.value)}
                placeholder="Describe tactical principles, analytical biases, preferred metrics, and evaluation criteria..."
                className="w-full px-3.5 py-2 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#00f59b]"
              />
            </div>

            <button
              type="submit"
              className="py-2.5 px-6 rounded-lg bg-[#00f59b] hover:bg-[#34d399] text-black font-bold text-sm w-fit shadow-[0_0_16px_rgba(0,245,155,0.4)]"
            >
              Create Persona
            </button>
          </form>
        )}

        {/* ── Mode 2: AI Persona Generation Form ── */}
        {activeTab === 'create_ai' && (
          <form onSubmit={handleAiGenerate} className="p-5 rounded-xl bg-purple-500/[0.04] border border-purple-500/20 flex flex-col space-y-4">
            <div className="flex items-center justify-between border-b border-purple-500/20 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <i className="ph ph-sparkle text-purple-400"></i>
                Generate Personas with AI
              </h3>
              <button type="button" onClick={() => setActiveTab('all')} className="text-xs text-neutral-400 hover:text-white">
                Back to Roster
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col space-y-1.5">
                <label className="text-xs font-semibold text-neutral-300">Target Field</label>
                <select
                  value={aiField}
                  onChange={(e) => setAiField(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-purple-400"
                >
                  {PERSONA_FIELDS.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col space-y-1.5">
                <label className="text-xs font-semibold text-neutral-300">Number of Personas (1-4)</label>
                <input
                  type="number"
                  min={1}
                  max={4}
                  value={aiCount}
                  onChange={(e) => setAiCount(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-purple-400"
                />
              </div>
            </div>

            <div className="flex flex-col space-y-1.5">
              <label className="text-xs font-semibold text-neutral-300">Analytical Prompt / Perspective Focus</label>
              <input
                type="text"
                value={aiDesc}
                onChange={(e) => setAiDesc(e.target.value)}
                placeholder="e.g. Generate 2 contrasting scouts evaluating pressing traps in a 5-4-1 block"
                className="w-full px-3.5 py-2 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-purple-400"
              />
            </div>

            <button
              type="submit"
              disabled={aiGenerating}
              className="py-2.5 px-6 rounded-lg bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600 text-white font-bold text-sm w-fit shadow-[0_0_18px_rgba(168,85,247,0.4)] disabled:opacity-50"
            >
              {aiGenerating ? 'Generating Personas...' : 'Generate with AI'}
            </button>
          </form>
        )}

        {/* ── Mode 3: Roster Card Grid ── */}
        <div className="flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-neutral-400">
              Active Agents ({personas.length})
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {personas.map((p) => {
              const isSystem = p.source === 'system';
              return (
                <div
                  key={p.id}
                  className="rounded-xl bg-[#080d19] border border-white/[0.08] p-4 flex flex-col justify-between hover:border-white/[0.2] transition-all space-y-3"
                >
                  <div className="flex flex-col space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm"
                          style={{
                            background: `color-mix(in srgb, ${p.color || '#00f59b'} 15%, transparent)`,
                            color: p.color || '#00f59b',
                            border: `1px solid ${p.color || '#00f59b'}`,
                          }}
                        >
                          <i className={p.icon || 'ph ph-user'}></i>
                        </div>
                        <div className="flex flex-col">
                          <span className="font-bold text-white text-sm">{p.name}</span>
                          <span className="text-[11px] text-neutral-400">{p.field}</span>
                        </div>
                      </div>

                      {/* Source Badge */}
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase font-bold tracking-wider ${
                          isSystem
                            ? 'bg-neutral-800 text-neutral-400 border border-neutral-700'
                            : p.source === 'generated'
                            ? 'bg-purple-500/15 text-purple-300 border border-purple-500/30'
                            : 'bg-[#00f59b]/15 text-[#00f59b] border border-[#00f59b]/30'
                        }`}
                      >
                        {isSystem ? 'System' : p.source === 'generated' ? 'AI' : 'Custom'}
                      </span>
                    </div>

                    <p className="text-[12px] text-neutral-300 line-clamp-2 leading-relaxed">
                      {p.stance || p.background}
                    </p>

                    {/* Expertise Pills */}
                    {p.expertise && p.expertise.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap pt-1">
                        {p.expertise.slice(0, 3).map((exp, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 rounded bg-white/[0.04] text-[10px] text-neutral-400 border border-white/[0.04]"
                          >
                            {exp}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-between pt-2 border-t border-white/[0.05]">
                    <span className="text-[11px] text-neutral-500 font-mono">
                      {isSystem ? 'Protected System Persona' : 'User Owned'}
                    </span>

                    <div className="flex items-center gap-2">
                      {!isSystem && (
                        <button
                          type="button"
                          onClick={() => handleDelete(p.id)}
                          className="px-2 py-1 rounded text-[11px] text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
                        >
                          Delete
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => {
                          if (onSelectPersonaForArena) onSelectPersonaForArena(p);
                          onClose();
                        }}
                        className="px-3 py-1 rounded bg-white/[0.06] hover:bg-[#00f59b]/20 hover:text-[#00f59b] text-white text-[11.5px] font-medium transition-colors"
                      >
                        Select for Arena
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
