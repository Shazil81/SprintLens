import type { ApiTask, Milestone } from "../api";
import { useFeatureData } from "../hooks/useFeatureData";
import { useWorkspace } from "../hooks/useWorkspace";

/** Makes scheduling and prerequisite status visible to developers as well as managers. */
export function TaskPlanningSummary({ task }: { task: ApiTask }) {
  const { data, setDetailTaskId } = useWorkspace();
  const resource = useFeatureData<Milestone>("milestones/");
  const milestone = resource.items.find((item) => item.id === task.milestone);
  const prerequisites = data.tasks.filter(
    (item) => item.apiId && task.dependency_ids.includes(item.apiId),
  );
  return (
    <section className="detail-section">
      <h3>Delivery plan</h3>
      <p>
        {milestone
          ? `${milestone.kind}: ${milestone.title} · ${milestone.due}`
          : task.milestone
            ? "Loading milestone…"
            : "No milestone assigned."}
      </p>
      {resource.error && <p role="alert">{resource.error}</p>}
      {prerequisites.length ? (
        <>
          <p className="detail-hint">
            Prerequisites must be complete before work can start.
          </p>
          <div className="feature-links">
            {prerequisites.map((item) => (
              <button
                className="text-button"
                key={item.apiId}
                onClick={() => setDetailTaskId(item.apiId!)}
              >
                {item.id} · {item.title} · {item.status}
              </button>
            ))}
          </div>
        </>
      ) : (
        <p className="detail-hint">No prerequisite tasks.</p>
      )}
    </section>
  );
}
