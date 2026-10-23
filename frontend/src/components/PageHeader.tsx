import { ArrowDownToLine } from "lucide-react";
import { useWorkspace } from "../hooks/useWorkspace";
/** Displays the current view title and report export action. */
export function PageHeader() {
  const { user, view, exportReport } = useWorkspace();
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">
          {new Date().toLocaleDateString("en-US", {
            weekday: "long",
            month: "long",
            day: "numeric",
          })}{" "}
          · {user.organization.name}
        </div>
        <h1>
          {view === "Overview"
            ? "Welcome back, " + user.name.split(" ")[0] + "."
            : view}
        </h1>
        <p>
          {view === "Overview"
            ? "Here’s what’s happening with your team today."
            : "Connected work. Clear ownership. Every change accounted for."}
        </p>
      </div>
      <button className="button secondary" onClick={exportReport}>
        <ArrowDownToLine size={16} />
        Export report
      </button>
    </div>
  );
}
