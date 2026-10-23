import { useCallback, useEffect, useState } from "react";
import { listAll, request } from "../api";
import { useWorkspace } from "./useWorkspace";

/** Keeps feature resources and errors local while refreshing shared task/audit data after writes. */
export function useFeatureData<T>(path: string) {
  const [items, setItems] = useState<T[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const { reload: reloadWorkspace } = useWorkspace();
  const load = useCallback(
    async () => setItems(await listAll<T>(path)),
    [path],
  );
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setItems([]);
    listAll<T>(path)
      .then((data) => {
        if (active) setItems(data);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [path]);
  async function mutate(url: string, method: string, body: object) {
    if (busy) return false;
    setBusy(true);
    setError("");
    try {
      await request(url, { method, body: JSON.stringify(body) });
      try {
        await Promise.all([load(), reloadWorkspace()]);
      } catch {
        setError(
          "Saved successfully, but refresh failed. Refresh before making another change.",
        );
      }
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed.");
      return false;
    } finally {
      setBusy(false);
    }
  }
  return { items, error, setError, loading, busy, load, mutate };
}
