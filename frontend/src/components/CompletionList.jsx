import { GraduationCap } from "lucide-react";
import { COMPLETION_TABS, tabFor } from "../services/completionTabs";
import { reportStatusLabel } from "../services/status";

function initials(name = "") {
  return name.split(" ").filter(Boolean).map((x) => x[0]).join("").slice(0, 2).toUpperCase();
}

export default function CompletionList({
  loading,
  submissions,
  selectedId,
  setSelectedId,
  tab,
  setTab,
  counts,
}) {
  const active = tabFor(tab);

  return (
    <div className="panel queue">
      <div className="panelHead">
        <div>
          <h3>Completion Queue</h3>
          <p>
            {submissions.length}{" "}
            {submissions.length === 1 ? "submission" : "submissions"}
          </p>
        </div>
      </div>

      <div className="queueTabs" role="tablist">
        {COMPLETION_TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={tab === t.key ? "queueTab on" : "queueTab"}
            onClick={() => setTab(t.key)}
          >
            {t.label} <span className="tabCount">{counts[t.key] ?? 0}</span>
          </button>
        ))}
      </div>

      {loading && submissions.length === 0 && (
        <div className="empty">Loading submissions...</div>
      )}

      {!loading && submissions.length === 0 && (
        <div className="empty">
          <GraduationCap size={42} />
          <h3>{active.empty.title}</h3>
          <p>{active.empty.body}</p>
        </div>
      )}

      <div className="candidateList">
        {submissions.map((s) => (
          <button
            key={s.id}
            className={s.id === selectedId ? "candidate active" : "candidate"}
            onClick={() => setSelectedId(s.id)}
          >
            <span className="fileTag">{s.student_id || "no id"}</span>

            <div className="avatar">{initials(s.student_name || "?")}</div>

            <div className="candidateMeta">
              <strong>{s.student_name || "Unnamed student"}</strong>
              <p>{s.company || "No host organisation stated"}</p>
              <small>
                {s.counted_working_days} days
                {s.evaluation_score !== null && s.evaluation_score !== undefined
                  ? ` · ${s.evaluation_score}/100`
                  : ""}
              </small>
            </div>

            <div className="candidateRight">
              {/* The number a coordinator actually acts on: how many things
                  the student must fix, or how many points need a decision. */}
              {s.clarification_count > 0 && (
                <span className="scorePill warn">{s.clarification_count}</span>
              )}
              {s.clarification_count === 0 && s.warning_count > 0 && (
                <span className="scorePill warn">{s.warning_count}</span>
              )}

              <span className={`stamp ${s.status}`}>
                <span className="stampDot" />
                {reportStatusLabel(s.status)}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
