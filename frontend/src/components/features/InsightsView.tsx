import { useEffect, useState } from "react";
import { request } from "../../api";
import type { AIConfiguration, InsightRun } from "../../types/reports";
import { useWorkspace } from "../../hooks/useWorkspace";
import { useFeatureData } from "../../hooks/useFeatureData";
import { FeatureState } from "./FeatureState";
import { SnapshotForm } from "./SnapshotForm";
import { InsightCard } from "./InsightCard";

/** Developers never fetch private manager insight history; the server enforces the same boundary. */
export function InsightsView() {
  const { user } = useWorkspace();
  return user.role === "Developer" ? (
    <article className="feature-card">
      <h2>Project insights</h2>
      <p>
        AI insight drafts are private manager tools. Published project reports
        are available in Reports.
      </p>
    </article>
  ) : (
    <ManagerInsights />
  );
}

function ManagerInsights() {
  const resource = useFeatureData<InsightRun>("insights/");
  const [config, setConfig] = useState<AIConfiguration | null>(null);
  const [statusError, setStatusError] = useState("");
  useEffect(() => {
    let active = true;
    request<AIConfiguration>("insights/configuration/")
      .then((value) => {
        if (active) setConfig(value);
      })
      .catch((e) => {
        if (active) setStatusError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  async function generate(run: InsightRun) {
    const success = await resource.mutate(
      `insights/${run.id}/generate/`,
      "POST",
      { input_hash: run.input_hash, consent: true },
    );
    if (!success) await resource.load().catch(() => {});
    return success;
  }
  return (
    <section className="feature-screen">
      <div className="section-title">
        <div>
          <h2>AI project insights</h2>
          <p>
            Weekly progress, recurring blocker signals and questions for the
            next check-in.
          </p>
        </div>
        <button
          className="button secondary"
          disabled={resource.busy}
          onClick={() =>
            resource.load().catch((e) => resource.setError(e.message))
          }
        >
          Refresh run status
        </button>
      </div>
      <article className="feature-card">
        <h3>{config?.configured ? "Gemini configured" : "Gemini setup"}</h3>
        <p>
          {config?.message || statusError || "Checking provider configuration…"}
        </p>
        <p>
          Prepare a source preview first; this makes no AI request. Generation
          requires your approval. Limit: {config?.daily_limit ?? "—"} submitted
          runs per day across your workspace.
        </p>
        {!config?.configured && (
          <p>
            On the backend, run <code>python local.py configure_local_ai</code>{" "}
            in your activated environment, then restart Django. Enter the key
            only in the hidden local prompt. Use a Google AI Studio project on
            the free tier.
          </p>
        )}
        <SnapshotForm
          busy={resource.busy}
          label="Prepare insight preview"
          onSubmit={(body) => resource.mutate("insights/", "POST", body)}
        />
      </article>
      <FeatureState
        loading={resource.loading}
        error={resource.error || statusError}
      />
      {!resource.loading && !resource.items.length && (
        <p className="detail-empty">No private insight previews yet.</p>
      )}
      {resource.items.map((run) => (
        <InsightCard
          key={run.id}
          run={run}
          busy={resource.busy}
          configured={!!config?.configured}
          onGenerate={() => generate(run)}
        />
      ))}
    </section>
  );
}
