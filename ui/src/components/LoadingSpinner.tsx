export function LoadingSpinner({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="loading">
      <p>{message}</p>
    </div>
  );
}
