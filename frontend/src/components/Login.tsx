import { useState, type FormEvent } from "react";
import { ArrowRight, ShieldCheck, Zap, GitPullRequest, CheckCircle2, Sun } from "lucide-react";
import { signIn, type User } from "../api";

/** Authenticates the user and passes the server identity to App. */
export function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
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
          <h1>Sign in to SprintLens</h1>
          <p>Your team’s next chapter starts here.</p>
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
          <div className="login-foot">
            Access is managed by your workspace administrator.
          </div>
        </form>
      </main>
    </div>
  );
}
