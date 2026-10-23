import { ArrowUpRight, CalendarDays, ListTodo } from "lucide-react";
import { statuses, type Status } from "../data";
import { slug, initials, transitionMap } from "../utils/workspace";
import { useWorkspace } from "../hooks/useWorkspace";
/** Displays tasks and permits only status options allowed by the current UI rules. */
export function TaskTable() {
  const { view, visible, busy, role, user, changeStatus, setDetailTaskId } =
    useWorkspace();
  return (
    <div className="table-wrap task-list-wrap">
      <table>
        <thead>
          <tr>
            <th>Task</th>
            <th>Project</th>
            <th>Assignee</th>
            <th>Status</th>
            <th>Due date</th>
            <th><span className="visually-hidden">Details</span></th>
          </tr>
        </thead>
        <tbody>
          {(view === "Overview" ? visible.slice(0, 4) : visible).map((t) => (
            <tr key={t.id}>
              <td>
                <span className="task-row-icon"><ListTodo size={19}/></span>
                <div className="task-row-copy"><small className="task-id">{t.id}</small>
                <button
                  className="task-title-button"
                  onClick={() => t.apiId && setDetailTaskId(t.apiId)}
                >
                  {t.title}
                </button>
                <span className={`priority ${slug(t.priority)}`}>
                  {t.priority} priority
                </span></div>
              </td>
              <td data-label="Project"><span className="task-project-chip">{t.project}</span></td>
              <td data-label="Assignee">
                <span className="person">
                  <span className="avatar small">{initials(t.assignee)}</span>
                  {t.assignee}
                </span>
              </td>
              <td data-label="Status">
                <select
                  aria-label={`Status for ${t.id}`}
                  className={`status ${slug(t.status)}`}
                  disabled={
                    busy ||
                    (role === "Developer" &&
                      t.assigneeId !== user.membership_id)
                  }
                  value={t.status}
                  onChange={(e) => changeStatus(t, e.target.value as Status)}
                >
                  {statuses.map((s) => (
                    <option
                      key={s}
                      disabled={
                        s !== t.status &&
                        (!transitionMap[t.status].includes(s) ||
                          (role === "Developer" &&
                            (s === "Done" || t.status === "Done")))
                      }
                    >
                      {s}
                    </option>
                  ))}
                </select>
              </td>
              <td className="date" data-label="Due"><CalendarDays size={14}/>
                {new Date(t.due + "T12:00:00").toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                })}
              </td>
              <td><button className="task-open-button" aria-label={`Open ${t.title}`} onClick={() => t.apiId && setDetailTaskId(t.apiId)}><ArrowUpRight size={18}/></button></td>
            </tr>
          ))}
        </tbody>
      </table>
      {!visible.length && (
        <div className="empty">
          No tasks match these filters. Try another search.
        </div>
      )}
    </div>
  );
}
