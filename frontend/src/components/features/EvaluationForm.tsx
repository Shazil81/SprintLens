import type { FormEvent } from "react";
import type { Review } from "../../api";
import { useWorkspace } from "../../hooks/useWorkspace";

/** Manual judgments need a written reason and supporting task evidence on the server. */
export function EvaluationForm({
  review,
  busy,
  onSave,
}: {
  review: Review;
  busy: boolean;
  onSave: (body: object) => Promise<boolean>;
}) {
  const { data } = useWorkspace();
  const rubric = review.assessment?.rubric;
  const ids = review.assessment?.evidence_snapshot.tasks.map((t) => t.id) || [];
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    await onSave({
      ...Object.fromEntries(values),
      supporting_task_ids: values.getAll("supporting_task_ids"),
      version: review.version,
    });
  }
  return (
    <form className="feature-form" onSubmit={submit}>
      <fieldset disabled={busy}>
        <legend>Human assessment</legend>
        <p>
          Assess the subject's contribution explicitly. Project tasks can
          support collaboration; assignment or commit counts do not prove
          ownership or quality.
        </p>
        {["quality", "delivery", "collaboration"].map((d) => (
          <div key={d}>
            <label>
              {d[0].toUpperCase() + d.slice(1)} rating
              <select
                name={`${d}_rating`}
                defaultValue={rubric?.[`${d}_rating`] || "Not assessed"}
              >
                {[
                  "Not assessed",
                  "Needs support",
                  "Meets expectations",
                  "Exceeds expectations",
                ].map((level) => (
                  <option key={level}>{level}</option>
                ))}
              </select>
            </label>
            <label>
              {d[0].toUpperCase() + d.slice(1)} evidence
              <textarea
                name={`${d}_evidence`}
                maxLength={4000}
                defaultValue={rubric?.[`${d}_evidence`] || ""}
              />
            </label>
          </div>
        ))}
        <label>
          Complexity context
          <textarea
            required
            name="complexity_context"
            maxLength={4000}
            defaultValue={rubric?.complexity_context || ""}
            placeholder="Describe uncertainty, scope and technical difficulty."
          />
        </label>
        <label>
          Blocker context
          <textarea
            required
            name="blockers_context"
            maxLength={4000}
            defaultValue={rubric?.blockers_context || ""}
            placeholder="Explain dependencies, support and factors outside the developer's control."
          />
        </label>
        <fieldset className="evidence-choices">
          <legend>Supporting project tasks</legend>
          {data.tasks
            .filter((t) => t.projectId === review.project && t.apiId)
            .map((task) => (
              <label key={task.apiId}>
                <input
                  type="checkbox"
                  name="supporting_task_ids"
                  value={task.apiId}
                  defaultChecked={ids.includes(task.apiId || "")}
                />
                {task.id} · {task.title} · {task.assignee}
              </label>
            ))}
        </fieldset>
        <p>
          Saving refreshes the evidence snapshot. Publishing in Reviews locks
          it. No overall score or ranking is generated.
        </p>
        <button className="button primary">Save assessment snapshot</button>
      </fieldset>
    </form>
  );
}
