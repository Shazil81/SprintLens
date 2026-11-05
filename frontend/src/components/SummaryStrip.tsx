import {
  CheckCircle2,
  FolderKanban,
  GitPullRequest,
  Clock3,
} from "lucide-react";
import { useWorkspace } from "../hooks/useWorkspace";
/** Derives a compact overview from the tasks scoped to this account. */
export function SummaryStrip() {
  const { summary, projects, loading, user } = useWorkspace();
  return (
    <div className="summary-strip" aria-label={user.role === "Developer" ? "Your assignment summary" : "Accessible team work summary"}>
      <span>
        <CheckCircle2 size={20} />
        <b>{loading ? "—" : summary.by_status.Done || 0}</b> <span className="summary-label">Tasks completed</span>
      </span>
      <span>
        <FolderKanban size={20} />
        <b>{loading ? "..." : projects.length}</b> <span className="summary-label">Accessible projects</span>
      </span>
      <span>
        <GitPullRequest size={20} />
        <b>{loading ? "—" : summary.by_status["In review"] || 0}</b> <span className="summary-label">Awaiting review</span>
      </span>
      <span>
        <Clock3 size={20} />
        <b>{loading ? "—" : summary.by_status.Blocked || 0}</b> <span className="summary-label">Blocked</span>
      </span>
    </div>
  );
}
