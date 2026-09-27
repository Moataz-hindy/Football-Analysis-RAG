import React, { useState, useEffect } from 'react';

/**
 * Profile Management & Intelligence Memory Modal.
 *
 * Implements Feature Group D, E & personalized reports view:
 * - View & update profile preferences
 * - Inspect and manage durable long-term memories
 * - Inspect generated personalized reports
 * - Logout action
 */

export default function ProfileModal({
  isOpen,
  profile,
  user,
  token,
  onClose,
  onUpdateProfile,
  onLogout,
}) {
  const [activeTab, setActiveTab] = useState('settings'); // 'settings', 'memory', 'reports'
  const [memories, setMemories] = useState([]);
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);

  // New Memory state
  const [newMemKey, setNewMemKey] = useState('');
  const [newMemVal, setNewMemVal] = useState('');
  const [newMemType, setNewMemType] = useState('preference');

  // Edit Profile state
  const [focus, setFocus] = useState(profile?.football_focus || '');
  const [style, setStyle] = useState(profile?.preferred_analysis_style || '');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const fetchMemories = async () => {
    try {
      const res = await fetch('/profile/memory', {
        headers: { Authorization: `Bearer ${token || localStorage.getItem('touchline_token')}` },
      });
      if (res.ok) setMemories(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchReports = async () => {
    try {
      const res = await fetch('/reports', {
        headers: { Authorization: `Bearer ${token || localStorage.getItem('touchline_token')}` },
      });
      if (res.ok) setReports(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchMemories();
      fetchReports();
      setFocus(profile?.football_focus || '');
      setStyle(profile?.preferred_analysis_style || '');
      setMsg(null);
    }
  }, [isOpen, profile]);

  if (!isOpen) return null;

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      const res = await fetch('/profile', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token || localStorage.getItem('touchline_token')}`,
        },
        body: JSON.stringify({
          football_focus: focus,
          preferred_analysis_style: style,
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setMsg('Profile preferences updated.');
        if (onUpdateProfile) onUpdateProfile(updated);
      }
    } catch (e) {
      setMsg('Failed to update.');
    } finally {
      setSaving(false);
    }
  };

  const handleAddMemory = async (e) => {
    e.preventDefault();
    if (!newMemKey.trim() || !newMemVal.trim()) return;
    try {
      const res = await fetch('/profile/memory', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token || localStorage.getItem('touchline_token')}`,
        },
        body: JSON.stringify({
          memory_type: newMemType,
          key: newMemKey.trim(),
          value: newMemVal.trim(),
          source: 'explicit',
        }),
      });
      if (res.ok) {
        setNewMemKey('');
        setNewMemVal('');
        fetchMemories();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteMemory = async (id) => {
    try {
      const res = await fetch(`/profile/memory/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token || localStorage.getItem('touchline_token')}` },
      });
      if (res.ok) fetchMemories();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-lg animate-fadeIn overflow-y-auto">
      <div className="relative w-full max-w-3xl rounded-2xl bg-[#0c1220] border border-white/[0.1] shadow-2xl p-6 sm:p-8 flex flex-col space-y-6 my-8 max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-neutral-400 hover:text-white transition-colors"
        >
          <i className="ph ph-x text-xl"></i>
        </button>

        {/* Header Profile Identity Badge */}
        <div className="flex items-center justify-between border-b border-white/[0.08] pb-5">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-[#00f59b]/15 border border-[#00f59b]/40 flex items-center justify-center text-[#00f59b] font-bold text-lg">
              {profile?.display_name?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold text-white">{profile?.display_name || 'Anonymous'}</span>
                <span className="px-2 py-0.5 rounded-full bg-[#00f59b]/15 border border-[#00f59b]/35 text-[#00f59b] text-[10.5px] font-mono uppercase font-bold tracking-wider">
                  {profile?.profile_type || 'scout'}
                </span>
              </div>
              <span className="text-xs text-neutral-400 font-mono">{user?.email || 'Logged in'}</span>
            </div>
          </div>

          <button
            onClick={onLogout}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-red-400 hover:bg-red-500/10 border border-red-500/20 transition-all flex items-center gap-1.5"
          >
            <i className="ph ph-sign-out text-sm"></i>
            <span>Log Out</span>
          </button>
        </div>

        {/* Tab Controls */}
        <div className="flex rounded-xl bg-white/[0.03] p-1 border border-white/[0.06]">
          {[
            { id: 'settings', label: 'Profile Settings', icon: 'ph ph-sliders' },
            { id: 'memory', label: `Durable Memory (${memories.length})`, icon: 'ph ph-brain' },
            { id: 'reports', label: `Personalized Reports (${reports.length})`, icon: 'ph ph-file-text' },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex-1 py-2 text-center text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                activeTab === t.id
                  ? 'bg-[#00f59b]/20 text-[#00f59b] border border-[#00f59b]/40 shadow-sm'
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              <i className={t.icon}></i>
              <span>{t.label}</span>
            </button>
          ))}
        </div>

        {msg && (
          <div className="p-3 rounded-lg bg-[#00f59b]/10 border border-[#00f59b]/30 text-[#00f59b] text-xs font-medium">
            {msg}
          </div>
        )}

        {/* ── TAB 1: Profile Settings ── */}
        {activeTab === 'settings' && (
          <form onSubmit={handleSaveProfile} className="flex flex-col space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col space-y-1.5">
                <label className="text-xs font-semibold text-neutral-300">Football Focus</label>
                <input
                  type="text"
                  value={focus}
                  onChange={(e) => setFocus(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#00f59b]"
                />
              </div>

              <div className="flex flex-col space-y-1.5">
                <label className="text-xs font-semibold text-neutral-300">Preferred Analysis Style</label>
                <input
                  type="text"
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#00f59b]"
                />
              </div>
            </div>

            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col space-y-2">
              <span className="text-xs font-bold text-neutral-300 font-mono uppercase tracking-wider">
                Active Preferences
              </span>
              <div className="text-xs text-neutral-400 space-y-1">
                <div>Preferred Report: <span className="text-white font-medium">{profile?.preferred_report_type || 'Scout Report'}</span></div>
                <div>Experience Level: <span className="text-white font-medium">{profile?.experience_level || 'Professional'}</span></div>
                <div>Favorite Teams: <span className="text-[#00f59b] font-medium">{profile?.favorite_teams?.join(', ') || 'None'}</span></div>
              </div>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="py-2.5 px-6 rounded-lg bg-[#00f59b] text-black font-bold text-xs w-fit shadow-[0_0_16px_rgba(0,245,155,0.4)] disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </form>
        )}

        {/* ── TAB 2: Persistent Long-Term Memory ── */}
        {activeTab === 'memory' && (
          <div className="flex flex-col space-y-4">
            <p className="text-xs text-neutral-400">
              The platform maintains durable profile memory to steer agent deliberations towards your priorities without having to re-specify them in every prompt.
            </p>

            {/* Add Memory Item */}
            <form onSubmit={handleAddMemory} className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.08] grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
              <div className="sm:col-span-4 flex flex-col space-y-1">
                <label className="text-[11px] font-semibold text-neutral-300">Memory Key</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Metric Focus"
                  value={newMemKey}
                  onChange={(e) => setNewMemKey(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-[#060a12] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-[#00f59b]"
                />
              </div>

              <div className="sm:col-span-6 flex flex-col space-y-1">
                <label className="text-[11px] font-semibold text-neutral-300">Value / Preference</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Always contrast high-block recoveries with standard PPDA"
                  value={newMemVal}
                  onChange={(e) => setNewMemVal(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-[#060a12] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-[#00f59b]"
                />
              </div>

              <div className="sm:col-span-2">
                <button
                  type="submit"
                  className="w-full py-2 rounded-lg bg-[#00f59b] text-black font-bold text-xs"
                >
                  + Add
                </button>
              </div>
            </form>

            {/* Memory List */}
            <div className="flex flex-col space-y-2 max-h-60 overflow-y-auto">
              {memories.map((m) => (
                <div
                  key={m.id}
                  className="p-3 rounded-lg bg-[#080d19] border border-white/[0.06] flex items-center justify-between gap-3 text-xs"
                >
                  <div className="flex flex-col space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">{m.key}</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-white/[0.06] text-neutral-400 font-mono">
                        {m.source}
                      </span>
                    </div>
                    <span className="text-neutral-300">{m.value}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteMemory(m.id)}
                    className="text-neutral-500 hover:text-red-400 transition-colors p-1"
                    title="Delete memory"
                  >
                    <i className="ph ph-trash text-sm"></i>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── TAB 3: Personalized Reports ── */}
        {activeTab === 'reports' && (
          <div className="flex flex-col space-y-4">
            {selectedReport ? (
              <div className="p-5 rounded-xl bg-white/[0.03] border border-white/[0.08] flex flex-col space-y-3">
                <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
                  <h3 className="text-base font-bold text-white">{selectedReport.title}</h3>
                  <button
                    onClick={() => setSelectedReport(null)}
                    className="text-xs text-[#00f59b] hover:underline"
                  >
                    Back to Reports
                  </button>
                </div>
                <div className="prose prose-invert text-xs leading-relaxed max-h-96 overflow-y-auto whitespace-pre-wrap">
                  {selectedReport.content}
                </div>
              </div>
            ) : (
              <div className="flex flex-col space-y-2 max-h-72 overflow-y-auto">
                {reports.length === 0 ? (
                  <div className="p-8 text-center text-xs text-neutral-500">
                    No personalized reports generated yet. Deliberate on a match in the Arena to generate one!
                  </div>
                ) : (
                  reports.map((r) => (
                    <div
                      key={r.id}
                      onClick={() => setSelectedReport(r)}
                      className="p-3.5 rounded-xl bg-[#080d19] border border-white/[0.06] hover:border-[#00f59b]/40 cursor-pointer transition-all flex items-center justify-between"
                    >
                      <div className="flex flex-col space-y-0.5">
                        <span className="font-bold text-white text-sm">{r.title}</span>
                        <div className="flex items-center gap-2 text-[11px] text-neutral-400 font-mono">
                          <span>{r.report_type}</span>
                          <span>•</span>
                          <span>{new Date(r.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <i className="ph ph-caret-right text-neutral-400"></i>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
