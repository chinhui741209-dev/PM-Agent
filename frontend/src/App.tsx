import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import Intake from "./pages/Intake";
import WbsReview from "./pages/WbsReview";
import Deploy from "./pages/Deploy";

export default function App() {
  const [health, setHealth] = useState<{ openai_configured: boolean; jira_configured: boolean } | null>(
    null
  );

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <>
      <nav className="nav">
        <span className="brand">🤖 AI Agent PM</span>
        <NavLink to="/" end>輸入需求</NavLink>
        <NavLink to="/wbs">WBS 檢視</NavLink>
        <NavLink to="/deploy">部署 Jira</NavLink>
        <span className="spacer" />
        {health && (
          <>
            <span className={`badge ${health.openai_configured ? "ok" : "off"}`}>
              OpenAI {health.openai_configured ? "已連線" : "未設定"}
            </span>
            <span className={`badge ${health.jira_configured ? "ok" : "off"}`}>
              Jira {health.jira_configured ? "已連線" : "未設定"}
            </span>
          </>
        )}
      </nav>
      <div className="container">
        <Routes>
          <Route path="/" element={<Intake />} />
          <Route path="/wbs" element={<WbsReview />} />
          <Route path="/wbs/:id" element={<WbsReview />} />
          <Route path="/deploy" element={<Deploy />} />
          <Route path="/deploy/:id" element={<Deploy />} />
        </Routes>
      </div>
    </>
  );
}
