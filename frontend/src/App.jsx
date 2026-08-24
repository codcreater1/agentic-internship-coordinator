import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";

import { getApplications } from "./services/api";
import { getReportSubmission, getReportSubmissions } from "./services/reportsApi";
import { countsByTab, tabFor } from "./services/completionTabs";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import CandidateList from "./components/CandidateList";
import CandidateDetails from "./components/CandidateDetails";
import WorkflowPanel from "./components/WorkflowPanel";
import ContractPanel from "./components/ContractPanel";
import CompletionList from "./components/CompletionList";
import CompletionDetails from "./components/CompletionDetails";
import CertificatePanel from "./components/CertificatePanel";

// Matches the n8n Gmail poll interval — refreshing faster only adds load.
const REFRESH_MS = 60000;

// A case is closed once the contract is signed, or the candidate was rejected.
// Everything else (pending review, interview awaiting signature) stays active.
function isCompleted(app) {
  return Boolean(app.signed_contract_download_url) || app.status === "rejected";
}

export default function App() {
  const [view, setView] = useState("applications");
  const [query, setQuery] = useState("");

  // --- applications ------------------------------------------------------
  const [applications, setApplications] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [tab, setTab] = useState("active");
  const [loading, setLoading] = useState(true);

  // --- completions -------------------------------------------------------
  const [submissions, setSubmissions] = useState([]);
  const [submissionTab, setSubmissionTab] = useState("toSign");
  const [selectedSubmissionId, setSelectedSubmissionId] = useState(null);
  const [submissionDetail, setSubmissionDetail] = useState(null);
  const [loadingSubmissions, setLoadingSubmissions] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const loadApplications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getApplications();
      setApplications(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSubmissions = useCallback(async () => {
    setLoadingSubmissions(true);
    try {
      const data = await getReportSubmissions();
      setSubmissions(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingSubmissions(false);
    }
  }, []);

  // Both queues are polled regardless of which one is on screen: the sidebar
  // badge is the point of the completion count, and a badge that only updates
  // once you open the view is not a badge.
  const loadAll = useCallback(async () => {
    await Promise.all([loadApplications(), loadSubmissions()]);
  }, [loadApplications, loadSubmissions]);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, REFRESH_MS);
    return () => clearInterval(interval);
  }, [loadAll]);

  // originalIndex is the position in the full newest-first list — the
  // index-based sign/preview endpoints depend on it, so map before filtering.
  const indexed = useMemo(
    () => applications.map((app, originalIndex) => ({ ...app, originalIndex })),
    [applications],
  );

  const counts = useMemo(
    () => ({
      active: indexed.filter((app) => !isCompleted(app)).length,
      completed: indexed.filter(isCompleted).length,
    }),
    [indexed],
  );

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return indexed
      .filter((app) => (tab === "completed" ? isCompleted(app) : !isCompleted(app)))
      .filter((app) => {
        const text =
          `${app.name} ${app.email} ${app.recommended_role} ${app.status}`.toLowerCase();
        return text.includes(q);
      });
  }, [indexed, query, tab]);

  // Track the selection by id so an auto-refresh never yanks the coordinator
  // off the case they are working on. Falls back to the first case in view.
  const selected = filtered.find((app) => app.id === selectedId) || filtered[0] || null;

  // --- completion queue derivations --------------------------------------

  const submissionCounts = useMemo(() => countsByTab(submissions), [submissions]);

  const filteredSubmissions = useMemo(() => {
    const q = query.toLowerCase();
    const active = tabFor(submissionTab);
    return submissions
      .filter(active.match)
      .filter((s) => {
        const text =
          `${s.student_name ?? ""} ${s.student_id ?? ""} ${s.company ?? ""} ${s.status}`.toLowerCase();
        return text.includes(q);
      });
  }, [submissions, query, submissionTab]);

  const selectedSubmissionRow =
    filteredSubmissions.find((s) => s.id === selectedSubmissionId) ||
    filteredSubmissions[0] ||
    null;

  // The queue rows are compact; the detail payload (findings, documents,
  // advisory reading) is fetched only for the row actually open.
  useEffect(() => {
    const id = selectedSubmissionRow?.id;
    if (!id) {
      setSubmissionDetail(null);
      return;
    }

    let cancelled = false;
    setLoadingDetail(true);
    getReportSubmission(id)
      .then((data) => {
        if (!cancelled) setSubmissionDetail(data);
      })
      .catch((err) => {
        console.error(err);
        if (!cancelled) setSubmissionDetail(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingDetail(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedSubmissionRow?.id, selectedSubmissionRow?.status]);

  // Only what is genuinely waiting on the coordinator.
  const toSignCount = submissionCounts.toSign ?? 0;

  return (
    <div className="shell">
      <Sidebar view={view} setView={setView} completionBadge={toSignCount} />

      <main className="main">
        <Header
          view={view}
          query={query}
          setQuery={setQuery}
          loading={view === "completions" ? loadingSubmissions : loading}
          refresh={loadAll}
        />

        {view === "applications" ? (
          <section className="workspace">
            <CandidateList
              loading={loading}
              candidates={filtered}
              selectedId={selected?.id ?? null}
              setSelectedId={setSelectedId}
              tab={tab}
              setTab={setTab}
              counts={counts}
            />

            <CandidateDetails selected={selected} />

            <div className="rightCol">
              <WorkflowPanel selected={selected} />
              <ContractPanel selected={selected} refresh={loadApplications} />
            </div>
          </section>
        ) : (
          <section className="workspace">
            <CompletionList
              loading={loadingSubmissions}
              submissions={filteredSubmissions}
              selectedId={selectedSubmissionRow?.id ?? null}
              setSelectedId={setSelectedSubmissionId}
              tab={submissionTab}
              setTab={setSubmissionTab}
              counts={submissionCounts}
            />

            <CompletionDetails selected={submissionDetail} loading={loadingDetail} />

            <div className="rightCol">
              <CertificatePanel selected={submissionDetail} refresh={loadSubmissions} />
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
