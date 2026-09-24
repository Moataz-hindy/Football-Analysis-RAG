import React, { useState } from 'react';
import TouchlineLogo from './TouchlineLogo.jsx';
import { TABS } from '../constants/agents.js';

const LOGO_SRC =
  'https://lh3.googleusercontent.com/aida/AEtjO1WJ_0FCLOZS3h2FKLcoDZncdFSo84nF0aL4OF8GWxypjz-niekwbBOcy5XkIF8lQW7lurhO4JGdy1-pNHKSn3Zm62NNBP272tHmwXMVP4e4U9cE78FXodPwH1LoZ8P0-z9kJu-6a0V3eFufN5hdmSTByA9HKzAbq5I-MlV5eBxx7fkPPqeIZTVpOD7pg6luUSPg6z5tlKhxNxuiK3iq6Uk2YqpAOnc5Huiptvci47-OmiP2RLXxJKCeGz-t';

export default function Header({ activeTab, setActiveTab, healthStatus }) {
  const [logoFailed, setLogoFailed] = useState(false);
  const activeIndex = Math.max(0, TABS.findIndex((t) => t.id === activeTab));
  const activeLabel = TABS[activeIndex].label;

  return (
    <header className="fixed top-0 w-full z-50 pt-safe bg-surface-container-lowest/80 backdrop-blur-2xl shadow-[0_4px_30px_rgba(0,0,0,0.5)]">
      <div className="h-16 px-margin flex items-center justify-between gap-space-sm max-w-7xl mx-auto">
        {/* Brand & Subtitle */}
        <div className="flex items-center gap-space-sm min-w-0">
          {!logoFailed ? (
            <img
              alt="Touchline Intelligence logo"
              className="h-8 w-auto object-contain flex-shrink-0"
              src={LOGO_SRC}
              onError={() => setLogoFailed(true)}
            />
          ) : (
            <div className="w-8 h-8 rounded-lg bg-surface-container-high border border-primary/30 flex items-center justify-center relative shadow-[0_0_12px_rgba(0,245,155,0.18)] flex-shrink-0">
              <TouchlineLogo className="w-5 h-5" />
            </div>
          )}
          <div className="flex flex-col min-w-0">
            <div className="flex items-center gap-space-xs">
              <span className="font-headline-md text-headline-md tracking-wider uppercase text-on-surface truncate">
                Touchline Intelligence
              </span>
            </div>
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant truncate">
              Tactical Multi-Agent Command •{' '}
              <span key={activeTab} className="inline-block fade-swap">
                {activeLabel}
              </span>
            </span>
          </div>
        </div>

        {/* Top Desktop Tabs (Synced with Bottom Nav) — equal-width grid so the active pill can slide */}
        <div className="hidden md:grid grid-cols-4 relative bg-surface-container-low/90 p-1 rounded-xl border border-white/[0.08]">
          <span
            aria-hidden="true"
            className="absolute top-1 bottom-1 left-1 rounded-lg bg-primary-container shadow-[0_0_12px_rgba(0,245,155,0.4)] transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
            style={{ width: 'calc((100% - 0.5rem) / 4)', transform: `translateX(${activeIndex * 100}%)` }}
          />
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                aria-current={isActive ? 'page' : undefined}
                className={`relative z-10 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg font-mono text-[11px] font-bold uppercase transition-colors duration-200 cursor-pointer active:scale-[0.97] ${
                  isActive ? 'text-on-primary' : 'text-on-surface-variant hover:text-white'
                }`}
              >
                <span className="material-symbols-outlined text-[16px]">{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Latency & Profile Avatar */}
        <div className="flex items-center gap-space-xs flex-shrink-0">
          <div className="h-7 px-space-xs flex items-center gap-space-xs rounded bg-surface-container-high/90">
            <span className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse"></span>
            <span className="font-label-sm text-label-sm uppercase text-primary font-bold whitespace-nowrap tabular-nums">
              LIVE API {healthStatus.latencyMs}ms
            </span>
          </div>
          <button
            onClick={() => setActiveTab(activeTab === 'devops' ? 'deliberation' : 'devops')}
            aria-label="Agent Command"
            title="Toggle DevOps Command Center"
            className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0 hover:brightness-110 hover:shadow-[0_0_14px_rgba(0,245,155,0.5)] active:scale-95 transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
          </button>
        </div>
      </div>
    </header>
  );
}
