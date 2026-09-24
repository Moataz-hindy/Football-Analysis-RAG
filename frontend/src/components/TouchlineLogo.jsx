import React from 'react';

// Custom Touchline Pitch Logo SVG from Stitch.ai
export default function TouchlineLogo({ className = 'h-7 w-auto' }) {
  return (
    <svg viewBox="0 0 100 100" fill="none" className={className}>
      <defs>
        <linearGradient id="pitchGlow" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#00f59b" />
          <stop offset="50%" stopColor="#00d2ff" />
          <stop offset="100%" stopColor="#71a1ff" />
        </linearGradient>
        <filter id="glowFilter" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
      <rect x="8" y="8" width="84" height="84" rx="20" fill="#06070a" stroke="url(#pitchGlow)" strokeWidth="2.5" />
      <path d="M22 50 H78 M50 22 V78" stroke="#00f59b" strokeOpacity="0.3" strokeWidth="1.5" strokeDasharray="3 3" />
      <circle cx="50" cy="50" r="16" stroke="url(#pitchGlow)" strokeWidth="2" fill="none" filter="url(#glowFilter)" />
      <circle cx="50" cy="50" r="5" fill="#00f59b" filter="url(#glowFilter)" />
      <polygon points="50,26 62,38 56,44 44,44 38,38" fill="none" stroke="#00d2ff" strokeWidth="1.5" />
      <polygon points="50,74 62,62 56,56 44,56 38,62" fill="none" stroke="#71a1ff" strokeWidth="1.5" />
      <circle cx="28" cy="36" r="3" fill="#71a1ff" />
      <circle cx="72" cy="36" r="3" fill="#00d2ff" />
      <circle cx="28" cy="64" r="3" fill="#f59e0b" />
      <circle cx="72" cy="64" r="3" fill="#ffb4ab" />
      <circle cx="50" cy="20" r="2.5" fill="#00f59b" />
      <circle cx="50" cy="80" r="2.5" fill="#c0c1ff" />
    </svg>
  );
}
