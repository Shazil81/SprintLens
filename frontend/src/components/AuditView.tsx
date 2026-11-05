import { useState } from "react";
import { usePagedData } from "../hooks/usePagedData";
import { PageControls } from "./PageControls";
import type { Audit } from "../data";
import { ShieldCheck, Check } from "lucide-react";
import { useWorkspace } from "../hooks/useWorkspace";
/** Renders read-only task history supplied by Django. */
export function AuditView() {
  const { revision } = useWorkspace();
  const [page, setPage] = useState(1);
  const resource = usePagedData<Audit>(`audit-events/?page=${page}&page_size=25`, revision);
  return (
    <section className="audit-panel">
      <div className="section-title">
        <div>
          <h2>A history you can follow</h2>
          <p>Changes across the projects and workspace you can access.</p>
        </div>
        <ShieldCheck size={23} />
      </div>
      {resource.loading && <p role="status" className="detail-empty">Loading history…</p>}
      {resource.error && <p role="alert">{resource.error}</p>}
      {resource.page?.count === 0 && <p className="detail-empty">No recorded changes yet.</p>}
      {resource.page?.results.map((event) => (
        <div className="audit-item" key={event.id}>
          <span className="audit-icon">
            <Check size={16} />
          </span>
          <div>
            <b>{event.text}</b>
            <p>
              {event.actor}{" "}
              <span>· {new Date(event.at).toLocaleString("en-US")}</span>
            </p>
          </div>
        </div>
      ))}
      <PageControls page={page} previous={Boolean(resource.page?.previous)} next={Boolean(resource.page?.next)} disabled={resource.loading} onChange={setPage} />
    </section>
  );
}
