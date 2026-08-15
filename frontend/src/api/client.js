const API_BASE = '/api';

function getToken() {
  return localStorage.getItem('access_token');
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers
  };

  const response = await fetch(`${API_BASE}${path}`, config);

  if (response.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('is_admin');
    window.location.hash = '#/login';
    throw new Error('Session expirée. Veuillez vous reconnecter.');
  }

  if (!response.ok) {
    let detail = `Erreur ${response.status}`;
    try {
      const body = await response.json();
      if (body.detail) detail = body.detail;
    } catch (_) {
      // pas de JSON
    }
    throw new Error(detail);
  }

  if (response.status === 204) return null;
  return response.json();
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path) => request(path, { method: 'DELETE' }),
  upload: (path, formData) => {
    const token = getToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return fetch(`${API_BASE}${path}`, { method: 'POST', body: formData, headers });
  }
};