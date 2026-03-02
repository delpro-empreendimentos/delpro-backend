export interface Document {
  id: string;
  filename: string;
  content_type: string;
  file_size_bytes: number;
  chunk_count: number;
  upload_date: string;
}

export interface Media {
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

export interface Broker {
  phone_number: string;
  name: string;
  product_type_luxo: boolean;
  product_type_alto: boolean;
  product_type_medio: boolean;
  product_type_mcmv: boolean;
  sell_type_investimento: boolean;
  sell_type_moradia: boolean;
  region_zona_norte: boolean;
  region_zona_sul: boolean;
  region_zona_central: boolean;
  interactions: number;
  date_joined: string;
  last_message_at: string;
  sold_delpro_product: boolean;
}

export interface BrokerListItem {
  phone_number: string;
  name: string;
  interactions: number;
  date_joined: string;
  last_message_at: string;
  sold_delpro_product: boolean;
}

export interface Paginated<T> {
  items: T[];
  total: number;
}

export type ToastType = 'info' | 'success' | 'error';

export interface ToastMessage {
  id: number;
  message: string;
  type: ToastType;
}
