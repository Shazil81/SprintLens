import type { FormEvent } from "react";
import type { ApiTask } from "../api";
import { useWorkspace } from "../hooks/useWorkspace";

/** Edits task metadata using the current server version; project moves are deliberately unsupported. */
export function TaskEditForm({
  task,
  busy,
  onSave,
}: {
  task: ApiTask;
  busy: boolean;
  onSave: (body: object) => Promise<boolean>;
}) {
  const { members, projects } = useWorkspace();
  const eligible = members.filter((member) =>
    projects
      .find((project) => project.id === task.project)
      ?.member_ids.includes(member.id),
  );
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await onSave({
      title: data.get("title"),
      assignee: Number(data.get("assignee")),
      priority: data.get("priority"),
      due: data.get("due"),
      acceptance_criteria: data.get("acceptance_criteria"),
      complexity: data.get("complexity"),
      complexity_context: data.get("complexity_context"),
      version: task.version,
    });
  }
  return (
    <details className="detail-section">
      <summary>Edit task details</summary>
      <form className="detail-form" onSubmit={submit} key={task.version}>
        <label>
          Task title
          <input
            name="title"
            required
            maxLength={140}
            defaultValue={task.title}
            disabled={busy}
          />
        </label>
        <label>
          Assignee
          <select name="assignee" defaultValue={task.assignee} disabled={busy}>
            {eligible.map((member) => (
              <option key={member.id} value={member.id}>
                {member.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Priority
          <select name="priority" defaultValue={task.priority} disabled={busy}>
            {["Low", "Medium", "High"].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Due date
          <input
            name="due"
            type="date"
            required
            defaultValue={task.due}
            disabled={busy}
          />
        </label>
        <label>
          Acceptance criteria
          <textarea
            name="acceptance_criteria"
            maxLength={10000}
            defaultValue={task.acceptance_criteria}
            disabled={busy}
          />
        </label>
        <label>
          Complexity estimate
          <select
            name="complexity"
            defaultValue={task.complexity}
            disabled={busy}
          >
            {["Unestimated", "Small", "Medium", "Large"].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Complexity explanation
          <textarea
            name="complexity_context"
            maxLength={4000}
            defaultValue={task.complexity_context}
            disabled={busy}
            placeholder="Explain scope, uncertainty and dependencies. Required for an estimate."
          />
        </label>
        <button className="button primary" disabled={busy}>
          Save task changes
        </button>
      </form>
    </details>
  );
}
