import { useState } from "react";
import JDParser from "./components/JDParser";
import CandidateDiscovery from "./components/CandidateDiscovery";
import EngagementChat from "./components/EngagementChat";
import Shortlist from "./components/Shortlist";
import "./App.css";

const TABS = ["Parse JD", "Discover", "Engage", "Shortlist"];

export default function App() {
  const [tab, setTab] = useState(0);
  const [parsedJD, setParsedJD] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [engagedData, setEngagedData] = useState({});

  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <svg viewBox="0 0 24 24" fill="white" width="18" height="18">
            <path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <h1>TalentScout AI</h1>
        <span className="badge">Catalyst Hackathon</span>
      </header>

      <nav className="tabs">
        {TABS.map((t, i) => (
          <button
            key={t}
            className={`tab ${tab === i ? "active" : ""}`}
            onClick={() => setTab(i)}
          >
            {i + 1}. {t}
          </button>
        ))}
      </nav>

      <main className="main">
        {tab === 0 && (
          <JDParser
            onParsed={(jd) => { setParsedJD(jd); setTab(1); }}
          />
        )}
        {tab === 1 && (
          <CandidateDiscovery
            parsedJD={parsedJD}
            onDiscovered={(c) => { setCandidates(c); }}
            candidates={candidates}
            onSelectCandidate={(id) => setTab(2)}
          />
        )}
        {tab === 2 && (
          <EngagementChat
            candidates={candidates}
            engagedData={engagedData}
            onUpdateEngagement={(id, data) =>
              setEngagedData((prev) => ({ ...prev, [id]: data }))
            }
            onDone={() => setTab(3)}
          />
        )}
        {tab === 3 && (
          <Shortlist
            candidates={candidates}
            engagedData={engagedData}
          />
        )}
      </main>
    </div>
  );
}
