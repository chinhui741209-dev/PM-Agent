import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { DeployResult, JiraMeta, JiraProject, WbsDraft } from "../api/types";

export default function Deploy() {
  const { id } = useParams();
  const [draft, setDraft] = useState<WbsDraft | null>(null);
  const [draftId, setDraftId] = useState(id ?? "");
  const [projects, setProjects] = useState<JiraProject[]>([]);
  const [projectKey, setProjectKey] = useState("");
  const [meta, setMeta] = useState<JiraMeta | null>(null);
  const [applyStatus, setApplyStatus] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<DeployResult | null>(null);

  useEffect(() => {
    if (id) {
      api.getWbs(id).then(setDraft).catch((e) => setError(String(e)));
    }
    api.jiraProjects().then(setProjects).catch((e) => setError(String(e)));
  }, [id]);

  async function loadMeta(key: string) {
    setProjectKey(key);
    setMeta(null);
    if (!key) return;
    try {
      setMeta(await api.jiraMeta(key));
    } catch (e) {
      setError(String(e));
    }
  }

  async function doDeploy() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const res = await api.deploy({
        draft_id: draftId,
        project_key: projectKey,
        apply_initial_status: applyStatus,
      });
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const countNodes = (n: WbsDraft | null) => {
    if (!n) return 0;
    let c = 0;
    const walk = (arr: any[]) => arr.forEach((x) => { c++; if (x.children) walk(x.children); });
    walk(n.nodes);
    return c;
  };

  return (
    <div>
      <h1>部署到 Jira</h1>

      {!id && (
        <div className="panel">
          <label>WBS 草稿 ID</label>
          <input type="text" value={draftId} onChange={(e) => setDraftId(e.target.value)} placeholder="貼上草稿 id" />
        </div>
      )}

      {draft && (
        <div className="info">
          將部署：<b>{countNodes(draft)}</b> 個工作項、<b>{draft.milestones.length}</b> 個里程碑
          （里程碑 → Jira Version、負責單位 → label、階層 → Epic/Story/Task）。
        </div>
      )}

      <div className="panel">
        <h2>目標 Jira 專案</h2>
        {projects.length === 0 ? (
          <p className="muted">尚未取得專案清單。請確認後端已設定 Jira 憑證（.env）。</p>
        ) : (
          <select value={projectKey} onChange={(e) => loadMeta(e.target.value)}>
            <option value="">— 選擇專案 —</option>
            {projects.map((p) => (
              <option key={p.key} value={p.key}>{p.name}（{p.key}）</option>
            ))}
          </select>
        )}

        {meta && (
          <div style={{ marginTop: 12 }}>
            <div className="row">
              <div>
                <label>專案 issue 類型</label>
                <div className="muted">{meta.issue_types.map((t) => t.name).join("、")}</div>
              </div>
              <div>
                <label>專案既有狀態（初始階段會對應到這些）</label>
                <div className="muted">{meta.statuses.join("、") || "—"}</div>
              </div>
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" style={{ width: "auto" }} checked={applyStatus} onChange={(e) => setApplyStatus(e.target.checked)} />
              部署後依工作流階段設定每張 issue 的初始狀態
            </label>
          </div>
        )}
      </div>

      {draft?.workflow && (
        <div className="panel">
          <h2>建議看板欄位順序</h2>
          <p className="muted">Jira REST API 無法自動建立自訂工作流，請依下列順序在 Jira 專案設定中調整看板欄位：</p>
          <div className="milestone-bar">
            {draft.workflow.stages.map((s, i) => (
              <div className="milestone-chip" key={s}>{i + 1}. {s}</div>
            ))}
          </div>
        </div>
      )}

      {error && <div className="error">{error}</div>}

      <button onClick={doDeploy} disabled={busy || !draftId || !projectKey}>
        {busy ? "部署中…" : "🚀 一鍵部署到 Jira"}
      </button>

      {result && (
        <div className="panel" style={{ marginTop: 20 }}>
          <h2>部署結果</h2>
          {result.milestones_created.length > 0 && (
            <p>已建立里程碑 Version：{result.milestones_created.join("、")}</p>
          )}
          {result.warnings.map((w, i) => <div className="warn" key={i}>⚠️ {w}</div>)}
          <table>
            <thead><tr><th>工作項</th><th>Issue</th><th>初始狀態</th><th>結果</th></tr></thead>
            <tbody>
              {result.created.map((c) => (
                <tr key={c.node_id}>
                  <td>{c.title}</td>
                  <td>{c.url ? <a href={c.url} target="_blank" rel="noreferrer">{c.issue_key}</a> : "—"}</td>
                  <td>{c.status_applied ?? "—"}</td>
                  <td className={c.error ? "deployed-err" : "deployed-ok"}>{c.error ? `✗ ${c.error}` : "✓ 已建立"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
