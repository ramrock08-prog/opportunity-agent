
import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";
import OpportunityCard from "./OpportunityCard";
import OpportunityDetail from "./OpportunityDetail";
import ProfileEditor from "./ProfileEditor";
import AuthScreen from "./AuthScreen";
import {
  apiFetch,
  clearAuthToken,
  errorMessage,
  getAuthToken,
  readJson,
} from "./api";

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
  const [sortMode, setSortMode] = useState("match");
  const [detailItem, setDetailItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  // Discovery state
  const [discovering, setDiscovering] = useState(false);
  const [discoveryMessage, setDiscoveryMessage] = useState("");

  // Authentication state
  const [authStatus, setAuthStatus] = useState(null);
  const [authUser, setAuthUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authReloadKey, setAuthReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function bootstrapAuth() {
      try {
        const response = await apiFetch("/api/auth/status");
        const data = await readJson(response);

        if (cancelled) return;

        setAuthStatus(data);

        if (data.auth_required && getAuthToken()) {
          const meResponse = await apiFetch("/api/auth/me");

          if (meResponse.ok) {
            const meData = await readJson(meResponse);
            if (!cancelled) setAuthUser(meData.user || null);
          } else {
            clearAuthToken();
          }
        }
      } catch {
        if (!cancelled) {
          setError(
            "Unable to connect to the backend. Make sure FastAPI is running on port 8000."
          );
        }
      } finally {
        if (!cancelled) setAuthLoading(false);
      }
    }

    bootstrapAuth();

    return () => {
      cancelled = true;
    };
  }, [authReloadKey]);

  // Load opportunities, recommendations, and bookmarks
  useEffect(() => {
    if (authLoading || !authStatus) return undefined;

    if (authStatus.auth_required && !authUser) {
      return undefined;
    }

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
          apiFetch("/api/opportunities"),
          apiFetch("/api/recommendations"),
          apiFetch("/api/bookmarks"),
        ]);

        if (
          [opportunitiesResponse, recommendationsResponse, bookmarksResponse]
            .some((response) => response.status === 401)
        ) {
          clearAuthToken();
          if (!cancelled) setAuthUser(null);
          return;
        }

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
  }, [reloadKey, authLoading, authStatus, authUser]);

  // Trigger a limited discovery run
  async function handleDiscover() {
    setDiscovering(true);
    setDiscoveryMessage("");

    try {
      const category =
        activeCategory === "all" ? "internship" : activeCategory;

      const response = await apiFetch("/api/discover", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          category,
          limit: 3,
        }),
      });

      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          errorMessage(
            data,
            "Discovery failed. Check the backend terminal."
          )
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
        ? await apiFetch(
            `/api/bookmarks?url=${encodeURIComponent(url)}`,
            { method: "DELETE" }
          )
        : await apiFetch("/api/bookmarks", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ url }),
          });

      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          errorMessage(data, "Could not update the bookmark.")
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

  function retryConnection() {
    setAuthReloadKey((value) => value + 1);
    setReloadKey((value) => value + 1);
  }

  async function handleLogout() {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
    } catch {
      // Clearing the local token still signs this browser out.
    }

    clearAuthToken();
    setAuthUser(null);
    setOpportunities([]);
    setRecommendations([]);
    setBookmarks([]);
    setProfile(null);
    setDetailItem(null);
    setActiveView("discover");
  }

  const handleAuthenticated = useCallback((user) => {
    setAuthUser(user);
    setReloadKey((value) => value + 1);
  }, []);

  // Filter opportunities and attach their recommendation scores
  const visibleOpportunities = useMemo(() => {
    const matchByUrl = new Map(
      recommendations.map((item) => [
        item.opportunity?.source_url,
        item,
      ])
    );

    const matchByTitle = new Map(
      recommendations.map((item) => [
        item.opportunity?.title,
        item,
      ])
    );

    let results = opportunities.map((item) => {
      const match =
        matchByUrl.get(item.source_url) ??
        matchByTitle.get(item.title);

      return {
        ...item,
        matchScore: match?.score,
        matchReasons: match?.reasons || [],
      };
    });

    if (activeView === "recommended") {
      results = results.filter(
        (item) => item.matchScore !== undefined
      );
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

    if (sortMode === "deadline") {
      results = [...results].sort((a, b) =>
        (a.deadline || "9999-12-31").localeCompare(
          b.deadline || "9999-12-31"
        )
      );
    } else if (sortMode === "title") {
      results = [...results].sort((a, b) =>
        a.title.localeCompare(b.title)
      );
    } else if (activeView !== "recommended") {
      results = [...results].sort(
        (a, b) => (b.matchScore ?? -1) - (a.matchScore ?? -1)
      );
    }

    if (activeView === "recommended") {
      results = [...results].sort(
        (a, b) => b.matchScore - a.matchScore
      );
    }

    return results;
  }, [
    opportunities,
    recommendations,
    bookmarks,
    activeView,
    activeCategory,
    searchText,
    sortMode,
  ]);

  const categoryCount = new Set(
    opportunities.map((item) => item.type)
  ).size;

  if (authLoading) {
    return (
      <div className="auth-loading">
        <div className="loading-spinner" />
        <p>Preparing your workspace...</p>
      </div>
    );
  }

  if (authStatus?.auth_required && !authUser) {
    return (
      <AuthScreen
        warning={authStatus.warning}
        status={authStatus}
        onAuthenticated={handleAuthenticated}
      />
    );
  }

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
          <span className="side-count">{bookmarks.length}</span>
        </button>

        <div className="sidebar-label second-label">YOUR PROFILE</div>

        <div className="profile-mini">
          <div className="avatar">
            {(
              authUser?.name ||
              authUser?.email ||
              profile?.name ||
              "S"
            )
              .charAt(0)
              .toUpperCase()}
          </div>
          <div>
            <strong>
              {authUser?.name ||
                `${profile?.degree || "Student"} ${
                  profile?.branch || ""
                }`}
            </strong>
            <span>
              {profile?.year_of_study
                ? `Year ${profile.year_of_study}`
                : "Student profile"}
            </span>
          </div>
        </div>

        <div className="account-box">
          {authStatus?.auth_required ? (
            <>
              <span title={authUser?.email}>{authUser?.email}</span>
              <button onClick={handleLogout}>Sign out</button>
            </>
          ) : (
            <span>Demo workspace · sign-in disabled</span>
          )}
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
            <button onClick={retryConnection}>Retry</button>
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

            <label className="sort-control">
              <span>Sort</span>
              <select
                value={sortMode}
                onChange={(event) =>
                  setSortMode(event.target.value)
                }
              >
                <option value="match">Best match</option>
                <option value="deadline">Deadline soonest</option>
                <option value="title">Title A–Z</option>
              </select>
            </label>

            <button
              className="filter-reset"
              onClick={() => {
                setSearchText("");
                setActiveCategory("all");
                setSortMode("match");
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
              {visibleOpportunities.map((item) => (
                <OpportunityCard
                  key={`${item.source_url}-${item.title}`}
                  item={item}
                  isSaved={bookmarks.includes(item.source_url)}
                  isBusy={Boolean(bookmarkBusy[item.source_url])}
                  onBookmark={handleBookmark}
                  onOpen={setDetailItem}
                />
              ))}
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

      {detailItem && (
        <OpportunityDetail
          key={detailItem.source_url}
          item={detailItem}
          matchInfo={recommendations.find(
            (entry) =>
              entry.opportunity?.source_url ===
              detailItem.source_url
          )}
          isSaved={bookmarks.includes(detailItem.source_url)}
          isBusy={Boolean(bookmarkBusy[detailItem.source_url])}
          onBookmark={handleBookmark}
          onClose={() => setDetailItem(null)}
        />
      )}
    </div>
  );
}

export default App;
