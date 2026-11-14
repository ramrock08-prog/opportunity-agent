
import { useEffect, useMemo, useState } from "react";
import "./App.css";
import ProfileEditor from "./ProfileEditor";

const API_BASE = "http://127.0.0.1:8000";

const CATEGORIES = [
  { label: "All opportunities", value: "all" },
  { label: "Internships", value: "internship" },
  { label: "Hackathons", value: "hackathon" },
  { label: "Jobs", value: "job" },
  { label: "Scholarships", value: "scholarship" },
  { label: "Fellowships", value: "fellowship" },
  { label: "Competitions", value: "competition" },
  { label: "Research", value: "research" },
];

function formatDate(value) {
  if (!value) return "Not specified";

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function App() {
  const [opportunities, setOpportunities] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [profile, setProfile] = useState(null);

  // Bookmark state
  const [bookmarks, setBookmarks] = useState([]);
  const [bookmarkBusy, setBookmarkBusy] = useState({});
  const [bookmarkMessage, setBookmarkMessage] = useState("");

  // Dashboard state
  const [activeCategory, setActiveCategory] = useState("all");
  const [activeView, setActiveView] = useState("discover");
  const [searchText, setSearchText] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  // Discovery state
  const [discovering, setDiscovering] = useState(false);
  const [discoveryMessage, setDiscoveryMessage] = useState("");

  // Load opportunities, recommendations, and bookmarks
  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const [
          opportunitiesResponse,
          recommendationsResponse,
          bookmarksResponse,
        ] = await Promise.all([
          fetch(`${API_BASE}/api/opportunities`),
          fetch(`${API_BASE}/api/recommendations`),
          fetch(`${API_BASE}/api/bookmarks`),
        ]);

        if (
          !opportunitiesResponse.ok ||
          !recommendationsResponse.ok ||
          !bookmarksResponse.ok
        ) {
          throw new Error(
            "The backend returned an unsuccessful response."
          );
        }

        const [
          opportunitiesData,
          recommendationsData,
          bookmarksData,
        ] = await Promise.all([
          opportunitiesResponse.json(),
          recommendationsResponse.json(),
          bookmarksResponse.json(),
        ]);

        if (cancelled) return;

        setOpportunities(opportunitiesData.opportunities || []);
        setRecommendations(
          recommendationsData.recommendations || []
        );
        setProfile(recommendationsData.profile || null);
        setBookmarks(bookmarksData.bookmarks || []);
      } catch {
        if (!cancelled) {
          setError(
            "Unable to connect to the backend. Make sure FastAPI is running on port 8000."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  // Trigger a limited discovery run
  async function handleDiscover() {
    setDiscovering(true);
    setDiscoveryMessage("");

    try {
      const category =
        activeCategory === "all" ? "internship" : activeCategory;

      const response = await fetch(`${API_BASE}/api/discover`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          category,
          limit: 3,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Discovery failed. Check the backend terminal."
        );
      }

      setDiscoveryMessage(
        `Discovery completed for ${category}. Refreshing results...`
      );

      setReloadKey((value) => value + 1);
    } catch (err) {
      setDiscoveryMessage(
        err.message || "Could not complete discovery."
      );
    } finally {
      setDiscovering(false);
    }
  }

  // Save or remove a bookmark through FastAPI
  async function handleBookmark(item) {
    const url = item.source_url;

    if (!url) {
      setBookmarkMessage("This opportunity has no source URL.");
      return;
    }

    const isSaved = bookmarks.includes(url);

    setBookmarkBusy((current) => ({
      ...current,
      [url]: true,
    }));
    setBookmarkMessage("");

    try {
      const response = isSaved
        ? await fetch(
            `${API_BASE}/api/bookmarks?url=${encodeURIComponent(url)}`,
            { method: "DELETE" }
          )
        : await fetch(`${API_BASE}/api/bookmarks`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ url }),
          });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Could not update the bookmark."
        );
      }

      setBookmarks(data.bookmarks || []);

      setBookmarkMessage(
        isSaved
          ? "Opportunity removed from your saved list."
          : "Opportunity saved to your bookmarks."
      );
    } catch (err) {
      setBookmarkMessage(
        err.message || "Could not update the bookmark."
      );
    } finally {
      setBookmarkBusy((current) => ({
        ...current,
        [url]: false,
      }));
    }
  }

  // Filter opportunities and attach their recommendation scores
  const visibleOpportunities = useMemo(() => {
    const scoreByUrl = new Map(
      recommendations.map((item) => [
        item.opportunity?.source_url,
        item.score,
      ])
    );

    const scoreByTitle = new Map(
      recommendations.map((item) => [
        item.opportunity?.title,
        item.score,
      ])
    );

    let results = opportunities.map((item) => ({
      ...item,
      matchScore:
        scoreByUrl.get(item.source_url) ??
        scoreByTitle.get(item.title),
    }));

    if (activeView === "recommended") {
      results = results
        .filter((item) => item.matchScore !== undefined)
        .sort((a, b) => b.matchScore - a.matchScore);
    }

    if (activeView === "saved") {
      results = results.filter((item) =>
        bookmarks.includes(item.source_url)
      );
    }

    if (activeCategory !== "all") {
      results = results.filter(
        (item) => item.type === activeCategory
      );
    }

    const query = searchText.trim().toLowerCase();

    if (query) {
      results = results.filter((item) => {
        const searchableText = [
          item.title,
          item.organization,
          item.description,
          item.location,
          ...(item.fields || []),
          ...(item.required_skills || []),
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return searchableText.includes(query);
      });
    }

    return results;
  }, [
    opportunities,
    recommendations,
    bookmarks,
    activeView,
    activeCategory,
    searchText,
  ]);

  const categoryCount = new Set(
    opportunities.map((item) => item.type)
  ).size;

  const averageScore = recommendations.length
    ? Math.round(
        recommendations.reduce(
          (total, item) => total + item.score,
          0
        ) / recommendations.length
      )
    : 0;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#dashboard">
          <span className="brand-mark">OA</span>
          <span>
            <strong>Opportunity</strong>
            <small>AGENT PLATFORM</small>
          </span>
        </a>

        <div className="sidebar-label">WORKSPACE</div>

        <button
          className={`side-link ${
            activeView === "discover" ? "selected" : ""
          }`}
          onClick={() => setActiveView("discover")}
        >
          <span className="side-icon">⌕</span>
          Discover
        </button>

        <button
          className={`side-link ${
            activeView === "recommended" ? "selected" : ""
          }`}
          onClick={() => setActiveView("recommended")}
        >
          <span className="side-icon">✳</span>
          For you
        </button>

        <button
          className={`side-link ${
            activeView === "saved" ? "selected" : ""
          }`}
          onClick={() => setActiveView("saved")}
        >
          <span className="side-icon">★</span>
          Saved opportunities
        </button>

        <div className="sidebar-label second-label">YOUR PROFILE</div>

        <div className="profile-mini">
          <div className="avatar">R</div>
          <div>
            <strong>
              {profile?.degree || "Student"} {profile?.branch || ""}
            </strong>
            <span>
              {profile?.year_of_study
                ? `Year ${profile.year_of_study}`
                : "Student profile"}
            </span>
          </div>
        </div>

        <div className="sidebar-bottom">
          <div className="status-dot" />
          <span>AI discovery workspace</span>
        </div>
      </aside>

      <main className="main-content" id="dashboard">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span>{" "}
            {activeView === "recommended"
              ? "For you"
              : activeView === "saved"
                ? "Saved opportunities"
                : "Discover"}
          </div>

          <div className="topbar-right">
            <span
              className={`connection-pill ${
                error ? "disconnected" : ""
              }`}
            >
              <span className="connection-dot" />
              {loading
                ? "Connecting"
                : error
                  ? "Backend offline"
                  : "Backend connected"}
            </span>

            <button
              className="refresh-button"
              onClick={() => setReloadKey((value) => value + 1)}
              disabled={loading}
            >
              ↻ <span>Refresh</span>
            </button>
          </div>
        </header>

        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="sparkle">✦</span>
              YOUR NEXT OPPORTUNITY STARTS HERE
            </div>

            <h1>
              Find your next
              <br />
              <span>big opportunity.</span>
            </h1>

            <p>
              Discover internships, hackathons, research programs,
              and more—all organized in one place and matched to
              your interests.
            </p>

            <button
              className="primary-button"
              onClick={() => {
                setActiveView("discover");
                setActiveCategory("all");
                setSearchText("");
              }}
            >
              Explore opportunities <span>→</span>
            </button>
          </div>

          <div className="hero-art" aria-hidden="true">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="hero-orb">✦</div>
            <div className="floating-tag tag-one">
              <span>✳</span> AI-powered matching
            </div>
            <div className="floating-tag tag-two">
              <span>↗</span> Career discovery
            </div>
          </div>
        </section>

        <ProfileEditor
          onSaved={() => setReloadKey((value) => value + 1)}
        />

        {error && (
          <div className="error-banner">
            <strong>Connection problem</strong>
            <span>{error}</span>
            <button onClick={() => setReloadKey((value) => value + 1)}>
              Retry
            </button>
          </div>
        )}

        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon purple">◇</div>
            <div className="stat-label">Available opportunities</div>
            <div className="stat-value">
              {loading ? "—" : opportunities.length}
            </div>
            <div className="stat-foot">Validated saved records</div>
          </div>

          <div className="stat-card">
            <div className="stat-icon blue">✳</div>
            <div className="stat-label">Categories represented</div>
            <div className="stat-value">
              {loading ? "—" : categoryCount}
            </div>
            <div className="stat-foot">Across your saved data</div>
          </div>

          <div className="stat-card">
            <div className="stat-icon green">↗</div>
            <div className="stat-label">Average match score</div>
            <div className="stat-value">
              {loading ? "—" : `${averageScore}%`}
            </div>
            <div className="stat-foot">
              Relevance estimate, not eligibility
            </div>
          </div>
        </section>

        <section className="opportunities-section">
          <div className="section-heading">
            <div>
              <div className="section-kicker">YOUR WORKSPACE</div>

              <h2>
                {activeView === "recommended"
                  ? "Recommended for you"
                  : activeView === "saved"
                    ? "Saved opportunities"
                    : "Explore opportunities"}
              </h2>

              <p>
                {activeView === "recommended"
                  ? "Ranked using your interests and profile."
                  : activeView === "saved"
                    ? "Your bookmarked opportunities, saved for later."
                    : "Search and filter the opportunities in your workspace."}
              </p>
            </div>

            <div className="section-actions">
              {activeView === "discover" && (
                <button
                  className="discover-button"
                  onClick={handleDiscover}
                  disabled={discovering || loading}
                >
                  {discovering
                    ? "Searching..."
                    : "✦ Find New Opportunities"}
                </button>
              )}

              <span className="result-count">
                {visibleOpportunities.length} results
              </span>
            </div>
          </div>

          {discoveryMessage && (
            <div className="discovery-message" role="status">
              {discoveryMessage}
            </div>
          )}

          {bookmarkMessage && (
            <div className="bookmark-message" role="status">
              {bookmarkMessage}
            </div>
          )}

          <div className="toolbar">
            <label className="search-box">
              <span>⌕</span>
              <input
                type="search"
                placeholder="Search title, organization, skill..."
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
              />
            </label>

            <button
              className="filter-reset"
              onClick={() => {
                setSearchText("");
                setActiveCategory("all");
              }}
            >
              Clear filters
            </button>
          </div>

          <div className="category-filters">
            {CATEGORIES.map((category) => (
              <button
                key={category.value}
                className={`category-chip ${
                  activeCategory === category.value ? "active" : ""
                }`}
                onClick={() => setActiveCategory(category.value)}
              >
                {category.label}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="empty-state">
              <div className="loading-spinner" />
              <h3>Loading your opportunities</h3>
              <p>Connecting to your Python backend...</p>
            </div>
          ) : visibleOpportunities.length === 0 ? (
            <div className="empty-state">
              <div className="empty-symbol">◇</div>

              <h3>
                {error
                  ? "Your workspace is waiting to connect"
                  : activeView === "saved"
                    ? "No saved opportunities yet"
                    : "No matching opportunities yet"}
              </h3>

              <p>
                {error
                  ? "Start the FastAPI backend and try refreshing."
                  : activeView === "saved"
                    ? "Use the Save button on an opportunity card to keep it here."
                    : "Try another category or search term. You can also run discovery to find more opportunities."}
              </p>

              <button
                className="secondary-button"
                onClick={() => {
                  setActiveCategory("all");
                  setSearchText("");
                  setActiveView("discover");
                }}
              >
                Explore all opportunities
              </button>
            </div>
          ) : (
            <div className="opportunity-grid">
              {visibleOpportunities.map((item) => {
                const isSaved = bookmarks.includes(item.source_url);
                const isBusy = Boolean(bookmarkBusy[item.source_url]);

                return (
                  <article
                    className="opportunity-card"
                    key={`${item.source_url}-${item.title}`}
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

                      <button
                        className={`bookmark-button ${
                          isSaved ? "saved" : ""
                        }`}
                        onClick={() => handleBookmark(item)}
                        disabled={isBusy}
                        aria-pressed={isSaved}
                        aria-label={
                          isSaved
                            ? `Remove ${item.title} from saved opportunities`
                            : `Save ${item.title}`
                        }
                      >
                        {isBusy
                          ? "Saving..."
                          : isSaved
                            ? "★ Saved"
                            : "☆ Save"}
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
                        Source: {item.source || "Web"}
                      </span>

                      {item.application_url ? (
                        <a
                          className="apply-link"
                          href={item.application_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          View opportunity <span>↗</span>
                        </a>
                      ) : (
                        <span className="muted-link">
                          No link available
                        </span>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <footer className="page-footer">
          <span>
            Opportunity Agent · AI-assisted opportunity discovery
          </span>
          <span>
            Relevance scores are estimates, not eligibility guarantees.
          </span>
        </footer>
      </main>
    </div>
  );
}

export default App;
