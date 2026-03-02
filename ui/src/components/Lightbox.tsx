import type { MouseEvent } from 'react';

interface LightboxProps {
  src: string;
  alt: string;
  onClose: () => void;
}

export function Lightbox({ src, alt, onClose }: LightboxProps) {
  const handleOverlayClick = (e: MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div className="lightbox-overlay" onClick={handleOverlayClick}>
      <img className="lightbox-img" src={src} alt={alt} />
      <button className="lightbox-close" onClick={onClose}>
        &times;
      </button>
    </div>
  );
}
