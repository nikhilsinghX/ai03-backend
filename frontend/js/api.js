const API_BASE = "http://localhost:8000/api";

async function call(method, path, body) {
  const res = await fetch(API_BASE + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${method} ${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  health: () => call("GET", "/health"),
  createSession: (jd_text, resume_text) =>
    call("POST", "/session", { jd_text, resume_text }),
  makeRubric: (id) => call("POST", `/session/${id}/rubric`),
  saveRubric: (id, rubric) => call("PUT", `/session/${id}/rubric`, rubric),
  makePlan: (id) => call("POST", `/session/${id}/plan`),
  consent: (id) => call("POST", `/session/${id}/consent`),
  start: (id) => call("POST", `/session/${id}/start`),
  answer: (id, text) => call("POST", `/session/${id}/answer`, { text }),
  finish: (id) => call("POST", `/session/${id}/finish`),
  getAssessment: (id) => call("GET", `/session/${id}/assessment`),
  getTranscript: (id) => call("GET", `/session/${id}/transcript`),
};