import { Bell, RefreshCw, Search } from "lucide-react";

// One header serving both queues. The copy changes because the two views
// answer different questions: who should we take on, and who finished.
const COPY = {
  applications: {
    title: "Applications Inbox",
    sub: "Candidate emails captured by n8n appear here after AI review, contract drafting and coordinator signature.",
    placeholder: "Search candidate...",
  },
  completions: {
    title: "Internship Completions",
    sub: "End-of-internship packages — report, employer evaluation and attendance record — checked automatically and waiting for your signature.",
    placeholder: "Search student, company or ID...",
  },
};

export default function Header({ view = "applications", query, setQuery, loading, refresh }) {
  const copy = COPY[view] || COPY.applications;

  return (
    <header className="top">
      <div>
        <p className="eyebrow">Recruitment Command Center</p>
        <h1>{copy.title}</h1>
        <p className="sub">{copy.sub}</p>
      </div>

      <div className="topActions">
        <div className="search">
          <Search size={18} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={copy.placeholder}
          />
        </div>

        <button className="iconBtn">
          <Bell size={18} />
        </button>

        <button className="refresh" onClick={refresh}>
          <RefreshCw size={18} className={loading ? "spinning" : ""} />
          Refresh
        </button>
      </div>
    </header>
  );
}
