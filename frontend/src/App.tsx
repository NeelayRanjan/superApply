import { useEffect, useRef, useState, useCallback } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  ArrowUpRight,
  ArrowUp,
  Bell,
  BriefcaseBusiness,
  Bookmark,
  Building2,
  ChartNoAxesCombined,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Command,
  FileText,
  LayoutDashboard,
  Leaf,
  ListFilter,
  MapPin,
  MessageSquare,
  Moon,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Star,
  Sun,
  ThumbsDown,
  ThumbsUp,
  X,
} from "lucide-react";
import { api, salary, type Job, type Company, type Profile } from "./api";

type View =
  | "Jobs"
  | "Pipeline"
  | "Analytics"
  | "Bank"
  | "Registry"
  | "Settings"
  | "Tailor";
const navigation = [
  ["Jobs", BriefcaseBusiness],
  ["Pipeline", LayoutDashboard],
  ["Analytics", ChartNoAxesCombined],
  ["Bank", FileText],
  ["Registry", Building2],
] as const;
export default function App() {
  const [view, setView] = useState<View>("Jobs");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<Job | null>(null);
  const [search, setSearch] = useState("");
  const [band, setBand] = useState("all");
  const [remote, setRemote] = useState("all");
  const [onlySaved, setOnlySaved] = useState(false);
  const [showFiltered, setShowFiltered] = useState(false);
  const [chatOpen, setChatOpen] = useState(true);
  const [dark, setDark] = useState(
    localStorage.getItem("firstlook-theme") === "dark",
  );
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<string[]>([]);
  const [active, setActive] = useState(0);
  const searchRef = useRef<HTMLInputElement>(null);
  const notify = (message: string) => {
    setNotice(message);
  };
  const refresh = useCallback(async () => {
    try {
      setJobs(await api<Job[]>("/jobs"));
    } catch (e) {
      setNotice(String(e));
    }
  }, []);
  useEffect(() => {
    void refresh();
    void api<{ saved_searches?: string[] }>("/settings").then((s) =>
      setSaved(s.saved_searches || []),
    );
  }, [refresh]);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("firstlook-theme", String(dark ? "dark" : "light"));
  }, [dark]);
  const filtered = jobs.filter(
    (j) =>
      (showFiltered || j.band !== "filtered") &&
      (!onlySaved || j.starred) &&
      (band === "all" || j.band === band) &&
      (remote === "all" || j.extraction.remote === remote) &&
      `${j.title} ${j.company} ${j.tags.join(" ")} ${j.locations.join(" ")} ${j.description}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const star = useCallback(
    async (job: Job) => {
      await api("/jobs/" + job.id + "/star", "POST");
      await refresh();
      setSelected((s) =>
        s?.id === job.id ? { ...s, starred: s.starred ? 0 : 1 } : s,
      );
    },
    [refresh],
  );
  const launch = (v: View, j: Job) => {
    setSelected(j);
    setView(v);
  };
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (
        (e.target as HTMLElement).matches(
          "input,textarea,select,[contenteditable]",
        )
      )
        return;
      if (e.key === "/") {
        e.preventDefault();
        searchRef.current?.focus();
      }
      if (e.key === "j") {
        e.preventDefault();
        setActive((a) => Math.min(a + 1, filtered.length - 1));
      }
      if (e.key === "k") {
        e.preventDefault();
        setActive((a) => Math.max(a - 1, 0));
      }
      const j = filtered[active];
      if (!j) return;
      if (e.key === "s") void star(j);
      if (e.key === "Enter") setSelected(j);
      if (e.key === "t") launch("Tailor", j);
      if (e.key === "a") {
        setSelected(j);
        setView("Pipeline");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [filtered, active, star]);
  const loadDemo = async () => {
    setBusy(true);
    try {
      await api("/demo", "POST");
      await refresh();
      notify("Synthetic demo loaded. These are example companies and jobs.");
    } catch (e) {
      notify(String(e));
    } finally {
      setBusy(false);
    }
  };
  const crawl = async () => {
    setBusy(true);
    try {
      const registry = await api<Company[]>("/registry");
      if (
        registry.length > 25 &&
        !window.confirm(
          `Crawl ${registry.length} boards? Estimated AI spend: 0 tokens. This makes live ATS requests.`,
        )
      )
        return;
      const result = await api<{ new: number }>("/crawl", "POST", {
        confirmed_bulk: registry.length > 25,
      });
      await refresh();
      notify(`Crawl finished · ${result.new} new jobs`);
    } catch (e) {
      notify(String(e));
    } finally {
      setBusy(false);
    }
  };
  const saveSearch = async () => {
    if (!search.trim()) return;
    const next = [...new Set([...saved, search])];
    await api("/settings", "PUT", { saved_searches: next });
    setSaved(next);
  };
  return (
    <div className="app-shell">
      <aside className="rail">
        <a
          className="brand"
          href="#"
          onClick={() => {
            setView("Jobs");
            setSelected(null);
          }}
        >
          <span className="brand-mark">
            <Leaf size={21} />
          </span>
          firstlook<span className="brand-dot">.</span>
        </a>
        <div className="workspace">
          <span className="avatar">Y</span>
          <div>
            Your workspace<small>Personal · Local only</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <span className="rail-label">WORKSPACE</span>
        <nav>
          {navigation.map(([name, Icon]) => (
            <button
              key={name}
              className={view === name ? "nav-item active" : "nav-item"}
              onClick={() => {
                setView(name);
                setSelected(null);
              }}
            >
              <Icon size={18} />
              {name}
              {name === "Jobs" && (
                <span className="nav-count">
                  {jobs.filter((j) => j.band !== "filtered").length}
                </span>
              )}
            </button>
          ))}
        </nav>
        <div className="rail-heading">
          <span className="rail-label">SAVED SEARCHES</span>
          <button
            className="icon-button"
            title="Save current search"
            onClick={() => void saveSearch()}
          >
            <Plus size={14} />
          </button>
        </div>
        {saved.length ? (
          saved.map((s) => (
            <button
              className="saved-search"
              key={s}
              onClick={() => {
                setSearch(s);
                setView("Jobs");
              }}
            >
              <Search size={14} />
              {s}
            </button>
          ))
        ) : (
          <p className="rail-note">Save a search to make it yours.</p>
        )}
        <button
          className="saved-search"
          onClick={() => {
            setOnlySaved((v) => !v);
            setView("Jobs");
          }}
        >
          <Bookmark size={15} />
          Starred jobs<span>{jobs.filter((j) => j.starred).length}</span>
        </button>
        <div className="rail-bottom">
          <div className="privacy-card">
            <ShieldCheck size={17} />
            <strong>Your search, your data.</strong>
            <p>
              Stored on this device.
              <br />
              No accounts. No tracking.
            </p>
          </div>
          <button
            className={view === "Settings" ? "nav-item active" : "nav-item"}
            onClick={() => setView("Settings")}
          >
            <Settings2 size={17} />
            Settings
          </button>
          <button className="nav-item" onClick={() => setDark((d) => !d)}>
            {dark ? <Sun size={17} /> : <Moon size={17} />}{" "}
            {dark ? "Light" : "Dark"} appearance
          </button>
          <div className="version">
            <span className="status-dot" />
            All systems local<span>v0.1.0</span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace
            <ChevronRight size={13} />
            <strong>{view}</strong>
          </div>
          <div className="top-actions">
            <span className="local-pill">
              <span className="status-dot" />
              Local workspace
            </span>
            <button
              className="icon-button"
              title="View follow-up reminders"
              onClick={() => setView("Pipeline")}
            >
              <Bell size={17} />
            </button>
            <button
              className="icon-button"
              title="Toggle assistant"
              onClick={() => setChatOpen((o) => !o)}
            >
              <MessageSquare size={18} />
            </button>
            <span className="avatar small">Y</span>
          </div>
        </header>
        <div className="work-area">
          <main className="main-panel">
            {notice && (
              <div role="status" className="notice">
                {notice}
                <button className="icon-button" onClick={() => setNotice("")}>
                  <X size={14} />
                </button>
              </div>
            )}
            {view === "Jobs" && (
              <>
                <div className="page-heading">
                  <div>
                    <div className="eyebrow">
                      A LITTLE EARLIER. A LITTLE CLOSER.
                    </div>
                    <h1>Your next chapter.</h1>
                    <p>Good opportunities, straight from the source.</p>
                  </div>
                  <button
                    className="primary"
                    disabled={busy}
                    onClick={() => void crawl()}
                  >
                    <Plus size={15} />
                    {busy ? "Working…" : "Find new jobs"}
                  </button>
                </div>
                <div className="overview">
                  <div>
                    <span className="overview-icon">
                      <BriefcaseBusiness size={18} />
                    </span>
                    <div>
                      <strong>
                        {jobs.filter((j) => j.band !== "filtered").length}
                      </strong>
                      <span>Open opportunities</span>
                    </div>
                  </div>
                  <div>
                    <span className="overview-icon green">
                      <Sparkles size={18} />
                    </span>
                    <div>
                      <strong>
                        {jobs.filter((j) => j.band === "strong").length}
                      </strong>
                      <span>Strong matches</span>
                    </div>
                  </div>
                  <div>
                    <span className="overview-icon amber">
                      <Bookmark size={18} />
                    </span>
                    <div>
                      <strong>{jobs.filter((j) => j.starred).length}</strong>
                      <span>Saved for later</span>
                    </div>
                  </div>
                  <div className="overview-note">
                    <ShieldCheck size={20} />
                    <span>
                      Zero AI spend
                      <br />
                      <small>Discovery & matching are free</small>
                    </span>
                  </div>
                </div>
                <div className="jobs-card">
                  <div className="table-tabs">
                    <div>
                      {[
                        ["all", "All opportunities"],
                        ["strong", "Strong matches"],
                        ["possible", "Might match"],
                      ].map(([key, label]) => (
                        <button
                          key={key}
                          className={band === key ? "tab active" : "tab"}
                          onClick={() => setBand(key)}
                        >
                          {label}
                          <span>
                            {
                              jobs.filter((j) =>
                                key === "all"
                                  ? j.band !== "filtered"
                                  : j.band === key,
                              ).length
                            }
                          </span>
                        </button>
                      ))}
                    </div>
                    <button
                      className={"icon-button " + (onlySaved ? "starred" : "")}
                      title="Show starred jobs"
                      onClick={() => setOnlySaved((o) => !o)}
                    >
                      <Bookmark size={17} />
                    </button>
                  </div>
                  <div className="table-toolbar">
                    <label className="search">
                      <Search size={16} />
                      <input
                        ref={searchRef}
                        value={search}
                        onChange={(e) => {
                          setSearch(e.target.value);
                          setActive(0);
                        }}
                        placeholder="Search roles, companies, or keywords…"
                      />
                      <kbd>/</kbd>
                    </label>
                    <select
                      aria-label="Remote policy"
                      value={remote}
                      onChange={(e) => setRemote(e.target.value)}
                    >
                      <option value="all">All locations</option>
                      <option value="remote">Remote</option>
                      <option value="hybrid">Hybrid</option>
                      <option value="onsite">Onsite</option>
                    </select>
                    <button
                      className={
                        showFiltered ? "secondary selected" : "secondary"
                      }
                      onClick={() => setShowFiltered((s) => !s)}
                    >
                      <ListFilter size={15} />
                      Filtered out
                    </button>
                  </div>
                  {jobs.length ? (
                    <JobsTable
                      jobs={filtered}
                      active={active}
                      onOpen={setSelected}
                      onStar={(j) => void star(j)}
                    />
                  ) : (
                    <Empty
                      icon={<BriefcaseBusiness size={28} />}
                      title="A fresh start for your search"
                      text="Choose your target titles and areas in Settings, add company boards, then find your first opportunities."
                    >
                      <button
                        className="primary"
                        onClick={() => setView("Settings")}
                      >
                        Set up your profile
                        <ArrowUpRight size={15} />
                      </button>
                      <button
                        className="secondary"
                        disabled={busy}
                        onClick={() => void loadDemo()}
                      >
                        Explore synthetic demo
                      </button>
                    </Empty>
                  )}
                  <div className="table-footer">
                    <span>
                      {filtered.length} opportunities ·{" "}
                      {jobs.some((j) => j.company_id.startsWith("demo-"))
                        ? "Synthetic demo data"
                        : "Direct from company boards"}
                    </span>
                    <span>
                      <kbd>j</kbd>
                      <kbd>k</kbd> navigate <kbd>s</kbd> star <kbd>t</kbd>{" "}
                      tailor
                    </span>
                  </div>
                </div>
                <div className="mode-note">
                  <CircleHelp size={14} />
                  {jobs[0]?.mode ||
                    "Lexical matching is active. Add the optional local model for semantic matches."}
                  <button onClick={() => setView("Settings")}>
                    View settings
                    <ArrowUpRight size={12} />
                  </button>
                </div>
                {selected && (
                  <JobDetail
                    job={selected}
                    onClose={() => setSelected(null)}
                    onStar={() => void star(selected)}
                    onTailor={() => launch("Tailor", selected)}
                    onApply={() => launch("Pipeline", selected)}
                    notify={notify}
                  />
                )}
              </>
            )}
            {view === "Registry" && <Registry notify={notify} />}
            {view === "Settings" && (
              <Settings notify={notify} onSaved={() => void refresh()} />
            )}
            {view === "Bank" && (
              <FeatureSlot name="Bank" job={selected} notify={notify} />
            )}
            {view === "Tailor" && (
              <FeatureSlot name="Tailor" job={selected} notify={notify} />
            )}
            {view === "Pipeline" && (
              <FeatureSlot name="Pipeline" job={selected} notify={notify} />
            )}
            {view === "Analytics" && (
              <FeatureSlot name="Analytics" job={selected} notify={notify} />
            )}
          </main>
          {chatOpen && (
            <Chat
              view={view}
              job={selected}
              notify={notify}
              onClose={() => setChatOpen(false)}
              onRefresh={() => void refresh()}
            />
          )}
        </div>
      </div>
    </div>
  );
}
function JobsTable({
  jobs,
  active,
  onOpen,
  onStar,
}: {
  jobs: Job[];
  active: number;
  onOpen: (j: Job) => void;
  onStar: (j: Job) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: jobs.length,
    getScrollElement: () => ref.current,
    estimateSize: () => 82,
    overscan: 8,
  });
  useEffect(() => {
    virtualizer.scrollToIndex(Math.max(0, active), { align: "auto" });
  }, [active, virtualizer]);
  return (
    <>
      <div className="job-table-header job-grid">
        <span>ROLE & COMPANY</span>
        <span>LOCATION</span>
        <span>COMPENSATION</span>
        <span>MATCH</span>
        <span>FOUND</span>
        <span />
      </div>
      <div
        ref={ref}
        className="table-scroll"
        role="table"
        aria-label="Job opportunities"
        aria-rowcount={jobs.length}
      >
        <div
          style={{ height: virtualizer.getTotalSize(), position: "relative" }}
        >
          {virtualizer.getVirtualItems().map((v) => {
            const j = jobs[v.index];
            return (
              <div
                key={j.id}
                role="row"
                aria-rowindex={v.index + 1}
                className={
                  "job-row job-grid " +
                  (v.index === active ? "keyboard-active" : "")
                }
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: v.size,
                  transform: `translateY(${v.start}px)`,
                }}
              >
                <button className="job-title-cell" onClick={() => onOpen(j)}>
                  <span className={"company-logo logo-" + (j.id % 5)}>
                    {j.company.slice(0, 1)}
                  </span>
                  <span>
                    <strong>{j.title}</strong>
                    <span className="company-line">
                      {j.company}
                      <span className="dot-separator">·</span>
                      <small>{j.tags.slice(0, 2).join(" · ")}</small>
                    </span>
                    {Boolean(j.ghost) && (
                      <small className="warning">
                        Long-running or reposted role
                      </small>
                    )}
                  </span>
                </button>
                <span className="location-cell">
                  <span>{j.locations[0]?.replace("Remote, ", "")}</span>
                  <small>
                    {j.extraction.remote === "remote" ? (
                      <>
                        <span className="tiny-dot" />
                        Remote
                      </>
                    ) : j.extraction.remote === "hybrid" ? (
                      "Hybrid"
                    ) : (
                      "Onsite / unspecified"
                    )}
                  </small>
                </span>
                <span className="salary-cell">
                  {salary(j)}
                  <small>
                    {j.extraction.compensation.min_cents
                      ? "Base salary"
                      : "Compensation undisclosed"}
                  </small>
                </span>
                <span>
                  <span className={"match-pill " + j.band}>
                    {j.band === "strong" ? (
                      <Sparkles size={11} />
                    ) : (
                      <span className="tiny-dot" />
                    )}
                    {j.band === "strong"
                      ? "Strong match"
                      : j.band === "possible"
                        ? "Might match"
                        : "Filtered"}
                  </span>
                  {j.exploration && (
                    <small className="exploration">Exploration pick</small>
                  )}
                </span>
                <span className="age-cell">
                  <span className="fresh-dot" />
                  {Math.max(
                    0,
                    Math.floor(
                      (Date.now() - new Date(j.first_seen).getTime()) /
                        86400000,
                    ),
                  )}
                  d ago
                </span>
                <button
                  aria-label={`${j.starred ? "Unstar" : "Star"} ${j.title} at ${j.company}`}
                  className={"icon-button " + (j.starred ? "starred" : "")}
                  onClick={() => onStar(j)}
                >
                  <Star size={17} fill={j.starred ? "currentColor" : "none"} />
                </button>
              </div>
            );
          })}
        </div>
        {jobs.length === 0 && (
          <p className="empty-inline">No opportunities match these filters.</p>
        )}
      </div>
    </>
  );
}
function JobDetail({
  job: j,
  onClose,
  onStar,
  onTailor,
  onApply,
  notify,
}: {
  job: Job;
  onClose: () => void;
  onStar: () => void;
  onTailor: () => void;
  onApply: () => void;
  notify: (s: string) => void;
}) {
  const [gap, setGap] = useState<{
    not_surfaced: string[];
    not_in_bank: string[];
  } | null>(null);
  useEffect(() => {
    void api<{ not_surfaced: string[]; not_in_bank: string[] }>(
      "/jobs/" + j.id + "/gap",
    )
      .then(setGap)
      .catch((e) => notify(String(e)));
  }, [j.id]);
  return (
    <section className="detail-sheet" role="dialog" aria-label="Job detail">
      <div className="detail-top">
        <button className="text-button" onClick={onClose}>
          <ChevronLeft size={16} />
          Back to opportunities
        </button>
        <button className="icon-button" onClick={onClose}>
          <X size={19} />
        </button>
      </div>
      <span className="company-logo large">{j.company[0]}</span>
      <p className="eyebrow">
        {j.company} · {j.platform}
      </p>
      <h2>{j.title}</h2>
      <p className="muted">
        <MapPin size={14} />
        {j.locations.join(" · ")} · {salary(j)}
      </p>
      <div className="button-row">
        <button className="primary" onClick={onTailor}>
          <Sparkles size={15} />
          Tailor resume
        </button>
        <button className="secondary" onClick={onApply}>
          Review application
          <ArrowUpRight size={15} />
        </button>
        <button className="secondary" onClick={onStar}>
          <Star size={15} />
          {j.starred ? "Saved" : "Save"}
        </button>
      </div>
      <div className="explanation">
        <h3>Why this could be a fit</h3>
        <p>
          {Math.round(j.score * 100)}% match · {j.band}
        </p>
        <div className="chip-row">
          {j.matched.map((s) => (
            <span className="chip good" key={s}>
              <Check size={11} />
              {s}
            </span>
          ))}
        </div>
        <p className="muted">
          Requirements not in your profile:{" "}
          {j.missing.join(", ") || "None identified"}
        </p>
        {j.dealbreakers.map((s) => (
          <p className="warning" key={s}>
            {s}
          </p>
        ))}
        <div className="button-row">
          <button
            className="text-button"
            onClick={() =>
              void api("/jobs/" + j.id + "/feedback", "POST", {
                label: 1,
              }).then(() => notify("Positive feedback saved locally"))
            }
          >
            <ThumbsUp size={14} />
            Good fit
          </button>
          <button
            className="text-button"
            onClick={() =>
              void api("/jobs/" + j.id + "/feedback", "POST", {
                label: 0,
              }).then(() => notify("Feedback saved locally"))
            }
          >
            <ThumbsDown size={14} />
            Not for me
          </button>
        </div>
      </div>
      {gap && (
        <div className="gap-grid">
          <div>
            <h3>In your bank, not surfaced</h3>
            <p>{gap.not_surfaced.join(", ") || "None identified"}</p>
          </div>
          <div>
            <h3>Not in your bank</h3>
            <p>{gap.not_in_bank.join(", ") || "None identified"}</p>
          </div>
        </div>
      )}
      <h3>About the opportunity</h3>
      <p className="description">{j.description}</p>
      <h3>Extracted requirements</h3>
      <dl className="facts">
        <dt>Seniority</dt>
        <dd>
          {j.extraction.seniority} · {j.extraction.years} years
        </dd>
        <dt>Sponsorship</dt>
        <dd>{j.extraction.visa}</dd>
        <dt>Clearance required</dt>
        <dd>{j.extraction.clearance ? "Yes" : "Not detected"}</dd>
        <dt>Geographic restriction</dt>
        <dd>{j.extraction.geography || "Not specified"}</dd>
      </dl>
      <a
        className="text-button"
        href={j.apply_url}
        target="_blank"
        rel="noreferrer"
      >
        Open original listing
        <ArrowUpRight size={14} />
      </a>
    </section>
  );
}
function Registry({ notify }: { notify: (s: string) => void }) {
  const [rows, setRows] = useState<Company[]>([]);
  const [query, setQuery] = useState("");
  const [url, setUrl] = useState("");
  const load = () =>
    api<Company[]>("/registry")
      .then(setRows)
      .catch((e) => notify(String(e)));
  useEffect(() => {
    void load();
  }, []);
  return (
    <>
      <PageHeading
        title="Company registry"
        subtitle="Your direct line to the companies that matter."
      />
      <div className="button-row">
        <button
          className="primary"
          onClick={() => void api("/registry/seed", "POST").then(() => load())}
        >
          <Plus size={15} />
          Load 524 seed candidates
        </button>
        <input
          placeholder="Find a company…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <div className="button-row" style={{ marginTop: 12 }}>
        <input
          aria-label="Careers URL"
          placeholder="https://company.example/careers"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <button
          className="secondary"
          onClick={() =>
            void api("/tools/registry_add", "POST", { url })
              .then(() => {
                setUrl("");
                void load();
                notify("Unverified board added");
              })
              .catch((e) => notify(String(e)))
          }
        >
          Discover board
        </button>
      </div>
      <p className="info-note">
        Seeded domains and board tokens are unverified guesses. Run{" "}
        <code>firstlook registry verify --all</code> to check them explicitly.
      </p>
      <div className="data-card">
        <table>
          <thead>
            <tr>
              <th>Company</th>
              <th>ATS · token</th>
              <th>Categories</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows
              .filter((r) => r.name.toLowerCase().includes(query.toLowerCase()))
              .map((r) => (
                <tr key={r.id}>
                  <td>
                    <strong>{r.name}</strong>
                    <small>{r.domain}</small>
                  </td>
                  <td>
                    {r.platform}
                    <small>{r.token}</small>
                  </td>
                  <td>
                    <input
                      aria-label={"Tags for " + r.name}
                      defaultValue={r.tags.join(", ")}
                      onBlur={(e) =>
                        void api("/registry/" + r.id, "PUT", {
                          tags: e.target.value
                            .split(",")
                            .map((v) => v.trim())
                            .filter(Boolean),
                        }).then(() => notify("Company tags saved"))
                      }
                    />
                  </td>
                  <td>
                    <span
                      className={
                        "match-pill " + (r.verified ? "strong" : "possible")
                      }
                    >
                      {r.verified ? "Verified" : "Unverified"}
                    </span>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
function Settings({
  notify,
  onSaved,
}: {
  notify: (s: string) => void;
  onSaved: () => void;
}) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [providerConfigured, setProviderConfigured] = useState(false);
  useEffect(() => {
    void api<{ provider_configured: boolean }>("/health").then((h) =>
      setProviderConfigured(h.provider_configured),
    );
  }, []);
  useEffect(() => {
    void api<Profile>("/profile").then(setProfile);
  }, []);
  if (!profile) return <p>Loading profile…</p>;
  const p = profile;
  const update = (key: string, value: unknown) =>
    setProfile({ ...p, [key]: value });
  return (
    <>
      <PageHeading
        title="Make it your search"
        subtitle="A few thoughtful preferences go a long way."
      />
      <form
        className="settings-form"
        onSubmit={(e) => {
          e.preventDefault();
          void api("/profile", "PUT", p)
            .then(() => {
              notify("Profile saved. Your matches have been refreshed.");
              onSaved();
            })
            .catch((e) => notify(String(e)));
        }}
      >
        <h3>What are you looking for?</h3>
        {(
          [
            ["titles", "Target titles", "Software Engineer, Backend Engineer"],
            ["locations", "Target areas", "United States, San Francisco"],
            ["must_skills", "Your core skills", "Python, SQL, AWS"],
            ["nice_skills", "Additional skills", "Docker, TypeScript"],
            ["dealbreakers", "Dealbreaker phrases", "unpaid, commission only"],
          ] as const
        ).map(([key, label, placeholder]) => (
          <label key={key}>
            {label}
            <input
              placeholder={placeholder}
              value={p[key].join(", ")}
              onChange={(e) =>
                update(
                  key,
                  e.target.value.split(",").map((x) => x.trimStart()),
                )
              }
            />
            <small>
              Separate values with commas
              {key === "locations"
                ? "; use Anywhere for no location restriction"
                : ""}
              .
            </small>
          </label>
        ))}
        <div className="form-grid">
          <label>
            Work style
            <select
              value={p.remote}
              onChange={(e) => update("remote", e.target.value)}
            >
              <option value="any">Any work style</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">Onsite</option>
            </select>
          </label>
          <label>
            Minimum annual pay ({p.currency})
            <input
              type="number"
              value={p.compensation_floor_cents / 100}
              onChange={(e) =>
                update("compensation_floor_cents", Number(e.target.value) * 100)
              }
            />
          </label>
        </div>
        <label className="check-label">
          <input
            type="checkbox"
            checked={p.needs_sponsorship}
            onChange={(e) => update("needs_sponsorship", e.target.checked)}
          />
          I require visa sponsorship
        </label>
        <label className="check-label">
          <input
            type="checkbox"
            checked={p.has_clearance}
            onChange={(e) => update("has_clearance", e.target.checked)}
          />
          I hold the required clearance
        </label>
        <h3>Your application details</h3>
        {["name", "email", "phone", "location", "website", "linkedin"].map(
          (key) => (
            <label key={key}>
              {key}
              <input
                value={p.contact[key] || ""}
                onChange={(e) =>
                  update("contact", { ...p.contact, [key]: e.target.value })
                }
              />
            </label>
          ),
        )}
        <h3>Explicit application answers</h3>
        <p className="muted">
          These answers are always shown for review. Unset sensitive fields
          default to decline to answer.
        </p>
        {[
          "work_authorization",
          "sponsorship",
          "eeo",
          "veteran",
          "disability",
        ].map((key) => (
          <label key={key}>
            {key.replaceAll("_", " ")}
            <input
              placeholder="Decline to answer"
              value={p.explicit_answers[key] || ""}
              onChange={(e) =>
                update("explicit_answers", {
                  ...p.explicit_answers,
                  [key]: e.target.value,
                })
              }
            />
          </label>
        ))}
        <button className="primary" type="submit">
          Save preferences
          <Check size={15} />
        </button>
      </form>
      <section className="settings-form">
        <h3>Local by default</h3>
        <p>
          Matching works without a model. Optional ONNX embeddings live in{" "}
          <code>models/</code>. Provider credentials belong in environment
          variables, never in your database.
        </p>
        <p className="info-note">
          No LLM provider configured: the deterministic tailor and local chat
          tools remain available.
        </p>
        <BudgetSettings notify={notify} />
      </section>
    </>
  );
}
function BudgetSettings({ notify }: { notify: (s: string) => void }) {
  const [daily, setDaily] = useState(20000);
  const [run, setRun] = useState(4000);
  useEffect(() => {
    void api<{ daily_tokens?: number; run_tokens?: number }>("/settings").then(
      (s) => {
        setDaily(s.daily_tokens ?? 20000);
        setRun(s.run_tokens ?? 4000);
      },
    );
  }, []);
  return (
    <>
      <div className="form-grid">
        <label>
          Daily token ceiling
          <input
            type="number"
            min="0"
            value={daily}
            onChange={(e) => setDaily(Number(e.target.value))}
          />
        </label>
        <label>
          Per-run token ceiling
          <input
            type="number"
            min="0"
            value={run}
            onChange={(e) => setRun(Number(e.target.value))}
          />
        </label>
      </div>
      <button
        className="secondary"
        onClick={() =>
          void api("/settings", "PUT", {
            daily_tokens: daily,
            run_tokens: run,
          }).then(() => notify("Budget ceilings saved"))
        }
      >
        Save budgets
      </button>
    </>
  );
}
export function PageHeading({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">YOUR WORKSPACE</div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
    </div>
  );
}
export function Empty({
  icon,
  title,
  text,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <h2>{title}</h2>
      <p>{text}</p>
      <div className="button-row">{children}</div>
    </div>
  );
}
// Feature panels are kept separate so the shell remains thin.
import { FeatureSlot } from "./Features";
function Chat({
  view,
  job,
  notify,
  onClose,
  onRefresh,
}: {
  view: string;
  job: Job | null;
  notify: (s: string) => void;
  onClose: () => void;
  onRefresh: () => void;
}) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ role: string; text: string }[]>(
    [],
  );
  const [sending, setSending] = useState(false);
  const [mode, setMode] = useState("local");
  const send = async (text: string) => {
    if (!text.trim()) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setSending(true);
    try {
      const result = await api<{ message: string; mode: string }>(
        "/chat",
        "POST",
        { message: text, context: { view, job_id: job?.id } },
      );
      setMessages((m) => [...m, { role: "assistant", text: result.message }]);
      setMode(result.mode);
      onRefresh();
    } catch (e) {
      notify(String(e));
    } finally {
      setSending(false);
    }
  };
  return (
    <aside className="chat-panel">
      <div className="chat-heading">
        <span>
          <Sparkles size={17} />
          Your search partner
        </span>
        <button
          className="icon-button"
          title="Collapse assistant"
          onClick={onClose}
        >
          <ChevronRight size={16} />
        </button>
      </div>
      <div className="chat-context">
        <span className="status-dot" />
        Looking at {job ? job.company : view.toLowerCase()}
      </div>
      <div className="chat-content">
        <div className="assistant-avatar">
          <Leaf size={21} />
        </div>
        <h3>
          A little clarity for
          <br />
          your next move.
        </h3>
        <p>
          I can help you explore your matches, surface your experience, and plan
          what comes next.
        </p>
        <div className="chat-intro">
          Your data stays on this device.
          <br />
          You stay in control of every application.
        </div>
        <span className="rail-label">A FEW PLACES TO START</span>
        {[
          "Show my strongest matches",
          "Explain this match",
          "What should I do next?",
        ].map((text) => (
          <button
            className="suggestion"
            key={text}
            onClick={() => void send(text)}
          >
            {text}
            <ArrowUpRight size={14} />
          </button>
        ))}
        {messages.map((m, i) => (
          <div key={i} className={"chat-message " + m.role}>
            <small>{m.role === "user" ? "YOU" : "FIRSTLOOK"}</small>
            <p>{m.text}</p>
          </div>
        ))}
      </div>
      <div className="chat-bottom">
        <div className="chat-mode">
          <span className="tiny-dot" />
          {mode === "local"
            ? "Local tools · no AI spend"
            : "Provider response · budget recorded"}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void send(input);
          }}
        >
          <textarea
            aria-label="Ask your search partner"
            placeholder="Ask about your search…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <div>
            <span>
              <Command size={12} />
              Your workspace, in context
            </span>
            <button
              aria-label="Send message"
              disabled={sending || !input.trim()}
            >
              <ArrowUp size={16} />
            </button>
          </div>
        </form>
        <small>Suggestions are a starting point. You decide.</small>
      </div>
    </aside>
  );
}
