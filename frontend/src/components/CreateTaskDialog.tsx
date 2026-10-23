import { closeDialogAnimated } from "../utils/dialogMotion";
import { X, Plus } from "lucide-react";
import { useWorkspace } from "../hooks/useWorkspace";
/** Collects task details and limits the assignee choices to project members. */
export function CreateTaskDialog() {
  const {
    dialog,
    creator,
    createTask,
    projects,
    formProject,
    setFormProject,
    setFormAssignee,
    formAssignee,
    eligibleMembers,
    formError,
    busy,
  } = useWorkspace();
  return (
    <dialog className="task-create-dialog" onCancel={(event) => { event.preventDefault(); void closeDialogAnimated(dialog.current); }} ref={dialog} onClose={() => creator.current?.focus()}>
      <form onSubmit={createTask}>
        <div className="section-title">
          <div>
            <div className="eyebrow">MAKE THE NEXT STEP CLEAR</div>
            <h2>Create a task</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Close task form"
            onClick={() => void closeDialogAnimated(dialog.current)}
          >
            <X />
          </button>
        </div>
        <label>
          Task title
          <input
            name="title"
            required
            maxLength={140}
            placeholder="What needs to get done?"
            autoFocus
            pattern=".*\S.*"
          />
        </label>
        <label>
          Project
          <select
            name="project"
            required
            value={formProject}
            onChange={(e) => {
              setFormProject(e.target.value);
              const project = projects.find(
                (p) => String(p.id) === e.target.value,
              );
              setFormAssignee(
                project?.member_ids[0] ? String(project.member_ids[0]) : "",
              );
            }}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Assignee
          <select
            name="assignee"
            required
            value={formAssignee}
            onChange={(e) => setFormAssignee(e.target.value)}
          >
            {eligibleMembers.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Acceptance criteria
          <textarea
            name="criteria"
            required
            maxLength={4000}
            placeholder="What must be true before this task is accepted?"
          />
        </label>
        <div className="form-row">
          <label>
            Priority
            <select name="priority">
              <option>Medium</option>
              <option>High</option>
              <option>Low</option>
            </select>
          </label>
          <label>
            Due date
            <input type="date" name="due" required />
          </label>
        </div>
        <p className="form-note">
          Saved to your workspace. Creating a task records a server audit event.
        </p>
        <div role="alert" className="form-error">
          {formError}
        </div>
        <button
          className="button primary"
          type="submit"
          disabled={busy || !eligibleMembers.length}
        >
          <Plus size={17} />
          {busy ? "Saving…" : "Create task"}
        </button>
      </form>
    </dialog>
  );
}
