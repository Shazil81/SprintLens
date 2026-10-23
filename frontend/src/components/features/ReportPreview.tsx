import type { ProjectReport } from "../../types/reports";

/** This client-facing preview contains project delivery facts and manually curated narrative. */
export function ReportPreview({ report }: { report: ProjectReport }) {
  const { snapshot } = report;
  return (
    <div className="report-preview">
      <div className="eyebrow">
        {report.status} · Version {report.version}
      </div>
      <h3>{report.title}</h3>
      <p>
        {snapshot.project.name} · Captured{" "}
        {new Date(snapshot.captured_at).toLocaleString("en-US")}
      </p>
      <p>
        Observed history: {snapshot.period.start} → {snapshot.period.end}.
        Current task state is as of capture.
      </p>
      <div className="report-counts">
        <span>{snapshot.current.open} open</span>
        <span>{snapshot.current.done} currently done</span>
        <span>{snapshot.current.blocked} blocked</span>
        <span>{snapshot.current.overdue} overdue</span>
      </div>
      {(
        [
          ["summary", "Summary"],
          ["achievements", "Achievements"],
          ["risks", "Risks and dependencies"],
          ["next_steps", "Next steps"],
        ] as const
      ).map(([key, label]) => (
        <section className="review-dimension" key={key}>
          <b>{label}</b>
          <p>{report[key] || "Not recorded."}</p>
        </section>
      ))}
      <p>
        Observed completions: {snapshot.observed.completion_events} events
        across {snapshot.observed.unique_completed_tasks} tasks. GitHub activity
        records: {snapshot.observed.github_activities}.
      </p>
      <details>
        <summary>Captured task evidence ({snapshot.tasks.length} rows)</summary>
        <div className="insight-table-wrap">
          <table className="insight-table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Task</th>
                <th>Status</th>
                <th>Due</th>
                <th>Signals</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.tasks.map((task) => (
                <tr key={task.code}>
                  <td>{task.code}</td>
                  <td>{task.title}</td>
                  <td>{task.status}</td>
                  <td>{task.due}</td>
                  <td>{task.signals.join(" · ") || "None recorded"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>Omitted rows: {snapshot.omitted_tasks}</p>
      </details>
      <details>
        <summary>Data limitations</summary>
        {snapshot.limitations.map((text) => (
          <p key={text}>{text}</p>
        ))}
      </details>
    </div>
  );
}
