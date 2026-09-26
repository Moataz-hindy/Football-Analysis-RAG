import test from 'node:test';
import assert from 'node:assert/strict';
import { createAdvisorClient, buildAdvisorRequest, DEFAULT_CONFIGURATION } from './advisorClient.js';

const request = { discussion_id: 'discussion-a', mode: 'decision', question: 'Should Team A sign a striker?' };
const discussion = { discussion_id: 'discussion-a', topic: request.question, num_rounds: 3, messages: [{ content: 'A discussion claim.', round_num: 3 }] };

function job(state, extra = {}) {
  return { job_id: 'job-a', request, snapshot_sha256: 'a'.repeat(64), state, cached: false, result: null, error: null, ...extra };
}

function response(status, body, headers = {}) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });
}

async function settle() {
  for (let i = 0; i < 40; i++) await Promise.resolve();
}

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function fakeClock() {
  let now = 0, nextId = 0;
  const pending = new Map();
  return {
    setTimer(fn, delay) { const id = ++nextId; pending.set(id, { fn, due: now + delay }); return id; },
    clearTimer(id) { pending.delete(id); },
    async advanceNext() {
      assert.ok(pending.size, 'Expected a scheduled timer.');
      const [id, timer] = [...pending].sort((a, b) => a[1].due - b[1].due)[0];
      pending.delete(id); now = timer.due; timer.fn(); await settle(); return now;
    },
    get pendingCount() { return pending.size; },
  };
}

function rig(responses, options = {}) {
  const calls = [], clock = fakeClock();
  const client = createAdvisorClient({
    fetchImpl: async (url, init = {}) => {
      calls.push({ url, ...init });
      assert.ok(responses.length, 'Unexpected fetch: ' + url);
      const next = responses.shift();
      if (typeof next === 'function') return next(url, init);
      return next;
    },
    setTimer: clock.setTimer,
    clearTimer: clock.clearTimer,
    pollMs: 10,
    requestTimeoutMs: 1_000,
    maxCapacityRetries: 2,
    ...options,
  });
  return { client, clock, calls };
}

test('decision request uses the saved question without guessing match details', () => {
  assert.deepEqual(buildAdvisorRequest(discussion), request);
  assert.throws(() => buildAdvisorRequest({ ...discussion, topic: ' ' }), /question/i);
  assert.throws(() => buildAdvisorRequest({ ...discussion, topic: 'a'.repeat(4001) }), /4000/);
});

test('match requests require distinct teams and safe preview times', () => {
  assert.throws(() => buildAdvisorRequest(discussion, { ...DEFAULT_CONFIGURATION, mode: 'match_review' }), /different teams/i);
  assert.throws(() => buildAdvisorRequest(discussion, { ...DEFAULT_CONFIGURATION, mode: 'match_review', team_a: 'France', team_b: ' france ' }), /different teams/i);
  const configuration = { mode: 'match_preview', team_a: 'France', team_b: 'Argentina', evidence_cutoff: '2026-09-25T09:00:00+02:00', match_kickoff: '2026-09-27T18:00:00+02:00' };
  const now = Date.parse('2026-09-26T12:00:00Z');
  const built = buildAdvisorRequest(discussion, configuration, now);
  assert.equal(built.evidence_cutoff, '2026-09-25T07:00:00.000Z');
  assert.equal(built.match_kickoff, '2026-09-27T16:00:00.000Z');
  assert.throws(() => buildAdvisorRequest(discussion, { ...configuration, evidence_cutoff: '2026-09-27T19:00:00Z' }, now), /cutoff/i);
  assert.throws(() => buildAdvisorRequest(discussion, { ...configuration, match_kickoff: '2026-09-24T19:00:00Z' }, now), /kickoff/i);
});

test('StrictMode subscriber replay reuses one pending POST', async () => {
  const pending = deferred();
  const { client, calls } = rig([() => pending.promise]);
  const task = client.getTask(request);
  const detachFirst = task.subscribe(() => {});
  await settle();
  detachFirst();
  assert.equal(client.getTask({ ...request }), task);
  const seen = [];
  const detachSecond = task.subscribe((snapshot) => seen.push(snapshot.phase));
  pending.resolve(response(202, job('queued')));
  await settle();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].method, 'POST');
  assert.deepEqual(JSON.parse(calls[0].body), { request, force: false });
  assert.equal(task.getSnapshot().phase, 'queued');
  assert.equal(seen.at(-1), 'queued');
  detachSecond();
});

const completed = (extra = {}) => job('completed', {
  result: { response: { status: 'partial', report: { mode: 'decision' }, missing_information: ['Financial evidence is missing.'] }, verification: { checks: [] } },
  ...extra,
});

test('cached terminal POST displays its result without polling', async () => {
  const { client, calls, clock } = rig([response(200, completed({ cached: true }))]);
  const task = client.getTask(request);
  const stop = task.subscribe(() => {});
  await settle();
  assert.equal(task.getSnapshot().phase, 'completed');
  assert.equal(task.getSnapshot().job.cached, true);
  assert.equal(task.getSnapshot().job.result.response.status, 'partial');
  assert.equal(calls.length, 1);
  assert.equal(clock.pendingCount, 0);
  stop();
});

test('a finished analytical failure remains explicit and can be retried normally', async () => {
  const failed = completed({ result: { response: { status: 'failed', report: null, error: 'No usable model response.' } } });
  const { client, calls, clock } = rig([response(200, failed), response(202, job('queued'))]);
  const task = client.getTask(request);
  const stop = task.subscribe(() => {});
  await settle();
  assert.equal(task.getSnapshot().phase, 'completed');
  assert.equal(task.getSnapshot().job.result.response.status, 'failed');
  assert.equal(clock.pendingCount, 0);
  task.retry();
  await settle();
  assert.equal(task.getSnapshot().phase, 'queued');
  assert.equal(calls.length, 2);
  assert.equal(JSON.parse(calls[1].body).force, false);
  stop();
});

test('a job for the wrong analysis mode is rejected even for the same discussion', async () => {
  const wrongRequest = { ...request, mode: 'match_review', team_a: 'France', team_b: 'Argentina' };
  const { client, clock } = rig([response(200, completed({ request: wrongRequest }))]);
  const task = client.getTask(request);
  const stop = task.subscribe(() => {});
  await settle();
  assert.equal(task.getSnapshot().phase, 'error');
  assert.match(task.getSnapshot().error, /incomplete advisor job/i);
  assert.equal(task.getSnapshot().job, null);
  assert.equal(clock.pendingCount, 0);
  stop();
});

test('equivalent timezone representations in returned requests are accepted', async () => {
  const previewRequest = {
    ...request,
    mode: 'match_preview',
    team_a: 'France',
    team_b: 'Argentina',
    evidence_cutoff: '2026-09-25T07:00:00.000Z',
    match_kickoff: '2026-09-27T16:00:00.000Z',
  };
  const returnedRequest = {
    ...previewRequest,
    evidence_cutoff: '2026-09-25T09:00:00+02:00',
    match_kickoff: '2026-09-27T18:00:00+02:00',
  };
  const { client } = rig([response(200, completed({ request: returnedRequest }))]);
  const task = client.getTask(previewRequest);
  const stop = task.subscribe(() => {});
  await settle();
  assert.equal(task.getSnapshot().phase, 'completed');
  stop();
});

test('a changed transcript revision gets a fresh task and normal cache-aware submission', async () => {
  const { client, calls } = rig([
    response(200, completed({ cached: true })),
    response(200, completed({ job_id: 'job-updated', cached: true })),
  ]);
  const first = client.getTask(request, { revision: 'original transcript' });
  const stopFirst = first.subscribe(() => {});
  await settle();
  stopFirst();
  assert.equal(client.getTask(request, { revision: 'original transcript' }), first);
  const updated = client.getTask(request, { revision: 'updated transcript' });
  assert.notEqual(updated, first);
  const stopUpdated = updated.subscribe(() => {});
  await settle();
  assert.equal(updated.getSnapshot().job.job_id, 'job-updated');
  assert.equal(calls.length, 2);
  assert.equal(JSON.parse(calls[1].body).force, false);
  stopUpdated();
});

test('force is used only for explicit refresh and not subsequent retries', async () => {
  const { client, calls } = rig([
    response(200, completed({ cached: true })),
    response(503, { detail: 'Temporary worker failure.' }),
    response(200, completed()),
  ]);
  const automatic = client.getTask(request);
  const stopAutomatic = automatic.subscribe(() => {});
  await settle();
  stopAutomatic();
  assert.equal(client.getTask(request), automatic);
  const refreshed = client.getTask(request, { force: true });
  assert.notEqual(refreshed, automatic);
  const stopRefreshed = refreshed.subscribe(() => {});
  await settle();
  assert.equal(refreshed.getSnapshot().phase, 'error');
  refreshed.retry();
  await settle();
  assert.equal(refreshed.getSnapshot().phase, 'completed');
  assert.deepEqual(calls.map((call) => JSON.parse(call.body).force), [false, true, false]);
  stopRefreshed();
});


test('queued jobs poll through running to a terminal result', async () => {
  const { client, calls, clock } = rig([
    response(202, job('queued')),
    response(200, job('running')),
    response(200, completed()),
  ]);
  const task = client.getTask(request);
  const stop = task.subscribe(() => {});
  await settle();
  assert.equal(task.getSnapshot().phase, 'queued');
  await clock.advanceNext();
  assert.equal(task.getSnapshot().phase, 'running');
  await clock.advanceNext();
  assert.equal(task.getSnapshot().phase, 'completed');
  assert.equal(calls.length, 3);
  assert.equal(calls[1].url, '/discussions/discussion-a/advisor/jobs/job-a');
  assert.equal(clock.pendingCount, 0);
  stop();
});

test('capacity retry respects Retry-After and then completes normally', async () => {
  const { client, calls, clock } = rig([
    response(429, { detail: 'The advisor is busy.' }, { 'Retry-After': '3' }),
    response(200, completed()),
  ]);
  const task = client.getTask(request);
  const stop = task.subscribe(() => {});
  await settle();
  assert.equal(task.getSnapshot().phase, 'queued');
  assert.equal(task.getSnapshot().error, null);
  assert.equal(await clock.advanceNext(), 3000);
  assert.equal(task.getSnapshot().phase, 'completed');
  assert.equal(calls.length, 2);
  stop();
});

test('repeated capacity errors stop after the configured retry budget', async () => {
  const busy = () => response(429, { detail: 'Still busy.' }, { 'Retry-After': '1' });
  const { client, calls, clock } = rig([busy(), busy(), busy()]);
  const task = client.getTask(request);
  const stop = task.subscribe(() => {});
  await settle();
  await clock.advanceNext();
  await clock.advanceNext();
  assert.equal(task.getSnapshot().phase, 'error');
  assert.match(task.getSnapshot().error, /Still busy/);
  assert.equal(calls.length, 3);
  assert.equal(clock.pendingCount, 0);
  stop();
});

test('configuration errors stop automatically and allow an explicit retry', async () => {
  const { client, calls, clock } = rig([
    response(503, { detail: 'Configure LLM_API_KEY first.' }),
    response(200, completed()),
  ]);
  const task = client.getTask(request);
  const stop = task.subscribe(() => {});
  await settle();
  assert.equal(task.getSnapshot().phase, 'error');
  assert.match(task.getSnapshot().error, /LLM_API_KEY/);
  assert.equal(clock.pendingCount, 0);
  task.retry();
  await settle();
  assert.equal(task.getSnapshot().phase, 'completed');
  assert.equal(calls.length, 2);
  assert.equal(JSON.parse(calls[1].body).force, false);
  stop();
});

test('an expired job is resubmitted normally once and can reuse cache', async () => {
  const { client, calls, clock } = rig([
    response(202, job('queued')),
    response(404, { detail: 'Job not found or expired.' }),
    response(200, completed({ cached: true })),
  ]);
  const task = client.getTask(request);
  const stop = task.subscribe(() => {});
  await settle();
  await clock.advanceNext();
  assert.equal(task.getSnapshot().job, null);
  await clock.advanceNext();
  assert.equal(task.getSnapshot().phase, 'completed');
  assert.equal(task.getSnapshot().job.cached, true);
  assert.equal(calls.length, 3);
  assert.equal(calls[2].method, 'POST');
  assert.equal(JSON.parse(calls[2].body).force, false);
  stop();
});

test('repeated expiry does not create an endless resubmission loop', async () => {
  const expired = () => response(404, { detail: 'Job expired.' });
  const { client, calls, clock } = rig([
    response(202, job('queued')), expired(),
    response(202, job('queued')), expired(),
  ]);
  const task = client.getTask(request);
  const stop = task.subscribe(() => {});
  await settle();
  await clock.advanceNext();
  await clock.advanceNext();
  await clock.advanceNext();
  assert.equal(task.getSnapshot().phase, 'error');
  assert.equal(calls.length, 4);
  assert.equal(clock.pendingCount, 0);
  stop();
});

test('changed snapshots report the conflict rather than silently reusing a report', async () => {
  const { client, calls, clock } = rig([
    response(202, job('queued')),
    response(409, { detail: 'This result belongs to an older discussion snapshot.' }),
  ]);
  const task = client.getTask(request);
  const stop = task.subscribe(() => {});
  await settle();
  await clock.advanceNext();
  assert.equal(task.getSnapshot().phase, 'error');
  assert.equal(task.getSnapshot().job, null);
  assert.match(task.getSnapshot().error, /older discussion snapshot/);
  assert.equal(calls.length, 2);
  assert.equal(clock.pendingCount, 0);
  stop();
});

test('failed jobs retain the backend explanation and stop polling', async () => {
  const { client, clock } = rig([response(202, job('failed', { error: 'Analysis could not finish.' }))]);
  const task = client.getTask(request);
  const stop = task.subscribe(() => {});
  await settle();
  assert.equal(task.getSnapshot().phase, 'error');
  assert.equal(task.getSnapshot().error, 'Analysis could not finish.');
  assert.equal(clock.pendingCount, 0);
  stop();
});

test('switching discussions isolates late responses and removes old listeners', async () => {
  const pendingA = deferred();
  const requestB = { ...request, discussion_id: 'discussion-b', question: 'Should Team B sign a defender?' };
  const completedB = completed({ job_id: 'job-b', request: requestB });
  const { client, calls } = rig([() => pendingA.promise, response(200, completedB)]);
  const taskA = client.getTask(request);
  let oldNotifications = 0;
  const stopA = taskA.subscribe(() => { oldNotifications += 1; });
  await settle();
  stopA();
  const notificationCount = oldNotifications;
  const taskB = client.getTask(requestB);
  const stopB = taskB.subscribe(() => {});
  await settle();
  pendingA.resolve(response(200, completed()));
  await settle();
  assert.equal(oldNotifications, notificationCount);
  assert.equal(taskB.getSnapshot().job.job_id, 'job-b');
  assert.equal(taskB.getSnapshot().job.request.discussion_id, 'discussion-b');
  assert.equal(calls.length, 2);
  assert.notEqual(taskA, taskB);
  stopB();
});

test('unsubscribing stops scheduled polling and resubscribing resumes it', async () => {
  const { client, calls, clock } = rig([response(202, job('queued')), response(200, completed())]);
  const task = client.getTask(request);
  const firstStop = task.subscribe(() => {});
  await settle();
  assert.equal(clock.pendingCount, 1);
  firstStop();
  assert.equal(clock.pendingCount, 0);
  const secondStop = task.subscribe(() => {});
  await clock.advanceNext();
  assert.equal(task.getSnapshot().phase, 'completed');
  assert.equal(calls.length, 2);
  secondStop();
});

test('different analysis modes have distinct task identities', () => {
  const { client } = rig([]);
  const review = { ...request, mode: 'match_review', team_a: 'France', team_b: 'Argentina' };
  assert.notEqual(client.getTask(request), client.getTask(review));
  assert.equal(client.getTask(review), client.getTask({ ...review }));
});

test('network requests time out and expose a reconnect explanation', async () => {
  const pending = (_url, init) => new Promise((_resolve, reject) => {
    init.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
  });
  const { client, clock } = rig([pending]);
  const task = client.getTask(request);
  const stop = task.subscribe(() => {});
  await settle();
  await clock.advanceNext();
  assert.equal(task.getSnapshot().phase, 'error');
  assert.match(task.getSnapshot().error, /timed out/i);
  assert.equal(clock.pendingCount, 0);
  stop();
});

test('the session cache evicts abandoned queued tasks while preserving active subscriptions', async () => {
  const activeRequest = { ...request, question: 'An actively viewed discussion question.' };
  const { client, calls } = rig([
    response(202, job('queued', { request: activeRequest, job_id: 'job-active' })),
    response(202, job('queued')),
    response(200, completed({ cached: true })),
  ]);
  const active = client.getTask(activeRequest);
  const stopActive = active.subscribe(() => {});
  await settle();
  const abandoned = client.getTask(request);
  const stopAbandoned = abandoned.subscribe(() => {});
  await settle();
  stopAbandoned();

  for (let index = 0; index < 26; index++) {
    client.getTask({ ...request, question: `Unviewed question ${index}` });
  }

  assert.equal(client.getTask(activeRequest), active);
  const resumed = client.getTask(request);
  assert.notEqual(resumed, abandoned);
  const stopResumed = resumed.subscribe(() => {});
  await settle();
  assert.equal(resumed.getSnapshot().phase, 'completed');
  assert.equal(resumed.getSnapshot().job.cached, true);
  assert.equal(calls.length, 3);
  assert.equal(JSON.parse(calls[2].body).force, false);
  stopActive();
  stopResumed();
});
