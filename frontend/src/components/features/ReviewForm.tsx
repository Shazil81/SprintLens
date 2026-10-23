import { useState, type FormEvent } from "react";
import type { Review } from "../../api";
import { useWorkspace } from "../../hooks/useWorkspace";

/** Captures narrative dimensions instead of using commit counts as a performance score. */
export function ReviewForm({
  initial,
  busy,
  onSave,
  onCancel,
}: {
  initial?: Review;
  busy: boolean;
  onSave: (body: object) => Promise<boolean>;
  onCancel: () => void;
}) {
  const { user, projects, members } = useWorkspace();
  const eligibleProjects = projects.filter((project) =>
    project.reviewer_ids.includes(user.membership_id),
  );
  const [project, setProject] = useState(
    initial?.project || eligibleProjects[0]?.id || 0,
  );
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    await onSave({
      cycle: values.get("cycle"),
      period_start: values.get("period_start"),
      period_end: values.get("period_end"),
      strengths: values.get("strengths"),
      improvements: values.get("improvements"),
      collaboration: values.get("collaboration"),
      delivery_context: values.get("delivery_context"),
      ...(initial
        ? { version: initial.version }
        : { project, subject: Number(values.get("subject")) }),
    });
  }
  return (
    <form className="feature-form" onSubmit={submit}>
      {!initial && (
        <>
          <label>
            Project
            <select
              value={project}
              onChange={(event) => setProject(Number(event.target.value))}
            >
              {eligibleProjects.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Developer / team member
            <select name="subject" required key={project}>
              <option value="">Choose a person</option>
              {members
                .filter(
                  (member) =>
                    member.id !== user.membership_id &&
                    projects
                      .find((p) => p.id === project)
                      ?.member_ids.includes(member.id),
                )
                .map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.name}
                  </option>
                ))}
            </select>
          </label>
        </>
      )}
      <label>
        Review cycle
        <input
          name="cycle"
          required
          maxLength={120}
          placeholder="October delivery review"
          defaultValue={initial?.cycle}
        />
      </label>
      <label>
        Period start
        <input
          type="date"
          name="period_start"
          required
          defaultValue={initial?.period_start}
        />
      </label>
      <label>
        Period end
        <input
          type="date"
          name="period_end"
          required
          defaultValue={initial?.period_end}
        />
      </label>
      {(
        [
          ["strengths", "Strengths & evidence"],
          ["improvements", "Improvement opportunities"],
          ["collaboration", "Collaboration & support"],
          ["delivery_context", "Delivery, complexity & blocker context"],
        ] as const
      ).map(([key, label]) => (
        <label key={key}>
          {label}
          <textarea
            name={key}
            required
            maxLength={4000}
            defaultValue={initial?.[key]}
          />
        </label>
      ))}
      <div className="feature-actions">
        <button className="button primary" disabled={busy || !project}>
          Save private draft
        </button>
        <button type="button" className="button secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
