import { useRef } from 'react';
import { useDevMode } from '../context/DevModeContext';
import * as api from '../services/api';
import type { Broker, BrokerListItem, Document, Media, Paginated, PromptData } from '../types';

function devMediaUrl(id: string): string {
  const seed = id.replace(/^dev-media-[\d]+-/, '') || id;
  return `https://picsum.photos/seed/${encodeURIComponent(seed)}/400/300`;
}

/**
 * Returns a stable API object that always reads the latest devMode state
 * via a ref, avoiding infinite re-render loops in useEffect dependencies.
 */
export function useApi() {
  const devMode = useDevMode();
  const devModeRef = useRef(devMode);
  devModeRef.current = devMode;

  // Build the api object once (via ref) so it's referentially stable
  const apiRef = useRef({
    async listDocuments(skip = 0, limit = 20): Promise<Paginated<Document>> {
      const dm = devModeRef.current;
      if (dm.active) {
        const all = [...dm.documents];
        return { items: all.slice(skip, skip + limit), total: all.length };
      }
      return api.listDocuments(skip, limit);
    },

    async getDocument(id: string): Promise<Document> {
      const dm = devModeRef.current;
      if (dm.active) {
        const doc = dm.documents.find((d) => d.id === id);
        if (!doc) throw new Error('Dev document not found');
        return { ...doc };
      }
      return api.getDocument(id);
    },

    async uploadDocuments(files: File[]) {
      const dm = devModeRef.current;
      if (dm.active) {
        await new Promise((r) => setTimeout(r, 400));
        return { uploaded: files.length };
      }
      return api.uploadDocuments(files);
    },

    documentContentUrl: api.documentContentUrl,

    async getDocumentContent(id: string): Promise<Response> {
      const dm = devModeRef.current;
      if (dm.active) {
        const doc = dm.documents.find((d) => d.id === id);
        if (doc && doc.content_type === 'text/plain') {
          const blob = new Blob(
            ['Dev mode sample text.\n\nLorem ipsum dolor sit amet, consectetur adipiscing elit.\nPhasellus euismod nisl eget ultricies ultrices.'],
            { type: 'text/plain' },
          );
          return new Response(blob);
        }
        throw new Error('PDF preview not available in dev mode');
      }
      return api.getDocumentContent(id);
    },

    async updateDocumentContent(id: string, content: string) {
      const dm = devModeRef.current;
      if (dm.active) {
        await new Promise((r) => setTimeout(r, 200));
        return;
      }
      return api.updateDocumentContent(id, content);
    },

    async updateDocument(id: string, data: Partial<Document>) {
      const dm = devModeRef.current;
      if (dm.active) {
        await new Promise((r) => setTimeout(r, 200));
        return;
      }
      return api.updateDocument(id, data);
    },

    async deleteDocument(id: string) {
      const dm = devModeRef.current;
      if (dm.active) {
        dm.deleteDocument(id);
        await new Promise((r) => setTimeout(r, 200));
        return;
      }
      return api.deleteDocument(id);
    },

    async listMedia(skip = 0, limit = 20): Promise<Paginated<Media>> {
      const dm = devModeRef.current;
      if (dm.active) {
        const all = [...dm.media];
        return { items: all.slice(skip, skip + limit), total: all.length };
      }
      return api.listMedia(skip, limit);
    },

    async getMedia(id: string): Promise<Media> {
      const dm = devModeRef.current;
      if (dm.active) {
        const item = dm.media.find((i) => i.id === id);
        if (!item) throw new Error('Dev media not found');
        return { ...item };
      }
      return api.getMedia(id);
    },

    mediaContentUrl(id: string): string {
      const dm = devModeRef.current;
      if (dm.active && id.startsWith('dev-media-')) {
        return devMediaUrl(id);
      }
      return api.mediaContentUrl(id);
    },

    async uploadMedia(file: File, description: string) {
      const dm = devModeRef.current;
      if (dm.active) {
        await new Promise((r) => setTimeout(r, 400));
        return;
      }
      return api.uploadMedia(file, description);
    },

    async updateMedia(id: string, data: Partial<Media>) {
      const dm = devModeRef.current;
      if (dm.active) {
        await new Promise((r) => setTimeout(r, 200));
        return;
      }
      return api.updateMedia(id, data);
    },

    async replaceMediaContent(id: string, file: File) {
      const dm = devModeRef.current;
      if (dm.active) {
        await new Promise((r) => setTimeout(r, 400));
        return;
      }
      return api.replaceMediaContent(id, file);
    },

    async deleteMedia(id: string) {
      const dm = devModeRef.current;
      if (dm.active) {
        dm.deleteMedia(id);
        await new Promise((r) => setTimeout(r, 200));
        return;
      }
      return api.deleteMedia(id);
    },

    async getPrompt(): Promise<PromptData> {
      const dm = devModeRef.current;
      if (dm.active) {
        return { content: dm.promptContent || '(no prompt saved yet)', updated_at: null };
      }
      return api.getPrompt();
    },

    async updatePrompt(content: string): Promise<PromptData> {
      const dm = devModeRef.current;
      if (dm.active) {
        dm.setPromptContent(content);
        await new Promise((r) => setTimeout(r, 300));
        return { content, updated_at: new Date().toISOString() };
      }
      return api.updatePrompt(content);
    },

    async listBrokers(sort_by?: string, order?: string, search?: string, skip = 0, limit = 20): Promise<Paginated<BrokerListItem>> {
      const dm = devModeRef.current;
      if (dm.active) {
        let list = [...dm.brokers];
        if (search) {
          const q = search.toLowerCase();
          list = list.filter((b) => b.name.toLowerCase().includes(q));
        }
        const key = (sort_by ?? 'interactions') as keyof BrokerListItem;
        list.sort((a, b) => {
          const av = a[key];
          const bv = b[key];
          if (av === undefined || bv === undefined) return 0;
          if (av < bv) return order === 'desc' ? 1 : -1;
          if (av > bv) return order === 'desc' ? -1 : 1;
          return 0;
        });
        return { items: list.slice(skip, skip + limit), total: list.length };
      }
      return api.listBrokers(sort_by, order, search, skip, limit);
    },

    async getBroker(phone: string): Promise<Broker> {
      return api.getBroker(phone);
    },

    async createBroker(data: Partial<Broker>): Promise<Broker> {
      return api.createBroker(data);
    },

    async updateBroker(phone: string, data: Partial<Broker>): Promise<Broker> {
      return api.updateBroker(phone, data);
    },

    async deleteBroker(phone: string): Promise<void> {
      return api.deleteBroker(phone);
    },
  });

  return apiRef.current;
}
