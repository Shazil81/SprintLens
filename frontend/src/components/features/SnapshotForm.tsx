import type { FormEvent } from "react";
import { useWorkspace } from "../../hooks/useWorkspace";

/** Both workflows capture a bounded project snapshot for an explicit reporting window. */
export function SnapshotForm({
  busy,
  label,
  onSubmit,
}: {
  busy: boolean;
  label: string;
  onSubmit: (body: object) => Promise<unknown>;
}) {
  const { projects } = useWorkspace();
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void onSubmit({
      project: Number(data.get("project")),
      days: Number(data.get("days")),
    });
  }
  return (
    <form className="insight-filters" onSubmit={submit}>
      <label>
        Project
        <select name="project" required disabled={busy}>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        History window
        <select name="days" defaultValue="7" disabled={busy}>
          {[7, 30, 90].map((days) => (
            <option key={days} value={days}>
              Last {days} days
            </option>
          ))}
        </select>
      </label>
      <button className="button primary" disabled={busy || !projects.length}>
        {busy ? "Working…" : label}
      </button>
    </form>
  );
}
