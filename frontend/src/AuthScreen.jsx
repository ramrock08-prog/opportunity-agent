import { useEffect, useMemo, useState } from "react";

import {
  apiFetch,
  errorMessage,
  readJson,
  setAuthToken,
} from "./api";

function initialUrlState() {
  if (typeof window === "undefined") {
    return { verifyToken: "", resetToken: "" };
  }

  const params = new URLSearchParams(window.location.search);

  return {
    verifyToken: params.get("verify_token") || "",
    resetToken: params.get("reset_token") || "",
  };
}

export default function AuthScreen({
  warning,
  status,
  onAuthenticated,
}) {
  const initial = useMemo(() => initialUrlState(), []);
  const [mode, setMode] = useState(
    initial.resetToken ? "reset" : "login"
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [resetToken, setResetToken] = useState(
    initial.resetToken
  );
  const [devVerifyToken, setDevVerifyToken] = useState("");
  const [verificationEmail, setVerificationEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [verifying, setVerifying] = useState(
    Boolean(initial.verifyToken)
  );
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const emailConfigured = status?.email_configured;
  const verificationRequired = status?.verification_required;

  useEffect(() => {
    if (!initial.verifyToken) return undefined;

    let active = true;

    apiFetch("/api/auth/verify-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: initial.verifyToken }),
    })
      .then(async (response) => ({
        ok: response.ok,
        data: await readJson(response),
      }))
      .then(({ ok, data }) => {
        if (!active) return;

        if (ok && data.token) {
          setAuthToken(data.token);
          onAuthenticated(data.user);
        } else {
          setError(
            errorMessage(
              data,
              "That verification link is invalid or expired."
            )
          );
          setMode("login");
        }
      })
      .catch(() => {
        if (active) {
          setError("The verification link could not be checked.");
          setMode("login");
        }
      })
      .finally(() => {
        if (active) setVerifying(false);
      });

    return () => {
      active = false;
    };
  }, [initial.verifyToken, onAuthenticated]);

  function finishAuthentication(data) {
    setAuthToken(data.token);
    onAuthenticated(data.user);
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setInfo("");

    try {
      if (mode === "forgot") {
        const response = await apiFetch(
          "/api/auth/forgot-password",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email }),
          }
        );
        const data = await readJson(response);

        if (!response.ok) {
          throw new Error(
            errorMessage(data, "Could not send the reset email.")
          );
        }

        if (data.dev_reset_token) {
          setResetToken(data.dev_reset_token);
          setMode("reset");
          setInfo("Development reset token loaded.");
        } else {
          setInfo(
            "If that email exists, a reset link has been sent. Check your inbox."
          );
        }
        return;
      }

      if (mode === "reset") {
        const response = await apiFetch(
          "/api/auth/reset-password",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              token: resetToken,
              password,
            }),
          }
        );
        const data = await readJson(response);

        if (!response.ok) {
          throw new Error(
            errorMessage(data, "Could not reset the password.")
          );
        }

        setPassword("");
        setResetToken("");
        setMode("login");
        setInfo("Password updated. Sign in with the new password.");
        return;
      }

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

      if (response.status === 403 && mode === "login") {
        setVerificationEmail(email);
        setDevVerifyToken("");
        setMode("verify");
        setInfo(
          "Verify your email before signing in. Check your inbox or resend the link."
        );
        return;
      }

      if (!response.ok) {
        throw new Error(
          errorMessage(data, "Sign-in could not be completed.")
        );
      }

      if (data.token) {
        finishAuthentication(data);
        return;
      }

      if (data.verification_required) {
        setVerificationEmail(data.email || email);
        setDevVerifyToken(data.dev_verification_token || "");
        setMode("verify");
        setInfo(
          data.email_sent === false
            ? "Email delivery is unavailable locally. Use the development verification button below."
            : "Check your email for the verification link."
        );
        return;
      }

      throw new Error("The server returned an unexpected response.");
    } catch (err) {
      setError(err.message || "The request could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  async function verifyNow(token) {
    setBusy(true);
    setError("");

    try {
      const response = await apiFetch(
        "/api/auth/verify-email",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        }
      );
      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          errorMessage(data, "Verification failed.")
        );
      }

      finishAuthentication(data);
    } catch (err) {
      setError(err.message || "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  async function resendVerification() {
    setBusy(true);
    setError("");
    setInfo("");

    try {
      const response = await apiFetch(
        "/api/auth/resend-verification",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: verificationEmail || email,
          }),
        }
      );
      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          errorMessage(data, "Could not resend the verification email.")
        );
      }

      if (data.dev_verification_token) {
        setDevVerifyToken(data.dev_verification_token);
      }

      setInfo(
        data.email_sent
          ? "Verification email sent. Check your inbox."
          : "If that account needs verification, a new link was prepared."
      );
    } catch (err) {
      setError(err.message || "Could not resend the verification email.");
    } finally {
      setBusy(false);
    }
  }

  const title =
    mode === "register"
      ? "Create your workspace"
      : mode === "forgot"
        ? "Reset your password"
        : mode === "reset"
          ? "Choose a new password"
          : mode === "verify"
            ? "Verify your email"
            : "Welcome back";

  const subtitle =
    mode === "register"
      ? "Your profile and bookmarks stay private to your account."
      : mode === "forgot"
        ? "We will email a single-use reset link if the account exists."
        : mode === "reset"
          ? "This link expires after 30 minutes and revokes old sessions."
          : mode === "verify"
            ? "Verification keeps account recovery and saved data safe."
            : "Sign in to load your profile and saved opportunities.";

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
          {["login", "register"].includes(mode) && (
            <div className="auth-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={mode === "login"}
                className={mode === "login" ? "active" : ""}
                onClick={() => {
                  setMode("login");
                  setError("");
                  setInfo("");
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
                  setInfo("");
                }}
              >
                Create account
              </button>
            </div>
          )}

          <h2>{title}</h2>
          <p className="auth-subtitle">{subtitle}</p>

          {warning && (
            <div className="auth-warning" role="alert">
              {warning}
            </div>
          )}

          {verificationRequired && emailConfigured === false && (
            <div className="auth-warning" role="alert">
              Email delivery is not configured on this server.
            </div>
          )}

          {verifying && (
            <div className="auth-info">Checking your verification link...</div>
          )}

          {info && <div className="auth-info">{info}</div>}

          {error && (
            <div className="auth-error" role="alert">
              {error}
            </div>
          )}

          {mode === "verify" ? (
            <div className="auth-verify">
              <p>
                Account: <strong>{verificationEmail || email}</strong>
              </p>

              {devVerifyToken && (
                <button
                  type="button"
                  className="primary-button auth-submit"
                  disabled={busy}
                  onClick={() => verifyNow(devVerifyToken)}
                >
                  {busy ? "Verifying..." : "Verify now (development)"}
                </button>
              )}

              <button
                type="button"
                className="auth-secondary"
                disabled={busy}
                onClick={resendVerification}
              >
                Resend verification email
              </button>

              <button
                type="button"
                className="auth-link"
                onClick={() => {
                  setMode("login");
                  setError("");
                  setInfo("");
                }}
              >
                Back to sign in
              </button>
            </div>
          ) : (
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

              {mode !== "reset" && (
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
              )}

              {mode !== "forgot" && (
                <label>
                  {mode === "reset" ? "New password" : "Password"}
                  <input
                    type="password"
                    value={password}
                    onChange={(event) =>
                      setPassword(event.target.value)
                    }
                    autoComplete={
                      mode === "register" || mode === "reset"
                        ? "new-password"
                        : "current-password"
                    }
                    minLength={8}
                    maxLength={128}
                    required
                    placeholder="At least 8 characters"
                  />
                </label>
              )}

              <button
                className="primary-button auth-submit"
                type="submit"
                disabled={busy}
              >
                {busy
                  ? "Please wait..."
                  : mode === "register"
                    ? "Create account"
                    : mode === "forgot"
                      ? "Send reset link"
                      : mode === "reset"
                        ? "Update password"
                        : "Sign in"}
              </button>

              {mode === "login" && (
                <button
                  type="button"
                  className="auth-link"
                  onClick={() => {
                    setMode("forgot");
                    setError("");
                    setInfo("");
                  }}
                >
                  Forgot password?
                </button>
              )}

              {mode !== "login" && (
                <button
                  type="button"
                  className="auth-link"
                  onClick={() => {
                    setMode("login");
                    setError("");
                    setInfo("");
                  }}
                >
                  Back to sign in
                </button>
              )}
            </form>
          )}

          <p className="auth-footnote">
            Passwords are hashed with PBKDF2-SHA256. Sessions use
            revocable signed tokens.
          </p>
        </div>
      </section>
    </div>
  );
}