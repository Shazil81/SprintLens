import { useFeatureData } from "../hooks/useFeatureData";
import { usePagedData } from "../hooks/usePagedData";
import type { ApiTask } from "../api";
import type { Audit } from "../data";
import {
  Clock3,
  ArrowUpRight,
  ShieldCheck,
  ArrowRight,
  Check,
} from "lucide-react";
import { dateKey, slug, initials } from "../utils/workspace";
import { useWorkspace } from "../hooks/useWorkspace";
/** Shows the next seven days of deadlines and recent server audit activity. */
export function OverviewPanels() {
  const { week, selectedDay, setSelectedDay, user, go, setQuery, revision, setDetailTaskId } =
    useWorkspace();
  const deadlines = usePagedData<ApiTask>(`tasks/?due=${selectedDay}&page_size=100${user.role === "Developer" ? "&mine=1" : ""}`, revision);
  const activity = usePagedData<Audit>("audit-events/?page_size=3", revision);
  return (
    <div className="lower-grid">
      <section className="schedule-panel">
        <div className="section-title">
          <h2>
            <Clock3 size={20} />
            Upcoming deadlines
          </h2>
          <span className="panel-caption">Next 7 days</span>
        </div>
        <div className="calendar-week">
          {week.map((day) => (
            <button
              key={dateKey(day)}
              className={selectedDay === dateKey(day) ? "selected" : ""}
              onClick={() => setSelectedDay(dateKey(day))}
            >
              <span>
                {day.toLocaleDateString("en-US", { weekday: "short" })}
              </span>
              <b>{day.getDate()}</b>
            </button>
          ))}
        </div>
        <div className="deadline-list">
          {deadlines.page?.results.map((t) => (
              <button
                key={t.id}
                className="deadline"
                onClick={() => {
                  setDetailTaskId(t.id);
                }}
              >
                <span className={"deadline-line " + slug(t.status)} />
                <div>
                  <b>{t.title}</b>
                  <small>
                    {t.project} · {t.status}
                  </small>
                </div>
                <span className="avatar small">{initials(t.assignee_name)}</span>
                <ArrowUpRight size={16} />
              </button>
            ))}
          {deadlines.loading && <p role="status" className="detail-empty">Loading deadlines…</p>}
          {deadlines.error && <p role="alert">{deadlines.error}</p>}
          {Boolean(deadlines.page?.next) && <button className="text-button" onClick={() => go("Tasks")}>See all assignments in Tasks</button>}
          {!deadlines.loading && !deadlines.error && !deadlines.page?.count && (
            <div className="empty">
              No deadlines on this day.
              <br />
              <small>A little space to focus.</small>
            </div>
          )}
        </div>
      </section>
      <section className="updates-panel">
        <div className="section-title">
          <h2>
            <ShieldCheck size={20} />
            Team activity
          </h2>
          <button className="text-button" onClick={() => go("Audit trail")}>
            View all <ArrowRight size={15} />
          </button>
        </div>
        {activity.page?.results.map((event) => (
          <div className="activity-entry" key={event.id}>
            <span className="activity-check">
              <Check size={14} />
            </span>
            <div>
              <b>{event.text}</b>
              <p>
                {event.actor} ·{" "}
                {new Date(event.at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                })}
              </p>
            </div>
          </div>
        ))}
        {activity.loading && <p role="status" className="detail-empty">Loading activity…</p>}
        {activity.error && <p role="alert">{activity.error}</p>}
        {!activity.loading && !activity.error && !activity.page?.count && <p className="detail-empty">No recorded activity yet.</p>}
        <div className="activity-note">
          <ShieldCheck size={16} />
          <span>Clear ownership. A record of every change.</span>
        </div>
      </section>
    </div>
  );
}
