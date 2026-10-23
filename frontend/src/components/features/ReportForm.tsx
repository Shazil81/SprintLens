import type { FormEvent } from "react";
import type { ProjectReport } from "../../types/reports";

/** Only narrative fields change; the source snapshot remains fixed and publication locks edits. */
export function ReportForm({
  report,
  busy,
  onSave,
}: {
  report: ProjectReport;
  busy: boolean;
  onSave: (body: object) => Promise<boolean>;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void onSave({
      ...Object.fromEntries(new FormData(event.currentTarget)),
      version: report.version,
    });
  }
  return (
    <form className="feature-form" onSubmit={submit}>
      <fieldset disabled={busy}>
        <legend>Curate the report before sharing</legend>
        <label>
          Report title
          <input
            name="title"
            required
            maxLength={160}
            defaultValue={report.title}
          />
        </label>
        {(
          [
            ["summary", "Summary"],
            ["achievements", "Achievements"],
            ["risks", "Risks and dependencies"],
            ["next_steps", "Next steps"],
          ] as const
        ).map(([key, label]) => (
          <label key={key}>
            {label}
            <textarea
              name={key}
              required={key === "summary" || key === "next_steps"}
              maxLength={4000}
              defaultValue={report[key]}
            />
          </label>
        ))}
        <p>
          Check that the narrative is suitable for your client. Publishing
          shares this report with project members and locks its text and
          snapshot.
        </p>
        <button className="button primary">Save report draft</button>
      </fieldset>
    </form>
  );
}
