import { useCallback, useEffect, useRef, useState } from "react";
import {
  listAll,
  request,
  type ApiTask,
  type Blocker,
  type WorkUpdate,
} from "../api";
import { useWorkspace } from "./useWorkspace";

/** Loads task activity independently of the dashboard and refreshes both after a write. */
export function useTaskDetail(taskId: string) {
  const { user, members, projects, reload } = useWorkspace();
  const [task, setTask] = useState<ApiTask | null>(null);
  const [updates, setUpdates] = useState<WorkUpdate[]>([]);
  const [blockers, setBlockers] = useState<Blocker[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const generation = useRef(0);
  const isManager = user.role !== "Developer";
  const canUpdate = task?.assignee === user.membership_id;
  const canReport = isManager || canUpdate;
  const projectMembers = members.filter((member) =>
    projects
      .find((project) => project.id === task?.project)
      ?.member_ids.includes(member.id),
  );
  const load = useCallback(async () => {
    const current = ++generation.current;
    const [detail, notes, risks] = await Promise.all([
      request<ApiTask>(`tasks/${taskId}/`),
      listAll<WorkUpdate>(`tasks/${taskId}/updates/`),
      listAll<Blocker>(`tasks/${taskId}/blockers/`),
    ]);
    // Ignore a response if this dialog has been closed or a newer load has started.
    if (current !== generation.current) return;
    setTask(detail);
    setUpdates(notes);
    setBlockers(risks);
  }, [taskId]);
  useEffect(() => {
    load()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
    return () => {
      generation.current += 1;
    };
  }, [load]);
  async function mutate(path: string, body: object, method = "POST") {
    if (busy) return false;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await request(`tasks/${taskId}/${path}`, {
        method,
        body: JSON.stringify(body),
      });
      setNotice("Saved to your workspace. Audit history updated.");
      // A successful write must not look like a failed write if the subsequent read is unavailable.
      try {
        await Promise.all([load(), reload()]);
      } catch {
        setError(
          "Saved successfully, but refresh failed. Close and reopen this task to load the latest data.",
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
  return {
    task,
    updates,
    blockers,
    loading,
    busy,
    error,
    notice,
    user,
    isManager,
    // Workspace administration alone does not grant project feedback access.
    canFeedback:
      isManager &&
      Boolean(
        projects
          .find((project) => project.id === task?.project)
          ?.reviewer_ids.includes(user.membership_id),
      ),
    canUpdate,
    canReport,
    projectMembers,
    mutate,
  };
}
