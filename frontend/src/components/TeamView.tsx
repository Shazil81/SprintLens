import { useState } from "react";
import { ArrowRight, UserPlus, ShieldCheck } from "lucide-react";
import { initials } from "../utils/workspace";
import { useWorkspace } from "../hooks/useWorkspace";
import type { Member } from "../api";
import { MemberCreateDialog } from "./MemberCreateDialog";
import { RoleEditorDialog } from "./RoleEditorDialog";

/** Displays workspace people; account creation and role controls are admin-only. */
export function TeamView() {
  const { data, members, go, setQuery, user, loading } = useWorkspace();
  const [creating, setCreating] = useState(false);
  const [editingRole, setEditingRole] = useState<Member | null>(null);
  const isAdmin = user.role === "Admin";
  return (
    <section>
      <div className="section-title">
        <div>
          <h2>
            People & access{" "}
            <span className="inline-count">{members.length}</span>
          </h2>
          <p>
            {user.role === "Developer"
              ? "People in the projects you can access."
              : "Your workspace directory. Project access is managed separately."}
          </p>
        </div>
        {isAdmin && (
          <button
            className="button primary"
            disabled={loading}
            onClick={() => setCreating(true)}
          >
            <UserPlus size={16} />
            Add member
          </button>
        )}
      </div>
      {!members.length && !loading && (
        <div className="empty">
          No team members are visible in your current projects.
        </div>
      )}
      <div className="team-grid">
        {members.map((member, i) => {
          const tasks = data.tasks.filter(
            (task) => task.assigneeId === member.id,
          );
          return (
            <div className="team-grid-item" key={member.id}>
              <article className="team-card">
                <span
                  className={`avatar large ${["green", "purple", "orange", "blue"][i % 4]}`}
                >
                  {initials(member.name)}
                </span>
                <h2>
                  {member.name}
                  {member.id === user.membership_id && (
                    <small className="you-label">You</small>
                  )}
                </h2>
                <p>{member.role}</p>
                <div className="team-metrics">
                  <span>
                    <b>
                      {tasks.filter((task) => task.status !== "Done").length}
                    </b>
                    Open tasks
                  </span>
                  <span>
                    <b>
                      {
                        tasks.filter((task) => task.status === "In review")
                          .length
                      }
                    </b>
                    In review
                  </span>
                  <span>
                    <b>
                      {tasks.filter((task) => task.status === "Blocked").length}
                    </b>
                    Blocked
                  </span>
                </div>
                <div className="member-card-actions">
                  <button
                    className="text-button"
                    onClick={() => {
                      go("Tasks");
                      setQuery(member.name);
                    }}
                  >
                    View tasks <ArrowRight size={16} />
                  </button>
                  {isAdmin && member.id !== user.membership_id && (
                    <button
                      className="text-button"
                      onClick={() => setEditingRole(member)}
                    >
                      <ShieldCheck size={14} />
                      Change role
                    </button>
                  )}
                </div>
              </article>
            </div>
          );
        })}
      </div>
      {creating && <MemberCreateDialog onClose={() => setCreating(false)} />}
      {editingRole && (
        <RoleEditorDialog
          member={editingRole}
          onClose={() => setEditingRole(null)}
        />
      )}
    </section>
  );
}
