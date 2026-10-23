import { closeDialogAnimated } from "../utils/dialogMotion";
import { useEffect, useRef } from "react";
import { X, CheckCircle2 } from "lucide-react";
import { useTaskDetail } from "../hooks/useTaskDetail";
import { useWorkspace } from "../hooks/useWorkspace";
import { slug } from "../utils/workspace";
import { TaskDiscussion } from "./TaskDiscussion";
import { TaskBlockers } from "./TaskBlockers";
import { TaskEditForm } from "./TaskEditForm";
import { TaskPlanningForm } from "./TaskPlanningForm";
import { TaskGitEvidence } from "./TaskGitEvidence";
import { TaskPlanningSummary } from "./TaskPlanningSummary";

/** Provides a task-focused dialog while keeping discussion and blocker UI separate. */
export function TaskDetailDialog({ taskId }: { taskId: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const { setDetailTaskId } = useWorkspace();
  const detail = useTaskDetail(taskId);
  const { task, loading, busy, error, notice } = detail;
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="task-detail-dialog"
      onCancel={(event) => { event.preventDefault(); void closeDialogAnimated(dialog.current); }}
      onClose={() => setDetailTaskId(null)}
      aria-labelledby="task-detail-heading"
    >
      <div className="detail-top">
        <div>
          <div className="eyebrow">TASK DETAILS</div>
          <h2 id="task-detail-heading">{task?.title || "Loading task…"}</h2>
        </div>
        <button
          className="icon-button"
          aria-label="Close task details"
          onClick={() => void closeDialogAnimated(dialog.current)}
        >
          <X size={21} />
        </button>
      </div>
      {error && (
        <div className="login-error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="notice" role="status">
          <CheckCircle2 size={16} />
          {notice}
        </div>
      )}
      {loading ? (
        <p role="status" className="detail-empty">
          Loading task discussion…
        </p>
      ) : (
        task && (
          <>
            <div className="detail-facts">
              <span>
                <small>Project</small>
                <b>{task.project_name}</b>
              </span>
              <span>
                <small>Assignee</small>
                <b>{task.assignee_name}</b>
              </span>
              <span>
                <small>Status</small>
                <b className={`status ${slug(task.status)}`}>{task.status}</b>
              </span>
              <span>
                <small>Due date</small>
                <b>
                  {new Date(task.due + "T12:00:00").toLocaleDateString("en-US")}
                </b>
              </span>
            </div>
            <div className="acceptance-note">
              <b>Acceptance criteria</b>
              <p>
                {task.acceptance_criteria ||
                  "No acceptance criteria added yet."}
              </p>
            </div>
            <TaskPlanningSummary task={task} />
            <div className="acceptance-note">
              <b>Complexity: {task.complexity}</b>
              <p>
                {task.complexity_context ||
                  "No complexity explanation recorded."}
              </p>
            </div>
            {detail.isManager && (
              <>
                <TaskEditForm
                  task={task}
                  busy={busy}
                  onSave={(body) => detail.mutate("", body, "PATCH")}
                />
                <TaskPlanningForm
                  task={task}
                  busy={busy}
                  onSave={(body) => detail.mutate("planning/", body, "PUT")}
                />
              </>
            )}
            <TaskBlockers
              blockers={detail.blockers}
              user={detail.user}
              assignee={task.assignee}
              isManager={detail.isManager}
              canReport={Boolean(detail.canReport)}
              completed={task.status === "Done"}
              members={detail.projectMembers}
              busy={busy}
              onReport={(body) => detail.mutate("blockers/", body)}
              onResolve={(id, resolution) =>
                detail.mutate(`blockers/${id}/resolve/`, { resolution })
              }
            />
            <TaskDiscussion
              updates={detail.updates}
              canUpdate={Boolean(detail.canUpdate)}
              canFeedback={detail.canFeedback}
              busy={busy}
              onSubmit={(body) => detail.mutate("updates/", body)}
            />
            <TaskGitEvidence taskId={task.id} />
          </>
        )
      )}
    </dialog>
  );
}
