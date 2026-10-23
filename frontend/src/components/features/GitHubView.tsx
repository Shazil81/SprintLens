import { useState, type FormEvent } from "react";
import { request, type GitActivity, type GitConnection } from "../../api";
import { useFeatureData } from "../../hooks/useFeatureData";
import { useWorkspace } from "../../hooks/useWorkspace";
import { FeatureState } from "./FeatureState";

/** Configures signed webhook ingestion and displays repository evidence without requesting a PAT. */
export function GitHubView() {
  const connections = useFeatureData<GitConnection>("github-connections/");
  const activities = useFeatureData<GitActivity>("github-activity/");
  const { user, projects, setDetailTaskId } = useWorkspace();
  const [setup, setSetup] = useState<{
    id: string;
    webhook_path: string;
    secret: string;
  } | null>(null);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    if (
      await connections.mutate("github-connections/", "POST", {
        project: Number(values.get("project")),
        repository: values.get("repository"),
      })
    )
      form.reset();
  }
  async function showSetup(id: string) {
    try {
      setSetup({
        id,
        ...(await request<{ webhook_path: string; secret: string }>(
          `github-connections/${id}/setup/`,
        )),
      });
    } catch (e) {
      connections.setError(
        e instanceof Error ? e.message : "Setup unavailable.",
      );
    }
  }
  return (
    <section className="feature-screen">
      <div className="section-title">
        <div>
          <h2>GitHub engineering activity</h2>
          <p>
            Commits, pull requests and code reviews as evidence—not performance
            scores.
          </p>
        </div>
        <button
          className="button secondary"
          onClick={() =>
            Promise.all([connections.load(), activities.load()]).catch((e) =>
              connections.setError(e.message),
            )
          }
        >
          Refresh GitHub activity
        </button>
      </div>
      <FeatureState
        loading={connections.loading || activities.loading}
        error={connections.error || activities.error}
      />
      {user.role === "Admin" && (
        <details className="feature-card">
          <summary>Connect a repository</summary>
          <form className="feature-form" onSubmit={create}>
            <label>
              Project
              <select name="project" required>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              GitHub repository
              <input
                name="repository"
                placeholder="owner/repository"
                required
                maxLength={200}
              />
            </label>
            <p className="detail-hint">
              This creates a webhook destination. Configure it in your GitHub
              repository to begin receiving events. No historical sync or GitHub
              login is implied.
            </p>
            <button
              className="button primary"
              disabled={connections.busy || !projects.length}
            >
              Add connection
            </button>
          </form>
        </details>
      )}
      <div className="feature-grid">
        {connections.items.map((connection) => (
          <article className="feature-card" key={connection.id}>
            <h3>{connection.repository}</h3>
            <p>{projects.find((p) => p.id === connection.project)?.name}</p>
            <span className="status">
              {!connection.enabled
                ? "Disabled"
                : connection.event_count
                  ? `${connection.event_count} events received`
                  : connection.delivery_count
                    ? "Webhook verified · awaiting repository activity"
                    : "Awaiting signed events"}
            </span>
            {connection.last_delivery_at && (
              <p className="detail-hint">
                Last valid delivery:{" "}
                {new Date(connection.last_delivery_at).toLocaleString("en-US")}
              </p>
            )}
            {user.role === "Admin" && (
              <div className="feature-actions">
                <button
                  className="button secondary"
                  onClick={() => showSetup(connection.id)}
                >
                  Webhook setup
                </button>
                <button
                  className="text-button"
                  disabled={connections.busy}
                  onClick={() =>
                    connections.mutate(
                      `github-connections/${connection.id}/toggle/`,
                      "POST",
                      { enabled: !connection.enabled },
                    )
                  }
                >
                  {connection.enabled
                    ? "Disable connection"
                    : "Enable connection"}
                </button>
              </div>
            )}
            {setup?.id === connection.id && (
              <div className="feature-form">
                <label>
                  Webhook path
                  <input readOnly value={setup.webhook_path} />
                </label>
                <label>
                  Webhook secret
                  <input
                    type="password"
                    readOnly
                    value={setup.secret}
                    autoComplete="off"
                  />
                </label>
                <p className="detail-hint">
                  Use your public HTTPS backend URL + this path, JSON content
                  type, and events: Pushes, Pull requests, Pull request reviews.
                  Keep SSL verification enabled. GitHub cannot deliver to
                  localhost. Copy the secret into GitHub's Secret field; it is
                  kept only in this page's memory.
                </p>
                <button
                  className="button secondary"
                  onClick={() => setSetup(null)}
                >
                  Hide setup
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
      {!connections.loading && !connections.items.length && (
        <p className="detail-empty">
          No repository connected. A workspace Admin can configure one.
        </p>
      )}
      <h3>Recent repository events</h3>
      <p className="detail-hint">
        Include the exact task code, such as CP-26B31428, in a commit message or
        PR title/body to link its evidence. Ambiguous references stay unlinked.
      </p>
      {!activities.loading && !activities.items.length && (
        <p className="detail-empty">No signed GitHub activity received yet.</p>
      )}
      {activities.items.map((item) => (
        <article className="feature-card" key={item.id}>
          <div className="eyebrow">
            {item.repository} · {item.event}
          </div>
          <h3>{item.title}</h3>
          <p>
            {item.actor} · Received {new Date(item.at).toLocaleString("en-US")}
          </p>
          <div className="feature-actions">
            {item.url && (
              <a href={item.url} target="_blank" rel="noopener noreferrer">
                View on GitHub
              </a>
            )}
            {item.task && (
              <button
                className="text-button"
                onClick={() => setDetailTaskId(item.task)}
              >
                Open linked task
              </button>
            )}
          </div>
        </article>
      ))}
    </section>
  );
}
