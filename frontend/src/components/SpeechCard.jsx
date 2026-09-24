import React from 'react';

/**
 * A single agent speech in the dialectical stream.
 *  - agent: entry from AGENTS / getAgentInfo
 *  - meta: timestamp / step line under the name
 *  - badge: { icon, label, className } stance pill
 *  - stats: [{ label, value, className }] telemetry footer items
 *  - action: { icon, label } footer button
 *  - index: position in the list, drives the staggered entrance
 */
export default function SpeechCard({ agent, meta, badge, content, stats, action, index = 0, onHover }) {
  return (
    <div
      className="speech-card card-enter w-full rounded-2xl bg-[#0d0f18]/90 border border-white/[0.08] p-4 relative flex flex-col space-y-3 shadow-lg hover:border-white/[0.14]"
      style={{ '--agent-color': agent.strokeColor, animationDelay: `${Math.min(index, 8) * 60}ms` }}
      onMouseEnter={onHover ? () => onHover(agent.id) : undefined}
      onMouseLeave={onHover ? () => onHover(null) : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3">
          <div
            className={`speech-avatar w-10 h-10 rounded-xl bg-surface-container-high border ${agent.border} flex items-center justify-center ${agent.textColor} ${agent.shadow} flex-shrink-0`}
          >
            <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              {agent.icon}
            </span>
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-headline text-[13px] font-bold text-white">{agent.name}</span>
              <span className={`font-mono text-[11px] ${agent.textColor}`}>#{agent.code}</span>
            </div>
            <span className="font-mono text-[10px] text-on-surface-variant">{meta}</span>
          </div>
        </div>

        {/* Stance Pill */}
        <div
          className={`px-2.5 py-1 rounded-full flex items-center gap-1 flex-shrink-0 font-mono text-[10px] font-bold tracking-tight ${badge.className}`}
        >
          <span className="material-symbols-outlined text-[13px]">{badge.icon}</span>
          <span>{badge.label}</span>
        </div>
      </div>

      {/* Message Content */}
      <p className="font-sans text-[13.5px] text-[#e1e1ef] leading-relaxed">{content}</p>

      {/* Telemetry Footer Bar */}
      <div className="pt-2 flex items-center justify-between text-[11px] font-mono border-t border-white/[0.06]">
        <div className="flex items-center gap-2 text-on-surface-variant">
          {stats.map((s, i) => (
            <React.Fragment key={s.label}>
              {i > 0 && <span className="text-white/20">•</span>}
              <span>
                {s.label}: <strong className={`font-medium ${s.className || 'text-white'}`}>{s.value}</strong>
              </span>
            </React.Fragment>
          ))}
        </div>
        <button className="group/action flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container-high border border-secondary/30 text-secondary hover:text-white hover:border-secondary/60 active:scale-95 transition-all">
          <span className="material-symbols-outlined text-[13px] transition-transform duration-200 group-hover/action:rotate-12">
            {action.icon}
          </span>
          <span className="font-medium text-[10px]">{action.label}</span>
        </button>
      </div>
    </div>
  );
}
