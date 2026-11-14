import { useEffect, useState } from "react";
import { apiFetch, errorMessage, readJson } from "./api";
import {
  deadlineLabel,
  formatDate,
  hostLabel,
  safeHttpUrl,
} from "./utils";

const STATUS_LABELS = {
  reachable: "Reachable",
  blocked: "Automated check blocked",
  unreachable: "Unreachable",
  timeout: "Timed out",
  invalid: "Invalid URL",
};

function Value({ label, children }) {
  return (
    <div className="detail-value">
      <span className="meta-label">{label}</span>
      <span>{children || "Not specified"}</span>
    </div>
  );
}

function TagList({ title, values, emptyText }) {
  const items = (values || []).filter(Boolean);

  return (
    <section className="detail-section">
      <h4>{title}</h4>

      {items.length ? (
        <ul className="tag-list">
          {items.map((value) => (
            <li key={value}>{value}</li>
          ))}
        </ul>
      ) : (
        <p className="detail-empty">{emptyText}</p>
      )}
    </section>
  );
}

export default function OpportunityDetail({
  item,
  matchInfo,
  isSaved,
  isBusy,
  onBookmark,
  onClose,
}) {
  const [verification, setVerification] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState("");

  async function runLinkCheck() {
    setVerifying(true);
    setVerifyError("");

    try {
      const response = await apiFetch(
        "/api/opportunities/verify",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source_url: item.source_url,
          }),
        }
      );

      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          errorMessage(data, "Could not check the links.")
        );
      }

      setVerification(data.verification);
    } catch (error) {
      setVerifyError(
        error.message || "Could not check the links."
      );
    } finally {
      setVerifying(false);
    }
  }

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("keydown", handleKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [onClose]);

  if (!item) return null;

  const applyUrl = safeHttpUrl(
    item.application_url || item.source_url
  );
  const sourceUrl = safeHttpUrl(item.source_url);
  const sameDestination =
    applyUrl && sourceUrl && applyUrl === sourceUrl;

  return (
    <div
      className="detail-overlay"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside
        className="detail-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-title"
      >
        <header className="detail-header">
          <div className="detail-heading">
            <span className={`type-badge type-${item.type}`}>
              {item.type}
            </span>
            <h2 id="detail-title">{item.title}</h2>
            <p>
              {item.organization ||
                item.source ||
                "Organization not specified"}
            </p>
          </div>

          <button
            className="detail-close"
            onClick={onClose}
            aria-label="Close opportunity details"
          >
            ✕
          </button>
        </header>

        <div className="detail-body">
          {item.matchScore !== undefined && (
            <div className="detail-match">
              <strong>{item.matchScore}% relevance match</strong>
              <span>
                A relevance estimate from your profile, not an
                eligibility decision.
              </span>

              {matchInfo?.reasons?.length > 0 && (
                <ul>
                  {matchInfo.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <p className="detail-description">
            {item.description ||
              "No description was extracted from the source page."}
          </p>

          <div className="detail-grid">
            <Value label="LOCATION">{item.location}</Value>
            <Value label="DEADLINE">
              {formatDate(item.deadline)}
              <small className="detail-subtle">
                {deadlineLabel(item.deadline)}
              </small>
            </Value>
            <Value label="START DATE">{formatDate(item.start_date)}</Value>
            <Value label="REMOTE">
              {item.remote === true
                ? "Remote"
                : item.remote === false
                  ? "On-site"
                  : "Not stated"}
            </Value>
            <Value label="STIPEND">{item.stipend}</Value>
            <Value label="PRIZE">{item.prize_money}</Value>
            <Value label="EXTRACTION CONFIDENCE">
              {typeof item.confidence === "number"
                ? `${Math.round(item.confidence * 100)}%`
                : "Not available"}
            </Value>
            <Value label="SOURCE HOST">
              {hostLabel(item.source_url) || "Unknown"}
            </Value>
          </div>

          <TagList
            title="Eligibility"
            values={item.eligibility}
            emptyText="No eligibility details were published in the extracted source."
          />

          <TagList
            title="Required skills"
            values={item.required_skills}
            emptyText="No required skills were listed in the extracted source."
          />

          <TagList
            title="Fields / disciplines"
            values={item.fields}
            emptyText="No fields were listed."
          />

          <TagList
            title="Degree requirements"
            values={item.degree_requirements}
            emptyText="No degree requirements were published."
          />

          <TagList
            title="Year requirements"
            values={item.year_requirements}
            emptyText="No year requirements were published."
          />

          <section className="detail-section">
            <h4>Source evidence</h4>

            {item.evidence?.length ? (
              <ul className="evidence-list">
                {item.evidence.map((quote) => (
                  <li key={quote}>“{quote}”</li>
                ))}
              </ul>
            ) : (
              <p className="detail-empty">
                No verbatim evidence snippets were stored for this
                record. Treat the extracted facts with extra caution.
              </p>
            )}

            {item.deadline_evidence && (
              <p className="deadline-evidence">
                Deadline evidence: “{item.deadline_evidence}”
              </p>
            )}
          </section>

          <section className="detail-section">
            <h4>Where the data came from</h4>

            <div className="detail-links">
              {sourceUrl && (
                <a
                  href={sourceUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  Source page ↗
                  <small>{hostLabel(sourceUrl)}</small>
                </a>
              )}

              {applyUrl && (
                <a
                  href={applyUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  {sameDestination
                    ? "Listing / application page ↗"
                    : "Application page ↗"}
                  <small>{hostLabel(applyUrl)}</small>
                </a>
              )}
            </div>

            <div className="verify-block">
              <div className="verify-heading">
                <div>
                  <strong>Live link check</strong>
                  <span>
                    Runs on demand so discovery does not slow down.
                  </span>
                </div>

                <button
                  className="verify-button"
                  onClick={runLinkCheck}
                  disabled={verifying}
                >
                  {verifying ? "Checking..." : "Check links now"}
                </button>
              </div>

              {verifyError && (
                <p className="verify-error" role="alert">
                  {verifyError}
                </p>
              )}

              {verification && (
                <div className="verify-results">
                  {[
                    ["Application", verification.application],
                    ["Source page", verification.source],
                  ].map(([label, result]) => (
                    <div className="verify-row" key={label}>
                      <span className="verify-label">{label}</span>
                      <span
                        className={`verify-pill status-${
                          result?.status || "invalid"
                        }`}
                      >
                        {STATUS_LABELS[result?.status] ||
                          "Unknown"}
                      </span>
                      <span className="verify-message">
                        {result?.status_code
                          ? `HTTP ${result.status_code}. `
                          : ""}
                        {result?.message}
                      </span>
                    </div>
                  ))}

                  <p className="verify-note">
                    {verification.deadline?.message}{" "}
                    {verification.disclaimer}
                  </p>
                </div>
              )}
            </div>

            <p className="detail-disclaimer">
              This record was extracted automatically. A link being
              reachable does not prove that applications are open,
              that a deadline is correct, or that you are eligible.
              Always confirm on the official page before applying.
            </p>
          </section>
        </div>

        <footer className="detail-footer">
          <button
            className={`bookmark-button ${isSaved ? "saved" : ""}`}
            onClick={() => onBookmark(item)}
            disabled={isBusy}
            aria-pressed={isSaved}
          >
            {isBusy ? "Saving..." : isSaved ? "★ Saved" : "☆ Save opportunity"}
          </button>

          {applyUrl ? (
            <a
              className="primary-button detail-apply"
              href={applyUrl}
              target="_blank"
              rel="noreferrer"
            >
              Open official listing <span>↗</span>
            </a>
          ) : (
            <span className="muted-link">No application link available</span>
          )}
        </footer>
      </aside>
    </div>
  );
}