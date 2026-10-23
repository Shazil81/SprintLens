import type { Review } from "../../api";
import { useWorkspace } from "../../hooks/useWorkspace";
import { useFeatureData } from "../../hooks/useFeatureData";
import { FeatureState } from "./FeatureState";
import { EvaluationForm } from "./EvaluationForm";
import { EvaluationSummary } from "./EvaluationSummary";

/** Use the existing private review resource instead of introducing a public employee scorecard. */
export function EvaluationView() {
  const resource = useFeatureData<Review>("reviews/");
  const { user, projects, go } = useWorkspace();
  return (
    <section className="feature-screen">
      <div className="section-title">
        <div>
          <h2>Fair performance evaluation</h2>
          <p>
            Quality, delivery and collaboration, explained through evidence and
            context.
          </p>
        </div>
        <button className="button secondary" onClick={() => go("Reviews")}>
          Open reviews & responses
        </button>
      </div>
      <article className="feature-card">
        <p>
          Assigned reviewers assess their own private drafts. Developers see
          their published assessments and can respond in Reviews. Missing
          evidence stays “Not assessed”; task volume, hours and commits never
          produce a score.
        </p>
      </article>
      <FeatureState loading={resource.loading} error={resource.error} />
      {!resource.loading && !resource.items.length && (
        <p className="detail-empty">
          No accessible reviews. An assigned reviewer can create a draft in
          Reviews first.
        </p>
      )}
      {resource.items.map((review) => (
        <article className="feature-card" key={review.id}>
          <div className="eyebrow">
            {review.status} · {review.period_start} → {review.period_end}
          </div>
          <h3>{review.cycle}</h3>
          <p>
            {review.subject_name} · Reviewer: {review.reviewer_name}
          </p>
          <EvaluationSummary assessment={review.assessment} />
          {review.status === "Draft" &&
            review.reviewer === user.membership_id &&
            user.role !== "Developer" &&
            projects
              .find((p) => p.id === review.project)
              ?.reviewer_ids.includes(user.membership_id) && (
              <details>
                <summary>Edit assessment</summary>
                <EvaluationForm
                  key={`${review.id}:${review.version}`}
                  review={review}
                  busy={resource.busy}
                  onSave={(body) =>
                    resource.mutate(
                      `reviews/${review.id}/assessment/`,
                      "PUT",
                      body,
                    )
                  }
                />
              </details>
            )}
        </article>
      ))}
    </section>
  );
}
