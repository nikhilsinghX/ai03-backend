(() => {
  // Empty base means same-origin: frontend and API are served on one port.
  const API_BASE = window.API_BASE || '';
  async function request(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
    return body;
  }
  window.InterviewAPI = {
    base: API_BASE,
    health: () => request('/health'),
    createSession: (jd_text, resume_text) => request('/sessions', { method: 'POST', body: JSON.stringify({ jd_text, resume_text }) }),
    editRubric: (id, rubric) => request(`/sessions/${encodeURIComponent(id)}/rubric`, { method: 'PUT', body: JSON.stringify(rubric) }),
    consent: (id) => request(`/sessions/${encodeURIComponent(id)}/consent`, { method: 'POST', body: '{}' }),
    start: (id) => request(`/sessions/${encodeURIComponent(id)}/start`, { method: 'POST', body: '{}' }),
    session: (id) => request(`/sessions/${encodeURIComponent(id)}`),
    answer: (id, text) => request(`/api/session/${encodeURIComponent(id)}/answer`, { method: 'POST', body: JSON.stringify({ text }) }),
    transcript: (id) => request(`/api/session/${encodeURIComponent(id)}/transcript`),
    finish: (id) => request(`/api/session/${encodeURIComponent(id)}/finish`, { method: 'POST', body: '{}' }),
    assessment: (id) => request(`/api/session/${encodeURIComponent(id)}/assessment`)
  };
})();
