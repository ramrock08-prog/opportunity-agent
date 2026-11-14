import { useEffect, useState } from "react";

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

  function openEditor() {
    setOpen(true);
    setMessage("");
    setError("");
  }

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
              : "Help the agent discover opportunities that suit you."}
          </p>
        </div>

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