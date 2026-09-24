import React from 'react';
import { TABS } from '../constants/agents.js';

export default function BottomNav({ activeTab, setActiveTab }) {
  return (
    <nav className="fixed bottom-0 w-full z-50 pb-safe bg-surface-container-lowest/85 backdrop-blur-2xl shadow-[0_-4px_30px_rgba(0,0,0,0.6)]">
      <div className="h-20 px-space-sm flex items-center justify-around max-w-xl mx-auto">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <a
              key={tab.id}
              onClick={(e) => {
                e.preventDefault();
                setActiveTab(tab.id);
              }}
              className={`group flex flex-col items-center justify-center min-w-[44px] min-h-[44px] flex-1 py-space-xs transition-colors duration-200 cursor-pointer active:scale-95 ${
                isActive ? 'text-primary-container' : 'text-on-surface-variant hover:text-on-surface'
              }`}
              data-path={tab.id}
              href={`#${tab.id}`}
              aria-current={isActive ? 'page' : undefined}
            >
              <div className="relative flex flex-col items-center gap-space-xs">
                <span
                  className={`material-symbols-outlined text-[24px] transition-transform duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] ${
                    isActive ? '-translate-y-0.5 scale-110' : 'group-hover:-translate-y-0.5'
                  }`}
                  style={{ fontVariationSettings: `'FILL' ${isActive ? 1 : 0}` }}
                >
                  {tab.icon}
                </span>
                <span className="font-label-sm text-label-sm uppercase tracking-wider">{tab.label}</span>
                <span
                  className={`h-0.5 rounded-full transition-all duration-300 ${
                    isActive ? 'w-8 bg-primary-container shadow-[0_0_12px_rgba(0,245,155,0.7)]' : 'w-0'
                  }`}
                ></span>
              </div>
            </a>
          );
        })}
      </div>
    </nav>
  );
}
