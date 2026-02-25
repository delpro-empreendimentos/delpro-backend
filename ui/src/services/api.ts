import type { Document, Image, PromptData } from '../types';

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

export async function listDocuments(): Promise<Document[]> {
  const res = await fetchWithTimeout(`${API_BASE}/documents`);
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

// ─── Images ─────────────────────────────────────────────────────────────────

export async function listImages(): Promise<Image[]> {
  const res = await fetchWithTimeout(`${API_BASE}/images`);
  if (!res.ok) throw new Error(`Server error ${res.status} — check that the backend started and tables were created`);
  return res.json();
}

export async function getImage(id: string): Promise<Image> {
  const res = await fetchWithTimeout(`${API_BASE}/images/${id}`);
  if (!res.ok) throw new Error(`Failed to get image: ${res.status}`);
  return res.json();
}

export function imageContentUrl(id: string): string {
  return `${API_BASE}/images/${id}/content`;
}

export async function uploadImage(file: File, description: string): Promise<void> {
  const form = new FormData();
  form.append('file', file);
  form.append('description', description);
  const res = await fetchWithTimeout(`${API_BASE}/images`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(await parseError(res, `Upload failed: ${res.status}`));
}

export async function updateImage(id: string, data: Partial<Image>): Promise<void> {
  const res = await fetchWithTimeout(`${API_BASE}/images/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await parseError(res, `Update failed: ${res.status}`));
}

export async function replaceImageContent(id: string, file: File): Promise<void> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetchWithTimeout(`${API_BASE}/images/${id}/content`, { method: 'PUT', body: form });
  if (!res.ok) throw new Error(await parseError(res, `Replace failed: ${res.status}`));
}

export async function deleteImage(id: string): Promise<void> {
  const res = await fetchWithTimeout(`${API_BASE}/images/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete image: ${res.status}`);
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
