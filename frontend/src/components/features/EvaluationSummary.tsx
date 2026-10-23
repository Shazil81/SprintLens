import type { Assessment } from "../../types/insights";

/** Published reviews retain this snapshot even when the underlying task changes. */
export function EvaluationSummary({
  assessment,
}: {
  assessment: Assessment | null;
}) {
  if (!assessment)
    return <p className="detail-empty">No structured assessment attached.</p>;
  const { rubric, evidence_snapshot: snapshot } = assessment;
  return (
    <div className="evaluation-summary">
      <h4>Evidence-based assessment</h4>
      {["quality", "delivery", "collaboration"].map((d) => (
        <div className="review-dimension" key={d}>
          <b>
            {d[0].toUpperCase() + d.slice(1)} · {rubric[`${d}_rating`]}
          </b>
          <p>{rubric[`${d}_evidence`] || "No assessment evidence recorded."}</p>
        </div>
      ))}
      <p>
        <b>Complexity context:</b> {rubric.complexity_context}
      </p>
      <p>
        <b>Blocker context:</b> {rubric.blockers_context}
      </p>
      <small>
        Snapshot captured{" "}
        {new Date(snapshot.captured_at).toLocaleString("en-US")}. Task metadata
        is as of capture; evidence links and blocker time use{" "}
        {snapshot.period_start} → {snapshot.period_end}.
      </small>
      {snapshot.tasks.map((task) => (
        <details key={task.id} className="evidence-task">
          <summary>
            {task.code} · {task.title}
          </summary>
          <p>
            {task.assignee} · {task.status} · Due {task.due}
          </p>
          <p>
            Complexity: {task.complexity} ·{" "}
            {task.complexity_context || "No estimate explanation"}
          </p>
          <p>
            Acceptance criteria: {task.acceptance_criteria || "Not recorded"}
          </p>
          <p>Blocked in period: {task.blocked_hours_in_period} hours</p>
          {task.links.map((link, i) => (
            <p key={i}>
              {/^https?:\/\//i.test(link.url) ? (
                <a href={link.url} target="_blank" rel="noreferrer">
                  {link.source}
                </a>
              ) : (
                link.source
              )}{" "}
              · {new Date(link.at).toLocaleDateString("en-US")}
            </p>
          ))}
        </details>
      ))}
    </div>
  );
}
