const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";
const TASK_WAIT_TIMEOUT_MS = 300000;


async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `API request failed: ${response.status}`);
  }

  return response.json();
}

async function requestText(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `API request failed: ${response.status}`);
  }
  return response.text();
}

function waitForTask(taskId, onProgress = () => {}) {
  let source;
  let polling = false;
  let settled = false;
  let timeoutId;

  return new Promise((resolve, reject) => {
    const finish = async () => {
      if (settled) return;
      try {
        const snapshot = await request(`/tasks/${taskId}`);
        onProgress(snapshot);
        if (["completed", "failed", "cancelled", "interrupted"].includes(snapshot.status)) {
          settled = true;
          window.clearTimeout(timeoutId);
          source?.close();
          resolve(snapshot);
        }
      } catch (error) {
        if (!settled) reject(error);
      }
    };

    const poll = async () => {
      if (settled) return;
      polling = true;
      await finish();
      if (!settled) window.setTimeout(poll, 700);
    };

    source = new EventSource(`${API_BASE}/tasks/${encodeURIComponent(taskId)}/events`);
    source.addEventListener("progress", (event) => {
      const payload = JSON.parse(event.data);
      onProgress(payload);
      if (["completed", "failed", "cancelled", "interrupted"].includes(payload.status)) finish();
    });
    source.onerror = () => {
      source.close();
      if (!polling) poll();
    };
    timeoutId = window.setTimeout(() => {
      if (settled) return;
      source?.close();
      finish().then(() => {
        if (!settled) {
          settled = true;
          reject(new Error("任务等待超时，可在历史会话中检查结果或重新运行。"));
        }
      });
    }, TASK_WAIT_TIMEOUT_MS);
  });
}


export const api = {
  health: () => request("/health"),
  evaluationSummary: () => request("/evaluation/summary"),
  profiles: () => request("/profiles"),
  domains: () => request("/domains"),
  demoSessions: () => request("/demo-sessions"),
  knowledgeSources: (params = {}) => {
    const search = new URLSearchParams();
    if (params.domain) search.set("domain", params.domain);
    if (params.query) search.set("query", params.query);
    return request(`/knowledge/sources${search.size ? `?${search.toString()}` : ""}`);
  },
  literatureExperiments: (domain = "") => request(
    `/knowledge/experiments${domain ? `?domain=${encodeURIComponent(domain)}` : ""}`,
  ),
  evidenceAssets: (params = {}) => {
    const search = new URLSearchParams();
    (params.evidenceIds || []).forEach((id) => search.append("evidence_ids", id));
    (params.sourceIds || []).forEach((id) => search.append("source_ids", id));
    if (params.topic) search.set("topic", params.topic);
    return request(`/evidence/assets${search.size ? `?${search.toString()}` : ""}`);
  },
  evidenceMediaUrl: (assetId) => `${API_BASE}/evidence/assets/${encodeURIComponent(assetId)}/media`,
  questions: (domain) => request(`/questions?domain=${encodeURIComponent(domain)}`),
  submitDiagnosis: (payload) => request("/diagnosis", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  runAgents: (payload) => request("/agent/run", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  startAgentTask: (payload) => request("/agent/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  waitForTask,
  task: (taskId) => request(`/tasks/${taskId}`),
  cancelTask: (taskId) => request(`/tasks/${taskId}/cancel`, { method: "POST" }),
  retryTask: (taskId) => request(`/tasks/${taskId}/retry`, { method: "POST" }),
  sessions: () => request("/sessions?limit=12"),
  session: (sessionId) => request(`/sessions/${sessionId}`),
  resources: (sessionId) => request(`/sessions/${sessionId}/resources`),
  report: (sessionId) => request(`/sessions/${sessionId}/report`),
  exportReport: (sessionId) => requestText(`/sessions/${sessionId}/export`),
  feedback: (sessionId, payload) => request(`/sessions/${sessionId}/feedback`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  ask: (sessionId, question) => request(`/sessions/${sessionId}/ask`, {
    method: "POST",
    body: JSON.stringify({ question }),
  }),
  startInquiryTask: (sessionId, question) => request(`/sessions/${sessionId}/inquiry-tasks`, {
    method: "POST",
    body: JSON.stringify({ question }),
  }),
  inquiries: (sessionId) => request(`/sessions/${sessionId}/inquiries`),
  startAssistantTask: (payload) => request("/assistant/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
};
