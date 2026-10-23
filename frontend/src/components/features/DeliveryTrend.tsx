import type { Analytics } from "../../types/insights";

/** A zero-based daily chart shows observed completion events, including re-completions. */
export function DeliveryTrend({ data }: { data: Analytics }) {
  const maximum = Math.max(1, ...data.trend.map((day) => day.completions));
  return (
    <article className="feature-card">
      <h3>Observed delivery</h3>
      <p>
        {data.period.start} → {data.period.end} ·{" "}
        {data.delivery.completion_events} completion events across{" "}
        {data.delivery.unique_completed_tasks} tasks
      </p>
      <svg
        className="delivery-chart"
        viewBox="0 0 800 150"
        role="img"
        aria-label={`Daily completion events from ${data.period.start} to ${data.period.end}. ${data.trend.map((day) => `${day.date}: ${day.completions}`).join("; ")}`}
      >
        <line x1="0" y1="130" x2="800" y2="130" stroke="#dce3ef" />
        {data.trend.map((day, i) => (
          <rect
            key={day.date}
            x={(i * 800) / data.trend.length + 2}
            y={130 - (day.completions / maximum) * 115}
            width={Math.max(2, 800 / data.trend.length - 4)}
            height={(day.completions / maximum) * 115}
            rx="3"
            fill="#3267df"
          >
            <title>
              {day.date}: {day.completions}
            </title>
          </rect>
        ))}
      </svg>
      <div className="feature-actions">
        <small>{data.period.start}</small>
        <small>{data.period.end}</small>
      </div>
      <p>
        Median observed start-to-accept:{" "}
        <b>
          {data.delivery.median_start_to_accept_hours === null
            ? "Not enough history"
            : `${data.delivery.median_start_to_accept_hours} hours`}
        </b>{" "}
        ({data.delivery.timed_events} timed events).
      </p>
      <p>
        {data.delivery.blocked_task_hours} blocked task-hours ·{" "}
        {data.delivery.linked_evidence_tasks} tasks with linked evidence.
        Parallel blockers on one task count once.
      </p>
    </article>
  );
}
