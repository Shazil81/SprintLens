import { closeDialogAnimated } from "../utils/dialogMotion";
import { useEffect, useRef, type FormEvent } from "react";
import { X, FolderKanban } from "lucide-react";
import type { Project } from "../api";
import { useManagementMutation } from "../hooks/useManagementMutation";

/** Creates project metadata or saves a version-checked edit; project codes stay stable. */
export function ProjectEditorDialog({
  project,
  onClose,
}: {
  project?: Project;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const { saving, error, save } = useManagementMutation();
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      name: String(form.get("name")).trim(),
      code: project?.code || String(form.get("code")).trim().toUpperCase(),
      description: String(form.get("description")).trim(),
      due: form.get("due"),
      color: form.get("color"),
      ...(project ? { version: project.version } : {}),
    };
    if (
      await save(
        project ? `projects/${project.id}/` : "projects/",
        project ? "PATCH" : "POST",
        payload,
      )
    )
      void closeDialogAnimated(dialog.current);
  }
  return (
    <dialog
      className="management-dialog"
      ref={dialog}
      onCancel={(event) => { event.preventDefault(); void closeDialogAnimated(dialog.current); }}
      onClose={onClose}
      aria-labelledby="project-editor-heading"
    >
      <form onSubmit={submit}>
        <div className="section-title">
          <div>
            <div className="eyebrow">PROJECT WORKSPACE</div>
            <h2 id="project-editor-heading">
              {project ? "Edit project" : "Create project"}
            </h2>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Close project form"
            onClick={() => void closeDialogAnimated(dialog.current)}
          >
            <X size={20} />
          </button>
        </div>
        <label>
          Project name
          <input
            name="name"
            required
            maxLength={120}
            defaultValue={project?.name}
            placeholder="e.g. Customer Portal"
            disabled={saving}
          />
        </label>
        <label>
          Project code
          <input
            name="code"
            required
            minLength={2}
            maxLength={12}
            pattern="[A-Za-z][A-Za-z0-9]{1,11}"
            defaultValue={project?.code}
            readOnly={Boolean(project)}
            placeholder="e.g. CP"
            disabled={saving}
          />
          <small className="field-help">
            A stable 2–12 character prefix for task references.
          </small>
        </label>
        <label>
          Description
          <textarea
            name="description"
            maxLength={4000}
            defaultValue={project?.description}
            placeholder="What will this project deliver?"
            disabled={saving}
          />
        </label>
        <div className="form-row">
          <label>
            Due date
            <input
              type="date"
              name="due"
              required
              defaultValue={project?.due}
              disabled={saving}
            />
          </label>
          <label>
            Project color
            <select
              name="color"
              defaultValue={project?.color || "blue"}
              disabled={saving}
            >
              <option value="blue">Blue</option>
              <option value="purple">Purple</option>
              <option value="green">Green</option>
              <option value="orange">Orange</option>
            </select>
          </label>
        </div>
        {!project && (
          <p className="form-note">
            You will join this project automatically. Add teammates using Manage
            team after creation.
          </p>
        )}
        {error && (
          <div className="login-error" role="alert">
            {error}
          </div>
        )}
        <button type="submit" className="button primary" disabled={saving}>
          <FolderKanban size={16} />
          {saving ? "Saving…" : project ? "Save project" : "Create project"}
        </button>
      </form>
    </dialog>
  );
}
