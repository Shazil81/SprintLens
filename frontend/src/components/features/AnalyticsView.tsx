import { useState } from "react";
import { useWorkspace } from "../../hooks/useWorkspace";
import { useAnalytics } from "../../hooks/useAnalytics";
import { FeatureState } from "./FeatureState";
import { DeliveryTrend } from "./DeliveryTrend";

/** Explain rule-based risks without attributing delays to employee performance. */
export function AnalyticsView() {
  const { projects, setDetailTaskId } = useWorkspace();
  const [project, setProject] = useState("");
  const [days, setDays] = useState("30");
  const resource = useAnalytics(project, days);
  const data = resource.data;
  return (
    <section className="feature-screen">
      <div className="section-title">
        <div>
          <h2>Delivery analytics & early risks</h2>
          <p>
            Current workload and observed history, with reasons behind every
            signal.
          </p>
        </div>
        <button className="button secondary" onClick={resource.refresh}>
          Refresh analytics
        </button>
      </div>
      <div className="insight-filters">
        <label>
          Project
          <select value={project} onChange={(e) => setProject(e.target.value)}>
            <option value="">All accessible projects</option>
            {projects.map((p) => (
              <option value={p.id} key={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          History window
          <select value={days} onChange={(e) => setDays(e.target.value)}>
            {["7", "30", "90"].map((v) => (
              <option key={v} value={v}>
                Last {v} days
              </option>
            ))}
          </select>
        </label>
      </div>
      <FeatureState loading={resource.loading} error={resource.error} />
      {data && (
        <>
          <div className="insight-metrics">
            {[
              ["Open tasks", data.snapshot.open],
              ["Completed now", data.snapshot.done],
              ["Overdue now", data.snapshot.overdue],
              ["Risk signals", data.risk_total],
            ].map(([label, value]) => (
              <article className="feature-card" key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </article>
            ))}
          </div>
          <DeliveryTrend data={data} />
          <div className="feature-grid">
            {data.projects.map((p) => (
              <article className="feature-card" key={p.id}>
                <div className="eyebrow">
                  {p.status}
                  {p.past_deadline ? " · Project deadline passed" : ""}
                </div>
                <h3>{p.name}</h3>
                <progress max={Math.max(1, p.total)} value={p.done} />
                <p>
                  {p.done} / {p.total} tasks done · {p.risk_count} tasks with
                  signals · Due {p.due}
                </p>
              </article>
            ))}
          </div>
          <article className="feature-card">
            <h3>Current workload</h3>
            <p>
              Alphabetical view. Task counts and complexity are context, not
              productivity scores. Developers see only their own named workload.
            </p>
            <div className="insight-table-wrap">
              <table className="insight-table">
                <thead>
                  <tr>
                    <th>Member</th>
                    <th>Open</th>
                    <th>Overdue</th>
                    <th>Blocked</th>
                    <th>Complexity mix</th>
                  </tr>
                </thead>
                <tbody>
                  {data.workload.map((row) => (
                    <tr key={row.member_id}>
                      <td>{row.name}</td>
                      <td>{row.open}</td>
                      <td>{row.overdue}</td>
                      <td>{row.blocked}</td>
                      <td>
                        {Object.entries(row.complexity)
                          .map(([key, value]) => `${key}: ${value}`)
                          .join(" · ") || "No open tasks"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
          <article className="feature-card">
            <h3>Tasks needing attention</h3>
            <p>
              Showing {data.risks.length} of {data.risk_total} tasks. Signals
              guide a conversation; they are not deadline predictions.
            </p>
            {!data.risks.length && <p>No active task signals.</p>}
            {data.risks.map((row) => (
              <div className="risk-row" key={row.task_id}>
                <div className="eyebrow">
                  {row.severity} · {row.project} · Due {row.due}
                </div>
                <button
                  className="insight-link"
                  onClick={() => setDetailTaskId(row.task_id)}
                >
                  {row.code} · {row.title}
                </button>
                <p>{row.assignee}</p>
                <ul>
                  {row.signals.map((signal) => (
                    <li key={signal}>{signal}</li>
                  ))}
                </ul>
              </div>
            ))}
          </article>
          <div className="feature-grid">
            <article className="feature-card">
              <h3>Milestone watch</h3>
              {!data.milestones.length && (
                <p>
                  No unfinished milestones due within seven days or overdue.
                </p>
              )}
              {data.milestones.map((m) => (
                <p key={m.id}>
                  <b>{m.title}</b> · {m.project} · {m.due} · {m.open_tasks} open{" "}
                  {m.overdue && "· Overdue"}
                </p>
              ))}
            </article>
            <article className="feature-card">
              <h3>Repeated blocker descriptions</h3>
              <p>
                Exact normalized descriptions within each project; no semantic
                AI matching.
              </p>
              {!data.recurring_blockers.length && (
                <p>No repeated descriptions in this window.</p>
              )}
              {data.recurring_blockers.map((b, i) => (
                <p key={i}>
                  {projects.find((p) => p.id === b.project_id)?.name}:{" "}
                  <b>{b.description}</b> · {b.task_count} tasks
                </p>
              ))}
            </article>
          </div>
          <article className="feature-card">
            <h3>How to read this page</h3>
            {data.notes.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </article>
        </>
      )}
    </section>
  );
}
