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
  const { week, selectedDay, setSelectedDay, scoped, go, setQuery, data } =
    useWorkspace();
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
          {scoped
            .filter((t) => t.due === selectedDay)
            .map((t) => (
              <button
                key={t.id}
                className="deadline"
                onClick={() => {
                  go("Tasks");
                  setQuery(t.id);
                }}
              >
                <span className={"deadline-line " + slug(t.status)} />
                <div>
                  <b>{t.title}</b>
                  <small>
                    {t.project} · {t.status}
                  </small>
                </div>
                <span className="avatar small">{initials(t.assignee)}</span>
                <ArrowUpRight size={16} />
              </button>
            ))}
          {!scoped.some((t) => t.due === selectedDay) && (
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
        {data.audit.slice(0, 3).map((event) => (
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
        <div className="activity-note">
          <ShieldCheck size={16} />
          <span>Clear ownership. A record of every change.</span>
        </div>
      </section>
    </div>
  );
}
