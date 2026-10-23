import { useState, type FormEvent } from "react";
import type { Goal } from "../../api";
import { useFeatureData } from "../../hooks/useFeatureData";
import { useWorkspace } from "../../hooks/useWorkspace";
import { FeatureState } from "./FeatureState";

/** Owners track learning progress; assigned project reviewers provide contextual coaching. */
export function GrowthView() {
  const resource = useFeatureData<Goal>("goals/");
  const { user, projects, members } = useWorkspace();
  const eligible = projects.filter((p) =>
    p.member_ids.includes(user.membership_id),
  );
  const [selectedProject, setProject] = useState(0);
  // Projects may finish loading after this screen first mounts.
  const project = eligible.some((p) => p.id === selectedProject)
    ? selectedProject
    : eligible[0]?.id || 0;
  const reviewer =
    user.role !== "Developer" &&
    projects
      .find((p) => p.id === project)
      ?.reviewer_ids.includes(user.membership_id);
  const owners = members.filter(
    (member) =>
      projects.find((p) => p.id === project)?.member_ids.includes(member.id) &&
      (reviewer || member.id === user.membership_id),
  );
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    if (
      await resource.mutate("goals/", "POST", {
        project,
        owner: Number(values.get("owner")),
        title: values.get("title"),
        skill: values.get("skill"),
        target_date: values.get("target_date"),
      })
    )
      form.reset();
  }
  async function edit(event: FormEvent<HTMLFormElement>, goal: Goal) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    await resource.mutate(`goals/${goal.id}/`, "PATCH", {
      title: values.get("title"),
      skill: values.get("skill"),
      target_date: values.get("target_date"),
      status: values.get("status"),
      version: goal.version,
    });
  }
  async function note(event: FormEvent<HTMLFormElement>, goal: Goal) {
    event.preventDefault();
    const form = event.currentTarget;
    if (
      await resource.mutate(`goals/${goal.id}/entries/`, "POST", {
        body: new FormData(form).get("body"),
      })
    )
      form.reset();
  }
  return (
    <section className="feature-screen">
      <div className="section-title">
        <div>
          <h2>Developer growth</h2>
          <p>
            Learning goals, visible milestones and a lasting coaching history.
          </p>
        </div>
      </div>
      <FeatureState loading={resource.loading} error={resource.error} />
      {eligible.length > 0 ? (
        <details className="feature-card">
          <summary>Create growth goal</summary>
          <form className="feature-form" onSubmit={create}>
            <label>
              Project
              <select
                value={project}
                onChange={(event) => setProject(Number(event.target.value))}
              >
                {eligible.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Goal owner
              <select
                name="owner"
                key={project}
                required
                defaultValue={user.membership_id}
              >
                {owners.map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Learning goal
              <input
                name="title"
                required
                maxLength={140}
                placeholder="Design reliable background jobs"
              />
            </label>
            <label>
              Skill
              <input
                name="skill"
                required
                maxLength={100}
                placeholder="Celery and distributed systems"
              />
            </label>
            <label>
              Target date
              <input name="target_date" type="date" required />
            </label>
            <button className="button primary" disabled={resource.busy}>
              Create goal
            </button>
          </form>
        </details>
      ) : (
        <p className="detail-hint">
          Join a project to create a personal learning goal.
        </p>
      )}
      {!resource.loading && !resource.items.length && (
        <p className="detail-empty">
          No growth goals available. Goals are visible to their owner and
          assigned project reviewers.
        </p>
      )}
      {resource.items.map((goal) => (
        <article className="feature-card" key={goal.id}>
          <div className="eyebrow">
            {goal.status} · {goal.owner_name}
          </div>
          <h3>{goal.title}</h3>
          <p>
            {goal.skill} · Target {goal.target_date}
          </p>
          <details>
            <summary>Edit goal & milestone status</summary>
            <form
              className="feature-form"
              key={goal.version}
              onSubmit={(event) => edit(event, goal)}
            >
              <label>
                Title
                <input
                  name="title"
                  required
                  maxLength={140}
                  defaultValue={goal.title}
                />
              </label>
              <label>
                Skill
                <input
                  name="skill"
                  required
                  maxLength={100}
                  defaultValue={goal.skill}
                />
              </label>
              <label>
                Target date
                <input
                  name="target_date"
                  type="date"
                  required
                  defaultValue={goal.target_date}
                />
              </label>
              <label>
                Status
                <select name="status" defaultValue={goal.status}>
                  <option>Planned</option>
                  <option>In progress</option>
                  <option>Achieved</option>
                </select>
              </label>
              <button className="button primary" disabled={resource.busy}>
                Save goal
              </button>
            </form>
          </details>
          {goal.entries.map((entry) => (
            <blockquote className="response-note" key={entry.id}>
              <b>
                {entry.author_name} · {entry.kind}
              </b>
              <p>{entry.body}</p>
              <small>
                {new Date(entry.created_at).toLocaleString("en-US")}
              </small>
            </blockquote>
          ))}
          <form
            className="feature-form"
            onSubmit={(event) => note(event, goal)}
          >
            <label>
              {goal.owner === user.membership_id
                ? "Progress or completed learning milestone"
                : "Coaching feedback"}
              <textarea name="body" required maxLength={4000} />
            </label>
            <button className="button secondary" disabled={resource.busy}>
              Add growth entry
            </button>
          </form>
        </article>
      ))}
    </section>
  );
}
