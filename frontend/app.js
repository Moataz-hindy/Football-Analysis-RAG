const state = {
  discussion: null,
  visibleRound: 0,
  replayTimer: null,
  topics: [],
};

const $ = (selector) => document.querySelector(selector);
const api = async (path, options = {}) => {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.error || `Request failed (${response.status})`);
  return data;
};

const roleNames = {
  tactical_analyst: "Tactical analyst",
  statistical_analyst: "Statistical analyst",
  fan_analyst: "Fan analyst",
  refereeing_analyst: "Refereeing analyst",
  performance_analyst: "Performance analyst",
  context_analyst: "Context analyst",
};

function labelForAgent(agentId) {
  return roleNames[agentId] || agentId.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function initials(agentId) {
  return agentId.split("_").map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

function setStatus(message, kind = "") {
  const element = $("#launch-status");
  element.textContent = message;
  element.className = `launch-status ${kind}`;
}

function topicCard(topic) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "topic-card";
  button.innerHTML = `<span class="topic-arrow">&#8599;</span><span><strong>${escapeHtml(topic.label)}</strong><small>${escapeHtml(topic.description)}</small></span>`;
  button.addEventListener("click", () => startDiscussion(topic.label));
  return button;
}

async function loadTopics() {
  try {
    const data = await api("/topics");
    state.topics = data.topics || [];
    const list = $("#topic-list");
    list.replaceChildren(...state.topics.map(topicCard));
  } catch (error) {
    $("#topic-list").innerHTML = `<div class="error-line">Could not load topics: ${escapeHtml(error.message)}</div>`;
  }
}

async function loadSavedDiscussions() {
  try {
    const data = await api("/discussions");
    const list = $("#saved-discussions");
    if (!data.discussions?.length) {
      list.innerHTML = '<div class="muted-line">No saved rooms yet.</div>';
      return;
    }
    list.replaceChildren(...data.discussions.map(savedDiscussionCard));
  } catch (error) {
    $("#saved-discussions").innerHTML = `<div class="error-line">Could not load saved rooms: ${escapeHtml(error.message)}</div>`;
  }
}

function savedDiscussionCard(discussion) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "saved-card";
  button.innerHTML = `<span class="saved-index">${String(discussion.num_rounds || 0).padStart(2, "0")}</span><span><strong>${escapeHtml(discussion.topic)}</strong><small>${discussion.num_messages || 0} messages / ${discussion.num_agents || 0} agents</small></span><span class="topic-arrow">&#8599;</span>`;
  button.addEventListener("click", () => openDiscussion(discussion.discussion_id));
  return button;
}

async function startDiscussion(topic) {
  if (!topic.trim()) return;
  stopReplay();
  setStatus("Sending the question to the room...", "working");
  try {
    const result = await api("/discussions", { method: "POST", body: JSON.stringify({ topic: topic.trim(), num_rounds: 3 }) });
    setStatus(result.message || `Room ${result.discussion_id} is queued.`, "success");
    await waitForDiscussion(result.discussion_id);
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function waitForDiscussion(discussionId) {
  for (let attempt = 0; attempt < 12; attempt += 1) {
    try {
      const status = await api(`/discussions/${encodeURIComponent(discussionId)}/status`);
      if (status.status === "completed") {
        await openDiscussion(discussionId);
        return;
      }
      if (status.status === "error" || status.status === "not_found") break;
      setStatus(`Room is ${status.status || "working"}...`, "working");
      await new Promise((resolve) => window.setTimeout(resolve, 1500));
    } catch (error) {
      setStatus(error.message, "error");
      return;
    }
  }
  setStatus("The room is queued. It will appear in saved rooms when the run completes.", "working");
  await loadSavedDiscussions();
}

async function openDiscussion(discussionId) {
  stopReplay();
  try {
    state.discussion = await api(`/discussions/${encodeURIComponent(discussionId)}`);
    state.visibleRound = 0;
    renderRoom();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function renderRoom() {
  const discussion = state.discussion;
  $("#empty-room").hidden = true;
  $("#discussion-room").hidden = false;
  $("#room-id").textContent = `/${discussion.discussion_id}`;
  $("#room-topic").textContent = discussion.topic;
  $("#room-meta").textContent = `${discussion.agents.length} agents / ${discussion.num_rounds} rounds`;
  $("#agent-cards").replaceChildren(...discussion.agents.map(agentCard));
  renderTimeline();
}

function agentCard(agent) {
  const card = document.createElement("div");
  card.className = "agent-card";
  card.innerHTML = `<span class="avatar">${initials(agent.agent_id)}</span><span><strong>${escapeHtml(labelForAgent(agent.agent_id))}</strong><small>${escapeHtml(agent.agent_id)}</small></span>`;
  return card;
}

function renderTimeline() {
  const discussion = state.discussion;
  const maxRound = Math.max(3, discussion.num_rounds || 3);
  const messagesByRound = new Map();
  (discussion.messages || []).forEach((message) => {
    if (!messagesByRound.has(message.round_num)) messagesByRound.set(message.round_num, []);
    messagesByRound.get(message.round_num).push(message);
  });
  const timeline = $("#timeline");
  timeline.replaceChildren();
  for (let round = 0; round <= maxRound; round += 1) {
    const section = document.createElement("section");
    section.className = `round-section ${round <= state.visibleRound ? "is-visible" : "is-muted"}`;
    section.innerHTML = `<div class="round-marker"><span>${String(round).padStart(2, "0")}</span><strong>${round === 0 ? "Initial opinions" : `Round ${round}`}</strong></div>`;
    const messages = messagesByRound.get(round) || [];
    const messageList = document.createElement("div");
    messageList.className = "message-list";
    if (round <= state.visibleRound) {
      if (messages.length) messageList.replaceChildren(...messages.map(messageCard));
      else messageList.innerHTML = '<div class="empty-round">No messages recorded for this round.</div>';
    } else {
      messageList.innerHTML = '<div class="locked-round">Replay this round to reveal the conversation.</div>';
    }
    section.appendChild(messageList);
    timeline.appendChild(section);
  }
  $("#replay-label").textContent = state.visibleRound === 0 ? "Initial opinions" : `Through round ${state.visibleRound}`;
  $("#replay-prev").disabled = state.visibleRound === 0;
  $("#replay-next").disabled = state.visibleRound >= maxRound;
}

function messageCard(message) {
  const card = document.createElement("article");
  card.className = "message-card";
  const recipients = message.recipient_ids?.length ? `To ${message.recipient_ids.map(labelForAgent).join(", ")}` : "Room address";
  card.innerHTML = `<div class="message-top"><span class="avatar small">${initials(message.sender_id)}</span><span><strong>${escapeHtml(labelForAgent(message.sender_id))}</strong><small>${escapeHtml(message.sender_id)}</small></span><span class="message-route">${escapeHtml(recipients)}</span></div><p>${escapeHtml(message.content)}</p>`;
  return card;
}

function changeRound(delta) {
  if (!state.discussion) return;
  const maxRound = Math.max(3, state.discussion.num_rounds || 3);
  state.visibleRound = Math.max(0, Math.min(maxRound, state.visibleRound + delta));
  renderTimeline();
}

function stopReplay() {
  if (state.replayTimer) window.clearInterval(state.replayTimer);
  state.replayTimer = null;
  if ($("#replay-play")) $("#replay-play").textContent = "Play replay";
}

function toggleReplay() {
  if (state.replayTimer) {
    stopReplay();
    return;
  }
  if (!state.discussion) return;
  const maxRound = Math.max(3, state.discussion.num_rounds || 3);
  if (state.visibleRound >= maxRound) state.visibleRound = 0;
  $("#replay-play").textContent = "Pause replay";
  state.replayTimer = window.setInterval(() => {
    if (state.visibleRound >= maxRound) {
      stopReplay();
      return;
    }
    changeRound(1);
  }, 1800);
  renderTimeline();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>\"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character]);
}

$("#custom-topic-form").addEventListener("submit", (event) => {
  event.preventDefault();
  startDiscussion($("#custom-topic").value);
});
$("#refresh-discussions").addEventListener("click", loadSavedDiscussions);
$("#replay-reset").addEventListener("click", () => { stopReplay(); state.visibleRound = 0; renderTimeline(); });
$("#replay-prev").addEventListener("click", () => { stopReplay(); changeRound(-1); });
$("#replay-next").addEventListener("click", () => { stopReplay(); changeRound(1); });
$("#replay-play").addEventListener("click", toggleReplay);
loadTopics();
loadSavedDiscussions();
