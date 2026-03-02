import type { Media } from '../types';

interface MediaCardProps {
  media: Media;
  mediaUrl: string;
  onClick: () => void;
}

export function MediaCard({ media, mediaUrl, onClick }: MediaCardProps) {
  const isPdf = media.content_type === 'application/pdf';

  return (
    <div className="image-card" onClick={onClick}>
      {isPdf ? (
        <div className="thumb pdf-thumb">
          <span className="pdf-icon">PDF</span>
        </div>
      ) : (
        <img className="thumb" src={mediaUrl} alt={media.filename} loading="lazy" />
      )}
      <div className="info">
        <div className="name">{media.filename}</div>
        <div className="desc">{media.description || ''}</div>
      </div>
    </div>
  );
}
