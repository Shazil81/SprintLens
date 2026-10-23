import { closeDialogAnimated } from "../utils/dialogMotion";
import { useEffect, useRef, type FormEvent } from "react";
import { X, UserPlus } from "lucide-react";
import { useManagementMutation } from "../hooks/useManagementMutation";

/** Admins create a workspace account; passwords go only to the API and never into audit data. */
export function MemberCreateDialog({ onClose }: { onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const { saving, error, save } = useManagementMutation();
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      username: String(form.get("username")).trim(),
      first_name: String(form.get("first_name")).trim(),
      last_name: String(form.get("last_name")).trim(),
      password: String(form.get("password")),
      role: form.get("role"),
    };
    if (await save("members/", "POST", payload)) void closeDialogAnimated(dialog.current);
  }
  return (
    <dialog
      className="management-dialog"
      ref={dialog}
      onCancel={(event) => { event.preventDefault(); void closeDialogAnimated(dialog.current); }}
      onClose={onClose}
      aria-labelledby="member-create-heading"
    >
      <form onSubmit={submit}>
        <div className="section-title">
          <div>
            <div className="eyebrow">WORKSPACE ADMINISTRATION</div>
            <h2 id="member-create-heading">Add team member</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Close member form"
            onClick={() => void closeDialogAnimated(dialog.current)}
          >
            <X size={20} />
          </button>
        </div>
        <div className="form-row">
          <label>
            First name
            <input
              name="first_name"
              required
              maxLength={150}
              disabled={saving}
            />
          </label>
          <label>
            Last name
            <input name="last_name" maxLength={150} disabled={saving} />
          </label>
        </div>
        <label>
          Username
          <input
            name="username"
            required
            maxLength={150}
            autoComplete="off"
            disabled={saving}
          />
        </label>
        <label>
          Initial password
          <input
            name="password"
            type="password"
            required
            minLength={8}
            maxLength={128}
            autoComplete="new-password"
            disabled={saving}
          />
        </label>
        <label>
          Workspace role
          <select name="role" defaultValue="Developer" disabled={saving}>
            <option>Developer</option>
            <option>Manager</option>
            <option>Admin</option>
          </select>
        </label>
        <p className="form-note">
          This creates an account immediately. No invitation email is sent.
          Project access is assigned separately through Manage team.
        </p>
        {error && (
          <div className="login-error" role="alert">
            {error}
          </div>
        )}
        <button className="button primary" disabled={saving}>
          <UserPlus size={16} />
          {saving ? "Creating…" : "Create member"}
        </button>
      </form>
    </dialog>
  );
}
