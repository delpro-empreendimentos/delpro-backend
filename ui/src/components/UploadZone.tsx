import { useRef, useState } from 'react';
import type { DragEvent } from 'react';

interface UploadZoneProps {
  icon: string;
  message: string;
  hint: string;
  accept: string;
  multiple?: boolean;
  onFiles: (files: File[]) => void;
}

export function UploadZone({ icon, message, hint, accept, multiple = false, onFiles }: UploadZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      onFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleClick = () => inputRef.current?.click();

  const handleChange = () => {
    if (inputRef.current?.files) {
      onFiles(Array.from(inputRef.current.files));
      inputRef.current.value = '';
    }
  };

  return (
    <div
      className={`upload-zone${dragOver ? ' drag-over' : ''}`}
      onClick={handleClick}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="icon">{icon}</div>
      <p>{message}</p>
      <p style={{ fontSize: '12px', marginTop: '4px' }}>{hint}</p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleChange}
        style={{ display: 'none' }}
      />
    </div>
  );
}
