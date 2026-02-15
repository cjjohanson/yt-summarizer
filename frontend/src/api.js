/**
 * API client for the YT Summarizer backend.
 */

const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });

  if (options.method === 'DELETE' && res.status === 204) {
    return null;
  }

  const data = await res.json();

  if (!res.ok) {
    const message = data?.detail?.message || data?.detail || 'Request failed';
    throw new Error(message);
  }

  return data;
}

export function submitVideo(url, opts = {}) {
  return request('/videos', {
    method: 'POST',
    body: JSON.stringify({ url, ...opts }),
  });
}

export function listVideos({ status, limit = 50, offset = 0, q } = {}) {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (q) params.set('q', q);
  params.set('limit', String(limit));
  params.set('offset', String(offset));
  return request(`/videos?${params}`);
}

export function getVideo(id) {
  return request(`/videos/${id}`);
}

export function getVideoStatus(id) {
  return request(`/videos/${id}/status`);
}

export function deleteVideo(id) {
  return request(`/videos/${id}`, { method: 'DELETE' });
}

export function getStats() {
  return request('/stats');
}

export function searchVideos(q, limit = 20) {
  const params = new URLSearchParams({ q, limit: String(limit) });
  return request(`/search?${params}`);
}
