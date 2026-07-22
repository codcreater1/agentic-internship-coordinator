import { Inbox } from "lucide-react";
import { statusLabel } from "../services/status";

function initials(name = "") {
  return name.split(" ").filter(Boolean).map((x) => x[0]).join("").slice(0, 2).toUpperCase();
}

function statusClass(status = "") {
  return status.toLowerCase();
}

const EMPTY_COPY = {
  active: {
    title: "No open cases",
    body: "When n8n sends a CV, it opens a case here.",
  },
  completed: {
    title: "No closed cases yet",
    body: "Signed contracts and rejected applications land here.",
  },
};

export default function CandidateList({
  loading,
  candidates,
  selectedId,
  setSelectedId,
  tab,
  setTab,
  counts,
}) {
  const empty = EMPTY_COPY[tab];

  return (
    <div className="panel queue">
      <div className="panelHead">
        <div>
          <h3>Application Queue</h3>
          <p>
            {candidates.length} {tab === "completed" ? "closed" : "open"}{" "}
            {candidates.length === 1 ? "case" : "cases"}
          </p>
        </div>
      </div>

      <div className="queueTabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "active"}
          className={tab === "active" ? "queueTab on" : "queueTab"}
          onClick={() => setTab("active")}
        >
          Active <span className="tabCount">{counts.active}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "completed"}
          className={tab === "completed" ? "queueTab on" : "queueTab"}
          onClick={() => setTab("completed")}
        >
          Completed <span className="tabCount">{counts.completed}</span>
        </button>
      </div>

      {loading && candidates.length === 0 && (
        <div className="empty">Loading applications...</div>
      )}

      {!loading && candidates.length === 0 && (
        <div className="empty">
          <Inbox size={42} />
          <h3>{empty.title}</h3>
          <p>{empty.body}</p>
        </div>
      )}

      <div className="candidateList">
        {candidates.map((app) => {
          const signed = Boolean(app.signed_contract_download_url);
          return (
            <button
              key={app.id}
              className={app.id === selectedId ? "candidate active" : "candidate"}
              onClick={() => setSelectedId(app.id)}
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
                <span className={`stamp ${signed ? "signed" : statusClass(app.status)}`}>
                  <span className="stampDot" />
                  {signed ? "signed" : statusLabel(app.status)}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
