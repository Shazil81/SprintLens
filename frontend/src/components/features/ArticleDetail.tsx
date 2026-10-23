import { useState } from "react";
import { listAll } from "../../api";
import type { ArticleRevision, KnowledgeArticle } from "../../types/insights";

/** History is fetched on demand and the API removes other authors' private draft revisions. */
export function ArticleDetail({ article }: { article: KnowledgeArticle }) {
  const [history, setHistory] = useState<ArticleRevision[] | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function loadHistory() {
    setLoading(true);
    setError("");
    try {
      setHistory(
        await listAll<ArticleRevision>(`knowledge/${article.id}/history/`),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "History could not be loaded.");
    } finally {
      setLoading(false);
    }
  }
  return (
    <div>
      <p className="article-content">{article.content}</p>
      <button
        className="button secondary"
        disabled={loading}
        onClick={loadHistory}
      >
        {loading ? "Loading revisions…" : "Load revision history"}
      </button>
      {error && <p role="alert">{error}</p>}
      {history?.map((revision) => (
        <details className="evidence-task" key={revision.id}>
          <summary>
            Version {revision.version} · {revision.snapshot.status} ·{" "}
            {revision.editor_name || "Workspace member"} ·{" "}
            {new Date(revision.at).toLocaleString("en-US")}
          </summary>
          <h4>{revision.snapshot.title}</h4>
          <p>{revision.snapshot.summary}</p>
          <p className="article-content">{revision.snapshot.content}</p>
        </details>
      ))}
    </div>
  );
}
