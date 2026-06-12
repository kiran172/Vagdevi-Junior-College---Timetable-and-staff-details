// Single place every network call goes through.
// To point at a hosted backend, set VITE_API_URL in frontend/.env:
//   VITE_API_URL=https://your-api.onrender.com
const BASE = import.meta.env.VITE_API_URL || '';

export function getAuth() {
  try { return JSON.parse(localStorage.getItem('vagdevi_auth')) || null; }
  catch { return null; }
}
export function setAuth(a) {
  if (a) localStorage.setItem('vagdevi_auth', JSON.stringify(a));
  else localStorage.removeItem('vagdevi_auth');
}

export async function api(path, { method = 'GET', body, params } = {}) {
  const url = new URL(BASE + '/api' + path, window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) url.searchParams.set(k, v);
  });
  const auth = getAuth();
  const res = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(auth ? { Authorization: `Bearer ${auth.token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) {
    setAuth(null);
    window.dispatchEvent(new Event('vagdevi-logout'));
    throw new ApiError(401, 'Session expired, log in again');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(res.status, data.detail || `Request failed (${res.status})`);
  }
  return data;
}

export class ApiError extends Error {
  constructor(status, message) {
    super(typeof message === 'string' ? message : JSON.stringify(message));
    this.status = status;
  }
}
