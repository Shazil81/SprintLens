import type { FormEvent } from "react";
import type { ApiTask, Milestone } from "../api";
import { useFeatureData } from "../hooks/useFeatureData";
import { useWorkspace } from "../hooks/useWorkspace";

/** Assigns sprint/milestone and prerequisites together through the graph-validation endpoint. */
export function TaskPlanningForm({
  task,
  busy,
  onSave,
}: {
  task: ApiTask;
  busy: boolean;
  onSave: (body: object) => Promise<boolean>;
}) {
  const { items, error, loading } = useFeatureData<Milestone>("milestones/");
  const { data } = useWorkspace();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    await onSave({
      milestone: values.get("milestone")
        ? Number(values.get("milestone"))
        : null,
      dependency_ids: values.getAll("dependency"),
      version: task.version,
    });
  }
  return (
    <details className="detail-section">
      <summary>Milestone & dependencies</summary>
      {error && <p role="alert">{error}</p>}
      <form className="detail-form" onSubmit={submit} key={task.version}>
        <label>
          Milestone or sprint
          <select
            name="milestone"
            defaultValue={task.milestone || ""}
            disabled={busy || loading}
          >
            <option value="">Unscheduled</option>
            {items
              .filter((item) => item.project === task.project)
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.kind}: {item.title}
                </option>
              ))}
          </select>
        </label>
        <fieldset>
          <legend>Must finish before this task starts</legend>
          {data.tasks
            .filter(
              (item) =>
                item.projectId === task.project &&
                item.apiId &&
                item.apiId !== task.id,
            )
            .map((item) => (
              <label className="check-row" key={item.apiId}>
                <input
                  type="checkbox"
                  name="dependency"
                  value={item.apiId}
                  defaultChecked={task.dependency_ids.includes(item.apiId!)}
                  disabled={busy}
                />
                <span>
                  {item.id} · {item.title} · {item.status}
                </span>
              </label>
            ))}
        </fieldset>
        <p className="detail-hint">
          Dependencies must belong to this project and cannot form a cycle.
        </p>
        <button
          className="button primary"
          disabled={busy || loading || Boolean(error)}
        >
          Save planning
        </button>
      </form>
    </details>
  );
}
