import React, { useEffect, useMemo, useState } from 'react';
import { advisorClient } from '../lib/advisorClient';

export default function AdvisorPanel({ discussion, status }) {
  const id = discussion?.discussion_id;
  const revision = useMemo(() => JSON.stringify([discussion?.topic, discussion?.messages]), [discussion]);
  const [request, setRequest] = useState({ sequence: 0, retryFailed: false });
  const [result, setResult] = useState(null);
  useEffect(() => {
    if (!id || status !== 'completed') return undefined;
    let active = true;
    setResult(null);
    const explicitRequest = request.revision === revision;
    advisorClient.get(id, revision, { refresh: explicitRequest && request.sequence > 0,
      retryFailed: explicitRequest && request.retryFailed })
      .then((data) => { if (active) setResult({ ...data, id, revision }); });
    return () => { active = false; };
  }, [id, revision, status, request]);

  if (!discussion) return null;
  const current = result?.id === id && result?.revision === revision ? result : null;
  return (
    <section aria-labelledby="advisor-title" className="card" style={{
      padding: '22px 24px', marginBottom: '20px', border: '1px solid var(--color-accent)',
      borderRadius: 'var(--radius-md)', background: 'var(--color-surface)',
    }}>
      <h2 id="advisor-title" style={{ margin: '0 0 10px', fontSize: '20px', color: 'var(--color-neutral-100)' }}>
        Advisor’s opinion
      </h2>
      {status !== 'completed' ? (
        <p style={{ color: 'var(--color-neutral-400)' }}>The Advisor’s opinion will appear here when the discussion finishes.</p>
      ) : !current ? (
        <p role="status">Preparing an assessment from the saved discussion. Temporary model failures are retried automatically; this can take several minutes…</p>
      ) : current.state === 'completed' ? (
        <>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, color: 'var(--color-neutral-100)' }}>{current.opinion}</div>
          <p style={{ fontSize: '12px', color: 'var(--color-neutral-400)', marginBottom: 0 }}>
            {current.evidence_available ? 'Based on the discussion and its saved sources; not independently fact-checked.'
              : 'Tentative assessment: this discussion has no saved source excerpts.'}
          </p>
          {current.sources?.length > 0 && (
            <details style={{ marginTop: '12px', fontSize: '13px' }}>
              <summary>Sources cited</summary>
              {current.sources.map((source) => (
                <div key={source.id} style={{ marginTop: '10px', overflowWrap: 'anywhere' }}>
                  {/^(https?):\/\//i.test(source.source)
                    ? <a href={source.source} target="_blank" rel="noreferrer">[{source.id}] {source.source}</a>
                    : <span>[{source.id}] {source.source}</span>}
                  <p>{source.excerpt}{source.shortened ? ' …' : ''}</p>
                </div>
              ))}
            </details>
          )}
        </>
      ) : (
        <div>
          <p role="alert">{current.error || 'The Advisor is unavailable.'}</p>
          {(current.retryable || current.reconnect) && (
            <button className="btn btn-ghost" type="button" onClick={() => setRequest((old) => ({
              sequence: old.sequence + 1, retryFailed: Boolean(current.retryable), revision,
            }))}>{current.retryable ? 'Retry opinion' : 'Check again'}</button>
          )}
        </div>
      )}
    </section>
  );
}
