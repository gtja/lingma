const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

export { API_BASE };

export async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {})
    }
  });

  const contentType = resp.headers.get('content-type') || '';
  if (!resp.ok) {
    if (contentType.includes('application/json')) {
      const errBody = await resp.json();
      const msg = errBody.message || errBody.error || 'Request failed';
      throw new Error(msg);
    }
    const text = await resp.text();
    throw new Error(text || 'Request failed');
  }

  if (contentType.includes('application/json')) {
    return resp.json();
  }
  return resp.text();
}

export async function apiGet(path) {
  return apiFetch(path, { method: 'GET' });
}

export async function apiPostJson(path, data) {
  return apiFetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data || {})
  });
}

export async function apiDelete(path) {
  return apiFetch(path, { method: 'DELETE' });
}

export async function apiPostForm(path, formData) {
  return apiFetch(path, {
    method: 'POST',
    body: formData
  });
}
