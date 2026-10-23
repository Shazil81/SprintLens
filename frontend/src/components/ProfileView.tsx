import { ArrowUpRight, BriefcaseBusiness, CheckCheck, ListTodo, Activity, ShieldCheck } from "lucide-react";
import type { Review } from "../api";
import { useWorkspace } from "../hooks/useWorkspace";
import { useFeatureData } from "../hooks/useFeatureData";
import { initials, slug } from "../utils/workspace";
import { EvaluationSummary } from "./features/EvaluationSummary";
import "../profile.css";

/** Shows the signed-in member's current assignments and published review evidence. */
export function ProfileView() {
  const { user, data, projects, loading, setDetailTaskId, go } = useWorkspace();
  const reviews = useFeatureData<Review>("reviews/");
  // Membership IDs identify assignments reliably, including duplicate display names.
  const tasks = data.tasks.filter((task) => task.assigneeId === user.membership_id);
  const completed = tasks.filter((task) => task.status === "Done");
  const active = tasks.filter((task) => task.status !== "Done").sort((a, b) => a.due.localeCompare(b.due));
  const blocked = active.filter((task) => task.status === "Blocked").length;
  const inReview = active.filter((task) => task.status === "In review").length;
  const projectCount = projects.filter((project) => project.member_ids.includes(user.membership_id)).length;
  const completion = tasks.length ? Math.round(completed.length / tasks.length * 100) : 0;
  const published = reviews.items.filter((review) => review.subject === user.membership_id && review.status !== "Draft")
    .sort((a, b) => b.period_end.localeCompare(a.period_end) || b.id - a.id);
  const latest = published[0];
  const metrics = [
    { label: "Active tasks", value: active.length, note: "All unfinished assignments", icon: Activity, tone: "blue" },
    { label: "Total tasks assigned", value: tasks.length, note: "Current assignments · all statuses", icon: ListTodo, tone: "violet" },
    { label: "Total tasks completed", value: completed.length, note: "Assignments marked done", icon: CheckCheck, tone: "green" },
  ];
  return <div className="profile-page">
    <section className="profile-identity" aria-label="Profile details">
      <div className="profile-cover"><span>YOUR WORKSPACE IDENTITY</span><ShieldCheck size={28}/></div>
      <div className="profile-identity-body">
        <span className="profile-avatar" aria-hidden="true">{initials(user.name)}</span>
        <h2>{user.name}</h2><span className="profile-role">{user.role}</span>
        <p>A clear view of your work and the progress behind it.</p>
        <dl><div><dt>Username</dt><dd>@{user.username}</dd></div><div><dt>Organization</dt><dd>{user.organization.name}</dd></div><div><dt>Role</dt><dd>{user.role}</dd></div></dl>
        <div className="profile-project-count"><BriefcaseBusiness size={19}/><span><b>{loading ? "—" : projectCount}</b> project memberships</span></div>
      </div>
    </section>
    <div className="profile-content">
      <section aria-labelledby="profile-overview"><div className="profile-section-heading"><div><span className="eyebrow">THE BIG PICTURE</span><h2 id="profile-overview">Overview</h2></div><span className="profile-scope">Your assignments</span></div>
        <div className="profile-metrics">{metrics.map(({ label, value, note, icon: Icon, tone }) => <article className={`profile-metric ${tone}`} key={label}><span className="profile-metric-icon"><Icon size={20}/></span><strong>{loading ? "—" : value}</strong><h3>{label}</h3><p>{note}</p></article>)}</div>
      </section>
      <section className="profile-panel" aria-labelledby="profile-active"><div className="profile-section-heading"><div><h2 id="profile-active">Active tasks <span className="profile-count">{loading ? "…" : active.length}</span></h2><p>Unfinished work, ordered by due date.</p></div></div>
        {loading ? <p role="status">Loading assignments…</p> : !active.length ? <p className="detail-empty">No active assignments. Your next assigned task will appear here.</p> : <div className="profile-task-list">{active.map((task) => <button className="profile-task" key={task.id} onClick={() => task.apiId && setDetailTaskId(task.apiId)}><span className="profile-task-marker"><ListTodo size={18}/></span><span className="profile-task-copy"><b>{task.title}</b><small>{task.id} · {task.project}</small></span><span className={`status ${slug(task.status)}`}>{task.status}</span><span className="profile-task-due">Due {new Date(`${task.due}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span><ArrowUpRight size={17}/></button>)}</div>}
      </section>
      <section className="profile-panel" aria-labelledby="profile-performance"><div className="profile-section-heading"><div><h2 id="profile-performance">Performance</h2><p>Delivery context and feedback, together.</p></div><button className="button secondary" onClick={() => go("Reviews")}>View reviews <ArrowUpRight size={15}/></button></div>
        <div className="profile-delivery"><div><b>Assignment completion</b><strong>{loading || !tasks.length ? "—" : `${completion}%`}</strong><div className="profile-progress" role="progressbar" aria-label="Assignment completion" aria-valuemin={0} aria-valuemax={100} aria-valuenow={completion}><span style={{ width: `${completion}%` }}/></div><small>Current task status, not a performance rating.</small></div><div className="profile-context"><span><b>{loading ? "—" : inReview}</b> In review</span><span><b>{loading ? "—" : blocked}</b> Blocked</span></div></div>
        {reviews.loading ? <p role="status">Loading feedback…</p> : reviews.error ? <p role="alert">Could not load feedback: {reviews.error}</p> : latest ? <div className="profile-feedback"><span className="eyebrow">LATEST PUBLISHED REVIEW · {latest.period_start} — {latest.period_end}</span><h3>{latest.cycle}</h3><p>Reviewed by {latest.reviewer_name}</p><EvaluationSummary assessment={latest.assessment}/>{latest.strengths && <p><b>Strengths:</b> {latest.strengths}</p>}{latest.improvements && <p><b>Growth areas:</b> {latest.improvements}</p>}{latest.collaboration && <p><b>Collaboration:</b> {latest.collaboration}</p>}{latest.delivery_context && <p><b>Delivery context:</b> {latest.delivery_context}</p>}</div> : <div className="profile-feedback"><h3>No published assessment yet</h3><p>Quality, delivery and collaboration feedback will appear after your reviewer publishes a review.</p></div>}
      </section>
    </div>
  </div>;
}
