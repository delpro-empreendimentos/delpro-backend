import type { Broker, BrokerListItem, Document, Media, Paginated, PromptData } from '../types';

const API_BASE = '/api';
const TIMEOUT_MS = 10000;

async function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    return res;
  } catch (err: unknown) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error('Request timed out — is the backend running?');
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

async function parseError(res: Response, fallback: string): Promise<string> {
  try {
    const err = await res.json();
    return err.detail || fallback;
  } catch {
    return fallback;
  }
}

// ─── Documents ──────────────────────────────────────────────────────────────

export async function listDocuments(skip = 0, limit = 20): Promise<Paginated<Document>> {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  const res = await fetchWithTimeout(`${API_BASE}/documents?${params}`);
  if (!res.ok) throw new Error(`Server error ${res.status} — check that the backend started and tables were created`);
  return res.json();
}

export async function getDocument(id: string): Promise<Document> {
  const res = await fetchWithTimeout(`${API_BASE}/documents/${id}`);
  if (!res.ok) throw new Error(`Failed to get document: ${res.status}`);
  return res.json();
}

export async function uploadDocuments(files: File[]): Promise<{ uploaded: number }> {
  const form = new FormData();
  for (const file of files) form.append('files', file);
  const res = await fetchWithTimeout(`${API_BASE}/documents`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(await parseError(res, `Upload failed: ${res.status}`));
  return res.json();
}

export function documentContentUrl(id: string): string {
  return `${API_BASE}/documents/${id}/content`;
}

export async function getDocumentContent(id: string): Promise<Response> {
  const res = await fetchWithTimeout(`${API_BASE}/documents/${id}/content`);
  if (!res.ok) throw new Error(`Failed to get document content: ${res.status}`);
  return res;
}

export async function updateDocumentContent(id: string, textContent: string): Promise<void> {
  const res = await fetchWithTimeout(`${API_BASE}/documents/${id}/content`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: textContent }),
  });
  if (!res.ok) throw new Error(await parseError(res, `Update failed: ${res.status}`));
}

export async function updateDocument(id: string, data: Partial<Document>): Promise<void> {
  const res = await fetchWithTimeout(`${API_BASE}/documents/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await parseError(res, `Update failed: ${res.status}`));
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetchWithTimeout(`${API_BASE}/documents/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete document: ${res.status}`);
}

// ─── Media ──────────────────────────────────────────────────────────────────

export async function listMedia(skip = 0, limit = 20): Promise<Paginated<Media>> {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  const res = await fetchWithTimeout(`${API_BASE}/media?${params}`);
  if (!res.ok) throw new Error(`Server error ${res.status} — check that the backend started and tables were created`);
  return res.json();
}

export async function getMedia(id: string): Promise<Media> {
  const res = await fetchWithTimeout(`${API_BASE}/media/${id}`);
  if (!res.ok) throw new Error(`Failed to get media: ${res.status}`);
  return res.json();
}

export function mediaContentUrl(id: string): string {
  return `${API_BASE}/media/${id}/content`;
}

export async function uploadMedia(file: File, description: string): Promise<void> {
  const form = new FormData();
  form.append('file', file);
  form.append('description', description);
  const res = await fetchWithTimeout(`${API_BASE}/media`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(await parseError(res, `Upload failed: ${res.status}`));
}

export async function updateMedia(id: string, data: Partial<Media>): Promise<void> {
  const res = await fetchWithTimeout(`${API_BASE}/media/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await parseError(res, `Update failed: ${res.status}`));
}

export async function replaceMediaContent(id: string, file: File): Promise<void> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetchWithTimeout(`${API_BASE}/media/${id}/content`, { method: 'PUT', body: form });
  if (!res.ok) throw new Error(await parseError(res, `Replace failed: ${res.status}`));
}

export async function deleteMedia(id: string): Promise<void> {
  const res = await fetchWithTimeout(`${API_BASE}/media/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete media: ${res.status}`);
}

// ─── Prompt ─────────────────────────────────────────────────────────────────

export async function getPrompt(): Promise<PromptData> {
  const res = await fetchWithTimeout(`${API_BASE}/prompt`);
  if (!res.ok) throw new Error(`Failed to load prompt: ${res.status}`);
  return res.json();
}

export async function updatePrompt(content: string): Promise<PromptData> {
  const res = await fetchWithTimeout(`${API_BASE}/prompt`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error(await parseError(res, `Update failed: ${res.status}`));
  return res.json();
}

// ─── Brokers ──────────────────────────────────────────────────────────────────

export async function listBrokers(
  sort_by = 'interactions',
  order = 'desc',
  search?: string,
  skip = 0,
  limit = 20,
): Promise<Paginated<BrokerListItem>> {
  const params = new URLSearchParams({ sort_by, order, skip: String(skip), limit: String(limit) });
  if (search) params.set('search', search);
  const res = await fetchWithTimeout(`${API_BASE}/brokers?${params}`);
  if (!res.ok) throw new Error(`Server error ${res.status}`);
  return res.json();
}

export async function getBroker(phone: string): Promise<Broker> {
  const res = await fetchWithTimeout(`${API_BASE}/brokers/${encodeURIComponent(phone)}`);
  if (!res.ok) throw new Error(`Failed to get broker: ${res.status}`);
  return res.json();
}

export async function createBroker(data: Partial<Broker>): Promise<Broker> {
  const res = await fetchWithTimeout(`${API_BASE}/brokers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await parseError(res, `Create failed: ${res.status}`));
  return res.json();
}

export async function updateBroker(phone: string, data: Partial<Broker>): Promise<Broker> {
  const res = await fetchWithTimeout(`${API_BASE}/brokers/${encodeURIComponent(phone)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await parseError(res, `Update failed: ${res.status}`));
  return res.json();
}

export async function deleteBroker(phone: string): Promise<void> {
  const res = await fetchWithTimeout(`${API_BASE}/brokers/${encodeURIComponent(phone)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete broker: ${res.status}`);
}
