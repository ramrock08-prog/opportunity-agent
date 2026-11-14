const configuredBase = import.meta.env.VITE_API_BASE || "";

export const API_BASE = (
  configuredBase || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

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