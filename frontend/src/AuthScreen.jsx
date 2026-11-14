import { useState } from "react";

import {
  apiFetch,
  errorMessage,
  readJson,
  setAuthToken,
} from "./api";

export default function AuthScreen({ warning, onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      const endpoint =
        mode === "register"
          ? "/api/auth/register"
          : "/api/auth/login";

      const response = await apiFetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          mode === "register"
            ? { email, password, name }
            : { email, password }
        ),
      });

      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          errorMessage(data, "Sign-in could not be completed.")
        );
      }

      setAuthToken(data.token);
      onAuthenticated(data.user);
    } catch (err) {
      setError(err.message || "Sign-in could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell">
      <section className="auth-story">
        <div className="brand auth-brand">
          <span className="brand-mark">OA</span>
          <span>
            <strong>Opportunity</strong>
            <small>AGENT PLATFORM</small>
          </span>
        </div>

        <div className="eyebrow">
          <span className="sparkle">✦</span>
          PERSONAL OPPORTUNITY WORKSPACE
        </div>

        <h1>
          One workspace for
          <br />
          <span>every opportunity.</span>
        </h1>

        <p>
          Discover internships, hackathons, research programs,
          scholarships, and more — ranked against your own profile.
        </p>

        <ul className="auth-points">
          <li>Private profiles and saved opportunities</li>
          <li>Evidence-based AI extraction</li>
          <li>Transparent match scores, never fake guarantees</li>
        </ul>
      </section>

      <section className="auth-card-wrap">
        <div className="auth-card">
          <div className="auth-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              className={mode === "login" ? "active" : ""}
              onClick={() => {
                setMode("login");
                setError("");
              }}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "register"}
              className={mode === "register" ? "active" : ""}
              onClick={() => {
                setMode("register");
                setError("");
              }}
            >
              Create account
            </button>
          </div>

          <h2>
            {mode === "register"
              ? "Create your workspace"
              : "Welcome back"}
          </h2>
          <p className="auth-subtitle">
            {mode === "register"
              ? "Your profile and bookmarks stay private to your account."
              : "Sign in to load your profile and saved opportunities."}
          </p>

          {warning && (
            <div className="auth-warning" role="alert">
              {warning}
            </div>
          )}

          {error && (
            <div className="auth-error" role="alert">
              {error}
            </div>
          )}

          <form className="auth-form" onSubmit={submit}>
            {mode === "register" && (
              <label>
                Name
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  autoComplete="name"
                  maxLength={100}
                  placeholder="Your name"
                />
              </label>
            )}

            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                required
                placeholder="you@example.com"
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                autoComplete={
                  mode === "register"
                    ? "new-password"
                    : "current-password"
                }
                minLength={8}
                maxLength={128}
                required
                placeholder="At least 8 characters"
              />
            </label>

            <button
              className="primary-button auth-submit"
              type="submit"
              disabled={busy}
            >
              {busy
                ? "Please wait..."
                : mode === "register"
                  ? "Create account"
                  : "Sign in"}
            </button>
          </form>

          <p className="auth-footnote">
            Passwords are hashed with PBKDF2-SHA256. Sessions use
            signed tokens.
          </p>
        </div>
      </section>
    </div>
  );
}