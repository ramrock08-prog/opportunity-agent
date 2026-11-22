
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
import { daysUntil } from "./utils";

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

  // Application tracker state
  const [applications, setApplications] = useState([]);
  const [applicationBusy, setApplicationBusy] = useState(false);
  const [applicationMessage, setApplicationMessage] = useState("");

  // Advanced filter state
  const [filterPanelOpen, setFilterPanelOpen] = useState(false);
  const [workMode, setWorkMode] = useState("any");
  const [deadlineWindow, setDeadlineWindow] = useState("any");
  const [paidOnly, setPaidOnly] = useState(false);
  const [skillMatchOnly, setSkillMatchOnly] = useState(false);
  const [locationFilter, setLocationFilter] = useState("");
  const [applicationFilter, setApplicationFilter] = useState("all");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [pagination, setPagination] = useState({
    key: "",
    count: 24,
  });

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
  const [syncingCurated, setSyncingCurated] = useState(false);
  const [curatedMessage, setCuratedMessage] = useState("");
  const [autoDiscovery, setAutoDiscovery] = useState({
    active: false,
    message: "",
  });

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
          applicationsResponse,
        ] = await Promise.all([
          apiFetch("/api/opportunities"),
          apiFetch("/api/recommendations"),
          apiFetch("/api/bookmarks"),
          apiFetch("/api/applications"),
        ]);

        if (
          [
            opportunitiesResponse,
            recommendationsResponse,
            bookmarksResponse,
            applicationsResponse,
          ].some((response) => response.status === 401)
        ) {
          clearAuthToken();
          if (!cancelled) setAuthUser(null);
          return;
        }

        if (
          !opportunitiesResponse.ok ||
          !recommendationsResponse.ok ||
          !bookmarksResponse.ok ||
          !applicationsResponse.ok
        ) {
          throw new Error(
            "The backend returned an unsuccessful response."
          );
        }

        const [
          opportunitiesData,
          recommendationsData,
          bookmarksData,
          applicationsData,
        ] = await Promise.all([
          opportunitiesResponse.json(),
          recommendationsResponse.json(),
          bookmarksResponse.json(),
          applicationsResponse.json(),
        ]);

        if (cancelled) return;

        setOpportunities(opportunitiesData.opportunities || []);
        setRecommendations(
          recommendationsData.recommendations || []
        );
        setProfile(recommendationsData.profile || null);
        setBookmarks(bookmarksData.bookmarks || []);
        setApplications(applicationsData.applications || []);
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
          limit: 8,
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

  async function handleCuratedImport() {
    setSyncingCurated(true);
    setCuratedMessage("");

    try {
      const response = await apiFetch("/api/discover/curated", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ country: "India", limit: 200 }),
      });
      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          errorMessage(
            data,
            "Could not sync curated internships."
          )
        );
      }

      setCuratedMessage(
        `Synced curated internships: ${data.stats.added} new, ${data.count} total records.`
      );
      setReloadKey((value) => value + 1);
    } catch (err) {
      setCuratedMessage(
        err.message || "Could not sync curated internships."
      );
    } finally {
      setSyncingCurated(false);
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

  async function handleApplicationStatus(
    item,
    status,
    note = ""
  ) {
    const url = item?.source_url;

    if (!url) {
      setApplicationMessage("This opportunity has no source URL.");
      return;
    }

    setApplicationBusy(true);
    setApplicationMessage("");

    try {
      const response = status
        ? await apiFetch("/api/applications", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              source_url: url,
              status,
              note,
            }),
          })
        : await apiFetch(
            `/api/applications?url=${encodeURIComponent(url)}`,
            { method: "DELETE" }
          );

      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          errorMessage(
            data,
            "Could not update the application tracker."
          )
        );
      }

      setApplications(data.applications || []);
      setApplicationMessage(
        status
          ? `Tracked as "${status}".`
          : "Removed from the application tracker."
      );
    } catch (err) {
      setApplicationMessage(
        err.message || "Could not update the application tracker."
      );
    } finally {
      setApplicationBusy(false);
    }
  }

  function handleApplyNow(item) {
    const url = item?.application_url || item?.source_url;

    if (!url) {
      setApplicationMessage(
        "This opportunity has no application link."
      );
      return;
    }

    handleApplicationStatus(item, "applied");
    window.open(url, "_blank", "noopener,noreferrer");
  }

  function retryConnection() {
    setAuthReloadKey((value) => value + 1);
    setReloadKey((value) => value + 1);
  }

  async function startOnboardingDiscovery() {
    const preferred = (profile?.opportunity_types || []).filter(
      (type) => type === "internship" || type === "job"
    );
    const categories = (
      preferred.length ? preferred : ["internship", "job"]
    ).slice(0, 2);

    let lastCount = null;

    for (const category of categories) {
      setAutoDiscovery({
        active: true,
        message: `Searching ${category} opportunities...`,
      });

      try {
        const response = await apiFetch("/api/discover", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ category, limit: 5 }),
        });
        const data = await readJson(response);

        if (!response.ok) {
          throw new Error(
            errorMessage(data, `The ${category} search failed.`)
          );
        }

        lastCount = data.count;
        setReloadKey((value) => value + 1);
      } catch {
        // Continue with the next category; the manual button remains.
      }
    }

    setAutoDiscovery({
      active: false,
      message:
        lastCount === null
          ? "Automatic search could not run. Use Find New Opportunities to try again."
          : `Search complete. ${lastCount} opportunities are now available.`,
    });
  }

  function handleProfileSaved() {
    const shouldAutoDiscover = profileIncomplete;
    setReloadKey((value) => value + 1);

    if (shouldAutoDiscover) {
      startOnboardingDiscovery();
    }
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
    setApplications([]);
    setProfile(null);
    setDetailItem(null);
    setActiveView("discover");
  }

  const handleAuthenticated = useCallback((user) => {
    setAuthUser(user);
    setReloadKey((value) => value + 1);
  }, []);

  const profileSkills = useMemo(
    () => profile?.skills || [],
    [profile]
  );

  const applicationStatusByUrl = useMemo(
    () =>
      new Map(
        applications.map((item) => [
          item.source_url,
          item.status,
        ])
      ),
    [applications]
  );

  const applicationNoteByUrl = useMemo(
    () =>
      new Map(
        applications.map((item) => [
          item.source_url,
          item.note || "",
        ])
      ),
    [applications]
  );

  const relatedOpportunities = useMemo(() => {
    if (!detailItem) return [];

    const currentSkills = new Set([
      ...(detailItem.required_skills || []),
      ...(detailItem.fields || []),
    ]);

    return opportunities
      .filter((item) => {
        if (item.source_url === detailItem.source_url) return false;

        const sharesSkill = (item.required_skills || []).some(
          (skill) => currentSkills.has(skill)
        );

        return item.type === detailItem.type || sharesSkill;
      })
      .slice(0, 4);
  }, [opportunities, detailItem]);

  // Filter opportunities and attach their recommendation scores
  const visibleOpportunities = useMemo(() => {
    const trackedByUrl = new Map(
      applications.map((item) => [
        item.source_url,
        item.status,
      ])
    );

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

    if (activeView === "applications") {
      results = results.filter((item) =>
        trackedByUrl.has(item.source_url)
      );

      if (applicationFilter !== "all") {
        results = results.filter(
          (item) =>
            trackedByUrl.get(item.source_url) === applicationFilter
        );
      }
    }

    if (workMode !== "any") {
      results = results.filter((item) => {
        if (workMode === "remote") return item.remote === true;
        if (workMode === "onsite") return item.remote === false;
        return item.remote === null || item.remote === undefined;
      });
    }

    if (deadlineWindow !== "any") {
      results = results.filter((item) => {
        const remaining = daysUntil(item.deadline);

        if (deadlineWindow === "none") return remaining === null;
        if (remaining === null) return false;

        if (deadlineWindow === "7") {
          return remaining >= 0 && remaining <= 7;
        }

        return remaining >= 0 && remaining <= 30;
      });
    }

    if (locationFilter.trim()) {
      const wanted = locationFilter.trim().toLowerCase();

      results = results.filter((item) =>
        (item.location || "").toLowerCase().includes(wanted)
      );
    }

    if (paidOnly) {
      results = results.filter(
        (item) => item.stipend || item.prize_money
      );
    }

    if (skillMatchOnly && profileSkills.length) {
      results = results.filter((item) => {
        const text = [
          item.title,
          item.organization,
          item.description,
          ...(item.required_skills || []),
          ...(item.fields || []),
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return profileSkills.some((skill) =>
          text.includes(skill.toLowerCase())
        );
      });
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
    applications,
    activeView,
    activeCategory,
    searchText,
    sortMode,
    workMode,
    deadlineWindow,
    paidOnly,
    skillMatchOnly,
    locationFilter,
    profileSkills,
    applicationFilter,
  ]);

  const categoryCount = new Set(
    opportunities.map((item) => item.type)
  ).size;

  const closingSoonCount = opportunities.filter((item) => {
    const remaining = daysUntil(item.deadline);
    return remaining !== null && remaining >= 0 && remaining <= 7;
  }).length;

  const applicationCounts = applications.reduce(
    (counts, item) => {
      counts[item.status] = (counts[item.status] || 0) + 1;
      return counts;
    },
    {}
  );

  const advancedFilterCount = [
    workMode !== "any",
    deadlineWindow !== "any",
    paidOnly,
    skillMatchOnly,
    locationFilter.trim() !== "",
  ].filter(Boolean).length;

  const filterKey = [
    activeView,
    activeCategory,
    searchText,
    sortMode,
    workMode,
    deadlineWindow,
    paidOnly,
    skillMatchOnly,
    locationFilter,
    applicationFilter,
  ].join("|");

  const visibleCount = Math.max(
    24,
    pagination.key === filterKey ? pagination.count : 24
  );
  const pagedOpportunities = visibleOpportunities.slice(
    0,
    visibleCount
  );

  const strengthItems = [
    ["Degree", Boolean(profile?.degree), 10],
    ["Branch", Boolean(profile?.branch), 10],
    ["Year of study", Boolean(profile?.year_of_study), 8],
    [
      "Graduation year",
      Boolean(profile?.graduation_year),
      8,
    ],
    [
      "Skills (5+)",
      Math.min((profile?.skills || []).length, 8) / 8,
      20,
    ],
    [
      "Interests (3+)",
      Math.min((profile?.interests || []).length, 6) / 6,
      15,
    ],
    [
      "Preferred locations",
      Math.min(
        (profile?.preferred_locations || []).length,
        3
      ) / 3,
      8,
    ],
    ["Phone", Boolean(profile?.phone), 5],
    ["College", Boolean(profile?.college), 5],
    ["GitHub", Boolean(profile?.github), 4],
    ["LinkedIn", Boolean(profile?.linkedin), 4],
    ["Portfolio", Boolean(profile?.portfolio), 3],
  ];

  const profileStrength = profile
    ? Math.round(
        strengthItems.reduce(
          (total, [, value, weight]) =>
            total + weight * (typeof value === "number" ? value : value ? 1 : 0),
          0
        )
      )
    : 0;

  const strengthTips = profile
    ? strengthItems
        .filter(([, value]) => !value)
        .map(([label]) => label)
    : [];

  const profileIncomplete = Boolean(
    !loading &&
      profile &&
      !profile.degree &&
      !profile.branch &&
      !profile.year_of_study &&
      !(profile.interests || []).length
  );

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
      <aside
        className={`sidebar ${sidebarOpen ? "open" : ""}`}
        onClickCapture={() => setSidebarOpen(false)}
      >
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

        <button
          className={`side-link ${
            activeView === "applications" ? "selected" : ""
          }`}
          onClick={() => setActiveView("applications")}
        >
          <span className="side-icon">◈</span>
          Applications
          <span className="side-count">{applications.length}</span>
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
        {sidebarOpen && (
          <div
            className="sidebar-overlay"
            role="presentation"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <header className="topbar">
          <button
            className="menu-button"
            onClick={() => setSidebarOpen((open) => !open)}
            aria-label="Toggle navigation"
          >
            ☰
          </button>

          <div className="breadcrumb">
            Workspace <span>/</span>{" "}
            {activeView === "recommended"
              ? "For you"
              : activeView === "saved"
                ? "Saved opportunities"
                : activeView === "applications"
                  ? "Applications"
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
                document
                  .getElementById("opportunities")
                  ?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                  });
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
          key={profileIncomplete ? "onboarding" : "profile"}
          initiallyOpen={profileIncomplete}
          onSaved={handleProfileSaved}
        />

        {profile && (
          <section className="profile-strength">
            <div
              className={`strength-ring ${
                profileStrength >= 80
                  ? "strong"
                  : profileStrength >= 55
                    ? "medium"
                    : "weak"
              }`}
            >
              {profileStrength}%
            </div>

            <div className="strength-copy">
              <div className="section-kicker">PROFILE STRENGTH</div>
              <h3>Improve your match scores</h3>

              {strengthTips.length ? (
                <p>
                  Add or complete:{" "}
                  <strong>{strengthTips.join(", ")}</strong>.
                </p>
              ) : (
                <p>
                  Your profile is complete. Strong profiles rank higher
                  and produce clearer match reasons.
                </p>
              )}
            </div>
          </section>
        )}

        {error && (
          <div className="error-banner">
            <strong>Connection problem</strong>
            <span>{error}</span>
            <button onClick={retryConnection}>Retry</button>
          </div>
        )}

        {autoDiscovery.message && (
          <div
            className={`auto-discovery-banner ${
              autoDiscovery.active ? "active" : ""
            }`}
            role="status"
          >
            {autoDiscovery.active && (
              <span className="loading-spinner small" />
            )}
            <span>{autoDiscovery.message}</span>
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

          <div className="stat-card">
            <div className="stat-icon amber">◷</div>
            <div className="stat-label">Closing within 7 days</div>
            <div className="stat-value">
              {loading ? "—" : closingSoonCount}
            </div>
            <div className="stat-foot">From published deadlines</div>
          </div>
        </section>

        <section
          className="opportunities-section"
          id="opportunities"
        >
          <div className="section-heading">
            <div>
              <div className="section-kicker">YOUR WORKSPACE</div>

              <h2>
                {activeView === "recommended"
                  ? "Recommended for you"
                  : activeView === "saved"
                    ? "Saved opportunities"
                    : activeView === "applications"
                      ? "My applications"
                      : "Explore opportunities"}
              </h2>

              <p>
                {activeView === "recommended"
                  ? "Ranked using your interests and profile."
                  : activeView === "saved"
                    ? "Your bookmarked opportunities, saved for later."
                    : activeView === "applications"
                      ? "Track what you applied to and where each application stands."
                      : "Search and filter the opportunities in your workspace."}
              </p>

              {activeView === "discover" &&
                opportunities.length <= 4 && (
                  <p className="workspace-hint">
                    This workspace has only the seeded records so far.
                    Use <strong>Find New Opportunities</strong> to search
                    another category.
                  </p>
                )}
            </div>

            <div className="section-actions">
              {activeView === "discover" && (
                <>
                  <button
                    className="discover-button"
                    onClick={handleDiscover}
                    disabled={discovering || loading}
                  >
                    {discovering
                      ? "Searching..."
                      : "✦ Find New Opportunities"}
                  </button>

                  <button
                    className="curated-button"
                    onClick={handleCuratedImport}
                    disabled={syncingCurated || loading}
                  >
                    {syncingCurated
                      ? "Syncing..."
                      : "⤓ Sync curated internships"}
                  </button>
                </>
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

          {applicationMessage && (
            <div className="discovery-message" role="status">
              {applicationMessage}
            </div>
          )}

          {curatedMessage && (
            <div className="discovery-message" role="status">
              {curatedMessage}
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
              className={`filter-reset ${
                advancedFilterCount ? "has-filters" : ""
              }`}
              onClick={() => setFilterPanelOpen((open) => !open)}
            >
              Filters
              {advancedFilterCount
                ? ` (${advancedFilterCount})`
                : ""}
            </button>

            <button
              className="filter-reset"
              onClick={() => {
                setSearchText("");
                setActiveCategory("all");
                setSortMode("match");
                setWorkMode("any");
                setDeadlineWindow("any");
                setPaidOnly(false);
                setSkillMatchOnly(false);
                setLocationFilter("");
              }}
            >
              Clear filters
            </button>
          </div>

          {filterPanelOpen && (
            <div className="filter-panel">
              <label>
                Work mode
                <select
                  value={workMode}
                  onChange={(event) =>
                    setWorkMode(event.target.value)
                  }
                >
                  <option value="any">Any</option>
                  <option value="remote">Remote</option>
                  <option value="onsite">On-site</option>
                  <option value="unknown">Not stated</option>
                </select>
              </label>

              <label>
                Deadline
                <select
                  value={deadlineWindow}
                  onChange={(event) =>
                    setDeadlineWindow(event.target.value)
                  }
                >
                  <option value="any">Any</option>
                  <option value="7">Closing within 7 days</option>
                  <option value="30">Closing within 30 days</option>
                  <option value="none">No deadline listed</option>
                </select>
              </label>

              <label>
                Location contains
                <input
                  type="search"
                  value={locationFilter}
                  onChange={(event) =>
                    setLocationFilter(event.target.value)
                  }
                  placeholder="India, Bengaluru, Remote"
                />
              </label>

              <label className="filter-check">
                <input
                  type="checkbox"
                  checked={paidOnly}
                  onChange={(event) =>
                    setPaidOnly(event.target.checked)
                  }
                />
                Stipend/prize listed
              </label>

              <label className="filter-check">
                <input
                  type="checkbox"
                  checked={skillMatchOnly}
                  onChange={(event) =>
                    setSkillMatchOnly(event.target.checked)
                  }
                />
                Matches my skills
              </label>
            </div>
          )}

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

          {activeView === "applications" && (
            <div className="application-filter">
              {["all", "interested", "applied", "interview", "offer", "rejected"]
                .filter(
                  (status) =>
                    status === "all" || applicationCounts[status]
                )
                .map((status) => (
                  <button
                    key={status}
                    className={`category-chip ${
                      applicationFilter === status ? "active" : ""
                    }`}
                    onClick={() => setApplicationFilter(status)}
                  >
                    {status === "all"
                      ? `All (${applications.length})`
                      : `${status} (${applicationCounts[status]})`}
                  </button>
                ))}
            </div>
          )}

          {activeView === "applications" &&
            applications.length > 0 && (
              <div className="application-summary">
                {["interested", "applied", "interview", "offer", "rejected"]
                  .filter((status) => applicationCounts[status])
                  .map((status) => (
                    <span
                      className={`status-pill status-${status}`}
                      key={status}
                    >
                      {status}: {applicationCounts[status]}
                    </span>
                  ))}
              </div>
            )}

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
                    : activeView === "applications"
                      ? "No applications tracked yet"
                      : "No matching opportunities yet"}
              </h3>

              <p>
                {error
                  ? "Start the FastAPI backend and try refreshing."
                  : activeView === "saved"
                    ? "Use the Save button on an opportunity card to keep it here."
                    : activeView === "applications"
                      ? "Open an opportunity, choose a status, and it will appear here."
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
            <>
              <div className="opportunity-grid">
                {pagedOpportunities.map((item) => (
                  <OpportunityCard
                    key={`${item.source_url}-${item.title}`}
                    item={item}
                    isSaved={bookmarks.includes(item.source_url)}
                    isBusy={Boolean(bookmarkBusy[item.source_url])}
                    applicationStatus={applicationStatusByUrl.get(
                      item.source_url
                    )}
                    onBookmark={handleBookmark}
                    onApply={handleApplyNow}
                    onOpen={setDetailItem}
                  />
                ))}
              </div>

              {visibleCount < visibleOpportunities.length && (
                <button
                  className="load-more"
                  onClick={() =>
                    setPagination({
                      key: filterKey,
                      count: visibleCount + 24,
                    })
                  }
                >
                  Show more ({visibleOpportunities.length - visibleCount}{" "}
                  remaining)
                </button>
              )}
            </>
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
          applicationStatus={applicationStatusByUrl.get(
            detailItem.source_url
          )}
          applicationBusy={applicationBusy}
          profileSkills={profileSkills}
          related={relatedOpportunities}
          onStatusChange={handleApplicationStatus}
          applicationNote={applicationNoteByUrl.get(
            detailItem.source_url
          )}
          onBookmark={handleBookmark}
          onApply={handleApplyNow}
          onOpen={setDetailItem}
          onClose={() => setDetailItem(null)}
        />
      )}
    </div>
  );
}

export default App;
