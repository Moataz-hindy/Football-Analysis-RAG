import React from 'react';
import AnimatedNumber from './AnimatedNumber.jsx';

const formatSyncTime = (sec) => {
  const hours = String(Math.floor(sec / 3600)).padStart(2, '0');
  const mins = String(Math.floor((sec % 3600) / 60)).padStart(2, '0');
  const secs = String(sec % 60).padStart(2, '0');
  return `${hours}:${mins}:${secs} ago`;
};

export default function DevOpsView({
  healthStatus,
  syncSeconds,
  simulatedThroughput,
  copiedTerminal,
  handleCopyTerminal,
  isProbing,
  handleReprobe,
}) {
  return (
    <div className="flex flex-col w-full px-margin py-space-sm gap-space-md">
      {/* Sub-Header Status Ribbon */}
      <div className="flex items-center justify-between bg-surface-container-low/80 backdrop-blur-xl px-space-md py-space-sm rounded-xl shadow-lg">
        <div className="flex items-center gap-space-sm min-w-0">
          <div className="w-2.5 h-2.5 rounded-full bg-primary-container animate-ping flex-shrink-0"></div>
          <span className="font-label-sm text-label-sm uppercase tracking-wider text-primary font-bold truncate">
            Mesh Node eu-west-1a // Nominal
          </span>
        </div>
        <div className="flex items-center gap-space-xs flex-shrink-0">
          <span className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Sync:</span>
          <span className="font-label-sm text-label-sm text-secondary font-semibold tabular-nums" id="telemetry-sync-time">
            {formatSyncTime(syncSeconds)}
          </span>
        </div>
      </div>

      {/* Cluster Health Overview Grid */}
      <div className="grid grid-cols-2 gap-space-sm">
        {/* Card 1: System SLA */}
        <div style={{ animationDelay: '0ms' }} className="metric-tile card-enter bg-surface-container-low/90 backdrop-blur-md p-space-md rounded-xl shadow-md flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute -right-6 -top-6 w-20 h-20 bg-primary-container/10 rounded-full blur-xl pointer-events-none"></div>
          <div className="flex items-center justify-between mb-space-xs">
            <span className="font-label-sm text-label-sm uppercase text-on-surface-variant">System SLA</span>
            <span className="material-symbols-outlined text-primary-container text-[18px]">verified</span>
          </div>
          <div className="flex flex-col">
            <span className="font-headline-lg-mobile text-headline-lg-mobile text-primary font-bold">
              <AnimatedNumber value={99.98} decimals={2} />%
            </span>
            <div className="flex items-center gap-space-xs mt-space-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-primary-container"></span>
              <span className="font-label-sm text-label-sm text-on-surface-variant">30d Up • Zero Sev-1</span>
            </div>
          </div>
        </div>

        {/* Card 2: Deliberation Latency */}
        <div style={{ animationDelay: '60ms' }} className="metric-tile card-enter bg-surface-container-low/90 backdrop-blur-md p-space-md rounded-xl shadow-md flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute -right-6 -top-6 w-20 h-20 bg-secondary-container/10 rounded-full blur-xl pointer-events-none"></div>
          <div className="flex items-center justify-between mb-space-xs">
            <span className="font-label-sm text-label-sm uppercase text-on-surface-variant">Deliberation</span>
            <span className="material-symbols-outlined text-secondary text-[18px]">bolt</span>
          </div>
          <div className="flex flex-col">
            <span className="font-headline-lg-mobile text-headline-lg-mobile text-secondary font-bold">
              <AnimatedNumber value={healthStatus.latencyMs || 42} duration={400} />
              <span className="font-label-md text-label-md text-on-surface-variant ml-0.5">ms</span>
            </span>
            <div className="flex items-center gap-space-xs mt-space-xs">
              <span className="font-label-sm text-label-sm text-on-surface-variant">p95: 68ms (Stable)</span>
            </div>
          </div>
        </div>

        {/* Card 3: Active Agents */}
        <div style={{ animationDelay: '120ms' }} className="metric-tile card-enter bg-surface-container-low/90 backdrop-blur-md p-space-md rounded-xl shadow-md flex flex-col justify-between relative overflow-hidden group">
          <div className="flex items-center justify-between mb-space-xs">
            <span className="font-label-sm text-label-sm uppercase text-on-surface-variant">Agent Workers</span>
            <span className="material-symbols-outlined text-primary-fixed-dim text-[18px]">hub</span>
          </div>
          <div className="flex flex-col">
            <div className="flex items-baseline gap-space-xs">
              <span className="font-headline-lg-mobile text-headline-lg-mobile text-on-surface font-bold">
                <AnimatedNumber value={6} />/6
              </span>
              <span className="font-label-sm text-label-sm text-primary uppercase font-bold">Hot Standby</span>
            </div>
            <div className="w-full bg-surface-container-highest h-1 rounded-full mt-space-sm overflow-hidden">
              <div className="bar-grow bg-primary-container h-full w-full rounded-full"></div>
            </div>
          </div>
        </div>

        {/* Card 4: Memory Footprint */}
        <div style={{ animationDelay: '180ms' }} className="metric-tile card-enter bg-surface-container-low/90 backdrop-blur-md p-space-md rounded-xl shadow-md flex flex-col justify-between relative overflow-hidden group">
          <div className="flex items-center justify-between mb-space-xs">
            <span className="font-label-sm text-label-sm uppercase text-on-surface-variant">Memory Usage</span>
            <span className="material-symbols-outlined text-tertiary-fixed-dim text-[18px]">memory</span>
          </div>
          <div className="flex flex-col">
            <div className="flex items-baseline gap-space-xs">
              <span className="font-headline-lg-mobile text-headline-lg-mobile text-on-surface font-bold">
                <AnimatedNumber value={2.1} decimals={1} />
              </span>
              <span className="font-label-sm text-label-sm text-on-surface-variant">/ 8.0 GB</span>
            </div>
            <div className="w-full bg-surface-container-highest h-1 rounded-full mt-space-sm overflow-hidden">
              <div className="bar-grow bg-secondary-container h-full rounded-full" style={{ width: '26.25%' }}></div>
            </div>
          </div>
        </div>
      </div>

      {/* Container Mesh & Microservices */}
      <div className="flex flex-col gap-space-sm">
        <div className="flex items-center justify-between px-space-xs">
          <div className="flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-primary-container text-[18px]">view_in_ar</span>
            <span className="font-headline-md text-headline-md text-on-surface font-bold tracking-tight">
              Mesh Microservices
            </span>
          </div>
          <span className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">
            Docker Swarm v24.0
          </span>
        </div>

        {/* Service 1: FastAPI */}
        <div style={{ animationDelay: '240ms' }} className="metric-tile card-enter bg-surface-container-low/90 backdrop-blur-md p-space-md rounded-xl shadow-md flex flex-col gap-space-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-sm min-w-0">
              <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-primary-container text-[20px]">rocket_launch</span>
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-space-xs">
                  <span className="font-body-md text-body-md font-bold text-on-surface truncate">FastAPI Ingestion Engine</span>
                  <span className="px-1.5 py-0.5 rounded bg-surface-container-high font-label-sm text-label-sm text-secondary">:8000</span>
                </div>
                <span className="font-label-sm text-label-sm text-on-surface-variant">v0.110.0 • Async ASGI Coroutine Pool</span>
              </div>
            </div>
            <span className="px-2 py-1 rounded bg-primary/10 text-primary font-label-sm text-label-sm uppercase font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse"></span>
              HEALTHY
            </span>
          </div>
          <div className="grid grid-cols-2 gap-space-sm bg-surface-container-lowest/60 p-space-sm rounded-lg">
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm text-on-surface-variant">INFERENCE SPEED</span>
              <span className="font-label-md text-label-md text-primary font-semibold">
                <span key={simulatedThroughput} className="tick-flash tabular-nums">
                  {simulatedThroughput}
                </span>{' '}
                tok/s
              </span>
            </div>
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm text-on-surface-variant">SOCKET CAPACITY</span>
              <span className="font-label-md text-label-md text-on-surface font-semibold">10,000 WSS (Pool 8%)</span>
            </div>
          </div>
        </div>

        {/* Service 2: PostgreSQL + pgvector */}
        <div style={{ animationDelay: '300ms' }} className="metric-tile card-enter bg-surface-container-low/90 backdrop-blur-md p-space-md rounded-xl shadow-md flex flex-col gap-space-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-sm min-w-0">
              <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-secondary-container text-[20px]">database</span>
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-space-xs">
                  <span className="font-body-md text-body-md font-bold text-on-surface truncate">PostgreSQL + pgvector</span>
                  <span className="px-1.5 py-0.5 rounded bg-surface-container-high font-label-sm text-label-sm text-secondary">:5432</span>
                </div>
                <span className="font-label-sm text-label-sm text-on-surface-variant">1,536-dim Embedding Spatial Index</span>
              </div>
            </div>
            <span className="px-2 py-1 rounded bg-primary/10 text-primary font-label-sm text-label-sm uppercase font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse"></span>
              OPTIMAL
            </span>
          </div>
          <div className="grid grid-cols-2 gap-space-sm bg-surface-container-lowest/60 p-space-sm rounded-lg">
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm text-on-surface-variant">KNN RECALL LATENCY</span>
              <span className="font-label-md text-label-md text-secondary font-semibold">1.2ms (HNSW)</span>
            </div>
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm text-on-surface-variant">RECORDS INDEXED</span>
              <span className="font-label-md text-label-md text-on-surface font-semibold">4.82M Spatial Vectors</span>
            </div>
          </div>
        </div>

        {/* Service 3: Celery + Redis Broker */}
        <div style={{ animationDelay: '360ms' }} className="metric-tile card-enter bg-surface-container-low/90 backdrop-blur-md p-space-md rounded-xl shadow-md flex flex-col gap-space-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-sm min-w-0">
              <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-tertiary-fixed-dim text-[20px]">sync_alt</span>
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-space-xs">
                  <span className="font-body-md text-body-md font-bold text-on-surface truncate">Celery / Redis Broker</span>
                  <span className="px-1.5 py-0.5 rounded bg-surface-container-high font-label-sm text-label-sm text-secondary">:6379</span>
                </div>
                <span className="font-label-sm text-label-sm text-on-surface-variant">Multi-Agent Deliberation Queue</span>
              </div>
            </div>
            <span className="px-2 py-1 rounded bg-primary/10 text-primary font-label-sm text-label-sm uppercase font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse"></span>
              STANDBY
            </span>
          </div>
          <div className="grid grid-cols-2 gap-space-sm bg-surface-container-lowest/60 p-space-sm rounded-lg">
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm text-on-surface-variant">PACKET LOSS / DROPS</span>
              <span className="font-label-md text-label-md text-primary font-semibold">0 pkts (0.000%)</span>
            </div>
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm text-on-surface-variant">PENDING TASKS</span>
              <span className="font-label-md text-label-md text-on-surface font-semibold">0 in Queue (Idle)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive API Documentation Hub */}
      <div className="flex flex-col gap-space-sm">
        <div className="flex items-center justify-between px-space-xs">
          <div className="flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-secondary-container text-[18px]">api</span>
            <span className="font-headline-md text-headline-md text-on-surface font-bold tracking-tight">
              API Interface Hub
            </span>
          </div>
          <span className="font-label-sm text-label-sm uppercase tracking-wider text-secondary font-semibold">
            v2.4 Spec Active
          </span>
        </div>
        <div className="grid grid-cols-3 gap-space-xs">
          {/* Swagger UI Link */}
          <a
            className="bg-surface-container-low hover:bg-surface-container-high hover:-translate-y-0.5 active:scale-95 transition-all duration-200 p-space-sm rounded-lg shadow-sm flex flex-col items-center text-center gap-space-xs group"
            href="/docs"
            target="_blank"
            rel="noreferrer"
          >
            <div className="w-9 h-9 rounded-full bg-primary-container/10 flex items-center justify-center text-primary-container group-hover:scale-105 transition-transform">
              <span className="material-symbols-outlined text-[20px]">code</span>
            </div>
            <span className="font-label-md text-label-md text-on-surface font-bold">Swagger UI</span>
            <span className="font-label-sm text-label-sm text-on-surface-variant">/docs</span>
            <span className="font-label-sm text-label-sm text-primary uppercase font-semibold mt-0.5">Test API</span>
          </a>

          {/* ReDoc Link */}
          <a
            className="bg-surface-container-low hover:bg-surface-container-high hover:-translate-y-0.5 active:scale-95 transition-all duration-200 p-space-sm rounded-lg shadow-sm flex flex-col items-center text-center gap-space-xs group"
            href="/redoc"
            target="_blank"
            rel="noreferrer"
          >
            <div className="w-9 h-9 rounded-full bg-secondary-container/10 flex items-center justify-center text-secondary-container group-hover:scale-105 transition-transform">
              <span className="material-symbols-outlined text-[20px]">menu_book</span>
            </div>
            <span className="font-label-md text-label-md text-on-surface font-bold">ReDoc</span>
            <span className="font-label-sm text-label-sm text-on-surface-variant">/redoc</span>
            <span className="font-label-sm text-label-sm text-secondary uppercase font-semibold mt-0.5">OpenAPI</span>
          </a>

          {/* Prometheus Stream Link */}
          <a
            className="bg-surface-container-low hover:bg-surface-container-high hover:-translate-y-0.5 active:scale-95 transition-all duration-200 p-space-sm rounded-lg shadow-sm flex flex-col items-center text-center gap-space-xs group"
            href="/metrics"
            target="_blank"
            rel="noreferrer"
          >
            <div className="w-9 h-9 rounded-full bg-tertiary-container/10 flex items-center justify-center text-tertiary-container group-hover:scale-105 transition-transform">
              <span className="material-symbols-outlined text-[20px]">insights</span>
            </div>
            <span className="font-label-md text-label-md text-on-surface font-bold">Metrics</span>
            <span className="font-label-sm text-label-sm text-on-surface-variant">/metrics</span>
            <span className="font-label-sm text-label-sm text-tertiary-fixed-dim uppercase font-semibold mt-0.5">Prometheus</span>
          </a>
        </div>
      </div>

      {/* Live Interactive Terminal Telemetry */}
      <div className="flex flex-col gap-space-xs">
        <div className="flex items-center justify-between px-space-xs">
          <div className="flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-primary text-[18px]">terminal</span>
            <span className="font-headline-md text-headline-md text-on-surface font-bold tracking-tight">
              Agent Daemon Terminal
            </span>
          </div>
          <span className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">
            TTY /dev/pts/3
          </span>
        </div>

        {/* Terminal Box */}
        <div className="bg-surface-container-lowest rounded-xl shadow-xl overflow-hidden flex flex-col">
          {/* Titlebar */}
          <div className="bg-surface-container px-space-md py-space-xs flex items-center justify-between select-none">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-error-container/80"></div>
              <div className="w-3 h-3 rounded-full bg-secondary-container/40"></div>
              <div className="w-3 h-3 rounded-full bg-primary-container/80"></div>
              <span className="font-label-sm text-label-sm text-on-surface-variant ml-space-xs truncate">
                bash — touchline-agent-cluster
              </span>
            </div>
            <button
              onClick={handleCopyTerminal}
              className="flex items-center gap-1 px-2 py-1 rounded bg-surface-container-high hover:bg-surface-bright text-on-surface active:scale-95 transition-all cursor-pointer"
              id="copy-terminal-btn"
            >
              <span key={copiedTerminal ? 'done' : 'idle'} className="material-symbols-outlined text-[14px] fade-swap">
                {copiedTerminal ? 'check' : 'content_copy'}
              </span>
              <span className="font-label-sm text-label-sm uppercase font-semibold" id="copy-btn-text">
                {copiedTerminal ? 'Copied!' : 'Copy Output'}
              </span>
            </button>
          </div>

          {/* Terminal Body */}
          <div className="p-space-md font-label-sm text-label-sm overflow-x-auto space-y-2 text-on-surface" id="terminal-content">
            <div className="flex items-center gap-space-xs text-on-surface-variant">
              <span className="text-primary font-bold">touchline@node-01:~$</span>
              <span className="text-secondary">curl -s http://localhost:8000/health/agents | jq</span>
            </div>
            <pre className="font-label-sm text-label-sm text-on-surface leading-relaxed whitespace-pre font-mono">
              <span className="text-on-surface-variant">&#123;</span>{'\n'}
              {'  '}<span className="text-secondary">"cluster_id"</span>: <span className="text-primary-container">"tactical-consensus-alpha"</span>,{'\n'}
              {'  '}<span className="text-secondary">"timestamp"</span>: <span className="text-on-surface">"2025-05-18T20:41:03.491Z"</span>,{'\n'}
              {'  '}<span className="text-secondary">"status"</span>: <span className="text-primary-container">"HEALTH_NOMINAL_OK"</span>,{'\n'}
              {'  '}<span className="text-secondary">"daemon_mesh"</span>: &#123;{'\n'}
              {'    '}<span className="text-secondary">"pitch_spatial_agent"</span>: &#123; <span className="text-secondary">"status"</span>: <span className="text-primary-container">"ONLINE"</span>, <span className="text-secondary">"ping_ms"</span>: <span className="text-primary">11.4</span> &#125;,{'\n'}
              {'    '}<span className="text-secondary">"tactical_xg_agent"</span>:    &#123; <span className="text-secondary">"status"</span>: <span className="text-primary-container">"ONLINE"</span>, <span className="text-secondary">"ping_ms"</span>: <span className="text-primary">14.1</span> &#125;,{'\n'}
              {'    '}<span className="text-secondary">"opposition_bias_agent"</span>:&#123; <span className="text-secondary">"status"</span>: <span className="text-primary-container">"ONLINE"</span>, <span className="text-secondary">"ping_ms"</span>: <span className="text-primary">9.8</span> &#125;,{'\n'}
              {'    '}<span className="text-secondary">"substitution_ai_agent"</span>:&#123; <span className="text-secondary">"status"</span>: <span className="text-primary-container">"ONLINE"</span>, <span className="text-secondary">"ping_ms"</span>: <span className="text-primary">12.0</span> &#125;,{'\n'}
              {'    '}<span className="text-secondary">"referee_bias_agent"</span>:   &#123; <span className="text-secondary">"status"</span>: <span className="text-primary-container">"ONLINE"</span>, <span className="text-secondary">"ping_ms"</span>: <span className="text-primary">16.3</span> &#125;,{'\n'}
              {'    '}<span className="text-secondary">"fatigue_telemetry_agent"</span>:&#123; <span className="text-secondary">"status"</span>: <span className="text-primary-container">"ONLINE"</span>, <span className="text-secondary">"ping_ms"</span>: <span className="text-primary">8.6</span> &#125;{'\n'}
              {'  '}&#125;,{'\n'}
              {'  '}<span className="text-secondary">"consensus_consensus_reached"</span>: <span className="text-primary-container">true</span>,{'\n'}
              {'  '}<span className="text-secondary">"mean_worker_jitter"</span>: <span className="text-secondary-fixed">"0.04ms"</span>{'\n'}
              <span className="text-on-surface-variant">&#125;</span>
            </pre>
          </div>

          {/* Terminal Footer / Command Bar */}
          <div className="bg-surface-container-high/60 px-space-md py-space-xs flex items-center justify-between text-on-surface-variant">
            <div className="flex items-center gap-space-xs">
              <span className="w-2 h-2 rounded-full bg-primary-container"></span>
              <span className="font-label-sm text-label-sm uppercase tracking-wider">Listening Port 8000 (Keep-Alive)</span>
            </div>
            <button
              onClick={handleReprobe}
              className="font-label-sm text-label-sm text-primary hover:text-primary-fixed uppercase font-semibold flex items-center gap-1 cursor-pointer"
              id="ping-refresh-btn"
            >
              <span className={`material-symbols-outlined text-[14px] ${isProbing ? 'animate-spin' : ''}`}>refresh</span>
              {isProbing ? 'Probing...' : 'Re-probe'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
