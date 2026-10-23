import type { FormEvent } from "react";
import type { KnowledgeArticle } from "../../types/insights";
import { useWorkspace } from "../../hooks/useWorkspace";

/** Content remains plain text; the reader never executes HTML from an article. */
export function ArticleForm({
  initial,
  busy,
  onSave,
  onCancel,
}: {
  initial?: KnowledgeArticle;
  busy: boolean;
  onSave: (body: object) => Promise<boolean>;
  onCancel: () => void;
}) {
  const { projects, user } = useWorkspace();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const body = {
      ...Object.fromEntries(data),
      tags: String(data.get("tags"))
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
      ...(initial
        ? { version: initial.version }
        : { project: Number(data.get("project")) }),
    };
    await onSave(body);
  }
  return (
    <form className="feature-form" onSubmit={submit}>
      <fieldset disabled={busy}>
        <legend>{initial ? "Edit article" : "New knowledge article"}</legend>
        {!initial && (
          <label>
            Project
            <select name="project" required>
              {projects
                .filter((p) => p.member_ids.includes(user.membership_id))
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
            </select>
          </label>
        )}
        <label>
          Title
          <input
            name="title"
            required
            maxLength={160}
            defaultValue={initial?.title}
          />
        </label>
        <label>
          Summary
          <textarea
            name="summary"
            required
            maxLength={400}
            defaultValue={initial?.summary}
          />
        </label>
        <label>
          Tags (comma separated)
          <input
            name="tags"
            maxLength={310}
            defaultValue={initial?.tags.join(", ")}
            placeholder="django, redis, troubleshooting"
          />
        </label>
        <label>
          Solution / documentation
          <textarea
            className="article-editor"
            name="content"
            required
            maxLength={20000}
            defaultValue={initial?.content}
            placeholder="Problem, context, solution, verification and useful references. Plain text and code are preserved."
          />
        </label>
        <label>
          Visibility
          <select name="status" defaultValue={initial?.status || "Draft"}>
            <option>Draft</option>
            <option>Published</option>
            {initial && <option>Archived</option>}
          </select>
        </label>
        <p>
          Drafts are private to their author. Published and archived articles
          are visible to project members. Every save retains a revision.
        </p>
        <div className="feature-actions">
          <button className="button primary">Save article</button>
          <button type="button" className="button secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </fieldset>
    </form>
  );
}
