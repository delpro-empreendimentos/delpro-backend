export interface Document {
  id: string;
  filename: string;
  content_type: string;
  file_size_bytes: number;
  chunk_count: number;
  upload_date: string;
}

export interface Image {
  id: string;
  filename: string;
  content_type: string;
  file_size_bytes: number;
  description: string;
  created_at: string;
}

export interface PromptData {
  content: string;
  updated_at: string | null;
}

export type ToastType = 'info' | 'success' | 'error';

export interface ToastMessage {
  id: number;
  message: string;
  type: ToastType;
}
