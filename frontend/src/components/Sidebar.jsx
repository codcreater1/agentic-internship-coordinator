import { FileText, GraduationCap, Inbox, Mail, ShieldCheck, Sparkles } from "lucide-react";

// Inbox and Completions are the two real views — the applications queue and
// the end-of-internship queue. The rest stay decorative, as they were.
const VIEWS = [
  { key: "applications", label: "Inbox", icon: Inbox },
  { key: "completions", label: "Completions", icon: GraduationCap },
];

const DECORATIVE = [
  { label: "Contracts", icon: FileText },
  { label: "Emails", icon: Mail },
  { label: "Security", icon: ShieldCheck },
];

export default function Sidebar({ view, setView, completionBadge = 0 }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brandMark">
          <Sparkles size={20} />
        </div>
        <div>
          <h2>Agentic IC</h2>
          <p>Candidate Intelligence</p>
        </div>
      </div>

      <nav className="nav">
        {VIEWS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            className={view === key ? "navItem active" : "navItem"}
            onClick={() => setView(key)}
          >
            <Icon size={18} /> {label}
            {/* Only surfaced on Completions, and only when something is
                actually waiting on the coordinator. A badge that is always
                lit stops being read. */}
            {key === "completions" && completionBadge > 0 && (
              <span className="navBadge">{completionBadge}</span>
            )}
          </button>
        ))}

        {DECORATIVE.map(({ label, icon: Icon }) => (
          <span key={label} className="navItem">
            <Icon size={18} /> {label}
          </span>
        ))}
      </nav>

      <div className="sideStatus">
        <div className="pulse" />
        <div>
          <strong>System online</strong>
          <p>n8n → FastAPI → Dashboard</p>
        </div>
      </div>
    </aside>
  );
}
