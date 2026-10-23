import { closeDialogAnimated } from "../utils/dialogMotion";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { X, ShieldCheck } from "lucide-react";
import type { Member, User } from "../api";
import { useManagementMutation } from "../hooks/useManagementMutation";

/** Keeps a role change explicit and explains the access it grants before submission. */
export function RoleEditorDialog({
  member,
  onClose,
}: {
  member: Member;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [role, setRole] = useState<User["role"]>(member.role);
  const { saving, error, save } = useManagementMutation();
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (await save(`members/${member.id}/`, "PATCH", { role }))
      void closeDialogAnimated(dialog.current);
  }
  return (
    <dialog
      className="management-dialog"
      ref={dialog}
      onCancel={(event) => { event.preventDefault(); void closeDialogAnimated(dialog.current); }}
      onClose={onClose}
      aria-labelledby="role-editor-heading"
    >
      <form onSubmit={submit}>
        <div className="section-title">
          <div>
            <div className="eyebrow">{member.name}</div>
            <h2 id="role-editor-heading">Change workspace role</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Close role form"
            onClick={() => void closeDialogAnimated(dialog.current)}
          >
            <X size={20} />
          </button>
        </div>
        <label>
          Role
          <select
            value={role}
            disabled={saving}
            onChange={(event) => setRole(event.target.value as User["role"])}
          >
            <option>Developer</option>
            <option>Manager</option>
            <option>Admin</option>
          </select>
        </label>
        <p className="form-note">
          {role === "Admin"
            ? "Admins manage all workspace projects, create accounts, and change roles."
            : role === "Manager"
              ? "Managers create projects and manage tasks and teams in projects they can access."
              : "Developers read accessible projects and update their assigned work."}
        </p>
        {error && (
          <div className="login-error" role="alert">
            {error}
          </div>
        )}
        <button
          className="button primary"
          disabled={saving || role === member.role}
        >
          <ShieldCheck size={16} />
          {saving ? "Saving…" : "Save role"}
        </button>
      </form>
    </dialog>
  );
}
