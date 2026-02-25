import { useRef } from 'react';
import { useDevMode } from '../context/DevModeContext';
import * as api from '../services/api';
import type { Document, Image, PromptData } from '../types';

function devImageUrl(id: string): string {
  const seed = id.replace(/^dev-img-[\d]+-/, '') || id;
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
    async listDocuments(): Promise<Document[]> {
      const dm = devModeRef.current;
      if (dm.active) return [...dm.documents];
      return api.listDocuments();
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

    async listImages(): Promise<Image[]> {
      const dm = devModeRef.current;
      if (dm.active) return [...dm.images];
      return api.listImages();
    },

    async getImage(id: string): Promise<Image> {
      const dm = devModeRef.current;
      if (dm.active) {
        const img = dm.images.find((i) => i.id === id);
        if (!img) throw new Error('Dev image not found');
        return { ...img };
      }
      return api.getImage(id);
    },

    imageContentUrl(id: string): string {
      const dm = devModeRef.current;
      if (dm.active && id.startsWith('dev-img-')) {
        return devImageUrl(id);
      }
      return api.imageContentUrl(id);
    },

    async uploadImage(file: File, description: string) {
      const dm = devModeRef.current;
      if (dm.active) {
        await new Promise((r) => setTimeout(r, 400));
        return;
      }
      return api.uploadImage(file, description);
    },

    async updateImage(id: string, data: Partial<Image>) {
      const dm = devModeRef.current;
      if (dm.active) {
        await new Promise((r) => setTimeout(r, 200));
        return;
      }
      return api.updateImage(id, data);
    },

    async replaceImageContent(id: string, file: File) {
      const dm = devModeRef.current;
      if (dm.active) {
        await new Promise((r) => setTimeout(r, 400));
        return;
      }
      return api.replaceImageContent(id, file);
    },

    async deleteImage(id: string) {
      const dm = devModeRef.current;
      if (dm.active) {
        dm.deleteImage(id);
        await new Promise((r) => setTimeout(r, 200));
        return;
      }
      return api.deleteImage(id);
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
  });

  return apiRef.current;
}
