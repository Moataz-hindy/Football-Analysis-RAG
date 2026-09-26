import { useEffect, useMemo, useRef, useState } from 'react';
import { advisorClient, buildAdvisorRequest, DEFAULT_CONFIGURATION } from '../lib/advisorClient';

const WAITING = { phase: 'waiting', job: null, error: null };

export default function useDiscussionAdvisor(discussion, discussionStatus) {
  const id = discussion?.discussion_id || null;
  const [drafts, setDrafts] = useState({});
  const selectedRequests = useRef(new Map());
  const [selection, setSelection] = useState({ id: null, task: null });
  const [result, setResult] = useState({ id: null, task: null, analysis: WAITING });
  const [validationError, setValidationError] = useState(null);
  const topic = discussion?.topic;
  // A reloaded transcript with the same ID must not reuse a previous report.
  // The backend remains responsible for the report's authoritative snapshot hash.
  const revision = useMemo(() => discussion ? JSON.stringify(discussion) : '', [discussion]);

  // Only a confirmed completed discussion may launch an automatic analysis.
  useEffect(() => {
    setValidationError(null);
    if (!id || discussionStatus !== 'completed') {
      setSelection({ id, task: null });
      return;
    }
    try {
      let request = selectedRequests.current.get(id);
      if (!request || request.question !== topic?.trim()) {
        request = buildAdvisorRequest({ discussion_id: id, topic });
        selectedRequests.current.set(id, request);
      }
      if (request.mode === 'match_preview' && new Date(request.match_kickoff).getTime() <= Date.now()) {
        throw new Error('Kickoff has passed. Choose a match review or a new future kickoff in analysis settings.');
      }
      setSelection({ id, task: advisorClient.getTask(request, { revision }) });
    } catch (error) {
      setValidationError({ id, message: error.message });
    }
  }, [id, topic, discussionStatus, revision]);

  useEffect(() => {
    if (!selection.task || selection.id !== id || discussionStatus !== 'completed') return undefined;
    let subscribed = true;
    const unsubscribe = selection.task.subscribe((analysis) => {
      if (subscribed) setResult({ id, task: selection.task, analysis });
    });
    return () => {
      subscribed = false;
      unsubscribe();
    };
  }, [selection, id, discussionStatus]);

  // An open preview also expires when kickoff passes, without a page reload.
  useEffect(() => {
    const job = result.id === id && result.task === selection.task ? result.analysis.job : null;
    if (job?.request?.mode !== 'match_preview' || result.analysis.phase !== 'completed') return undefined;
    let timer;
    const expire = () => {
      const remaining = new Date(job.request.match_kickoff).getTime() - Date.now();
      if (remaining > 0) {
        timer = setTimeout(expire, Math.min(remaining, 2_000_000_000));
      } else {
        setResult({ id, task: selection.task, analysis: {
          phase: 'error', job: null,
          error: 'Kickoff has passed. Choose a match review or a new future kickoff in analysis settings.',
        } });
      }
    };
    expire();
    return () => clearTimeout(timer);
  }, [id, selection.task, result]);

  const configuration = drafts[id] || DEFAULT_CONFIGURATION;
  function run(force) {
    if (!id || discussionStatus !== 'completed') return;
    try {
      const request = buildAdvisorRequest(discussion, configuration);
      selectedRequests.current.set(id, request);
      const task = advisorClient.getTask(request, { force, revision });
      setValidationError(null);
      setSelection({ id, task });
      const snapshot = task.getSnapshot();
      if (!force && (snapshot.phase === 'error' || snapshot.job?.result?.response?.status === 'failed')) {
        task.retry();
      }
    } catch (error) {
      setValidationError({ id, message: error.message });
    }
  }

  let analysis = WAITING;
  if (selection.id === id && selection.task && discussionStatus === 'completed') {
    analysis = result.id === id && result.task === selection.task
      ? result.analysis : selection.task.getSnapshot();
  }
  if (validationError?.id === id) {
    analysis = { ...analysis, phase: 'error', error: validationError.message };
  }

  return {
    analysis,
    configuration,
    onConfigurationChange: (next) => setDrafts((previous) => ({ ...previous, [id]: next })),
    onRetry: () => run(false),
    onRefresh: () => run(true),
  };
}
