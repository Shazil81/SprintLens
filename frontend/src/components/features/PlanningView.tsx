import { useState, type FormEvent } from "react";
import type { Milestone } from "../../api";
import { useFeatureData } from "../../hooks/useFeatureData";
import { useWorkspace } from "../../hooks/useWorkspace";
import { FeatureState } from "./FeatureState";

/** Plans date-bounded sprints and milestones and shows completion from linked tasks. */
export function PlanningView() {
  const resource = useFeatureData<Milestone>("milestones/");
  const { projects, user, data, setDetailTaskId } = useWorkspace();
  const [editing, setEditing] = useState<Milestone | null>(null);
  const canManage = user.role !== "Developer";
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const body = {
      title: values.get("title"),
      kind: values.get("kind"),
      start: values.get("start"),
      due: values.get("due"),
      ...(editing
        ? { version: editing.version }
        : { project: Number(values.get("project")) }),
    };
    if (
      await resource.mutate(
        editing ? `milestones/${editing.id}/` : "milestones/",
        editing ? "PATCH" : "POST",
        body,
      )
    ) {
      setEditing(null);
      form.reset();
    }
  }
  return (
    <section className="feature-screen">
      <div className="section-title">
        <div>
          <h2>Sprints & milestones</h2>
          <p>Plan outcomes, then connect tasks from their details.</p>
        </div>
        <button
          className="button secondary"
          onClick={() =>
            resource.load().catch((e) => resource.setError(e.message))
          }
        >
          Refresh planning
        </button>
      </div>
      <FeatureState loading={resource.loading} error={resource.error} />
      {canManage && (
        <details
          className="feature-card"
          open={Boolean(editing)}
          key={editing?.id || "new"}
        >
          <summary>
            {editing ? "Edit milestone" : "Create milestone or sprint"}
          </summary>
          <form className="feature-form" onSubmit={submit}>
            {!editing && (
              <label>
                Project
                <select name="project" required>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              Title
              <input
                name="title"
                maxLength={140}
                required
                defaultValue={editing?.title}
              />
            </label>
            <label>
              Type
              <select name="kind" defaultValue={editing?.kind || "Milestone"}>
                <option>Milestone</option>
                <option>Sprint</option>
              </select>
            </label>
            <label>
              Start date
              <input
                name="start"
                type="date"
                required
                defaultValue={editing?.start}
              />
            </label>
            <label>
              End date
              <input
                name="due"
                type="date"
                required
                defaultValue={editing?.due}
              />
            </label>
            <div className="feature-actions">
              <button
                className="button primary"
                disabled={resource.busy || !projects.length}
              >
                Save milestone
              </button>
              {editing && (
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setEditing(null)}
                >
                  Cancel edit
                </button>
              )}
            </div>
          </form>
        </details>
      )}
      {!resource.loading && !resource.items.length && (
        <p className="detail-empty">
          No milestones yet. Start with the next deliverable or sprint.
        </p>
      )}
      <div className="feature-grid">
        {resource.items.map((item) => (
          <article className="feature-card" key={item.id}>
            <div className="eyebrow">
              {projects.find((p) => p.id === item.project)?.name} · {item.kind}
            </div>
            <h3>{item.title}</h3>
            <p>
              {item.start} → {item.due}
            </p>
            <progress max={item.total || 1} value={item.completed} />
            <p>
              {item.completed} of {item.total} tasks completed
            </p>
            <div className="feature-links">
              {data.tasks
                .filter((task) => task.milestone === item.id)
                .map((task) => (
                  <button
                    key={task.apiId}
                    className="text-button"
                    onClick={() => setDetailTaskId(task.apiId!)}
                  >
                    {task.title} · {task.status}
                  </button>
                ))}
            </div>
            {canManage && (
              <button
                className="button secondary"
                onClick={() => setEditing(item)}
              >
                Edit milestone
              </button>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
