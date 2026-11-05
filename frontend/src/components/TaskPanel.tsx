import { useEffect, useState } from "react";
import type { ApiTask } from "../api";
import { usePagedData } from "../hooks/usePagedData";
import { PageControls } from "./PageControls";
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
    user,
    revision,
  } = useWorkspace();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState(query);
  useEffect(() => {
    const timeout = window.setTimeout(() => setSearch(query), 250);
    return () => window.clearTimeout(timeout);
  }, [query]);
  const params = new URLSearchParams({
    page: String(page),
    page_size: view === "Overview" ? "4" : "20",
  });
  if (role === "Developer") params.set("mine", "1");
  if (search) params.set("search", search);
  if (projectFilter !== "All projects") params.set("project", projectFilter);
  if (filter !== "All statuses") params.set("status", filter);
  useEffect(() => setPage(1), [search, projectFilter, filter, revision]);
  const resource = usePagedData<ApiTask>(`tasks/?${params}`, revision);
  const tasks = (resource.page?.results || []).map((task) => ({
    ...task,
    apiId: task.id,
    id: task.code,
    projectId: task.project,
    assigneeId: task.assignee,
    project: task.project_name,
    assignee: task.assignee_name,
    status: task.status as import("../data").Status,
  }));
  const total = resource.page?.count ?? 0;
  return (
    <section className="task-panel task-workspace">
      <div className="section-title">
        <div>
          <h2>
            {role === "Developer" ? "My tasks" : "Team tasks"}{" "}
            <span className="task-total">{resource.loading ? "…" : total}</span>
          </h2>

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

      {resource.error && (
        <p className="login-error" role="alert">
          {resource.error}
          <button
            className="text-button"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </p>
      )}

      {resource.loading ? (
        <p className="detail-empty" role="status">
          Loading tasks…
        </p>
      ) : (
        !resource.error && <TaskTable tasks={tasks} />
      )}

      {view === "Tasks" && (
        <PageControls
          page={page}
          previous={Boolean(resource.page?.previous)}
          next={Boolean(resource.page?.next)}
          disabled={resource.loading}
          onChange={setPage}
        />
      )}

      <div className="table-footer">
        {view === "Overview" ? (
          <button className="text-button" onClick={() => go("Tasks")}>
            View all {resource.loading ? "…" : total} tasks{" "}
            <ArrowRight size={14} />
          </button>
        ) : (
          <span>{resource.loading ? "…" : total} tasks</span>
        )}

        <span>Saved to server · Changes are audited</span>
      </div>
    </section>
  );
}
