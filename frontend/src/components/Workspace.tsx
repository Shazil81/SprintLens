import { usePageTransition } from "../hooks/usePageTransition";
import type { User } from "../api";
import { useWorkspaceController } from "../hooks/useWorkspaceController";
import { WorkspaceContext } from "../hooks/useWorkspace";
import { Navbar } from "./Navbar";
import { PageHeader } from "./PageHeader";
import { WorkspaceMessages } from "./WorkspaceMessages";
import { SummaryStrip } from "./SummaryStrip";
import { ProjectsView } from "./ProjectsView";
import { TaskPanel } from "./TaskPanel";
import { OverviewPanels } from "./OverviewPanels";
import { TeamView } from "./TeamView";
import { AuditView } from "./AuditView";
import { CreateTaskDialog } from "./CreateTaskDialog";
import { WorkspaceFooter } from "./WorkspaceFooter";
import { TaskDetailDialog } from "./TaskDetailDialog";
import { PlanningView } from "./features/PlanningView";
import { ReviewsView } from "./features/ReviewsView";
import { GrowthView } from "./features/GrowthView";
import { GitHubView } from "./features/GitHubView";
import { NotificationsView } from "./features/NotificationsView";
import { AnalyticsView } from "./features/AnalyticsView";
import { EvaluationView } from "./features/EvaluationView";
import { KnowledgeView } from "./features/KnowledgeView";
import { InsightsView } from "./features/InsightsView";
import { ReportsView } from "./features/ReportsView";

/** Composes workspace features; data and actions live in the controller hook. */
export function Workspace({
  user,
  onLogout,
}: {
  user: User;
  onLogout: () => void;
}) {
  const controller = useWorkspaceController(user, onLogout);
  const { view, detailTaskId } = controller;
  const pageRef = usePageTransition(view);
  return (
    <WorkspaceContext.Provider value={controller}>
      <div className="app-shell">
        <div className="main-shell">
          <Navbar />
          <main ref={pageRef} className={view === "Overview" ? "overview-page" : undefined}>
            <PageHeader />
            <WorkspaceMessages />
            {view === "Overview" && <SummaryStrip />}
            {view === "Projects" && <ProjectsView />}
            {view === "Overview" && <OverviewPanels />}
            {(view === "Overview" || view === "Tasks") && <TaskPanel />}
            {view === "Team" && <TeamView />}
            {view === "Planning" && <PlanningView />}
            {view === "Reviews" && <ReviewsView />}
            {view === "Growth" && <GrowthView />}
            {view === "Analytics" && <AnalyticsView />}
            {view === "Evaluation" && <EvaluationView />}
            {view === "Knowledge" && <KnowledgeView />}
            {view === "Insights" && <InsightsView />}
            {view === "Reports" && <ReportsView />}
            {view === "GitHub" && <GitHubView />}
            {view === "Notifications" && <NotificationsView />}
            {view === "Audit trail" && <AuditView />}
            <WorkspaceFooter />
          </main>
        </div>
        <CreateTaskDialog />
        {detailTaskId && (
          <TaskDetailDialog key={detailTaskId} taskId={detailTaskId} />
        )}
      </div>
    </WorkspaceContext.Provider>
  );
}
