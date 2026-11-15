import { useState } from "react";

import { safeHttpUrl } from "./utils";

const DETAIL_FIELDS = [
  ["name", "Name", "Your full name"],
  ["phone", "Phone", "+91 ..."],
  ["college", "College", "College or university"],
  ["degree", "Degree", "B.Tech"],
  ["branch", "Branch", "ECE"],
  ["graduation_year", "Graduation year", "2027"],
  ["github", "GitHub", "https://github.com/..."],
  ["linkedin", "LinkedIn", "https://linkedin.com/in/..."],
  ["portfolio", "Portfolio", "https://your-site.com"],
];

export default function ApplyModal({
  item,
  profile,
  email,
  busy,
  onSaveDetails,
  onApply,
  onClose,
}) {
  const [form, setForm] = useState(() => ({
    name: profile?.name || "",
    phone: profile?.phone || "",
    college: profile?.college || "",
    degree: profile?.degree || "",
    branch: profile?.branch || "",
    graduation_year: profile?.graduation_year ?? "",
    github: profile?.github || "",
    linkedin: profile?.linkedin || "",
    portfolio: profile?.portfolio || "",
  }));
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const applyUrl = safeHttpUrl(
    item.application_url || item.source_url
  );

  const missingCore = !form.name || !form.phone || !form.college;

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handlePrimary() {
    setError("");

    try {
      await onSaveDetails({
        ...form,
        graduation_year:
          form.graduation_year === ""
            ? null
            : Number(form.graduation_year),
      });
      onApply(item);
    } catch (err) {
      setError(
        err.message || "Could not save your application details."
      );
    }
  }

  async function copyAll() {
    const text = [
      `Name: ${form.name}`,
      `Email: ${email || ""}`,
      `Phone: ${form.phone}`,
      `College: ${form.college}`,
      `Degree: ${form.degree} ${form.branch}`,
      `Graduation year: ${form.graduation_year || ""}`,
      `Skills: ${(profile?.skills || []).join(", ")}`,
      `GitHub: ${form.github}`,
      `LinkedIn: ${form.linkedin}`,
      `Portfolio: ${form.portfolio}`,
    ].join("\n");

    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div
      className="detail-overlay"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside
        className="detail-panel apply-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="apply-title"
      >
        <header className="detail-header">
          <div className="detail-heading">
            <span className="type-badge type-internship">
              Apply
            </span>
            <h2 id="apply-title">{item.title}</h2>
            <p>
              {item.organization ||
                item.source ||
                "Organization not specified"}
            </p>
          </div>

          <button
            className="detail-close"
            onClick={onClose}
            aria-label="Close apply panel"
          >
            ✕
          </button>
        </header>

        <div className="detail-body">
          <p className="detail-empty">
            Your saved details are ready to paste into the official
            application. External sites cannot be auto-filled, but
            nothing is lost: copy everything in one click.
          </p>

          {missingCore && (
            <div className="apply-warning" role="alert">
              Add your name, phone, and college so applications carry
              complete details. They will be saved to your profile.
            </div>
          )}

          <div className="apply-grid">
            {DETAIL_FIELDS.map(([field, label, placeholder]) => (
              <label key={field}>
                {label}
                <input
                  value={form[field]}
                  onChange={(event) =>
                    update(field, event.target.value)
                  }
                  placeholder={placeholder}
                  maxLength={field === "college" ? 150 : 300}
                />
              </label>
            ))}
          </div>

          <div className="apply-summary">
            <span className="meta-label">EMAIL</span>
            <strong>{email || "Account email"}</strong>
            <span className="meta-label">SKILLS</span>
            <strong>
              {(profile?.skills || []).join(", ") || "None saved"}
            </strong>
          </div>

          {error && (
            <div className="apply-warning" role="alert">
              {error}
            </div>
          )}
        </div>

        <footer className="detail-footer apply-footer">
          <button
            type="button"
            className="share-button"
            onClick={copyAll}
          >
            {copied ? "Copied" : "Copy all details"}
          </button>

          <button
            type="button"
            className="primary-button detail-apply"
            disabled={busy || !applyUrl}
            onClick={handlePrimary}
          >
            {busy
              ? "Saving..."
              : "Save details & open application"}
          </button>
        </footer>
      </aside>
    </div>
  );
}