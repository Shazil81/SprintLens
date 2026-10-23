/** Common status messages for server-backed feature screens. */
export function FeatureState({
  loading,
  error,
}: {
  loading: boolean;
  error: string;
}) {
  return (
    <>
      {loading && <p role="status">Loading workspace records…</p>}
      {error && (
        <p className="login-error" role="alert">
          {error}
        </p>
      )}
    </>
  );
}
