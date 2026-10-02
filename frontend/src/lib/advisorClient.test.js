import test from 'node:test';
import assert from 'node:assert/strict';
import { createAdvisorClient } from './advisorClient.js';

function stub(replies) {
  const calls = [];
  return { calls, client: createAdvisorClient({ wait: async () => {}, fetchImpl: async (url, options) => {
    calls.push(options.method || 'GET');
    const data = replies.shift();
    if (data instanceof Error) throw data;
    assert.ok(data, 'Unexpected additional request');
    return { ok: true, json: async () => data };
  } }) };
}

test('effect replay shares one POST and reopening cached result costs no POST', async () => {
  const { client, calls } = stub([{ state: 'missing' }, { state: 'completed', opinion: 'Advice' }]);
  const first = client.get('a', 'v1');
  assert.equal(first, client.get('a', 'v1'));
  assert.equal((await first).opinion, 'Advice');
  await client.get('a', 'v1');
  assert.deepEqual(calls, ['GET', 'POST']);
  const reopened = stub([{ state: 'completed', opinion: 'Advice' }]);
  await reopened.client.get('a', 'v1');
  assert.deepEqual(reopened.calls, ['GET']);
});

test('lost POST response reconnects and polls without another POST', async () => {
  const { client, calls } = stub([{ state: 'missing' }, new Error('network'),
    { state: 'running' }, { state: 'completed', opinion: 'Advice' }]);
  assert.equal((await client.get('a', 'v1')).state, 'completed');
  assert.deepEqual(calls, ['GET', 'POST', 'GET', 'GET']);
});

test('failed result requires explicit retry', async () => {
  const { client, calls } = stub([{ state: 'failed', retryable: true },
    { state: 'failed', retryable: true }, { state: 'completed', opinion: 'Advice' }]);
  assert.equal((await client.get('a', 'v1')).state, 'failed');
  await client.get('a', 'v1');
  assert.deepEqual(calls, ['GET']);
  assert.equal((await client.get('a', 'v1', { refresh: true, retryFailed: true })).state, 'completed');
  assert.deepEqual(calls, ['GET', 'GET', 'POST']);
});

test('different discussions and revised transcripts have separate requests', async () => {
  const { client, calls } = stub([{ state: 'completed', opinion: 'A' }, { state: 'completed', opinion: 'B' },
    { state: 'completed', opinion: 'A updated' }]);
  assert.equal((await client.get('a', 'v1')).opinion, 'A');
  assert.equal((await client.get('b', 'v1')).opinion, 'B');
  assert.equal((await client.get('a', 'v2')).opinion, 'A updated');
  assert.deepEqual(calls, ['GET', 'GET', 'GET']);
});

test('long provider recovery keeps polling beyond five minutes without duplicate POSTs', async () => {
  const { client, calls } = stub([{ state: 'missing' }, new Error('POST timed out'),
    ...Array.from({ length: 150 }, () => ({ state: 'running' })),
    { state: 'completed', opinion: 'Recovered advice' }]);
  assert.equal((await client.get('a', 'v1')).opinion, 'Recovered advice');
  assert.equal(calls.filter((method) => method === 'POST').length, 1);
});

test('structured decision uses its own endpoint and reconnects without duplicate generation', async () => {
  const calls = [];
  const replies = [{ state: 'missing' }, new Error('timeout'), { state: 'running' },
    { state: 'completed', decision: { definitive_ruling: 'Conditional approval' } }];
  const client = createAdvisorClient({ endpoint: 'advisor/decision', wait: async () => {},
    fetchImpl: async (url, options) => {
      calls.push([url, options.method || 'GET']);
      const data = replies.shift();
      if (data instanceof Error) throw data;
      return { ok: true, json: async () => data };
    } });
  const result = await client.get('a', 'v1');
  assert.equal(result.decision.definitive_ruling, 'Conditional approval');
  assert.ok(calls.every(([url]) => url === '/discussions/a/advisor/decision'));
  assert.deepEqual(calls.map(([, method]) => method), ['GET', 'POST', 'GET', 'GET']);
});
