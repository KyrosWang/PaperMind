export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (typeof window === "undefined") {
    headers.set("X-API-Key", process.env.APP_API_KEY ?? "change-me");
    return fetch(`${process.env.API_URL ?? "http://localhost:8000/api"}${path}`, { ...init, headers });
  }
  return fetch(`/api/proxy${path}`, { ...init, headers });
}

export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

