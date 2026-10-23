import type { GitActivity } from "../api";
import { useFeatureData } from "../hooks/useFeatureData";

/** Shows only signed repository events explicitly linked to this task code. */
export function TaskGitEvidence({ taskId }: { taskId: string }) {
  const resource = useFeatureData<GitActivity>(
    `github-activity/?task=${taskId}`,
  );
  return (
    <section className="detail-section">
      <h3>GitHub evidence</h3>
      {resource.error && <p role="alert">{resource.error}</p>}
      {resource.loading ? (
        <p>Loading evidence…</p>
      ) : !resource.items.length ? (
        <p className="detail-hint">
          No GitHub evidence linked yet. Reference this task code in a commit or
          pull request after connecting its repository.
        </p>
      ) : (
        resource.items.map((item) => (
          <div className="discussion-item" key={item.id}>
            <b>{item.title}</b>
            <p>
              {item.event} · {item.actor}
            </p>
            {item.url && (
              <a href={item.url} target="_blank" rel="noopener noreferrer">
                View on GitHub
              </a>
            )}
          </div>
        ))
      )}
    </section>
  );
}
