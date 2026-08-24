import {
  AlertCircle,
  Brain,
  CalendarCheck,
  FileText,
  GraduationCap,
  Info,
  ShieldAlert,
} from "lucide-react";

import { reportAttachmentUrl } from "../services/reportsApi";
import {
  DOCUMENT_LABELS,
  REPORT_STATUS_SUMMARY,
  reportStatusLabel,
  severityLabel,
} from "../services/status";

function initials(name = "") {
  return name.split(" ").filter(Boolean).map((x) => x[0]).join("").slice(0, 2).toUpperCase();
}

// Findings are grouped by what they demand rather than listed flat: a
// coordinator needs to separate "the student must fix this" from "you should
// look at this" before reading a single message.
const GROUPS = [
  {
    severity: "reject",
    title: "Cannot be approved",
    icon: ShieldAlert,
    className: "findingGroup bad",
    note: "Resending will not clear these. They need a conversation with the student.",
  },
  {
    severity: "clarify",
    title: "Waiting on the student",
    icon: AlertCircle,
    className: "findingGroup warn",
    note: "The student has been emailed exactly these points and can resend once fixed.",
  },
  {
    severity: "warning",
    title: "Open points for you",
    icon: Info,
    className: "findingGroup warn",
    note: "Nothing here blocks a signature, but each needs a decision before you give one.",
  },
  {
    severity: "info",
    title: "Notes",
    icon: Info,
    className: "findingGroup",
    note: null,
  },
];

export default function CompletionDetails({ selected, loading }) {
  if (loading && !selected) {
    return (
      <div className="panel profile">
        <div className="empty big">Loading submission...</div>
      </div>
    );
  }

  if (!selected) {
    return (
      <div className="panel profile">
        <div className="empty big">
          <GraduationCap size={52} />
          <h2>Select a submission</h2>
          <p>The internship record will open here.</p>
        </div>
      </div>
    );
  }

  const findings = selected.findings || [];
  const advisory = selected.advisory;

  return (
    <div className="panel profile">
      <div className="profileTop">
        <span className="caseLabel">{selected.student_id || "no student id"}</span>

        <div className="profileHeading">
          <div className="avatar large">{initials(selected.student_name || "?")}</div>
          <div>
            <h2>{selected.student_name || "Unnamed student"}</h2>
            <p>{selected.intern_email}</p>
          </div>
        </div>

        <span className={`stamp ${selected.status}`}>
          <span className="stampDot" />
          {reportStatusLabel(selected.status)}
        </span>
      </div>

      <div className="statusNote">
        <CalendarCheck size={17} />
        <p>{REPORT_STATUS_SUMMARY[selected.status] || selected.report}</p>
      </div>

      {/* The verified figures — what the certificate would actually assert. */}
      <div className="verifiedGrid">
        <div className="miniPanel">
          <p>Attended working days</p>
          <h3>
            {selected.counted_working_days}
            <small> / {selected.total_hours}h</small>
          </h3>
        </div>
        <div className="miniPanel">
          <p>Employer evaluation</p>
          <h3>
            {selected.evaluation_score ?? "—"}
            {selected.evaluation_score !== null && <small> / 100</small>}
          </h3>
        </div>
        <div className="miniPanel">
          <p>Report length</p>
          <h3>
            {selected.report_word_count}
            <small> words</small>
          </h3>
        </div>
        <div className="miniPanel">
          <p>Peak similarity</p>
          <h3>{Math.round((selected.max_similarity || 0) * 100)}%</h3>
        </div>
      </div>

      <div className="split">
        <div className="miniPanel">
          <p>Host organisation</p>
          <h3>{selected.company || "—"}</h3>
        </div>
        <div className="miniPanel">
          <p>Internship period</p>
          <h3>
            {selected.start_date || "—"} → {selected.end_date || "—"}
          </h3>
        </div>
      </div>

      {/* Findings, grouped by what they demand. */}
      {GROUPS.map((group) => {
        const items = findings.filter((f) => f.severity === group.severity);
        if (items.length === 0) return null;
        const Icon = group.icon;

        return (
          <div key={group.severity} className={group.className}>
            <h3>
              <Icon size={15} /> {group.title}
              <span className="findingCount">{items.length}</span>
            </h3>
            {group.note && <p className="findingNote">{group.note}</p>}

            <ul className="findingList">
              {items.map((f) => (
                <li key={f.code}>
                  <div className="findingHead">
                    <code>{f.code}</code>
                    <span className={`sevTag ${f.severity}`}>
                      {severityLabel(f.severity)}
                    </span>
                  </div>
                  <p>{f.message}</p>
                  {f.remedy && (
                    <p className="findingRemedy">
                      <strong>Student was told:</strong> {f.remedy}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        );
      })}

      {findings.length === 0 && (
        <div className="findingGroup ok">
          <h3>
            <CalendarCheck size={15} /> No findings
          </h3>
          <p className="findingNote">
            Every check passed. Nothing was raised against this submission.
          </p>
        </div>
      )}

      {/* Advisory reading — explicitly labelled as not part of the decision. */}
      {advisory && (
        <div className="report advisory">
          <h3>
            <Brain size={15} /> Advisory reading
          </h3>
          {advisory.available ? (
            <>
              <p>{advisory.summary}</p>
              {advisory.role_alignment && (
                <p className="advisoryLine">
                  <strong>Role alignment:</strong> {advisory.role_alignment}
                </p>
              )}
              {advisory.depth_rating !== null &&
                advisory.depth_rating !== undefined && (
                  <p className="advisoryLine">
                    <strong>Technical depth:</strong> {advisory.depth_rating}/100
                  </p>
                )}
              {advisory.questions_for_coordinator?.length > 0 && (
                <>
                  <p className="advisoryLine">
                    <strong>Worth asking:</strong>
                  </p>
                  <ul className="advisoryQuestions">
                    {advisory.questions_for_coordinator.map((q) => (
                      <li key={q}>{q}</li>
                    ))}
                  </ul>
                </>
              )}
              <p className="advisoryFoot">
                Written by the model after the decision was already made. It did
                not affect the status above.
              </p>
            </>
          ) : (
            <p className="advisoryFoot">{advisory.summary}</p>
          )}
        </div>
      )}

      {/* The submitted documents themselves. */}
      {selected.documents?.length > 0 && (
        <div className="docList">
          <h3>
            <FileText size={15} /> Submitted documents
          </h3>
          {selected.documents.map((doc) => (
            <a
              key={doc.sha256}
              className="docRow"
              href={reportAttachmentUrl(selected.id, doc.role)}
              target="_blank"
              rel="noreferrer"
            >
              <div>
                <strong>{DOCUMENT_LABELS[doc.role] || doc.role}</strong>
                <small>
                  {doc.filename} · {doc.page_count} pp
                </small>
              </div>
              <code title={doc.sha256}>{doc.sha256.slice(0, 12)}…</code>
            </a>
          ))}
          <p className="findingNote">
            The signed certificate carries the hash of these exact files, so it
            cannot be detached from what it attests to.
          </p>
        </div>
      )}
    </div>
  );
}
