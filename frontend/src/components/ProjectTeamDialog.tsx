import { closeDialogAnimated } from "../utils/dialogMotion";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { X, Users } from "lucide-react";
import type { Project } from "../api";
import { useWorkspace } from "../hooks/useWorkspace";
import { useManagementMutation } from "../hooks/useManagementMutation";

/** Replaces the project roster while protecting assignees and unresolved blocker owners. */
export function ProjectTeamDialog({
  project,
  onClose,
}: {
  project: Project;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const { members, user } = useWorkspace();
  const [selected, setSelected] = useState(project.member_ids);
  const [reviewers, setReviewers] = useState(project.reviewer_ids);
  const { saving, error, save } = useManagementMutation();
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (
      await save(`projects/${project.id}/members/`, "PUT", {
        member_ids: selected,
        ...(user.role === "Admin" ? { reviewer_ids: reviewers.filter((id) => selected.includes(id)) } : {}),
        version: project.version,
      })
    )
      void closeDialogAnimated(dialog.current);
  }
  return (
    <dialog
      className="management-dialog"
      ref={dialog}
      onCancel={(event) => { event.preventDefault(); void closeDialogAnimated(dialog.current); }}
      onClose={onClose}
      aria-labelledby="project-team-heading"
    >
      <form onSubmit={submit}>
        <div className="section-title">
          <div>
            <div className="eyebrow">{project.name}</div>
            <h2 id="project-team-heading">Manage project team</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Close team form"
            onClick={() => void closeDialogAnimated(dialog.current)}
          >
            <X size={20} />
          </button>
        </div>
        <p className="form-note">
          Selected workspace members can access this project. Reassign open work
          and resolve blockers before removing a member.
        </p>
        <div className="member-selection">
          {members.map((member) => (
            <label className="member-option" key={member.id}>
              <input
                type="checkbox"
                checked={selected.includes(member.id)}
                disabled={
                  saving ||
                  (user.role === "Manager" && member.id === user.membership_id)
                }
                onChange={(event) =>
                  setSelected((ids) =>
                    event.target.checked
                      ? [...ids, member.id]
                      : ids.filter((id) => id !== member.id),
                  )
                }
              />
              <span>
                <b>{member.name}</b>
                <small>
                  {member.role}
                  {member.id === user.membership_id ? " · You" : ""}
                </small>
              </span>
            </label>
          ))}
        </div>
        <fieldset className="member-selection">
          <legend>Project reviewers</legend>
          <p className="form-note">Assigned reviewers can give task feedback. Only workspace admins can change this assignment.</p>
          {members.filter((member) => selected.includes(member.id) && member.role !== "Developer").map((member) => (
            <label className="member-option" key={member.id}>
              <input type="checkbox" checked={reviewers.includes(member.id)} disabled={saving || user.role !== "Admin"}
                onChange={(event) => setReviewers((ids) => event.target.checked ? [...ids, member.id] : ids.filter((id) => id !== member.id))} />
              <span><b>{member.name}</b><small>{member.role} · Task feedback</small></span>
            </label>
          ))}
        </fieldset>
        {error && (
          <div className="login-error" role="alert">
            {error}
          </div>
        )}
        <button className="button primary" disabled={saving}>
          <Users size={16} />
          {saving ? "Saving…" : "Save team"}
        </button>
      </form>
    </dialog>
  );
}
