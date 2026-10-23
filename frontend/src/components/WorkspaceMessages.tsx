import { CheckCircle2, X } from "lucide-react";
import { useWorkspace } from "../hooks/useWorkspace";
/** Shows help, loading feedback, and dismissible action messages. */
export function WorkspaceMessages() {
  const { help, loading, notice, setNotice } = useWorkspace();
  return (
    <>
      {" "}
      {help && (
        <div className="info-panel">
          <b>SprintLens · Connected engineering workspace</b>
          <p>
            Tasks are saved by Django. Your account controls project access, and
            every task change records an audit event. Planning, private reviews,
            growth goals and notifications are available. GitHub activity
            requires a configured repository webhook. AI insights are a later
            milestone.
          </p>
        </div>
      )}
      {loading && (
        <div className="info-panel" role="status">
          Loading workspace data…
        </div>
      )}
      {notice && (
        <div className="notice" role="status">
          <CheckCircle2 size={17} />
          {notice}
          <button
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
          >
            <X size={15} />
          </button>
        </div>
      )}
    </>
  );
}
