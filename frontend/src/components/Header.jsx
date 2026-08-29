import { Bell, RefreshCw, Search } from "lucide-react";

export default function Header({ query, setQuery, loading, refresh }) {
  return (
    <header className="top">
      <div>
        <p className="eyebrow">Recruitment Command Center</p>
        <h1>Applications Inbox</h1>
        <p className="sub">
          Candidate emails captured by n8n appear here after AI review,
          contract drafting and coordinator signature.
        </p>
      </div>

      <div className="topActions">
        <div className="search">
          <Search size={18} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search candidate..."
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