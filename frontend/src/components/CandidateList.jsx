import { Inbox } from "lucide-react";

function initials(name = "") {
  return name.split(" ").filter(Boolean).map((x) => x[0]).join("").slice(0, 2).toUpperCase();
}

function statusClass(status = "") {
  return status.toLowerCase();
}

export default function CandidateList({ loading, candidates, selectedIndex, setSelectedIndex }) {
  return (
    <div className="panel queue">
      <div className="panelHead">
        <div>
          <h3>Application Queue</h3>
          <p>{candidates.length} candidates on file</p>
        </div>
      </div>

      {loading && <div className="empty">Loading applications...</div>}

      {!loading && candidates.length === 0 && (
        <div className="empty">
          <Inbox size={42} />
          <h3>No applications yet</h3>
          <p>When n8n sends a CV, it opens a case here.</p>
        </div>
      )}

      <div className="candidateList">
        {candidates.map((app, index) => (
          <button
            key={`${app.email}-${app.originalIndex}`}
            className={index === selectedIndex ? "candidate active" : "candidate"}
            onClick={() => setSelectedIndex(index)}
          >
            <span className="fileTag">
              FILE-{String(app.originalIndex + 1).padStart(3, "0")}
            </span>

            <div className="avatar">{initials(app.name)}</div>

            <div className="candidateMeta">
              <strong>{app.name}</strong>
              <p>{app.recommended_role}</p>
              <small>{app.email}</small>
            </div>

            <div className="candidateRight">
              <span className="scorePill">{app.candidate_score}</span>
              <span className={`stamp ${statusClass(app.status)}`}>
                <span className="stampDot" />
                {app.status}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}