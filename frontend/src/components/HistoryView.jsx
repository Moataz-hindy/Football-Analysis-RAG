import React from 'react';

export default function HistoryView({ savedDiscussions, setSavedDiscussions, loadDiscussion, setActiveTab }) {
  return (
    <div className="flex flex-col w-full px-margin py-space-sm gap-space-md">
      {/* Header Ribbon */}
      <div className="flex items-center justify-between bg-surface-container-low/80 backdrop-blur-xl px-space-md py-space-sm rounded-xl shadow-lg">
        <div className="flex items-center gap-space-sm min-w-0">
          <div className="w-2.5 h-2.5 rounded-full bg-primary-container animate-ping flex-shrink-0"></div>
          <span className="font-label-sm text-label-sm uppercase tracking-wider text-primary font-bold truncate">
            Discussion Archives & Saved Rooms
          </span>
        </div>
        <div className="flex items-center gap-space-xs flex-shrink-0">
          <span className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Total:</span>
          <span className="font-label-sm text-label-sm text-secondary font-semibold">
            {savedDiscussions.length} Saved
          </span>
        </div>
      </div>

      {/* Discussion List */}
      <div className="flex flex-col gap-space-sm">
        <div className="flex items-center justify-between px-space-xs">
          <div className="flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-primary-container text-[18px]">history_toggle_off</span>
            <span className="font-headline-md text-headline-md text-on-surface font-bold tracking-tight">
              Recorded Debates
            </span>
          </div>
          <button
            onClick={() => {
              fetch('/discussions')
                .then((r) => r.json())
                .then((d) => setSavedDiscussions(d.discussions || []))
                .catch(console.error);
            }}
            className="group/refresh font-label-sm text-label-sm text-primary hover:text-primary-fixed uppercase font-semibold flex items-center gap-1 cursor-pointer active:scale-95 transition-transform"
          >
            <span className="material-symbols-outlined text-[14px] transition-transform duration-500 group-hover/refresh:-rotate-180">refresh</span>
            Refresh
          </button>
        </div>

        {savedDiscussions.length === 0 ? (
          <div className="card-enter bg-surface-container-low/90 backdrop-blur-md p-space-lg rounded-xl shadow-md text-center flex flex-col items-center gap-space-sm">
            <span className="material-symbols-outlined text-[36px] text-on-surface-variant">folder_off</span>
            <h3 className="font-headline-md text-headline-md font-bold text-on-surface">No Saved Deliberations Found</h3>
            <p className="font-body-md text-body-md text-on-surface-variant max-w-md">
              Launch a deliberation topic from the Deliberation Room to record multi-agent rounds and dialectical synthesis here.
            </p>
            <button
              onClick={() => setActiveTab('deliberation')}
              className="mt-space-xs px-space-md py-space-xs bg-primary-container text-on-primary font-label-sm text-label-sm font-bold uppercase rounded-lg hover:brightness-110 transition-all cursor-pointer"
            >
              Go to Deliberation
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-sm">
            {savedDiscussions.map((disc, idx) => (
              <div
                key={disc.discussion_id || idx}
                style={{ animationDelay: `${Math.min(idx, 10) * 50}ms` }}
                onClick={() => {
                  loadDiscussion(disc.discussion_id);
                  setActiveTab('deliberation');
                }}
                className="card-enter metric-tile active:scale-[0.99] bg-surface-container-low/90 hover:bg-surface-container-high transition-all p-space-md rounded-xl shadow-md flex flex-col justify-between gap-space-sm border border-white/[0.04] hover:border-primary-container/40 cursor-pointer group"
              >
                <div className="flex items-start justify-between gap-space-xs">
                  <div className="flex flex-col min-w-0">
                    <span className="font-label-sm text-label-sm text-secondary font-mono truncate">
                      {disc.discussion_id}
                    </span>
                    <h4 className="font-body-md text-body-md font-bold text-on-surface group-hover:text-primary transition-colors line-clamp-2 mt-0.5">
                      {disc.topic || 'Untitled Tactical Debate'}
                    </h4>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-primary/10 text-primary font-label-sm text-label-sm font-bold uppercase flex-shrink-0">
                    LOAD
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-space-xs bg-surface-container-lowest/60 p-space-xs rounded-lg text-center">
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm text-on-surface-variant">AGENTS</span>
                    <span className="font-label-md text-label-md text-primary font-semibold">
                      {disc.num_agents || 6}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm text-on-surface-variant">ROUNDS</span>
                    <span className="font-label-md text-label-md text-secondary font-semibold">
                      {disc.num_rounds || 3}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm text-on-surface-variant">MSGS</span>
                    <span className="font-label-md text-label-md text-on-surface font-semibold">
                      {disc.num_messages || 18}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-on-surface-variant pt-1 border-t border-white/[0.04]">
                  <span className="font-label-sm text-label-sm">
                    {disc.timestamp ? new Date(disc.timestamp).toLocaleString() : 'Recent Debate'}
                  </span>
                  <span className="font-label-sm text-label-sm text-primary group-hover:translate-x-0.5 transition-transform flex items-center gap-1 font-semibold">
                    Replay <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
