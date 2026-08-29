import { useEffect, useMemo, useState } from "react";
import "./App.css";

import { getApplications } from "./services/api";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import CandidateList from "./components/CandidateList";
import CandidateDetails from "./components/CandidateDetails";
import WorkflowPanel from "./components/WorkflowPanel";
import ContractPanel from "./components/ContractPanel";

// Matches the n8n Gmail poll interval — refreshing faster only adds load.
const REFRESH_MS = 60000;

// A case is closed once the contract is signed, or the candidate was rejected.
// Everything else (pending review, interview awaiting signature) stays active.
function isCompleted(app) {
  return Boolean(app.signed_contract_download_url) || app.status === "rejected";
}

export default function App() {
  const [applications, setApplications] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [tab, setTab] = useState("active");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadApplications() {
    setLoading(true);
    try {
      const data = await getApplications();
      setApplications(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadApplications();
    const interval = setInterval(loadApplications, REFRESH_MS);
    return () => clearInterval(interval);
  }, []);

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

  return (
    <div className="shell">
      <Sidebar />

      <main className="main">
        <Header
          query={query}
          setQuery={setQuery}
          loading={loading}
          refresh={loadApplications}
        />

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
      </main>
    </div>
  );
}
