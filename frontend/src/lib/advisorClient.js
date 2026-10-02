// One shared request per discussion revision, including React effect replay.
// Backend persistence is authoritative across tabs, reloads and API workers.
export function createAdvisorClient({ endpoint = 'advisor', fetchImpl = (...args) => fetch(...args),
  wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms)) } = {}) {
  const tasks = new Map();
  async function request(url, options) {
    const response = await fetchImpl(url, { ...options, signal: AbortSignal.timeout(60000) });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The Advisor is unavailable.');
    return data;
  }
  async function run(id, retryFailed) {
    const url = `/discussions/${encodeURIComponent(id)}/${endpoint}`;
    let data = await request(url);
    if (data.state === 'missing' || (retryFailed && data.retryable)) {
      try {
        data = await request(url, { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ retry_failed: retryFailed }) });
      } catch (error) {
        // A lost POST response may hide a successful or still-running request.
        // Reconnect with GET; never submit a second paid attempt automatically.
        data = await request(url);
        if (data.state === 'missing') throw error;
      }
    }
    // The backend renews active claims and marks abandoned claims as failed.
    // Keep reconnecting through long provider retry windows without another POST.
    while (data.state === 'running') {
      await wait(2500);
      data = await request(url);
    }
    if (!['completed', 'failed'].includes(data.state)) {
      throw new Error('The Advisor is still pending. Check again shortly.');
    }
    return data;
  }
  return {
    get(id, revision, { refresh = false, retryFailed = false } = {}) {
      const key = JSON.stringify([id, revision]);
      if (refresh || !tasks.has(key)) {
        // Store settled failures too: remounts do not automatically retry.
        tasks.set(key, run(id, retryFailed).catch((error) => ({ state: 'failed', error: error.message, reconnect: true })));
        if (tasks.size > 32) tasks.delete(tasks.keys().next().value);
      }
      return tasks.get(key);
    },
  };
}

export const advisorClient = createAdvisorClient();

export const decisionClient = createAdvisorClient({ endpoint: 'advisor/decision' });
