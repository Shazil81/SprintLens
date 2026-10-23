import {
  CheckCircle2,
  FolderKanban,
  GitPullRequest,
  Clock3,
} from "lucide-react";
import { useWorkspace } from "../hooks/useWorkspace";
/** Derives a compact overview from the tasks scoped to this account. */
export function SummaryStrip() {
  const { done, projects, review, blocked } = useWorkspace();
  return (
    <div className="summary-strip">
      <span>
        <CheckCircle2 size={20} />
        <b>{done}</b> Tasks completed
      </span>
      <span>
        <FolderKanban size={20} />
        <b>{projects.length}</b> Active projects
      </span>
      <span>
        <GitPullRequest size={20} />
        <b>{review}</b> Awaiting review
      </span>
      <span>
        <Clock3 size={20} />
        <b>{blocked.length}</b> Blocked
      </span>
    </div>
  );
}
