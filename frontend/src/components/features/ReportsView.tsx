import { useState } from "react";
import type { ProjectReport } from "../../types/reports";
import { useWorkspace } from "../../hooks/useWorkspace";
import { useFeatureData } from "../../hooks/useFeatureData";
import { FeatureState } from "./FeatureState";
import { SnapshotForm } from "./SnapshotForm";
import { ReportForm } from "./ReportForm";
import { ReportPreview } from "./ReportPreview";

/** Downloads use the same authenticated server record as the preview; nothing is published publicly. */
export function ReportsView() {
  const resource = useFeatureData<ProjectReport>("reports/");
  const { user, projects } = useWorkspace();
  const [editing, setEditing] = useState<string | null>(null);
  return (
    <section className="feature-screen">
      <div className="section-title">
        <div>
          <h2>Project reports</h2>
          <p>
            Capture, curate and export a clear project update for your client.
          </p>
        </div>
      </div>
      <article className="feature-card">
        <p>
          Drafts are author-private. Published reports are visible to project
          members; downloads are authenticated. Share exported files with your
          client manually. Private reviews, growth notes and employee ratings
          are excluded automatically.
        </p>
        {user.role !== "Developer" && (
          <SnapshotForm
            busy={resource.busy}
            label="Create report draft"
            onSubmit={(body) => resource.mutate("reports/", "POST", body)}
          />
        )}
      </article>
      <FeatureState loading={resource.loading} error={resource.error} />
      {!resource.loading && !resource.items.length && (
        <p className="detail-empty">No accessible reports yet.</p>
      )}
      {resource.items.map((report) => (
        <article className="feature-card" key={report.id}>
          <div className="eyebrow">
            {projects.find((p) => p.id === report.project)?.name}
          </div>
          <ReportPreview report={report} />
          <div className="feature-actions">
            {["pdf", "csv", "json"].map((kind) => (
              <a
                className="button secondary"
                key={kind}
                href={`/api/v1/reports/${report.id}/download/?file=${kind}`}
                download
              >
                Download {kind.toUpperCase()}
              </a>
            ))}
            {report.status === "Draft" &&
              report.creator === user.membership_id &&
              user.role !== "Developer" && (
                <>
                  <button
                    className="button secondary"
                    onClick={() =>
                      setEditing(editing === report.id ? null : report.id)
                    }
                  >
                    {editing === report.id ? "Close editor" : "Edit report"}
                  </button>
                  <button
                    className="button primary"
                    disabled={resource.busy}
                    onClick={() =>
                      resource.mutate(`reports/${report.id}/publish/`, "POST", {
                        version: report.version,
                      })
                    }
                  >
                    Publish report
                  </button>
                </>
              )}
          </div>
          {editing === report.id && report.status === "Draft" && (
            <ReportForm
              key={report.version}
              report={report}
              busy={resource.busy}
              onSave={(body) =>
                resource.mutate(`reports/${report.id}/`, "PATCH", body)
              }
            />
          )}
        </article>
      ))}
    </section>
  );
}
