import { useState, type FormEvent } from "react";
import { ArrowRight, ShieldCheck, Zap, GitPullRequest, CheckCircle2, Sun, Code2, BriefcaseBusiness } from "lucide-react";
import { signIn, type User } from "../api";

/** Authenticates the user and passes the server identity to App. */
export function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [portal, setPortal] = useState<"Developer" | "Manager" | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      onLogin(
        (
          await signIn(
            String(data.get("username")),
            String(data.get("password")),
          )
        ).user,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-shell">
      <div className="login-story">
        <a className="login-brand" href="/">
          <Zap size={25} fill="currentColor" /> SprintLens<span>.</span>
        </a>
        <div>
          <span className="login-kicker">YOUR ENGINEERING WORKSPACE</span>
          <h1>
            A fresh perspective.
            <br />A better workday.
          </h1>
          <p>
            Bring your projects, your people, and every step of progress into
            focus.
          </p>
          <div className="login-preview" aria-label="Workspace features"><div className="preview-heading"><span>YOUR WORK, IN FOCUS</span><Sun size={24}/></div><div className="preview-cards"><span><CheckCircle2/>Track milestones<small>Every step forward counts</small></span><span><GitPullRequest/>Connect your code<small>Bring evidence into view</small></span></div><div className="preview-timeline"><span>Plan</span><i/><span>Build</span><i/><span>Grow</span></div></div>
          <div className="login-pill">
            <ShieldCheck size={18} />
            Clear ownership. Transparent progress.
          </div>
        </div>
        <small>
          Project tracking · Engineering activity · Developer growth
        </small>
      </div>
      <main className="login-main">
        <form onSubmit={submit}>
          <span className="login-kicker">WELCOME BACK</span>
          <h1>{portal ? `${portal} sign in` : "Sign in to SprintLens"}</h1>
          <p>{portal === "Developer" ? "Your tasks, feedback and growth in one place." : portal === "Manager" ? "Bring your team’s work into focus. Admin accounts can sign in here too." : "Choose your workspace to continue."}</p>
          <div className="login-portals" aria-label="Choose your workspace">
            {(["Developer", "Manager"] as const).map((role) => {
              const Icon = role === "Developer" ? Code2 : BriefcaseBusiness;
              return <button type="button" key={role} aria-pressed={portal === role} className={`login-portal ${portal === role ? "selected" : ""}`} disabled={busy} onClick={() => { setPortal(role); setError(""); }}><Icon size={22}/><b>{role}</b><small>{role === "Developer" ? "Build, deliver & grow" : "Plan, support & review"}</small></button>;
            })}
          </div>
          {portal && <>
          <label>
            Username
            <input
              name="username"
              autoComplete="username"
              required
              placeholder="Enter your username"
              maxLength={150}
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              placeholder="Enter your password"
              maxLength={1024}
            />
          </label>
          {error && (
            <div className="login-error" role="alert">
              {error}
            </div>
          )}
          <button className="button primary" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
            <ArrowRight size={17} />
          </button>
          </>}
          <div className="login-foot">
            Access is managed by your workspace administrator.
          </div>
        </form>
      </main>
    </div>
  );
}
