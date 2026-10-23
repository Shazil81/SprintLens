import { useState, type FormEvent } from "react";
import { request } from "../../api";
import type { KnowledgeArticle, KnowledgeSummary } from "../../types/insights";
import { useWorkspace } from "../../hooks/useWorkspace";
import { useFeatureData } from "../../hooks/useFeatureData";
import { FeatureState } from "./FeatureState";
import { ArticleForm } from "./ArticleForm";
import { ArticleDetail } from "./ArticleDetail";

/** Separate compact search results from full article bodies and revision history. */
export function KnowledgeView() {
  const { projects, user } = useWorkspace();
  const [filters, setFilters] = useState("");
  const resource = useFeatureData<KnowledgeSummary>(`knowledge/?${filters}`);
  const [article, setArticle] = useState<KnowledgeArticle | null>(null);
  const [editor, setEditor] = useState<KnowledgeArticle | "new" | null>(null);
  const [opening, setOpening] = useState(false);
  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const params = new URLSearchParams();
    new FormData(event.currentTarget).forEach((value, key) => {
      if (String(value).trim()) params.set(key, String(value).trim());
    });
    setFilters(params.toString());
    setArticle(null);
    setEditor(null);
  }
  async function open(id: number, edit = false) {
    setOpening(true);
    resource.setError("");
    try {
      const full = await request<KnowledgeArticle>(`knowledge/${id}/`);
      setArticle(full);
      setEditor(edit ? full : null);
    } catch (e) {
      resource.setError(
        e instanceof Error ? e.message : "Article could not be opened.",
      );
    } finally {
      setOpening(false);
    }
  }
  return (
    <section className="feature-screen">
      <div className="section-title">
        <div>
          <h2>Team knowledge hub</h2>
          <p>Document the solution once. Help your team solve it again.</p>
        </div>
        {projects.some((p) => p.member_ids.includes(user.membership_id)) && (
          <button
            className="button primary"
            onClick={() => {
              setEditor("new");
              setArticle(null);
            }}
          >
            Write article
          </button>
        )}
      </div>
      <form className="insight-filters" onSubmit={search}>
        <label>
          Search
          <input
            name="search"
            maxLength={100}
            placeholder="Search solutions…"
          />
        </label>
        <label>
          Tag
          <input name="tag" maxLength={30} placeholder="e.g. django" />
        </label>
        <label>
          Project
          <select name="project">
            <option value="">All accessible projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select name="status">
            <option value="">Published + my drafts</option>
            {["Published", "Draft", "Archived"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <button className="button secondary">Search articles</button>
      </form>
      <FeatureState
        loading={resource.loading || opening}
        error={resource.error}
      />
      {editor && (
        <article className="feature-card">
          <ArticleForm
            key={editor === "new" ? "new" : `${editor.id}:${editor.version}`}
            initial={editor === "new" ? undefined : editor}
            busy={resource.busy}
            onCancel={() => setEditor(null)}
            onSave={async (body) => {
              const saved = await resource.mutate(
                editor === "new" ? "knowledge/" : `knowledge/${editor.id}/`,
                editor === "new" ? "POST" : "PATCH",
                body,
              );
              if (saved) {
                setEditor(null);
                setArticle(null);
              }
              return saved;
            }}
          />
        </article>
      )}
      {article && !editor && (
        <article className="feature-card">
          <div className="feature-actions">
            <h3>{article.title}</h3>
            <button
              className="button secondary"
              onClick={() => setArticle(null)}
            >
              Close article
            </button>
          </div>
          <p>{article.summary}</p>
          <p>
            {article.status} · {article.author_name} · Version {article.version}
          </p>
          <ArticleDetail
            key={`${article.id}:${article.version}`}
            article={article}
          />
        </article>
      )}
      {!resource.loading && !resource.items.length && (
        <p className="detail-empty">
          No matching articles. Drafts from other authors remain private.
        </p>
      )}
      <div className="feature-grid">
        {resource.items.map((item) => {
          const canEdit =
            item.author === user.membership_id ||
            (user.role !== "Developer" &&
              projects
                .find((p) => p.id === item.project)
                ?.reviewer_ids.includes(user.membership_id));
          return (
            <article className="feature-card" key={item.id}>
              <div className="eyebrow">
                {item.status} ·{" "}
                {projects.find((p) => p.id === item.project)?.name}
              </div>
              <h3>{item.title}</h3>
              <p>{item.summary}</p>
              <div className="article-tags">
                {item.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
              <p>
                <small>
                  {item.author_name} · Updated{" "}
                  {new Date(item.updated_at).toLocaleDateString("en-US")}
                </small>
              </p>
              <div className="feature-actions">
                <button
                  className="button secondary"
                  disabled={opening}
                  onClick={() => open(item.id)}
                >
                  Read article
                </button>
                {canEdit && (
                  <button
                    className="button secondary"
                    disabled={opening}
                    onClick={() => open(item.id, true)}
                  >
                    Edit article
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
