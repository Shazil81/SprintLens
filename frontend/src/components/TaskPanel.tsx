import { Plus, Search, ArrowRight } from "lucide-react";
import { statuses } from "../data";
import { TaskTable } from "./TaskTable";
import { useWorkspace } from "../hooks/useWorkspace";
/** Combines task filters, creation trigger, table, and the overview view-all link. */
export function TaskPanel() {
  const {
    role,
    creator,
    loading,
    projects,
    openTask,
    query,
    setQuery,
    projectFilter,
    setProjectFilter,
    filter,
    setFilter,
    view,
    go,
    visible,
  } = useWorkspace();
  return (
    <section className="task-panel task-workspace">
      <div className="section-title">
        <div>
          <span className="task-section-eyebrow">WORK IN MOTION</span>
          <h2>{role === "Developer" ? "My tasks" : "Team tasks"} <span className="task-total">{visible.length}</span></h2>
          <p>The next steps that move the work forward.</p>
        </div>
        {role === "Manager" && (
          <button
            className="button primary"
            ref={creator}
            disabled={loading || !projects.length}
            onClick={openTask}
          >
            <Plus size={17} />
            Create task
          </button>
        )}
      </div>
      <div className="filters">
        <label className="search">
          <Search size={17} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search tasks, people, or projects"
            aria-label="Search tasks"
          />
        </label>
        <select
          aria-label="Filter by project"
          value={projectFilter}
          onChange={(e) => setProjectFilter(e.target.value)}
        >
          <option>All projects</option>
          {projects.map((p) => (
            <option key={p.id} value={String(p.id)}>
              {p.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Filter by status"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option>All statuses</option>
          {statuses.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>
      <TaskTable />
      <div className="table-footer">
        {view === "Overview" ? (
          <button className="text-button" onClick={() => go("Tasks")}>
            View all {visible.length} tasks <ArrowRight size={14} />
          </button>
        ) : (
          <span>{visible.length} tasks</span>
        )}
        <span>Saved to server · Changes are audited</span>
      </div>
    </section>
  );
}
