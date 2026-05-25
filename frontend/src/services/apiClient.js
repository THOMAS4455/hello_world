export const getApiBaseUrl = () => process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export const buildQuery = (params = {}) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    if (Array.isArray(value)) {
      if (value.length > 0) {
        searchParams.append(key, value.join(','));
      }
      return;
    }
    searchParams.append(key, String(value));
  });
  const query = searchParams.toString();
  return query ? `?${query}` : '';
};

export const getAuthHeaders = () => {
  try {
    const raw = localStorage.getItem('persist:root');
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw);
    const authState = parsed?.auth ? JSON.parse(parsed.auth) : null;
    const token = authState?.token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
};

export const normalizeApiError = (status, payload, fallback = 'Request failed') => {
  if (payload?.message) {
    return new Error(payload.message);
  }
  return new Error(`${fallback}: ${status}`);
};

export async function apiRequest(endpoint, options = {}) {
  const baseUrl = options.baseUrl || getApiBaseUrl();
  const query = options.params ? buildQuery(options.params) : '';
  const url = `${baseUrl}${endpoint}${query}`;
  const method = options.method || 'GET';
  const headers = {
    ...getAuthHeaders(),
    ...options.headers,
  };

  if (options.body !== undefined && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    method,
    headers,
    body: options.body,
    signal: options.signal,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok || payload?.success === false) {
    throw normalizeApiError(response.status, payload);
  }

  return payload;
}
