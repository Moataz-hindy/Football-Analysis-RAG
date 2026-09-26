import React, { useId, useRef, useState } from 'react';
import './AdvisorPanel.css';

const REPORT_LABELS = {
  complete: 'Report complete',
  partial: 'Partial report',
  insufficient_evidence: 'Insufficient evidence',
  failed: 'Analysis failed',
};

const SUPPORT_LABELS = {
  source_backed: 'Source excerpt',
  discussion_claim: 'Discussion claim',
  inference: 'Inference',
  disputed: 'Disputed',
};

const VERDICT_LABELS = {
  supported: 'Supported by excerpt',
  grounded_inference: 'Grounded inference',
  discussion_only: 'Discussion claim only',
  disputed: 'Disputed',
  unsupported: 'Unsupported',
  contradicted: 'Contradicted',
  unassessed: 'Not assessed',
};

const RETAINED_VERDICTS = new Set([
  'supported', 'grounded_inference', 'discussion_only', 'disputed',
]);

function safeSourceUrl(value) {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

function displayClaim(claim) {
  if (!claim?.text) return 'Claim';
  try {
    const value = JSON.parse(claim.text);
    return value.text || value.claim || value.rationale || value.outcome || claim.text;
  } catch {
    return claim.text;
  }
}

function Citations({ ids = [], onSelect, evidenceId }) {
  if (!ids.length) return null;
  return (
    <span className="advisor-citations" aria-label="Cited evidence">
      {ids.map((id) => (
        <button
          key={id}
          type="button"
          className="advisor-citation"
          aria-label={`Read cited evidence ${id}`}
          aria-controls={`${evidenceId}-${id}`}
          onClick={() => onSelect(id)}
        >
          {id}
        </button>
      ))}
    </span>
  );
}

function Point({ point, onSelect, evidenceId }) {
  return (
    <li className="advisor-point">
      <p>{point.text || point.claim}</p>
      <div className="advisor-point-meta">
        {point.support && (
          <span className={`advisor-support advisor-support-${point.support}`}>
            {SUPPORT_LABELS[point.support] || point.support.replaceAll('_', ' ')}
          </span>
        )}
        <Citations ids={point.evidence_ids} onSelect={onSelect} evidenceId={evidenceId} />
      </div>
    </li>
  );
}

function Points({ title, points = [], empty, onSelect, evidenceId }) {
  if (!points.length && !empty) return null;
  return (
    <div className="advisor-points-section">
      <h4>{title}</h4>
      {points.length ? (
        <ul className="advisor-point-list">
          {points.map((point, index) => (
            <Point key={index} point={point} onSelect={onSelect} evidenceId={evidenceId} />
          ))}
        </ul>
      ) : <p className="advisor-muted">{empty}</p>}
    </div>
  );
}

function Reactions({ reactions = [], onSelect, evidenceId }) {
  if (!reactions.length) return null;
  return (
    <div className="advisor-points-section">
      <h4>Possible opponent responses</h4>
      <ul className="advisor-point-list">
        {reactions.map((reaction, index) => (
          <Point
            key={index}
            point={{ ...reaction, text: `${reaction.opponent}: ${reaction.text}` }}
            onSelect={onSelect}
            evidenceId={evidenceId}
          />
        ))}
      </ul>
    </div>
  );
}

function Option({ title, option, onSelect, evidenceId }) {
  return (
    <article className="advisor-subcard">
      <span className="advisor-eyebrow">{title}</span>
      <h3>{option?.option || 'Assessment unavailable'}</h3>
      {option ? (
        <>
          <Points title="Pros" points={option.pros} empty="No supported benefits were retained." onSelect={onSelect} evidenceId={evidenceId} />
          <Points title="Cons" points={option.cons} empty="No supported drawbacks were retained." onSelect={onSelect} evidenceId={evidenceId} />
          <Reactions reactions={option.opponent_responses} onSelect={onSelect} evidenceId={evidenceId} />
        </>
      ) : <p className="advisor-muted">There was not enough supported content to keep this option.</p>}
    </article>
  );
}

function TeamReview({ review, label, onSelect, evidenceId }) {
  const sections = [
    ['actual_actions', 'What the team did'],
    ['what_worked', 'What worked'],
    ['what_failed', 'What failed'],
    ['responses_to_opponent', 'Responses to the opponent'],
  ];
  return (
    <article className="advisor-subcard">
      <span className="advisor-eyebrow">Match review</span>
      <h3>{review?.team || label}</h3>
      {review ? (
        <>
          {sections.map(([key, title]) => (
            <Points key={key} title={title} points={review[key]} empty="No supported points retained." onSelect={onSelect} evidenceId={evidenceId} />
          ))}
          {(review.plausible_adjustments || []).map((option, index) => (
            <Option key={index} title="Possible adjustment" option={option} onSelect={onSelect} evidenceId={evidenceId} />
          ))}
        </>
      ) : <p className="advisor-muted">No supported team review was retained.</p>}
    </article>
  );
}

function TeamPlan({ plan, label, onSelect, evidenceId }) {
  return (
    <article className="advisor-subcard">
      <span className="advisor-eyebrow">Match plan</span>
      <h3>{plan?.team || label}</h3>
      {plan ? (
        <>
          <Points title="Should do" points={plan.should_do} empty="No supported actions retained." onSelect={onSelect} evidenceId={evidenceId} />
          <Points title="Should avoid" points={plan.should_avoid} empty="No supported risks retained." onSelect={onSelect} evidenceId={evidenceId} />
          <Reactions reactions={plan.opponent_responses} onSelect={onSelect} evidenceId={evidenceId} />
        </>
      ) : <p className="advisor-muted">No supported team plan was retained.</p>}
    </article>
  );
}

function Conditions({ items = [] }) {
  if (!items.length) return null;
  return (
    <div className="advisor-points-section">
      <h4>Conditions</h4>
      <ul className="advisor-plain-list">
        {items.map((item, index) => <li key={index}>{item}</li>)}
      </ul>
    </div>
  );
}

function Disagreements({ report, onSelect, evidenceId }) {
  if (!report.disagreements?.length && !report.disagreement_coverage) return null;
  return (
    <details className="advisor-details">
      <summary>Disagreements{report.disagreements?.length ? ` · ${report.disagreements.length}` : ''}</summary>
      {report.disagreement_coverage && <p className="advisor-muted">{report.disagreement_coverage}</p>}
      {(report.disagreements || []).map((item, index) => (
        <article key={index} className="advisor-disagreement">
          <h4>{item.issue}</h4>
          <span className="advisor-support advisor-support-disputed">{item.relationship?.replaceAll('_', ' ') || 'Disputed'}</span>
          {[item.side_a, item.side_b].filter(Boolean).map((side, sideIndex) => (
            <div key={sideIndex} className="advisor-disagreement-side">
              <p>{side.statement}</p>
              <blockquote>{side.quote}</blockquote>
              <Citations ids={[side.evidence_id]} onSelect={onSelect} evidenceId={evidenceId} />
            </div>
          ))}
        </article>
      ))}
    </details>
  );
}

function Verification({ verification, onSelect, evidenceId }) {
  if (!verification) {
    return <p className="advisor-verification-note">No citation verification details are available for this result.</p>;
  }
  const checks = verification.checks || [];
  const claims = new Map((verification.claims || []).map((claim) => [claim.id, claim]));
  const rejected = checks.filter((check) => !RETAINED_VERDICTS.has(check.verdict));
  const removedReferences = checks.filter((check) => check.unused_evidence_ids?.length).length;
  return (
    <details className="advisor-details">
      <summary>
        Citation checks · {checks.length} claims
        {rejected.length > 0 ? ` · ${rejected.length} rejected or unassessed` : ''}
      </summary>
      <p className="advisor-muted">Checks compare claims with the cited excerpts. They do not authenticate real-world facts or sources.</p>
      {verification.coverage && <p className="advisor-muted">{verification.coverage}</p>}
      {verification.error && <p className="advisor-notice advisor-notice-warning">{verification.error}</p>}
      {removedReferences > 0 && <p className="advisor-muted">Unused citations were removed from {removedReferences} claims.</p>}
      {!checks.length && <p className="advisor-muted">No claim checks were returned.</p>}
      {checks.map((check) => (
        <details className="advisor-check" key={check.claim_id}>
          <summary>
            <span className={`advisor-check-verdict ${RETAINED_VERDICTS.has(check.verdict) ? '' : 'advisor-check-rejected'}`}>
              {VERDICT_LABELS[check.verdict] || check.verdict}
            </span>
            <span>{displayClaim(claims.get(check.claim_id))}</span>
          </summary>
          <p>{check.reason}</p>
          {(check.quotes || []).map((quote, index) => (
            <div key={index} className="advisor-checked-quote">
              <span className="advisor-eyebrow">{quote.role}</span>
              <blockquote>{quote.quote}</blockquote>
              <Citations ids={[quote.evidence_id]} onSelect={onSelect} evidenceId={evidenceId} />
            </div>
          ))}
          {check.unused_evidence_ids?.length > 0 && (
            <p className="advisor-muted">Unused citations: {check.unused_evidence_ids.join(', ')}</p>
          )}
        </details>
      ))}
    </details>
  );
}

function Research({ research, onSelect, evidenceId }) {
  if (!research) return null;
  const attempts = research.attempts || [];
  const toolLabels = {
    knowledge_search: 'Search knowledge base',
    web_search: 'Search the web',
    read_web_page: 'Read web page',
  };
  const statusLabels = {
    success: 'Evidence retrieved',
    empty: 'No usable evidence found',
    failed: 'Retrieval failed',
    excluded: 'Evidence excluded',
  };
  return (
    <details className="advisor-details">
      <summary>Evidence research · {attempts.length} attempts</summary>
      <p className="advisor-muted">The advisor uses the saved discussion and can retrieve additional database and web excerpts. Finding a source does not establish that its claims are true.</p>
      {!attempts.length && <p className="advisor-muted">No additional retrieval attempts were recorded.</p>}
      {attempts.map((attempt, index) => {
        const href = safeSourceUrl(attempt.url);
        return (
          <article key={index} className="advisor-check">
            <h4>{toolLabels[attempt.tool] || attempt.tool?.replaceAll('_', ' ') || 'Retrieve evidence'}</h4>
            <p className="advisor-muted">{statusLabels[attempt.status] || attempt.status}</p>
            {attempt.query && <p>Search query: {attempt.query}</p>}
            {href && <p><a href={href} target="_blank" rel="noopener noreferrer">Requested source <i className="ph ph-arrow-square-out" aria-hidden="true" /></a></p>}
            {attempt.reason && <p>{attempt.reason}</p>}
            <Citations ids={attempt.source_ids} onSelect={onSelect} evidenceId={evidenceId} />
          </article>
        );
      })}
      {research.limitations?.length > 0 && (
        <ul className="advisor-plain-list">{research.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul>
      )}
    </details>
  );
}

export default function AdvisorPanel({
  discussion,
  discussionStatus = 'checking',
  analysis = { phase: 'waiting', job: null, error: null },
  configuration = { mode: 'decision' },
  onConfigurationChange,
  onRetry,
  onRefresh,
}) {
  const uniqueId = useId();
  const evidenceId = `advisor-evidence-${uniqueId}`;
  const settingsId = `advisor-settings-${uniqueId}`;
  const evidenceContainer = useRef(null);
  const [activeEvidence, setActiveEvidence] = useState(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const job = analysis.job;
  const response = job?.result?.response;
  const report = response?.report;
  const decisionHasBothOptions = report?.mode !== 'decision' || [report.do_it, report.do_not_do_it].every((option) => (
    [...(option?.pros || []), ...(option?.cons || [])].some((point) => point.evidence_ids?.length)
  ));
  const recommendation = decisionHasBothOptions ? report?.recommendation : null;
  const verification = job?.result?.verification;
  const phase = analysis.phase;
  const busy = ['submitting', 'queued', 'running'].includes(phase);
  const mode = configuration.mode || 'decision';
  const needsTeams = mode !== 'decision';
  const missingConfiguration = needsTeams && (
    !configuration.team_a?.trim()
    || !configuration.team_b?.trim()
    || (mode === 'match_preview' && (!configuration.evidence_cutoff || !configuration.match_kickoff))
  );
  const evidence = Array.from(new Map([
    ...(response?.research?.evidence || []),
    ...(verification?.evidence || []),
    ...(report?.evidence || []),
  ].map((item) => [item.id, item])).values());

  const change = (key, value) => onConfigurationChange?.({ ...configuration, [key]: value });
  const selectEvidence = (id) => {
    setActiveEvidence(id);
    setEvidenceOpen(true);
    window.requestAnimationFrame(() => {
      const target = Array.from(evidenceContainer.current?.querySelectorAll('[data-evidence-id]') || [])
        .find((element) => element.dataset.evidenceId === id);
      if (target) {
        target.open = true;
        const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
        target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' });
        target.focus({ preventScroll: true });
      }
    });
  };

  const contentProps = { onSelect: selectEvidence, evidenceId };
  const status = response?.status;
  const displayStatus = phase === 'error' || busy ? phase : status || phase;
  const label = REPORT_LABELS[displayStatus] || {
    waiting: 'After the final round',
    submitting: 'Starting analysis',
    queued: 'Queued',
    running: 'Analyzing & checking evidence',
    completed: 'Finished',
    error: 'Could not finish',
  }[displayStatus] || 'Advisor';

  return (
    <section id="discussion-advisor" className="advisor-panel" aria-labelledby={`advisor-title-${uniqueId}`}>
      <header className="advisor-header">
        <div className="advisor-heading">
          <span className="advisor-icon"><i className="ph ph-compass" aria-hidden="true" /></span>
          <div>
            <span className="advisor-eyebrow">From debate to decision</span>
            <h2 id={`advisor-title-${uniqueId}`}>Discussion Advisor</h2>
          </div>
        </div>
        <span className={`advisor-status advisor-status-${displayStatus}`} role="status" aria-live="polite">
          {busy && <i className="ph ph-spinner advisor-spinner" aria-hidden="true" />}
          {label}
        </span>
      </header>

      <p className="advisor-intro">An assessment using the discussion, relevant database evidence and web research, generated after all rounds finish.</p>

      <details className="advisor-details advisor-settings">
        <summary>Analysis settings · {{ decision: 'Decision', match_review: 'Match review', match_preview: 'Match preview' }[mode]}</summary>
        <div className="advisor-settings-grid">
          <label htmlFor={`${settingsId}-mode`}>
            Analysis type
            <select id={`${settingsId}-mode`} value={mode} disabled={busy} onChange={(event) => change('mode', event.target.value)}>
              <option value="decision">Decision · pros, cons & recommendation</option>
              <option value="match_review">Match review · what happened & adjustments</option>
              <option value="match_preview">Match preview · team plans & prediction</option>
            </select>
          </label>
          {needsTeams && (
            <>
              <label htmlFor={`${settingsId}-team-a`}>
                Team A
                <input id={`${settingsId}-team-a`} value={configuration.team_a || ''} disabled={busy} placeholder="Exact team name" onChange={(event) => change('team_a', event.target.value)} />
              </label>
              <label htmlFor={`${settingsId}-team-b`}>
                Team B
                <input id={`${settingsId}-team-b`} value={configuration.team_b || ''} disabled={busy} placeholder="Exact team name" onChange={(event) => change('team_b', event.target.value)} />
              </label>
            </>
          )}
          {mode === 'match_preview' && (
            <>
              <label htmlFor={`${settingsId}-cutoff`}>
                Evidence cutoff · your local time
                <input id={`${settingsId}-cutoff`} type="datetime-local" value={configuration.evidence_cutoff || ''} disabled={busy} onChange={(event) => change('evidence_cutoff', event.target.value)} />
              </label>
              <label htmlFor={`${settingsId}-kickoff`}>
                Kickoff · your local time
                <input id={`${settingsId}-kickoff`} type="datetime-local" value={configuration.match_kickoff || ''} disabled={busy} onChange={(event) => change('match_kickoff', event.target.value)} />
              </label>
            </>
          )}
        </div>
        {mode === 'match_preview' && (
          <p className="advisor-muted">Set a past or current evidence cutoff before a future kickoff. Only evidence eligible at that cutoff can support a prediction. Unknown source dates can prevent a prediction.</p>
        )}
        {missingConfiguration && <p className="advisor-muted">Complete the team names{mode === 'match_preview' ? ' and both dates' : ''} to run this analysis.</p>}
        <button type="button" className="advisor-button advisor-button-primary" disabled={busy || missingConfiguration || discussionStatus !== 'completed'} onClick={onRetry}>
          Apply settings & analyze
        </button>
      </details>

      {phase === 'waiting' && (
        <div className="advisor-state">
          <i className={`ph ${discussionStatus === 'failed' ? 'ph-warning-circle' : 'ph-hourglass-medium'}`} aria-hidden="true" />
          <div>
            <h3>{discussionStatus === 'failed' ? 'Discussion did not finish' : discussionStatus === 'unknown' ? 'Discussion completion could not be confirmed' : discussionStatus === 'checking' ? 'Checking discussion status' : 'Waiting for the discussion'}</h3>
            <p>{discussionStatus === 'failed' ? 'Start a new discussion or retry the failed discussion. The advisor needs its completed rounds.' : discussionStatus === 'unknown' ? 'Restore the backend connection to confirm that all discussion rounds finished.' : 'The advisor will start automatically once the final round is saved.'}</p>
          </div>
        </div>
      )}
      {busy && (
        <div className="advisor-state" aria-busy="true">
          <i className="ph ph-spinner advisor-spinner" aria-hidden="true" />
          <div>
            <h3>{phase === 'queued' ? 'Waiting for the advisor worker' : phase === 'submitting' ? 'Preparing your analysis' : 'Researching the question and checking evidence'}</h3>
            <p>The advisor searches the knowledge base and web, reads relevant sources, then checks its cited reasoning. The report will appear here when it finishes.</p>
          </div>
        </div>
      )}

      {(analysis.error || job?.error || response?.error) && (
        <div className="advisor-notice advisor-notice-error" role="alert">
          <h3>Advisor could not finish</h3>
          <p>{analysis.error || job?.error || response?.error}</p>
          <button type="button" className="advisor-button" disabled={busy || missingConfiguration || discussionStatus !== 'completed'} onClick={onRetry}>Retry analysis</button>
        </div>
      )}

      {response && !busy && (
        <>
          <div className="advisor-report-context">
            <span><strong>Question being assessed:</strong> {response.request?.question || discussion?.topic}</span>
            {job?.cached && <span className="advisor-support">Saved result</span>}
          </div>
          {status === 'partial' && <p className="advisor-notice advisor-notice-warning">Some sections or claims could not be supported. Read the limitations alongside the recommendation.</p>}
          {status === 'insufficient_evidence' && <p className="advisor-notice advisor-notice-warning">The discussion and available research do not provide enough eligible evidence for a reliable assessment.</p>}

          {report && (
            <div className="advisor-report">
              <Points title="Evidence findings" points={report.findings} {...contentProps} />
              {report.mode === 'decision' && (
                <>
                  <div className="advisor-grid">
                    <Option title="Take the action" option={report.do_it} {...contentProps} />
                    <Option title="Do not take the action" option={report.do_not_do_it} {...contentProps} />
                  </div>
                  {(report.alternatives || []).map((option, index) => <Option key={index} title="Alternative" option={option} {...contentProps} />)}
                </>
              )}
              {report.mode === 'match_review' && (
                <>
                  <Points title="What happened" points={report.what_happened} {...contentProps} />
                  <div className="advisor-grid">
                    <TeamReview review={report.team_a_review} label={response.request?.team_a || 'Team A'} {...contentProps} />
                    <TeamReview review={report.team_b_review} label={response.request?.team_b || 'Team B'} {...contentProps} />
                  </div>
                </>
              )}
              {report.mode === 'match_preview' && (
                <>
                  <div className="advisor-grid">
                    <TeamPlan plan={report.team_a_plan} label={response.request?.team_a || 'Team A'} {...contentProps} />
                    <TeamPlan plan={report.team_b_plan} label={response.request?.team_b || 'Team B'} {...contentProps} />
                  </div>
                  <article className="advisor-subcard">
                    <span className="advisor-eyebrow">Conditional prediction</span>
                    {report.prediction ? (
                      <>
                        <h3>{report.prediction.outcome}</h3>
                        <p className="advisor-muted">Scope: {report.prediction.scope === 'qualification' ? 'Qualification' : '90 minutes'}</p>
                        <p>{report.prediction.rationale}</p>
                        <Citations ids={report.prediction.evidence_ids} {...contentProps} />
                        <Conditions items={report.prediction.conditions} />
                        <p className="advisor-uncertainty"><strong>Uncertainty:</strong> {report.prediction.uncertainty}</p>
                      </>
                    ) : <p className="advisor-muted">No prediction passed the evidence requirements.</p>}
                  </article>
                </>
              )}
              <Points title="Decisive factors" points={report.decisive_factors} {...contentProps} />
              {recommendation ? (
                <article className="advisor-recommendation">
                  <span className="advisor-eyebrow"><i className="ph ph-signpost" aria-hidden="true" /> Advisor recommendation</span>
                  <h3>{recommendation.text}</h3>
                  <p>{recommendation.rationale}</p>
                  <Citations ids={recommendation.evidence_ids} {...contentProps} />
                  <Conditions items={recommendation.conditions} />
                  <p className="advisor-uncertainty"><strong>Uncertainty:</strong> {recommendation.uncertainty}</p>
                </article>
              ) : <p className="advisor-notice">No recommendation was retained after evidence checking.</p>}
              {report.assumptions?.length > 0 && (
                <details className="advisor-details">
                  <summary>Assumptions · {report.assumptions.length}</summary>
                  <p className="advisor-muted">These assumptions have not been authenticated by citation checking.</p>
                  <ul className="advisor-plain-list">{report.assumptions.map((item, index) => <li key={index}>{item}</li>)}</ul>
                </details>
              )}
              <Disagreements report={report} {...contentProps} />
            </div>
          )}

          {response.missing_information?.length > 0 && (
            <aside className="advisor-limitations">
              <h3><i className="ph ph-warning-circle" aria-hidden="true" /> Evidence gaps & limitations</h3>
              <ul className="advisor-plain-list">{response.missing_information.map((item, index) => <li key={index}>{item}</li>)}</ul>
            </aside>
          )}

          <Research research={response.research} {...contentProps} />
          <Verification verification={verification} {...contentProps} />

          {evidence.length > 0 && (
            <details className="advisor-details advisor-evidence" open={evidenceOpen} onToggle={(event) => {
              if (event.target === event.currentTarget) setEvidenceOpen(event.currentTarget.open);
            }} ref={evidenceContainer}>
              <summary>Evidence library · {evidence.length} excerpts</summary>
              <p className="advisor-muted">Original excerpts include evidence cited by removed claims. A discussion message records what an agent said; it does not establish that the claim is true.</p>
              {evidence.map((item) => {
                const href = safeSourceUrl(item.source);
                const origin = {
                  discussion: 'Discussion evidence',
                  knowledge_base: 'Knowledge base',
                  web_search: 'Web search',
                  web_page: 'Web page',
                }[item.origin || 'discussion'] || 'Research evidence';
                return (
                  <details key={item.id} id={`${evidenceId}-${item.id}`} data-evidence-id={item.id} tabIndex={-1} className={`advisor-evidence-item ${activeEvidence === item.id ? 'advisor-evidence-active' : ''}`} open={activeEvidence === item.id ? true : undefined}>
                    <summary><span className="advisor-evidence-label">{item.id}</span><span>{item.kind === 'message' ? `Discussion message ${item.message_ref || item.id}` : item.title || item.source || 'Retrieved evidence'}</span></summary>
                    <div className="advisor-evidence-meta">
                      <span>{origin}</span>
                      {href && <a href={href} target="_blank" rel="noopener noreferrer">Open source <i className="ph ph-arrow-square-out" aria-hidden="true" /></a>}
                      {item.kind === 'source' && <span>{item.published_at ? `Recorded publication: ${new Date(item.published_at).toLocaleString()}` : 'Publication time unknown'}</span>}
                      {item.modified_at && <span>Recorded update: {new Date(item.modified_at).toLocaleString()}</span>}
                      {item.message_ref ? <span>Attached to {item.message_ref}</span> : <span>Independently retrieved</span>}
                      {item.retrieved_at && <span>Retrieved: {new Date(item.retrieved_at).toLocaleString()}</span>}
                      {item.query && <span>Search query: {item.query}</span>}
                      {item.content_kind && <span>Content: {item.content_kind.replaceAll('_', ' ')}</span>}
                    </div>
                    <blockquote className="advisor-evidence-excerpt">{item.excerpt}</blockquote>
                  </details>
                );
              })}
            </details>
          )}
          <footer className="advisor-footer">
            <p>Based on this saved discussion and eligible excerpts from database and web research. Retrieval time is not publication time.</p>
            <button type="button" className="advisor-button" disabled={busy || missingConfiguration || discussionStatus !== 'completed'} onClick={onRefresh}><i className="ph ph-arrows-clockwise" aria-hidden="true" /> Reanalyze discussion</button>
          </footer>
        </>
      )}
    </section>
  );
}
