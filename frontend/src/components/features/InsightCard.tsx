import { useState } from "react";
import type { InsightOutput, InsightRun } from "../../types/reports";

/** Model prose is untrusted plain text; citations resolve only to the saved input bundle. */
export function InsightCard({
  run,
  busy,
  configured,
  onGenerate,
}: {
  run: InsightRun;
  busy: boolean;
  configured: boolean;
  onGenerate: () => Promise<boolean>;
}) {
  const [consent, setConsent] = useState(false);
  const output = run.status === "Ready" ? (run.output as InsightOutput) : null;
  return (
    <article className="feature-card">
      <div className="eyebrow">
        {run.status} · {run.provider} · {run.model}
      </div>
      <h3>
        Project insights · {run.input_snapshot.period.start} →{" "}
        {run.input_snapshot.period.end}
      </h3>
      <p>
        Snapshot{" "}
        {new Date(run.input_snapshot.captured_at).toLocaleString("en-US")}. This
        run is private to you.
      </p>
      <details>
        <summary>Review exact source payload</summary>
        <pre className="insight-json">
          {JSON.stringify(run.input_snapshot, null, 2)}
        </pre>
      </details>
      {run.status === "Prepared" && (
        <div className="insight-consent">
          <label>
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />
            I reviewed this snapshot and approve sending it to Google's Gemini
            API.
          </label>
          <p>
            The payload includes project/task titles and delivery counts. No
            names, private reviews, growth notes or work-note bodies are added.
            Google's free-tier data policy applies. Your API project's billing
            tier controls charges.
          </p>
          <button
            className="button primary"
            disabled={busy || !configured || !consent}
            onClick={onGenerate}
          >
            {busy ? "Generating…" : "Generate Gemini insights"}
          </button>
        </div>
      )}
      {run.status === "Generating" && (
        <p role="status">
          Generation was submitted. Refresh run status; do not resubmit this
          preview. If the server stopped, prepare a new preview after checking
          provider usage.
        </p>
      )}
      {run.error && (
        <p className="login-error" role="alert">
          {run.error}
        </p>
      )}
      {output && (
        <div className="evaluation-summary">
          <h4>AI draft — verify before use</h4>
          <p>{output.summary}</p>
          {output.findings.map((finding, i) => (
            <div className="review-dimension" key={i}>
              <b>{finding.kind}</b>
              <p>{finding.text}</p>
              {finding.evidence_ids.map((id) => (
                <details className="evidence-task" key={id}>
                  <summary>Source: {id}</summary>
                  <pre className="insight-json">
                    {JSON.stringify(run.input_snapshot.evidence[id], null, 2)}
                  </pre>
                </details>
              ))}
            </div>
          ))}
          {output.limitations.map((text, i) => (
            <p key={i}>
              <small>{text}</small>
            </p>
          ))}
          <p>
            No actions were taken. Review source facts before copying any
            narrative into a report.
          </p>
        </div>
      )}
    </article>
  );
}
