// Empty means "same origin". Vite proxies /api to FastAPI locally,
// and the production build is served by FastAPI itself.
const configuredBase = import.meta.env.VITE_API_BASE || "";
const TOKEN_KEY = "opportunity_agent_token";
const ACCOUNT_KEY = "opportunity_agent_known_account";

export const API_BASE = configuredBase.replace(/\/+$/, "");

let authToken = "";

function readStoredToken() {
  try {
    return window.localStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

export function getAuthToken() {
  if (!authToken) authToken = readStoredToken();
  return authToken;
}

export function setAuthToken(token) {
  authToken = token || "";

  try {
    if (token) {
      window.localStorage.setItem(TOKEN_KEY, token);
    } else {
      window.localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // Storage can be unavailable in private browsing; the in-memory
    // token still works for this session.
  }
}

export function clearAuthToken() {
  setAuthToken("");
}

export function hasKnownAccount() {
  try {
    return window.localStorage.getItem(ACCOUNT_KEY) === "1";
  } catch {
    return false;
  }
}

export function markKnownAccount() {
  try {
    window.localStorage.setItem(ACCOUNT_KEY, "1");
  } catch {
    // Ignore storage restrictions; this only affects the default tab.
  }
}

export function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getAuthToken();

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
}

export async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

export function errorMessage(data, fallback) {
  if (typeof data?.detail === "string") return data.detail;

  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => item.msg)
      .filter(Boolean)
      .join(", ");
  }

  return fallback;
}