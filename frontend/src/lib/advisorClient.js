// Shared jobs survive React's development effect replay and tab changes.
export const DEFAULT_CONFIGURATION = Object.freeze({
  mode: 'decision', team_a: '', team_b: '', evidence_cutoff: '', match_kickoff: '',
});

export function buildAdvisorRequest(discussion, configuration = DEFAULT_CONFIGURATION, now = Date.now()) {
  const discussionId = discussion?.discussion_id;
  const question = discussion?.topic?.trim();
  if (!discussionId || !/^[A-Za-z0-9_-]+$/.test(discussionId)) {
    throw new Error('Load a saved discussion before requesting advice.');
  }
  if (!question || question.length > 4000) {
    throw new Error('The discussion question must contain between 1 and 4000 characters.');
  }
  const mode = configuration.mode;
  if (!['decision', 'match_review', 'match_preview'].includes(mode)) {
    throw new Error('Choose a supported analysis type.');
  }
  const request = { discussion_id: discussionId, mode, question };
  if (mode !== 'decision') {
    request.team_a = configuration.team_a?.trim();
    request.team_b = configuration.team_b?.trim();
    if (!request.team_a || !request.team_b || request.team_a.toLowerCase() === request.team_b.toLowerCase()) {
      throw new Error('Enter two different teams for a match analysis.');
    }
  }
  if (mode === 'match_preview') {
    const cutoff = new Date(configuration.evidence_cutoff || NaN);
    const kickoff = new Date(configuration.match_kickoff || NaN);
    if (!Number.isFinite(cutoff.getTime()) || !Number.isFinite(kickoff.getTime())) {
      throw new Error('A preview needs an evidence cutoff and a kickoff time.');
    }
    if (cutoff.getTime() > now || kickoff.getTime() <= now || cutoff >= kickoff) {
      throw new Error('Use a cutoff at or before now and a future kickoff after that cutoff.');
    }
    request.evidence_cutoff = cutoff.toISOString();
    request.match_kickoff = kickoff.toISOString();
  }
  return request;
}

function detailMessage(body, status) {
  if (typeof body?.detail === 'string') return body.detail;
  if (Array.isArray(body?.detail)) {
    return body.detail.map((item) => item.msg || 'Invalid request').join('; ');
  }
  return `Advisor request failed (HTTP ${status}).`;
}

export function createAdvisorClient({
  fetchImpl = (...args) => fetch(...args),
  setTimer = setTimeout,
  clearTimer = clearTimeout,
  pollMs = 2000,
  requestTimeoutMs = 20000,
  maxCapacityRetries = 3,
} = {}) {
  const tasks = new Map();

  function createTask(request, force) {
    const endpoint = `/discussions/${encodeURIComponent(request.discussion_id)}/advisor/jobs`;
    let snapshot = { phase: 'waiting', job: null, error: null };
    const listeners = new Set();
    let timer = null;
    let inFlight = false;
    let capacityRetries = 0;
    let expiredResubmissions = 0;
    let nextDelay = pollMs;

    function emit(next) {
      snapshot = next;
      listeners.forEach((listener) => listener(snapshot));
    }

    function schedule(delay = nextDelay) {
      if (!listeners.size || timer !== null || inFlight) return;
      timer = setTimer(() => {
        timer = null;
        void drive();
      }, delay);
    }

    async function callApi(url, options) {
      const controller = new AbortController();
      const timeout = setTimer(() => controller.abort(), requestTimeoutMs);
      try {
        const response = await fetchImpl(url, { ...options, signal: controller.signal });
        let body = null;
        try { body = await response.json(); } catch (_) { /* Report invalid responses below. */ }
        if (!response.ok) {
          const error = new Error(detailMessage(body, response.status));
          error.status = response.status;
          const retryAfter = Number(response.headers?.get('Retry-After'));
          error.retryMs = Number.isFinite(retryAfter) && retryAfter > 0
            ? Math.min(retryAfter * 1000, 30000) : 3000;
          throw error;
        }
        return body;
      } catch (error) {
        if (error.name === 'AbortError') {
          throw new Error('The advisor request timed out. Retry to reconnect to the job.');
        }
        throw error;
      } finally {
        clearTimer(timeout);
      }
    }

    async function drive() {
      if (inFlight || !listeners.size) return;
      inFlight = true;
      const polling = Boolean(snapshot.job);
      if (!polling) emit({ phase: 'submitting', job: null, error: null });
      try {
        const job = await callApi(
          polling ? `${endpoint}/${encodeURIComponent(snapshot.job.job_id)}` : endpoint,
          polling ? {} : {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request, force }),
          },
        );
        const requestMatches = Object.entries(request).every(([key, value]) => (
          ['evidence_cutoff', 'match_kickoff'].includes(key)
            ? new Date(job?.request?.[key]).getTime() === new Date(value).getTime()
            : job?.request?.[key] === value
        ));
        if (!job?.job_id || !requestMatches
          || !['queued', 'running', 'completed', 'failed'].includes(job.state)
          || (job.state === 'completed' && !job.result?.response)) {
          throw new Error('The server returned an incomplete advisor job. Retry after checking the backend.');
        }
        capacityRetries = 0;
        nextDelay = pollMs;
        if (job.state === 'failed') {
          emit({ phase: 'error', job, error: job.error || 'The advisor job failed. You can retry it.' });
        } else {
          emit({ phase: job.state, job, error: null });
        }
      } catch (error) {
        if (error.status === 429 && capacityRetries < maxCapacityRetries) {
          capacityRetries += 1;
          nextDelay = error.retryMs;
          emit({ phase: 'queued', job: snapshot.job, error: null });
        } else if (polling && error.status === 404 && expiredResubmissions < 1) {
          // Worker records can expire or disappear after a server restart.
          // Resubmit normally so the backend can reuse its snapshot-aware cache.
          expiredResubmissions += 1;
          force = false;
          nextDelay = pollMs;
          emit({ phase: 'queued', job: null, error: null });
        } else {
          emit({
            phase: 'error',
            job: error.status === 409 ? null : snapshot.job,
            error: error.message || 'Could not reach the advisor. Check that the backend is running.',
          });
        }
      } finally {
        inFlight = false;
        if (['queued', 'running'].includes(snapshot.phase)) schedule();
      }
    }

    return {
      getSnapshot: () => snapshot,
      isUnused: () => !listeners.size && !inFlight,
      subscribe(listener) {
        listeners.add(listener);
        listener(snapshot);
        if (snapshot.phase === 'waiting') void drive();
        else if (['queued', 'running'].includes(snapshot.phase)) schedule();
        return () => {
          listeners.delete(listener);
          if (!listeners.size && timer !== null) {
            clearTimer(timer);
            timer = null;
          }
        };
      },
      retry() {
        if (inFlight) return;
        if (timer !== null) clearTimer(timer);
        timer = null;
        capacityRetries = 0;
        expiredResubmissions = 0;
        force = false;
        const job = ['queued', 'running'].includes(snapshot.job?.state) ? snapshot.job : null;
        emit({ phase: job ? job.state : 'waiting', job, error: null });
        void drive();
      },
    };
  }

  return {
    getTask(request, { force = false, revision = '' } = {}) {
      const key = JSON.stringify([request, revision]);
      if (force || !tasks.has(key)) {
        tasks.set(key, createTask(request, force));
        // Keep a small session cache, without dropping an active subscription.
        if (tasks.size > 24) {
          for (const [oldKey, task] of tasks) {
            if (oldKey !== key && task.isUnused()) tasks.delete(oldKey);
            if (tasks.size <= 24) break;
          }
        }
      }
      return tasks.get(key);
    },
  };
}

export const advisorClient = createAdvisorClient();
