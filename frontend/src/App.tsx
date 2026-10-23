import { useSession } from "./hooks/useSession";
import { Login } from "./components/Login";
import { Workspace } from "./components/Workspace";
import { ConnectionState } from "./components/ConnectionState";

/** Selects the startup, sign-in, or authenticated workspace screen. */
export default function App() {
  const { user, setUser, loading, error, bootstrap } = useSession();
  if (loading || error)
    return (
      <ConnectionState loading={loading} error={error} onRetry={bootstrap} />
    );
  return user ? (
    <Workspace key={user.id} user={user} onLogout={() => setUser(null)} />
  ) : (
    <Login onLogin={setUser} />
  );
}
