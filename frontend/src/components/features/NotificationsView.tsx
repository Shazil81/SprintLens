import { useEffect } from "react";
import type { InboxItem } from "../../api";
import { useFeatureData } from "../../hooks/useFeatureData";
import { FeatureState } from "./FeatureState";

/** Polls a private durable inbox; Celery generates alerts independently of the browser. */
export function NotificationsView() {
  const resource = useFeatureData<InboxItem>("notifications/");
  useEffect(() => {
    const timer = window.setInterval(
      () => resource.load().catch((e) => resource.setError(e.message)),
      30000,
    );
    return () => window.clearInterval(timer);
  }, [resource.load]);
  return (
    <section className="feature-screen">
      <div className="section-title">
        <div>
          <h2>Your notifications</h2>
          <p>
            Deadline reminders, unresolved blockers, review requests and daily
            team summaries.
          </p>
        </div>
        <div className="feature-actions">
          <button
            className="button secondary"
            onClick={() =>
              resource.load().catch((e) => resource.setError(e.message))
            }
          >
            Refresh inbox
          </button>
          <button
            className="button primary"
            disabled={resource.busy}
            onClick={() =>
              resource.mutate("notifications/read_all/", "POST", {})
            }
          >
            Mark all as read
          </button>
        </div>
      </div>
      <FeatureState loading={resource.loading} error={resource.error} />
      <p className="detail-hint">
        Inbox refreshes every 30 seconds while open. Scheduled delivery requires
        the Redis broker, Celery worker and a single beat scheduler.
      </p>
      {!resource.loading && !resource.items.length && (
        <p className="detail-empty">
          You're all caught up. Notifications will appear when work needs your
          attention.
        </p>
      )}
      {resource.items.map((item) => (
        <article
          className={`feature-card ${item.read_at ? "" : "unread"}`}
          key={item.id}
        >
          <div className="eyebrow">
            {item.kind} · {item.read_at ? "Read" : "Unread"}
          </div>
          <h3>{item.title}</h3>
          <p>{item.body}</p>
          <small>{new Date(item.created_at).toLocaleString("en-US")}</small>
          {!item.read_at && (
            <button
              className="button secondary"
              disabled={resource.busy}
              onClick={() =>
                resource.mutate(`notifications/${item.id}/read/`, "POST", {})
              }
            >
              Mark as read
            </button>
          )}
        </article>
      ))}
    </section>
  );
}
