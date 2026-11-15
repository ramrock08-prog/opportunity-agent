import { useEffect, useRef, useState } from "react";

import { apiFetch, errorMessage, readJson } from "./api";

const TYPES = [
  "hackathon",
  "internship",
  "job",
  "scholarship",
  "fellowship",
  "competition",
  "research",
  "other",
];

function toForm(profile) {
  return {
    ...profile,
    phone: profile.phone || "",
    college: profile.college || "",
    graduation_year: profile.graduation_year ?? "",
    github: profile.github || "",
    linkedin: profile.linkedin || "",
    portfolio: profile.portfolio || "",
    year_of_study: profile.year_of_study ?? "",
    skills: (profile.skills || []).join(", "),
    interests: (profile.interests || []).join(", "),
    preferred_locations: (
      profile.preferred_locations || []
    ).join(", "),
    opportunity_types: profile.opportunity_types || [],
  };
}

function toList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function ProfileEditor({
  onSaved,
  initiallyOpen = false,
}) {
  const [open, setOpen] = useState(initiallyOpen);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [resumeBusy, setResumeBusy] = useState(false);
  const [resumeMessage, setResumeMessage] = useState("");
  const [resumeError, setResumeError] = useState("");
  const fileInputRef = useRef(null);
  const pendingResumeOpen = useRef(false);

  function openEditor() {
    setOpen(true);
    setMessage("");
    setError("");
  }

  function startResumeImport() {
    setMessage("");
    setError("");
    setResumeError("");

    if (open) {
      fileInputRef.current?.click();
      return;
    }

    pendingResumeOpen.current = true;
    setOpen(true);
  }

  useEffect(() => {
    if (open && pendingResumeOpen.current) {
      pendingResumeOpen.current = false;
      fileInputRef.current?.click();
    }
  }, [open, form]);

  // Load once when the editor opens, including the first-run auto-open.
  useEffect(() => {
    if (!open || form) return undefined;

    let active = true;

    apiFetch("/api/profile")
      .then(async (response) => ({
        ok: response.ok,
        data: await readJson(response),
      }))
      .then(({ ok, data }) => {
        if (!active) return;

        if (!ok) {
          setError(
            errorMessage(data, "Could not load profile.")
          );
          return;
        }

        setForm(toForm(data));
      })
      .catch(() => {
        if (active) setError("Could not load profile.");
      });

    return () => {
      active = false;
    };
  }, [open, form]);

  async function handleResumeFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";

    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setResumeError("Choose a resume smaller than 5 MB.");
      return;
    }

    setResumeBusy(true);
    setResumeError("");
    setResumeMessage("");

    try {
      const body = new FormData();
      body.append("file", file);

      const response = await apiFetch(
        "/api/profile/import-resume",
        { method: "POST", body }
      );
      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          errorMessage(data, "Could not read the resume.")
        );
      }

      setForm(toForm(data.profile));
      setResumeMessage(
        `Imported ${data.filename}. Review the fields below, then save your profile.`
      );
    } catch (err) {
      setResumeError(
        err.message || "Could not read the resume."
      );
    } finally {
      setResumeBusy(false);
    }
  }

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function toggleType(type) {
    setForm((current) => ({
      ...current,
      opportunity_types: current.opportunity_types.includes(type)
        ? current.opportunity_types.filter((item) => item !== type)
        : [...current.opportunity_types, type],
    }));
  }

  async function saveProfile(event) {
    event.preventDefault();

    if (!form) return;

    setSaving(true);
    setError("");
    setMessage("");

    const payload = {
      name: form.name,
      degree: form.degree,
      branch: form.branch,
      year_of_study:
        form.year_of_study === ""
          ? null
          : Number(form.year_of_study),
      skills: toList(form.skills),
      interests: toList(form.interests),
      preferred_locations: toList(form.preferred_locations),
      remote_preferred: form.remote_preferred,
      opportunity_types: form.opportunity_types,
      phone: form.phone,
      college: form.college,
      graduation_year:
        form.graduation_year === ""
          ? null
          : Number(form.graduation_year),
      github: form.github,
      linkedin: form.linkedin,
      portfolio: form.portfolio,
    };

    try {
      const response = await apiFetch("/api/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          errorMessage(data, "Could not save profile.")
        );
      }

      setForm(toForm(data.profile));
      setMessage("Profile saved. Recommendations are refreshing.");
      onSaved?.();
    } catch (err) {
      setError(err.message || "Could not save profile.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section
      className="profile-editor-section"
      id="profile-settings"
    >
      <div className="profile-editor-heading">
        <div>
          <div className="section-kicker">PERSONALIZATION</div>
          <h2>
            {initiallyOpen ? "Set up your profile" : "Profile settings"}
          </h2>
          <p>
            {initiallyOpen
              ? "Tell us what you study and what you are interested in so recommendations are relevant."
              : "Import a resume to auto-fill your details, or edit the profile manually."}
          </p>
        </div>

        <div className="profile-heading-actions">
          <button
            className="resume-heading-button"
            onClick={startResumeImport}
          >
            Import resume
          </button>

          <button
            className="discover-button"
            onClick={() => {
              if (open) {
                setOpen(false);
              } else {
                openEditor();
              }
            }}
          >
            {open ? "Close editor" : "Edit profile"}
          </button>
        </div>
      </div>

      {message && (
        <div className="profile-message" role="status">
          {message}
        </div>
      )}

      {error && (
        <div className="profile-error" role="alert">
          {error}
        </div>
      )}

      {open && (
        <div className="profile-editor-card">
          <div className="resume-import">
            <div>
              <strong>Import your resume or CV</strong>
              <span>
                PDF, DOCX, or TXT up to 5 MB. AI fills the fields;
                review them before saving.
              </span>
            </div>

            <label
              className={`resume-upload ${resumeBusy ? "busy" : ""}`}
            >
              {resumeBusy ? "Reading resume..." : "Upload resume"}
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleResumeFile}
                disabled={resumeBusy}
              />
            </label>
          </div>

          {resumeMessage && (
            <div className="resume-message" role="status">
              {resumeMessage}
            </div>
          )}

          {resumeError && (
            <div className="profile-error" role="alert">
              {resumeError}
            </div>
          )}

          {!form ? (
            <p>Loading your profile...</p>
          ) : (
            <form onSubmit={saveProfile}>
              <div className="profile-form-grid">
                <label>
                  Name
                  <input
                    value={form.name}
                    onChange={(e) => updateField("name", e.target.value)}
                    maxLength={100}
                  />
                </label>

                <label>
                  Degree
                  <input
                    value={form.degree}
                    onChange={(e) => updateField("degree", e.target.value)}
                    placeholder="B.Tech"
                    maxLength={100}
                  />
                </label>

                <label>
                  Branch
                  <input
                    value={form.branch}
                    onChange={(e) => updateField("branch", e.target.value)}
                    placeholder="ECE"
                    maxLength={100}
                  />
                </label>

                <label>
                  Year of study
                  <select
                    value={form.year_of_study}
                    onChange={(e) =>
                      updateField("year_of_study", e.target.value)
                    }
                  >
                    <option value="">Not specified</option>
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((year) => (
                      <option key={year} value={year}>
                        Year {year}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Phone
                  <input
                    value={form.phone}
                    onChange={(e) => updateField("phone", e.target.value)}
                    placeholder="+91 ..."
                    maxLength={30}
                  />
                </label>

                <label>
                  College
                  <input
                    value={form.college}
                    onChange={(e) => updateField("college", e.target.value)}
                    placeholder="College or university"
                    maxLength={150}
                  />
                </label>

                <label>
                  Graduation year
                  <input
                    type="number"
                    min="2000"
                    max="2100"
                    value={form.graduation_year}
                    onChange={(e) =>
                      updateField("graduation_year", e.target.value)
                    }
                    placeholder="2027"
                  />
                </label>

                <label className="full-width">
                  GitHub
                  <input
                    value={form.github}
                    onChange={(e) => updateField("github", e.target.value)}
                    placeholder="https://github.com/..."
                    maxLength={300}
                  />
                </label>

                <label className="full-width">
                  LinkedIn
                  <input
                    value={form.linkedin}
                    onChange={(e) => updateField("linkedin", e.target.value)}
                    placeholder="https://linkedin.com/in/..."
                    maxLength={300}
                  />
                </label>

                <label className="full-width">
                  Portfolio
                  <input
                    value={form.portfolio}
                    onChange={(e) =>
                      updateField("portfolio", e.target.value)
                    }
                    placeholder="https://your-site.com"
                    maxLength={300}
                  />
                </label>

                <label className="full-width">
                  Skills
                  <input
                    value={form.skills}
                    onChange={(e) => updateField("skills", e.target.value)}
                    placeholder="Python, C++, React"
                  />
                  <small>Separate skills with commas.</small>
                </label>

                <label className="full-width">
                  Interests
                  <input
                    value={form.interests}
                    onChange={(e) =>
                      updateField("interests", e.target.value)
                    }
                    placeholder="AI, Machine Learning, Software Engineering"
                  />
                  <small>Separate interests with commas.</small>
                </label>

                <label className="full-width">
                  Preferred locations
                  <input
                    value={form.preferred_locations}
                    onChange={(e) =>
                      updateField("preferred_locations", e.target.value)
                    }
                    placeholder="India, Delhi, Remote"
                  />
                  <small>Separate locations with commas.</small>
                </label>
              </div>

              <label className="remote-option">
                <input
                  type="checkbox"
                  checked={form.remote_preferred}
                  onChange={(e) =>
                    updateField("remote_preferred", e.target.checked)
                  }
                />
                Prefer remote opportunities
              </label>

              <fieldset className="type-fieldset">
                <legend>Opportunity types</legend>

                <div className="type-checkbox-grid">
                  {TYPES.map((type) => (
                    <label key={type}>
                      <input
                        type="checkbox"
                        checked={form.opportunity_types.includes(type)}
                        onChange={() => toggleType(type)}
                      />
                      <span>{type}</span>
                    </label>
                  ))}
                </div>
              </fieldset>

              <button
                className="discover-button save-profile-button"
                type="submit"
                disabled={saving}
              >
                {saving ? "Saving..." : "Save profile"}
              </button>
            </form>
          )}
        </div>
      )}
    </section>
  );
}