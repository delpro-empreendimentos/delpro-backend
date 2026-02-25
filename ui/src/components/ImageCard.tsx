import type { Image } from '../types';

interface ImageCardProps {
  image: Image;
  imageUrl: string;
  onClick: () => void;
}

export function ImageCard({ image, imageUrl, onClick }: ImageCardProps) {
  return (
    <div className="image-card" onClick={onClick}>
      <img className="thumb" src={imageUrl} alt={image.filename} loading="lazy" />
      <div className="info">
        <div className="name">{image.filename}</div>
        <div className="desc">{image.description || ''}</div>
      </div>
    </div>
  );
}
