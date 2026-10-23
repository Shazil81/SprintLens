import { useState } from "react";
import { Plus, Pencil, Users } from "lucide-react";
import type { Project } from "../api";
import { ProjectEditorDialog } from "./ProjectEditorDialog";
import { ProjectTeamDialog } from "./ProjectTeamDialog";
import { ArrowUpRight, Clock3 } from "lucide-react";
import { useWorkspace } from "../hooks/useWorkspace";
/** Renders project progress cards and links each card to its task filter. */
export function ProjectsView() {
  const { projects, scoped, go, setProjectFilter, user, loading } =
    useWorkspace();
  const [editor, setEditor] = useState<{ project?: Project } | null>(null);
  const [team, setTeam] = useState<Project | null>(null);
  const canManage = user.role !== "Developer";
  return (
    <section className="projects-section">
      {editor && (
        <ProjectEditorDialog
          project={editor.project}
          onClose={() => setEditor(null)}
        />
      )}
      {team && (
        <ProjectTeamDialog project={team} onClose={() => setTeam(null)} />
      )}
      <div className="section-title">
        <div>
          <h2>
            Projects in motion{" "}
            <span className="inline-count">{projects.length}</span>
          </h2>
          <p>From the big picture to the next small step.</p>
        </div>
      </div>
      {canManage && (
        <button
          className="button primary project-create"
          disabled={loading}
          onClick={() => setEditor({})}
        >
          <Plus size={16} />
          Create project
        </button>
      )}
      {!projects.length && !loading && (
        <div className="empty">
          No projects yet. Create a project to start planning work.
        </div>
      )}
      <div className="row g-3">
        {projects.map((p) => {
          const tasks = scoped.filter((t) => t.projectId === p.id);
          const completed = tasks.filter((t) => t.status === "Done").length;
          const percent = tasks.length
            ? Math.round((completed / tasks.length) * 100)
            : 0;
          const risk = tasks.some((t) => t.status === "Blocked");
          return (
            <div className="col-md-4" key={p.code}>
              <button
                className="project-card"
                onClick={() => {
                  go("Tasks");
                  setProjectFilter(String(p.id));
                }}
              >
                <div className="project-top">
                  <span className={`project-symbol ${p.color}`}>{p.code}</span>
                  <span className={`badge ${risk ? "risk" : "healthy"}`}>
                    {risk ? "Needs attention" : "No open blockers"}
                  </span>
                </div>
                <h3>
                  {p.name}
                  <ArrowUpRight size={17} />
                </h3>
                <p>{p.description}</p>
                <div className="progress-label">
                  <span>
                    {completed} of {tasks.length} tasks complete
                  </span>
                  <b>{percent}%</b>
                </div>
                <div className="progress-track">
                  <span style={{ width: `${percent}%` }} />
                </div>
                <div className="project-footer">
                  <span>
                    <Clock3 size={13} />
                    Due{" "}
                    {new Date(p.due + "T12:00:00").toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                  <span>{p.member_ids.length} members</span>
                </div>
              </button>
              {canManage && (
                <div className="project-manage-actions">
                  <button
                    className="text-button"
                    onClick={() => setEditor({ project: p })}
                  >
                    <Pencil size={13} />
                    Edit project
                  </button>
                  <button className="text-button" onClick={() => setTeam(p)}>
                    <Users size={13} />
                    Manage team
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
