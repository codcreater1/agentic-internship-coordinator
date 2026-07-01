import { FileText, Inbox, Mail, ShieldCheck, Sparkles } from "lucide-react";

export default function Sidebar() {
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
        <span className="navItem active"><Inbox size={18} /> Inbox</span>
        <span className="navItem"><FileText size={18} /> Contracts</span>
        <span className="navItem"><Mail size={18} /> Emails</span>
        <span className="navItem"><ShieldCheck size={18} /> Security</span>
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