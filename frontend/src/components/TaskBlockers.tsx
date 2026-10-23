import { useState, type FormEvent } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { Blocker, Member, User } from "../api";

type Props = {
  blockers: Blocker[];
  user: User;
  assignee: number;
  isManager: boolean;
  canReport: boolean;
  completed: boolean;
  members: Member[];
  busy: boolean;
  onReport: (body: object) => Promise<boolean>;
  onResolve: (id: number, resolution: string) => Promise<boolean>;
};

/** Resolves one blocker with a written explanation while preserving its history. */
function ResolutionForm({
  busy,
  onResolve,
}: {
  busy: boolean;
  onResolve: (resolution: string) => Promise<boolean>;
}) {
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (await onResolve(String(new FormData(form).get("resolution")).trim()))
      form.reset();
  }
  return (
    <form className="resolution-form" onSubmit={submit}>
      <label>
        Resolution note
        <textarea
          name="resolution"
          required
          maxLength={2000}
          placeholder="How was this blocker resolved?"
          disabled={busy}
        />
      </label>
      <button className="button secondary" disabled={busy}>
        <CheckCircle2 size={14} />
        Resolve blocker
      </button>
    </form>
  );
}

/** Lists blocker ownership, age, and resolutions without hiding resolved records. */
export function TaskBlockers({
  blockers,
  user,
  assignee,
  isManager,
  canReport,
  completed,
  members,
  busy,
  onReport,
  onResolve,
}: Props) {
  const [showForm, setShowForm] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    if (
      await onReport({
        reason: String(values.get("reason")).trim(),
        owner: isManager ? Number(values.get("owner")) : user.membership_id,
      })
    ) {
      form.reset();
      setShowForm(false);
    }
  }
  return (
    <section className="detail-section">
      <div className="detail-section-heading">
        <h3>
          <AlertTriangle size={18} />
          Blockers{" "}
          <span className="inline-count">
            {blockers.filter((item) => !item.resolved_at).length} open
          </span>
        </h3>
        {canReport && !completed && (
          <button
            className="text-button"
            onClick={() => setShowForm(!showForm)}
            disabled={busy}
          >
            {showForm ? "Cancel" : "+ Report blocker"}
          </button>
        )}
      </div>
      {showForm && (
        <form className="detail-form blocker-form" onSubmit={submit}>
          <label>
            Blocker reason
            <textarea
              name="reason"
              required
              maxLength={2000}
              placeholder="What is stopping progress?"
              disabled={busy}
            />
          </label>
          {isManager && (
            <label>
              Blocker owner
              <select name="owner" defaultValue={assignee} disabled={busy}>
                {members.map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <p className="detail-hint">
            Reporting a blocker marks this task as Blocked. Resolve all open
            blockers before moving it forward.
          </p>
          <button className="button primary" disabled={busy}>
            Save blocker
          </button>
        </form>
      )}
      {!blockers.length && (
        <p className="detail-empty">
          No recorded blockers. Keep dependencies visible as they arise.
        </p>
      )}
      {blockers.map((blocker) => {
        const canResolve =
          isManager ||
          blocker.owner === user.membership_id ||
          assignee === user.membership_id ||
          blocker.reporter_user_id === user.id;
        return (
          <article
            className={`blocker-item ${blocker.resolved_at ? "resolved" : ""}`}
            key={blocker.id}
          >
            <div className="discussion-meta">
              <span
                className={`note-kind ${blocker.resolved_at ? "" : "blocker-label"}`}
              >
                {blocker.resolved_at ? "Resolved" : "Open"}
              </span>
              <time>
                Opened {new Date(blocker.opened_at).toLocaleString("en-US")}
              </time>
            </div>
            <p>{blocker.reason}</p>
            <small>
              Owner: {blocker.owner_name} · Reported by {blocker.reporter}
            </small>
            {blocker.resolved_at ? (
              <div className="resolution-note">
                <b>Resolution</b>
                <p>{blocker.resolution}</p>
                <small>
                  {blocker.resolved_by} ·{" "}
                  {new Date(blocker.resolved_at).toLocaleString("en-US")}
                </small>
              </div>
            ) : (
              canResolve && (
                <ResolutionForm
                  busy={busy}
                  onResolve={(text) => onResolve(blocker.id, text)}
                />
              )
            )}
          </article>
        );
      })}
    </section>
  );
}
