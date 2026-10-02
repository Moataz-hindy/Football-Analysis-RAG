// A mode change must also clear the other mode's selections from the API payload.
export function buildDiscussionRequest({ topic, rounds, mode, agentCount, campA, campB }) {
  const dynamic = mode === 'dynamic';
  const selected = [...campA, ...campB];
  return {
    topic,
    num_rounds: rounds,
    num_agents: dynamic ? agentCount : selected.length,
    dynamic_personas: dynamic,
    persona_ids: dynamic ? null : selected,
    camp_a_ids: dynamic ? null : campA,
    camp_b_ids: dynamic ? null : campB,
  };
}
