import { formatDate, hostLabel, safeHttpUrl } from "./utils";

export default function OpportunityCard({
  item,
  isSaved,
  isBusy,
  applicationStatus,
  onBookmark,
  onApply,
  onOpen,
}) {
  const applyUrl = safeHttpUrl(
    item.application_url || item.source_url
  );

  return (
    <article
      className="opportunity-card"
      data-source-url={item.source_url}
    >
      <div className="card-topline">
        <span className={`type-badge type-${item.type}`}>
          {item.type}
        </span>

        {item.matchScore !== undefined && (
          <span className="match-badge">
            {item.matchScore}% match
          </span>
        )}

        {applicationStatus && (
          <span className={`status-pill status-${applicationStatus}`}>
            {applicationStatus}
          </span>
        )}

        <button
          className={`bookmark-button ${isSaved ? "saved" : ""}`}
          onClick={() => onBookmark(item)}
          disabled={isBusy}
          aria-pressed={isSaved}
          aria-label={
            isSaved
              ? `Remove ${item.title} from saved opportunities`
              : `Save ${item.title}`
          }
        >
          {isBusy ? "Saving..." : isSaved ? "★ Saved" : "☆ Save"}
        </button>
      </div>

      <div className="company-line">
        <div className="company-avatar">
          {(item.organization || item.source || "O")
            .charAt(0)
            .toUpperCase()}
        </div>

        <span>
          {item.organization ||
            item.source ||
            "Organization not specified"}
        </span>
      </div>

      <h3>{item.title}</h3>

      <p className="card-description">
        {item.description ||
          "Description not provided by the source."}
      </p>

      <div className="metadata">
        <div>
          <span className="meta-label">LOCATION</span>
          <span>{item.location || "Not specified"}</span>
        </div>

        <div>
          <span className="meta-label">DEADLINE</span>
          <span>{formatDate(item.deadline)}</span>
        </div>
      </div>

      <div className="card-footer">
        <span className="source-label">
          Source: {item.source || hostLabel(item.source_url) || "Web"}
        </span>

        <div className="card-actions">
          <button
            className="apply-button"
            onClick={() => onApply(item)}
            disabled={!applyUrl}
            title={
              applyUrl
                ? "Open the official application page"
                : "No application link available"
            }
            aria-label={`Apply to ${item.title}`}
          >
            Apply
          </button>

          <button
            className="details-button"
            onClick={() => onOpen(item)}
            aria-label={`View details for ${item.title}`}
          >
            Details
          </button>

          {applyUrl && (
            <a
              className="apply-link"
              href={applyUrl}
              target="_blank"
              rel="noreferrer"
            >
              View opportunity <span>↗</span>
            </a>
          )}
        </div>
      </div>
    </article>
  );
}