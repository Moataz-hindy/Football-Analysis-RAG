import test from 'node:test';
import assert from 'node:assert/strict';
import { buildDiscussionRequest } from './discussionRequest.js';

const selection = { topic: 'Evaluate the low block', rounds: 3, agentCount: 4,
  campA: ['tactical_analyst'], campB: ['statistical_analyst'] };

test('switching between saved and generated personas sends only the selected mode', () => {
  const saved = buildDiscussionRequest({ ...selection, mode: 'custom' });
  assert.equal(saved.dynamic_personas, false);
  assert.equal(saved.num_agents, 2);
  assert.deepEqual(saved.persona_ids, ['tactical_analyst', 'statistical_analyst']);
  assert.deepEqual(saved.camp_a_ids, selection.campA);
  assert.deepEqual(saved.camp_b_ids, selection.campB);
  const generated = JSON.parse(JSON.stringify(buildDiscussionRequest({ ...selection, mode: 'dynamic' })));
  assert.equal(generated.dynamic_personas, true);
  assert.equal(generated.num_agents, 4);
  assert.equal(generated.num_rounds, 3);
  assert.equal(generated.persona_ids, null);
  assert.equal(generated.camp_a_ids, null);
  assert.equal(generated.camp_b_ids, null);
  assert.deepEqual(buildDiscussionRequest({ ...selection, mode: 'custom' }), saved);
});
