import React from 'react';

export default function SharedEvidenceBrief({ brief }) {
  if (!brief) return null;
  return (
    <details className="card" style={{ padding: '16px 24px', marginBottom: '16px' }}>
      <summary>Shared evidence · {brief.sources?.length || 0} excerpts</summary>
      <p>Every specialist receives these excerpts before the opening round. Each must assess whether
        they support the question’s premise. Citations identify sources; they do not certify a claim.</p>
      {(brief.limitations || []).map((note, index) => <p key={index}>{note}</p>)}
      {(brief.sources || []).map((source) => (
        <div key={source.metadata.evidence_id} style={{ marginTop: '12px', overflowWrap: 'anywhere' }}>
          <strong>[{source.metadata.evidence_id}] </strong>
          {/^https?:\/\//i.test(source.source)
            ? <a href={source.source} target="_blank" rel="noreferrer">{source.metadata.title || source.source}</a>
            : <span>{source.source}</span>}
          <p>{source.content}{source.metadata.shortened ? ' … (excerpt shortened)' : ''}</p>
        </div>
      ))}
    </details>
  );
}
