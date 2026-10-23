import { useEffect, useState } from "react";
import { session, type User } from "../api";
/** Restores the server session when the application starts. */
export function useSession() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  // Restore identity and the CSRF token without storing credentials in the browser.
  async function bootstrap() {
    setLoading(true);
    setError("");
    try {
      setUser((await session()).user);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to connect.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void bootstrap();
  }, []);
  return { user, setUser, loading, error, bootstrap };
}
