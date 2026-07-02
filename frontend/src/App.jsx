import { useEffect, useMemo, useState } from "react";
import "./App.css";

import { getApplications } from "./services/api";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import CandidateList from "./components/CandidateList";
import CandidateDetails from "./components/CandidateDetails";
import WorkflowPanel from "./components/WorkflowPanel";
import ContractPanel from "./components/ContractPanel";

export default function App() {
  const [applications, setApplications] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadApplications() {
    setLoading(true);
    try {
      const data = await getApplications();
      setApplications(Array.isArray(data) ? data : []);
      setSelectedIndex(0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadApplications();
    const interval = setInterval(loadApplications, 12000);
    return () => clearInterval(interval);
  }, []);

  const filtered = useMemo(() => {
    return applications
      .map((app, originalIndex) => ({ ...app, originalIndex }))
      .filter((app) => {
        const text = `${app.name} ${app.email} ${app.recommended_role} ${app.status}`.toLowerCase();
        return text.includes(query.toLowerCase());
      });
  }, [applications, query]);

  const selected = filtered[selectedIndex] || null;

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
            selectedIndex={selectedIndex}
            setSelectedIndex={setSelectedIndex}
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