/**
 * Thin fetch wrapper for the Privacy Ops API. Attaches the internal JWT
 * (obtained via /api/v1/auth/oidc/callback after Entra ID login) from
 * wherever the app's auth flow stores it — this scaffold uses a simple
 * in-memory/localStorage placeholder; replace with your app's real auth
 * state management before relying on this beyond local dev.
 */
const API_BASE = "/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("access_token");
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error ${res.status}: ${detail}`);
  }

  return res.json() as Promise<T>;
}
