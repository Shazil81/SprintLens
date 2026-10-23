import { useState, type FormEvent } from "react";
import type { Review } from "../../api";
import { useWorkspace } from "../../hooks/useWorkspace";
import { useFeatureData } from "../../hooks/useFeatureData";
import { ReviewForm } from "./ReviewForm";
import { FeatureState } from "./FeatureState";
import { EvaluationSummary } from "./EvaluationSummary";

/** Drafts are private to their author; published reviews support permanent developer responses. */
export function ReviewsView() {
  const resource = useFeatureData<Review>("reviews/");
  const { user, projects, go } = useWorkspace();
  const [form, setForm] = useState<Review | "new" | null>(null);
  const canCreate =
    user.role !== "Developer" &&
    projects.some((p) => p.reviewer_ids.includes(user.membership_id));
  async function response(event: FormEvent<HTMLFormElement>, review: Review) {
    event.preventDefault();
    const element = event.currentTarget;
    if (
      await resource.mutate(`reviews/${review.id}/respond/`, "POST", {
        body: new FormData(element).get("body"),
      })
    )
      element.reset();
  }
  return (
    <section className="feature-screen">
      <div className="section-title">
        <div>
          <h2>Two-way performance reviews</h2>
          <p>Private drafts. Contextual feedback. A voice for the developer.</p>
        </div>
        {canCreate && (
          <button className="button primary" onClick={() => setForm("new")}>
            Create review
          </button>
        )}
      </div>
      <FeatureState loading={resource.loading} error={resource.error} />
      {form && (
        <article className="feature-card">
          <h3>{form === "new" ? "New review" : "Edit draft"}</h3>
          <ReviewForm
            key={form === "new" ? "new" : `${form.id}:${form.version}`}
            initial={form === "new" ? undefined : form}
            busy={resource.busy}
            onCancel={() => setForm(null)}
            onSave={async (body) => {
              const saved = await resource.mutate(
                form === "new" ? "reviews/" : `reviews/${form.id}/`,
                form === "new" ? "POST" : "PATCH",
                body,
              );
              if (saved) setForm(null);
              return saved;
            }}
          />
        </article>
      )}
      {!resource.loading && !resource.items.length && (
        <p className="detail-empty">
          No reviews available. Unpublished drafts are visible only to their
          author.
        </p>
      )}
      {resource.items.map((review) => (
        <article className="feature-card" key={review.id}>
          <div className="eyebrow">
            {review.status} · {review.period_start} → {review.period_end}
          </div>
          <h3>{review.cycle}</h3>
          <p>
            {review.subject_name} · Reviewed by {review.reviewer_name}
          </p>
          {(
            [
              ["strengths", "Strengths"],
              ["improvements", "Improvement opportunities"],
              ["collaboration", "Collaboration"],
              ["delivery_context", "Delivery context"],
            ] as const
          ).map(([key, label]) => (
            <div className="review-dimension" key={key}>
              <b>{label}</b>
              <p>{review[key]}</p>
            </div>
          ))}
          <EvaluationSummary assessment={review.assessment} />
          {review.status === "Draft" &&
            review.reviewer === user.membership_id && (
              <div className="feature-actions">
                <button
                  className="button secondary"
                  onClick={() => go("Evaluation")}
                >
                  Add evidence assessment
                </button>
                <button
                  className="button secondary"
                  onClick={() => setForm(review)}
                >
                  Edit draft
                </button>
                <button
                  className="button primary"
                  disabled={resource.busy}
                  onClick={() =>
                    resource.mutate(`reviews/${review.id}/publish/`, "POST", {
                      version: review.version,
                    })
                  }
                >
                  Publish review
                </button>
                <small>
                  Publishing makes this review visible to its subject and locks
                  its text.
                </small>
              </div>
            )}
          {review.responses.map((item) => (
            <blockquote className="response-note" key={item.id}>
              <b>{item.author_name}</b>
              <p>{item.body}</p>
              <small>{new Date(item.created_at).toLocaleString("en-US")}</small>
            </blockquote>
          ))}
          {review.status !== "Draft" &&
            review.subject === user.membership_id && (
              <form
                className="feature-form"
                onSubmit={(event) => response(event, review)}
              >
                <label>
                  Your perspective
                  <textarea
                    name="body"
                    required
                    maxLength={4000}
                    placeholder="Share your context, agreement, questions, or blockers."
                  />
                </label>
                <button className="button primary" disabled={resource.busy}>
                  Add response
                </button>
              </form>
            )}
        </article>
      ))}
    </section>
  );
}
