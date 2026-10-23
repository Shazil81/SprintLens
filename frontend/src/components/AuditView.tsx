import { ShieldCheck, Check } from "lucide-react";
import { useWorkspace } from "../hooks/useWorkspace";
/** Renders read-only task history supplied by Django. */
export function AuditView() {
  const { data } = useWorkspace();
  return (
    <section className="audit-panel">
      <div className="section-title">
        <div>
          <h2>A history you can follow</h2>
          <p>Changes across the projects and workspace you can access.</p>
        </div>
        <ShieldCheck size={23} />
      </div>
      {data.audit.map((event) => (
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
    </section>
  );
}
