import { useState } from "react";
import { request } from "../api";
import { useWorkspace } from "./useWorkspace";

/** Shares save/error handling without mixing account or project form state into App. */
export function useManagementMutation() {
  const { reload, setNotice } = useWorkspace();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  async function save(path: string, method: string, payload: object) {
    if (saving) return false;
    setSaving(true);
    setError("");
    try {
      await request(path, { method, body: JSON.stringify(payload) });
      try {
        await reload();
        setNotice("Saved successfully. Audit history updated.");
      } catch {
        setNotice(
          "Saved successfully, but refresh failed. Use Refresh to load the latest workspace.",
        );
      }
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed.");
      return false;
    } finally {
      setSaving(false);
    }
  }
  return { saving, error, save };
}
