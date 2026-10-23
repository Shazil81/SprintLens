/** Gives session startup failures an explicit retry action. */
export function ConnectionState({
  loading,
  error,
  onRetry,
}: {
  loading: boolean;
  error: string;
  onRetry: () => void;
}) {
  if (loading)
    return <div className="connection-state">Connecting to SprintLens…</div>;
  return (
    <div className="connection-state">
      <h1>SprintLens</h1>
      <p role="alert">{error}</p>
      <button className="button primary" onClick={onRetry}>
        Retry connection
      </button>
    </div>
  );
}
