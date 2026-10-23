import { useState, type FormEvent } from "react";
import { ExternalLink, MessageSquare, Send } from "lucide-react";
import type { WorkUpdate } from "../api";

type Props = {
  updates: WorkUpdate[];
  canUpdate: boolean;
  canFeedback: boolean;
  busy: boolean;
  onSubmit: (body: object) => Promise<boolean>;
};

/** Shows a permanent task discussion and submits progress or manager feedback. */
export function TaskDiscussion({
  updates,
  canUpdate,
  canFeedback,
  busy,
  onSubmit,
}: Props) {
  const [kind, setKind] = useState("Update");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    if (
      await onSubmit({
        kind: canFeedback && !canUpdate ? "Feedback" : kind,
        body: String(values.get("body")).trim(),
        evidence_url: String(values.get("evidence_url") || ""),
      })
    )
      form.reset();
  }
  return (
    <section className="detail-section">
      <h3>
        <MessageSquare size={18} />
        Work updates & feedback
      </h3>
      {!canUpdate && !canFeedback && <p className="detail-hint">Only the assignee can post progress updates. Task feedback is limited to assigned project reviewers.</p>}
      {(canUpdate || canFeedback) && (
        <form className="detail-form" onSubmit={submit}>
          {canUpdate && canFeedback ? (
            <label>
              Note type
              <select
                value={kind}
                onChange={(e) => setKind(e.target.value)}
                disabled={busy}
              >
                <option>Update</option>
                <option>Feedback</option>
              </select>
            </label>
          ) : (
            <p className="detail-hint">
              {canFeedback
                ? "Share clear, actionable feedback with the assignee."
                : "Share progress, evidence, or your response to manager feedback."}
            </p>
          )}
          <label>
            {canFeedback && (!canUpdate || kind === "Feedback")
              ? "Feedback"
              : "Progress update"}
            <textarea
              name="body"
              required
              maxLength={4000}
              placeholder="What changed? What comes next?"
              disabled={busy}
            />
          </label>
          <label>
            Evidence link <span className="optional">(optional)</span>
            <input
              type="url"
              name="evidence_url"
              maxLength={1000}
              placeholder="https://github.com/your-team/project/pull/42"
              disabled={busy}
            />
          </label>
          <button className="button primary" disabled={busy}>
            <Send size={14} />
            {busy ? "Saving…" : "Post note"}
          </button>
        </form>
      )}
      <div className="discussion-feed">
        {!updates.length && (
          <p className="detail-empty">
            No updates yet. Start with a short progress note.
          </p>
        )}
        {updates.map((update) => (
          <article className="discussion-item" key={update.id}>
            <div className="discussion-meta">
              <b>{update.author}</b>
              <span
                className={`note-kind ${update.kind === "Feedback" ? "feedback" : ""}`}
              >
                {update.kind}
              </span>
              <time>{new Date(update.created_at).toLocaleString("en-US")}</time>
            </div>
            <p>{update.body}</p>
            {update.evidence_url && (
              <a
                href={update.evidence_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                View evidence <ExternalLink size={12} />
              </a>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
