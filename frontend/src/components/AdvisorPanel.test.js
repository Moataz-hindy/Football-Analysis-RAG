import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { build } from 'esbuild';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

// Compile the real component without a browser, CSS runtime or network.
const compiled = await build({
  entryPoints: [fileURLToPath(new URL('./AdvisorPanel.jsx', import.meta.url))],
  bundle: true,
  write: false,
  platform: 'node',
  format: 'cjs',
  external: ['react'],
  loader: { '.css': 'empty' },
});
const require = createRequire(import.meta.url);
const module = { exports: {} };
new Function('require', 'module', 'exports', compiled.outputFiles[0].text)(
  require, module, module.exports,
);
const AdvisorPanel = module.exports.default;

const request = {
  discussion_id: 'advisor-test',
  mode: 'decision',
  question: 'Should the team sign an attacker?',
};
const source = {
  id: 'S001',
  kind: 'source',
  message_ref: 'M001',
  source: 'https://example.com/squad',
  excerpt: 'The squad needs depth, but the transfer budget is limited.',
  published_at: '2026-09-20T12:00:00Z',
};
const point = {
  text: 'The attacker could improve squad depth.',
  evidence_ids: ['S001'],
  support: 'inference',
};
const risk = {
  text: 'A large fee could restrict other squad improvements.',
  evidence_ids: ['S001'],
  support: 'inference',
};
const recommendation = {
  text: 'Sign an attacker only within the agreed budget.',
  rationale: 'Depth would help, but affordability is a necessary condition.',
  evidence_ids: ['S001'],
  conditions: ['Confirm the fee and wages before committing.'],
  uncertainty: 'The current asking price is unknown.',
};
const baseReport = {
  evidence: [source],
  findings: [{
    claim: 'The discussion identifies a need for squad depth.',
    evidence_ids: ['S001'],
    support: 'source_backed',
  }],
  assumptions: ['The attacker would accept the proposed role.'],
  recommendation,
};
const decisionReport = {
  ...baseReport,
  mode: 'decision',
  action: 'Sign an attacker',
  do_it: { option: 'Sign an attacker', pros: [point], cons: [risk] },
  do_not_do_it: { option: 'Keep the existing squad', pros: [risk], cons: [point] },
  alternatives: [{ option: 'Consider a loan', pros: [point], cons: [risk] }],
};

function makeJob(report = decisionReport, options = {}) {
  return {
    job_id: 'job-test',
    request,
    snapshot_sha256: 'a'.repeat(64),
    state: 'completed',
    cached: false,
    result: {
      response: {
        request: { ...request, mode: report?.mode || request.mode },
        snapshot_sha256: 'a'.repeat(64),
        status: 'complete',
        report,
        missing_information: [],
        error: null,
        ...(options.response || {}),
      },
      verification: options.verification || null,
    },
    ...(options.job || {}),
  };
}

function render(props = {}) {
  return renderToStaticMarkup(React.createElement(AdvisorPanel, {
    discussion: { topic: request.question },
    discussionStatus: 'completed',
    configuration: { mode: 'decision' },
    analysis: { phase: 'completed', job: makeJob(), error: null },
    onConfigurationChange() {},
    onRetry() {},
    onRefresh() {},
    ...props,
  }));
}

function applyButton(html) {
  const match = html.match(/<button\b[^>]*>Apply settings &amp; analyze<\/button>/);
  assert.ok(match, 'The settings apply button should be rendered.');
  return match[0];
}

test('renders the original backend decision model without optional future fields', () => {
  const html = render();
  assert.match(html, /id="discussion-advisor"/);
  assert.match(html, /Report complete/);
  assert.match(html, /Take the action/);
  assert.match(html, /Do not take the action/);
  assert.match(html, /Keep the existing squad/);
  assert.match(html, /Consider a loan/);
  assert.match(html, /Advisor recommendation/);
  assert.match(html, /Confirm the fee and wages before committing/);
  assert.match(html, /The current asking price is unknown/);
  assert.match(html, /These assumptions have not been authenticated/);
  assert.match(html, /Read cited evidence S001/);
  assert.match(html, /Recorded publication/);
});

test('explains checking, running, failed and unknown discussion completion states', () => {
  const states = {
    checking: 'Checking discussion status',
    running: 'Waiting for the discussion',
    failed: 'Discussion did not finish',
    unknown: 'Discussion completion could not be confirmed',
  };
  for (const [discussionStatus, label] of Object.entries(states)) {
    const html = render({ discussionStatus, analysis: { phase: 'waiting', job: null } });
    assert.ok(html.includes(label), discussionStatus);
    assert.match(applyButton(html), /disabled=""/, discussionStatus);
    assert.doesNotMatch(html, /Advisor recommendation/);
  }
});

test('shows queued/running progress without presenting an old result as current', () => {
  for (const [phase, status] of [
    ['submitting', 'Starting analysis'],
    ['queued', 'Queued'],
    ['running', 'Analyzing &amp; checking evidence'],
  ]) {
    const html = render({ analysis: { phase, job: makeJob(), error: null } });
    assert.ok(html.includes(status), phase);
    assert.match(html, /aria-busy="true"/);
    assert.match(applyButton(html), /disabled=""/);
    assert.doesNotMatch(html, /Report complete/);
    assert.doesNotMatch(html, /Advisor recommendation/);
  }
});

test('renders partial status with missing information and explicit uncertainty', () => {
  const html = render({ analysis: {
    phase: 'completed',
    job: makeJob(decisionReport, { response: {
      status: 'partial',
      missing_information: ['No reliable wage information was available.'],
    } }),
  } });
  assert.match(html, /Partial report/);
  assert.match(html, /Some sections or claims could not be supported/);
  assert.match(html, /Evidence gaps &amp; limitations/);
  assert.match(html, /No reliable wage information was available/);
  assert.match(html, /The current asking price is unknown/);
});

test('does not fabricate a report for insufficient evidence or analysis failure', () => {
  const insufficient = render({ analysis: {
    phase: 'completed',
    job: makeJob(null, { response: {
      status: 'insufficient_evidence',
      missing_information: ['All attached sources lacked publication dates.'],
    } }),
  } });
  assert.match(insufficient, /Insufficient evidence/);
  assert.match(insufficient, /All attached sources lacked publication dates/);
  assert.doesNotMatch(insufficient, /Advisor recommendation/);

  const failed = render({ analysis: {
    phase: 'completed',
    job: makeJob(null, { response: { status: 'failed', error: 'Model response was invalid.' } }),
  } });
  assert.match(failed, /Analysis failed/);
  assert.match(failed, /Model response was invalid/);
  assert.match(failed, /Retry analysis/);
  assert.doesNotMatch(failed, /Advisor recommendation/);
});

test('transport errors override a previously complete status and remain actionable', () => {
  const html = render({ analysis: {
    phase: 'error', job: makeJob(), error: 'The server connection was interrupted.',
  } });
  assert.match(html, /Could not finish/);
  assert.doesNotMatch(html, /advisor-status-complete/);
  assert.match(html, /The server connection was interrupted/);
  assert.match(html, /Retry analysis/);
});

test('renders each team review and supported possible adjustments', () => {
  const review = {
    ...baseReport,
    mode: 'match_review',
    what_happened: [{ claim: 'Team B won the match.', evidence_ids: ['S001'], support: 'source_backed' }],
    team_a_review: {
      team: 'Team A', actual_actions: [point], what_worked: [point], what_failed: [risk],
      responses_to_opponent: [point],
      plausible_adjustments: [{ option: 'Protect the wide channel', pros: [point], cons: [risk] }],
    },
    team_b_review: null,
  };
  const html = render({ analysis: { phase: 'completed', job: makeJob(review, {
    response: { status: 'partial', request: { ...request, mode: 'match_review', team_a: 'Team A', team_b: 'Team B' } },
  }) } });
  for (const text of ['What happened', 'What the team did', 'What worked', 'What failed', 'Responses to the opponent', 'Protect the wide channel']) {
    assert.ok(html.includes(text), text);
  }
  assert.match(html, /No supported team review was retained/);
});

test('renders preview plans, conditional prediction scope, conditions and uncertainty', () => {
  const preview = {
    ...baseReport,
    mode: 'match_preview',
    team_a_plan: { team: 'Team A', should_do: [point], should_avoid: [risk] },
    team_b_plan: { team: 'Team B', should_do: [risk], should_avoid: [point] },
    prediction: {
      outcome: 'Team A has a narrow edge.', scope: 'qualification',
      rationale: 'The discussion identifies greater squad depth.', evidence_ids: ['S001'],
      conditions: ['Both first-choice defenders start.'],
      uncertainty: 'The starting lineups remain unknown.',
    },
  };
  const html = render({
    configuration: { mode: 'match_preview', team_a: 'Team A', team_b: 'Team B', evidence_cutoff: '2026-09-25T12:00', match_kickoff: '2026-09-28T20:00' },
    analysis: { phase: 'completed', job: makeJob(preview) },
  });
  assert.match(html, /Should do/);
  assert.match(html, /Should avoid/);
  assert.match(html, /Conditional prediction/);
  assert.match(html, /Scope: Qualification/);
  assert.match(html, /Both first-choice defenders start/);
  assert.match(html, /The starting lineups remain unknown/);
  assert.match(html, /Evidence cutoff · your local time/);
  assert.match(html, /Kickoff · your local time/);
  assert.doesNotMatch(applyButton(html), /disabled=""/);

  const omitted = render({ analysis: { phase: 'completed', job: makeJob({ ...preview, prediction: null }, { response: { status: 'partial' } }) } });
  assert.match(omitted, /No prediction passed the evidence requirements/);
  assert.doesNotMatch(omitted, /Team A has a narrow edge/);
});

test('citation audit distinguishes excerpt support from real-world authentication', () => {
  const removedEvidence = {
    ...source, id: 'S002', source: 'https://example.com/removed', excerpt: 'Original excerpt for the rejected claim.',
  };
  const verification = {
    claims: [
      { id: 'C1', text: JSON.stringify({ claim: 'Supported depth claim' }) },
      { id: 'C2', text: JSON.stringify({ claim: 'Unsupported transfer fee claim' }) },
    ],
    checks: [
      { claim_id: 'C1', verdict: 'supported', reason: 'The source states this premise.', quotes: [{ evidence_id: 'S001', quote: 'The squad needs depth', role: 'supports' }], unused_evidence_ids: [] },
      { claim_id: 'C2', verdict: 'unsupported', reason: 'The excerpt does not state a fee.', quotes: [{ evidence_id: 'S002', quote: 'Original excerpt', role: 'premise' }], unused_evidence_ids: ['S002'] },
    ],
    evidence: [source, removedEvidence],
    coverage: 'Only cited claims were checked.',
    error: null,
  };
  const html = render({ analysis: { phase: 'completed', job: makeJob(decisionReport, { verification }) } });
  assert.match(html, /2 claims · 1 rejected or unassessed/);
  assert.match(html, /They do not authenticate real-world facts or sources/);
  assert.match(html, /Supported by excerpt/);
  assert.match(html, /Unsupported transfer fee claim/);
  assert.match(html, /The excerpt does not state a fee/);
  assert.match(html, /Unused citations: S002/);
  assert.match(html, /Evidence library · 2 excerpts/);
  assert.match(html, /Original excerpt for the rejected claim/);
  assert.doesNotMatch(html, /Cached &amp; Verified|verified real-world truth/i);
});

test('shows missing and failed verification without claiming checks succeeded', () => {
  assert.match(render(), /No citation verification details are available/);
  const html = render({ analysis: { phase: 'completed', job: makeJob(decisionReport, { verification: {
    claims: [], checks: [], evidence: [], error: 'Citation checking could not finish.',
  } }) } });
  assert.match(html, /No claim checks were returned/);
  assert.match(html, /Citation checking could not finish/);
});

test('escapes discussion/source text and creates external links only for HTTP(S)', () => {
  const sources = [
    { ...source, id: 'S001', source: 'javascript:alert(1)', excerpt: '<script>alert(1)</script>' },
    { ...source, id: 'S002', source: 'data:text/html,<script>alert(2)</script>' },
    { ...source, id: 'S003', source: 'file:///etc/passwd' },
    { ...source, id: 'S004', source: 'https://example.com/article?tag=<script>' },
    { ...source, id: 'M001', kind: 'message', source: null, excerpt: '<img src=x onerror=alert(3)>' },
  ];
  const html = render({ analysis: { phase: 'completed', job: makeJob({
    ...decisionReport, evidence: sources,
    findings: [{ ...baseReport.findings[0], claim: '<script>unsafe claim</script>' }],
  }) } });
  assert.match(html, /&lt;script&gt;unsafe claim&lt;\/script&gt;/);
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.match(html, /&lt;img src=x onerror=alert\(3\)&gt;/);
  assert.doesNotMatch(html, /<script>|<img src=x|href="(?:javascript:|data:|file:)/i);
  assert.match(html, /href="https:\/\/example\.com\/article/);
  assert.match(html, /rel="noopener noreferrer"/);
  assert.match(html, /A discussion message records what an agent said/);
});

test('disables applying settings until completion and required match fields exist', () => {
  assert.doesNotMatch(applyButton(render()), /disabled=""/);
  for (const discussionStatus of ['checking', 'running', 'unknown', 'failed']) {
    assert.match(applyButton(render({ discussionStatus })), /disabled=""/);
  }
  for (const configuration of [
    { mode: 'match_review', team_a: 'Team A', team_b: '' },
    { mode: 'match_review', team_a: ' ', team_b: 'Team B' },
    { mode: 'match_preview', team_a: 'Team A', team_b: 'Team B', evidence_cutoff: '', match_kickoff: '' },
    { mode: 'match_preview', team_a: 'Team A', team_b: 'Team B', evidence_cutoff: '2026-09-25T12:00', match_kickoff: '' },
  ]) {
    assert.match(applyButton(render({ configuration })), /disabled=""/);
  }
});

test('renders optional disagreements, decisive factors and conditional opponent responses', () => {
  const html = render({ analysis: { phase: 'completed', job: makeJob({
    ...decisionReport,
    do_it: {
      ...decisionReport.do_it,
      opponent_responses: [{ ...point, opponent: 'Team B', text: 'Could defend deeper.' }],
    },
    decisive_factors: [{ ...point, text: 'Affordability is decisive.' }],
    disagreements: [{
      issue: 'Whether to sign now', relationship: 'competing_recommendations',
      side_a: { statement: 'Sign now', quote: 'We should sign now.', evidence_id: 'M001' },
      side_b: { statement: 'Wait', quote: 'We should wait.', evidence_id: 'M002' },
    }],
    disagreement_coverage: 'Bounded discovery does not prove consensus.',
  }) } });
  assert.match(html, /Possible opponent responses/);
  assert.match(html, /Team B: Could defend deeper/);
  assert.match(html, /Affordability is decisive/);
  assert.match(html, /Whether to sign now/);
  assert.match(html, /competing recommendations/);
  assert.match(html, /We should sign now/);
  assert.match(html, /We should wait/);
  assert.match(html, /Bounded discovery does not prove consensus/);
});

test('labels cache reuse as a saved result without implying independent verification', () => {
  const html = render({ analysis: { phase: 'completed', job: makeJob(decisionReport, { job: { cached: true } }) } });
  assert.match(html, /Saved result/);
  assert.doesNotMatch(html, /Cached &amp; Verified/);
});

test('labels the question neutrally instead of showing the uncited action as a verdict', () => {
  const html = render({ analysis: { phase: 'completed', job: makeJob({
    ...decisionReport,
    action: 'Barcelona should not pursue the acquisition of Julián Álvarez.',
    recommendation: null,
  }) } });
  assert.match(html, /Question being assessed:/);
  assert.match(html, /Should the team sign an attacker\?/);
  assert.doesNotMatch(html, /Barcelona should not pursue/);
  assert.match(html, /No recommendation was retained after evidence checking/);
});

test('does not display an old recommendation when either decision option lacks cited points', () => {
  for (const missingOption of ['do_it', 'do_not_do_it']) {
    const html = render({ analysis: { phase: 'completed', job: makeJob({
      ...decisionReport,
      [missingOption]: { option: 'Incomplete option', pros: [], cons: [] },
    }) } });
    assert.doesNotMatch(html, /Advisor recommendation/);
    assert.doesNotMatch(html, /Sign an attacker only within the agreed budget/);
    assert.match(html, /No recommendation was retained/);
  }
});

test('shows independent web and database research origins without invented discussion attachments', () => {
  const research = {
    attempts: [
      { tool: 'knowledge_search', query: 'attacker squad depth', status: 'success', source_ids: ['R001'] },
      { tool: 'web_search', query: 'attacker asking price <script>', status: 'success', source_ids: ['R002'] },
      { tool: 'read_web_page', url: 'https://example.com/transfer', status: 'success', source_ids: ['R003'] },
    ],
    evidence: [
      { ...source, id: 'R001', message_ref: null, origin: 'knowledge_base', title: 'Squad depth dataset', query: 'attacker squad depth', content_kind: 'database_excerpt' },
      { ...source, id: 'R002', message_ref: null, origin: 'web_search', title: 'Transfer search result', published_at: null, query: 'attacker asking price <script>', retrieved_at: '2026-09-27T12:00:00Z', content_kind: 'search_result' },
      { ...source, id: 'R003', message_ref: null, origin: 'web_page', title: 'Transfer article', retrieved_at: '2026-09-27T12:02:00Z', modified_at: '2026-09-21T12:00:00Z', content_kind: 'page_excerpt' },
    ],
    limitations: ['Search results are excerpts, not full article text.'],
  };
  const html = render({ analysis: { phase: 'completed', job: makeJob(decisionReport, {
    response: { research },
  }) } });
  assert.match(html, /Evidence research · 3 attempts/);
  assert.match(html, /Evidence library · 4 excerpts/);
  assert.match(html, /Knowledge base/);
  assert.match(html, /Web search/);
  assert.match(html, /Web page/);
  assert.match(html, /Independently retrieved/);
  assert.match(html, /Attached to M001/);
  assert.doesNotMatch(html, /Attached to (?:null|undefined)/);
  assert.match(html, /Squad depth dataset/);
  assert.match(html, /Transfer article/);
  assert.match(html, /Search query: attacker asking price &lt;script&gt;/);
  assert.match(html, /Content: search result/);
  assert.match(html, /Retrieved:/);
  assert.match(html, /Recorded update:/);
  assert.match(html, /Publication time unknown/);
  assert.match(html, /Retrieval time is not publication time/);
  assert.doesNotMatch(html, /verified publication|<script>/i);
});

test('retains research attempts and excerpts when analysis has insufficient evidence', () => {
  const html = render({ analysis: { phase: 'completed', job: makeJob(null, {
    response: {
      status: 'insufficient_evidence',
      research: {
        attempts: [
          { tool: 'web_search', query: 'current transfer price', status: 'failed', source_ids: [], reason: 'The search service was unavailable.' },
          { tool: 'read_web_page', url: 'javascript:alert(1)', status: 'excluded', source_ids: [], reason: 'The page could not establish pre-cutoff availability.' },
        ],
        evidence: [{ ...source, id: 'R001', message_ref: null, origin: 'knowledge_base', title: 'Retrieved squad information' }],
        limitations: ['No reliable wage information could be retrieved.'],
      },
    },
  }) } });
  assert.match(html, /Insufficient evidence/);
  assert.match(html, /Evidence research · 2 attempts/);
  assert.match(html, /Retrieval failed/);
  assert.match(html, /Evidence excluded/);
  assert.match(html, /The search service was unavailable/);
  assert.match(html, /No reliable wage information could be retrieved/);
  assert.match(html, /Evidence library · 1 excerpts/);
  assert.match(html, /Retrieved squad information/);
  assert.doesNotMatch(html, /Advisor recommendation|href="javascript:/i);
});
