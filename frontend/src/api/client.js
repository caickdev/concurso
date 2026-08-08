// Deploy unificado (frontend + api no mesmo projeto Vercel, roteado via
// rewrites em vercel.json): caminho relativo funciona sem configuração.
// Deploy separado (frontend e backend em projetos Vercel distintos): defina
// VITE_API_URL com a origem do backend (ex.: https://api-concursos.vercel.app).
const API_ORIGIN = import.meta.env.VITE_API_URL?.replace(/\/$/, "") ?? "";
const API_BASE = `${API_ORIGIN}/api/v1`;

class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Erro na requisição (HTTP ${status})`);
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Wrapper de fetch com `credentials: "include"` — necessário para que o
 * cookie HttpOnly de autenticação seja enviado/recebido pelo backend.
 */
async function request(path, { method = "GET", body, params } = {}) {
  let url = `${API_BASE}${path}`;
  if (params) {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
    );
    const qs = query.toString();
    if (qs) url += `?${qs}`;
  }

  const response = await fetch(url, {
    method,
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(response.status, data?.detail);
  }
  return data;
}

export const api = {
  auth: {
    register: (payload) => request("/auth/register", { method: "POST", body: payload }),
    login: (payload) => request("/auth/login", { method: "POST", body: payload }),
    logout: () => request("/auth/logout", { method: "POST" }),
    me: () => request("/auth/me"),
    forgotPassword: (payload) => request("/auth/forgot-password", { method: "POST", body: payload }),
    resetPassword: (payload) => request("/auth/reset-password", { method: "POST", body: payload }),
  },
  users: {
    updateMe: (payload) => request("/users/me", { method: "PATCH", body: payload }),
    listNotebook: () => request("/users/me/notebook"),
    addToNotebook: (payload) => request("/users/me/notebook", { method: "POST", body: payload }),
    updateNotebookItem: (id, payload) =>
      request(`/users/me/notebook/${id}`, { method: "PATCH", body: payload }),
    removeFromNotebook: (id) => request(`/users/me/notebook/${id}`, { method: "DELETE" }),
  },
  questions: {
    filter: (params) => request("/questions/filter", { params }),
    detail: (id) => request(`/questions/${id}`),
    submitAnswer: (id, payload) =>
      request(`/questions/${id}/answer`, { method: "POST", body: payload }),
    explainAI: (id, payload) =>
      request(`/questions/${id}/explain-ai`, { method: "POST", body: payload }),
    batch: (questions) => request("/questions/batch", { method: "POST", body: { questions } }),
  },
  comments: {
    list: (questionId) => request(`/questions/${questionId}/comments`),
    create: (questionId, payload) =>
      request(`/questions/${questionId}/comments`, { method: "POST", body: payload }),
    report: (questionId, commentId, payload) =>
      request(`/questions/${questionId}/comments/${commentId}/report`, {
        method: "POST",
        body: payload,
      }),
  },
  leaderboard: {
    get: (limit = 50) => request("/leaderboard", { params: { limit } }),
  },
  taxonomy: {
    subjects: () => request("/subjects"),
    boards: () => request("/boards"),
    states: () => request("/states"),
  },
};

export { ApiError };
