import React, { useState } from 'react';

/**
 * Authentication Modal: Sign In & Register.
 *
 * Implements real backend authentication per Feature Group B:
 * - Uses /auth/login and /auth/register
 * - Never trusts client-side user ID
 * - Switches to profile onboarding upon successful registration
 */

export default function AuthModal({
  isOpen,
  initialMode = 'login', // 'login' or 'register'
  onClose,
  onLoginSuccess,
  onRegisterSuccess,
}) {
  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (mode === 'register') {
        const res = await fetch('/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: email.trim(),
            password,
            display_name: displayName.trim(),
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Registration failed.');
        }
        localStorage.setItem('touchline_token', data.token);
        if (onRegisterSuccess) {
          onRegisterSuccess(data);
        }
      } else {
        const res = await fetch('/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email.trim(), password }),
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Invalid email or password.');
        }
        localStorage.setItem('touchline_token', data.token);
        if (onLoginSuccess) {
          onLoginSuccess(data);
        }
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Authentication error.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-md rounded-2xl bg-[#0c1220] border border-white/[0.1] shadow-2xl p-6 sm:p-8 flex flex-col space-y-6">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-neutral-400 hover:text-white transition-colors"
          aria-label="Close authentication modal"
        >
          <i className="ph ph-x text-xl"></i>
        </button>

        {/* Brand Header */}
        <div className="flex flex-col space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#00f59b] shadow-[0_0_8px_#00f59b]"></span>
            <span className="font-mono text-[11px] font-bold text-[#00f59b] uppercase tracking-wider">
              Touchline Security Gateway
            </span>
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            {mode === 'register' ? 'Create Your Workspace' : 'Sign in to Touchline'}
          </h2>
          <p className="text-[13px] text-neutral-400">
            {mode === 'register'
              ? 'Initialize your personal profile and dedicated football memory.'
              : 'Enter your credentials to access your saved deliberations and models.'}
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex rounded-xl bg-white/[0.04] p-1 border border-white/[0.06]">
          <button
            type="button"
            onClick={() => { setMode('login'); setError(null); }}
            className={`flex-1 py-2 text-center text-xs font-semibold rounded-lg transition-all ${
              mode === 'login'
                ? 'bg-[#00f59b]/20 text-[#00f59b] border border-[#00f59b]/40 shadow-sm'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setMode('register'); setError(null); }}
            className={`flex-1 py-2 text-center text-xs font-semibold rounded-lg transition-all ${
              mode === 'register'
                ? 'bg-[#00f59b]/20 text-[#00f59b] border border-[#00f59b]/40 shadow-sm'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            Register
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-3 rounded-lg bg-red-500/15 border border-red-500/40 text-red-200 text-xs font-medium flex items-center gap-2">
            <i className="ph ph-warning-circle text-base flex-shrink-0"></i>
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
          {mode === 'register' && (
            <div className="flex flex-col space-y-1.5">
              <label className="text-xs font-semibold text-neutral-300">Display Name</label>
              <input
                type="text"
                required
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. Marwan"
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#00f59b] focus:ring-1 focus:ring-[#00f59b] transition-all"
              />
            </div>
          )}

          <div className="flex flex-col space-y-1.5">
            <label className="text-xs font-semibold text-neutral-300">Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. scout@football.ai"
              className="w-full px-3.5 py-2.5 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#00f59b] focus:ring-1 focus:ring-[#00f59b] transition-all"
            />
          </div>

          <div className="flex flex-col space-y-1.5">
            <label className="text-xs font-semibold text-neutral-300">Password</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              className="w-full px-3.5 py-2.5 rounded-lg bg-[#060a12] border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#00f59b] focus:ring-1 focus:ring-[#00f59b] transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-[#00f59b] hover:bg-[#34d399] text-black font-bold text-sm shadow-[0_0_20px_rgba(0,245,155,0.35)] transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 mt-2"
          >
            {loading ? 'Processing...' : mode === 'register' ? 'Create Account & Continue' : 'Sign In'}
          </button>
        </form>

        {/* Quick Demo Credentials */}
        <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] text-[11px] text-neutral-400 flex items-center justify-between">
          <span>Demo Account:</span>
          <button
            type="button"
            onClick={() => {
              setEmail('marwan@football.ai');
              setPassword('password123');
              setMode('login');
            }}
            className="text-[#00f59b] hover:underline font-mono"
          >
            Fill Demo (marwan@football.ai)
          </button>
        </div>
      </div>
    </div>
  );
}
