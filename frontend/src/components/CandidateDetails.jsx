import { Brain, Download, Inbox, Sparkles } from "lucide-react";
import { signedDownloadUrl } from "../services/api";

function initials(name = "") {
  return name.split(" ").filter(Boolean).map((x) => x[0]).join("").slice(0, 2).toUpperCase();
}

function statusClass(status = "") {
  return status.toLowerCase();
}

export default function CandidateDetails({ selected }) {
  if (!selected) {
    return (
      <div className="panel profile">
        <div className="empty big">
          <Inbox size={52} />
          <h2>Select a candidate</h2>
          <p>Their case file will open here.</p>
        </div>
      </div>
    );
  }

  const downloadUrl = signedDownloadUrl(selected.signed_contract_download_url);

  return (
    <div className="panel profile">
      <div className="profileTop">
        <span className="caseLabel">
          FILE-{String(selected.originalIndex + 1).padStart(3, "0")}
        </span>

        <div className="profileHeading">
          <div className="avatar large">{initials(selected.name)}</div>
          <div>
            <h2>{selected.name}</h2>
            <p>{selected.email}</p>
          </div>
        </div>

        <span className={`stamp ${statusClass(selected.status)}`}>
          <span className="stampDot" />
          {selected.status}
        </span>
      </div>

      <div className="scoreHero">
        <div className="gauge">
          <svg width="116" height="116" viewBox="0 0 116 116">
            <circle className="gaugeTrack" cx="58" cy="58" r="48" fill="none" strokeWidth="9" />
            <circle
              className="gaugeValue"
              cx="58"
              cy="58"
              r="48"
              fill="none"
              strokeWidth="9"
              strokeLinecap="round"
              strokeDasharray="302"
              strokeDashoffset={302 - (302 * selected.candidate_score) / 100}
            />
          </svg>

          <div className="gaugeReadout">
            <span className="gaugeNumber">{selected.candidate_score}</span>
            <span className="gaugeUnit">MATCH</span>
          </div>
        </div>

        <div className="scoreContext">
          <p className="eyebrow">AI Evaluation</p>
          <h3>Composite candidate match</h3>
          <p className="scoreCaption">
            Derived from role fit, experience signal and written evaluation.
          </p>
        </div>

        <Brain className="scoreBrain" size={28} />
      </div>

      <div className="split">
        <div className="miniPanel">
          <p>Recommended Role</p>
          <h3>{selected.recommended_role}</h3>
        </div>

        <div className="miniPanel">
          <p>Email Subject</p>
          <h3>{selected.email_subject}</h3>
        </div>
      </div>

      <div className="report">
        <h3><Sparkles size={15} /> Evaluation Report</h3>
        <p>{selected.report}</p>
      </div>

      <div className="actions">
        {downloadUrl ? (
          <a className="primary" href={downloadUrl} target="_blank">
            <Download size={17} />
            Download Signed Contract
          </a>
        ) : (
          <button className="disabled">Waiting for coordinator signature</button>
        )}
      </div>
    </div>
  );
}