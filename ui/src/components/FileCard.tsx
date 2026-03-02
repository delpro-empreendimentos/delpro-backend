import type { Document } from '../types';
import { formatBytes, formatDate, getFileIcon } from '../utils';

interface FileCardProps {
  doc: Document;
  onClick: () => void;
}

export function FileCard({ doc, onClick }: FileCardProps) {
  const icon = getFileIcon(doc.content_type);

  return (
    <div className="file-card" onClick={onClick}>
      <div className={`icon ${icon.className}`}>{icon.symbol}</div>
      <div className="name">{doc.filename}</div>
      <div className="meta">{formatBytes(doc.file_size_bytes)}</div>
      <div className="meta">{doc.chunk_count} chunks</div>
      <div className="meta">{formatDate(doc.upload_date)}</div>
    </div>
  );
}
