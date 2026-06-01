import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { WbsDraft, WbsNode } from "../api/types";

interface FlatRow {
  node: WbsNode;
  depth: number;
}

function flatten(nodes: WbsNode[], depth = 0): FlatRow[] {
  const out: FlatRow[] = [];
  for (const node of nodes) {
    out.push({ node, depth });
    if (node.children?.length) out.push(...flatten(node.children, depth + 1));
  }
  return out;
}

function updateNode(nodes: WbsNode[], id: string, patch: Partial<WbsNode>): WbsNode[] {
  return nodes.map((n) => {
    if (n.id === id) return { ...n, ...patch };
    if (n.children?.length) return { ...n, children: updateNode(n.children, id, patch) };
    return n;
  });
}

export default function WbsReview() {
  const { id } = useParams();
  const nav = useNavigate();
  const [draft, setDraft] = useState<WbsDraft | null>(null);
  const [drafts, setDrafts] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState("");

  useEffect(() => {
    if (id) {
      api.getWbs(id).then(setDraft).catch((e) => setError(String(e)));
    } else {
      fetch("/api/wbs").then((r) => r.json()).then(setDrafts).catch(() => {});
    }
  }, [id]);

  if (!id) {
    return (
      <div>
        <h1>WBS 草稿</h1>
        {drafts.length === 0 ? (
          <p className="muted">尚無草稿，請先到「輸入需求」產生一份。</p>
        ) : (
          <div className="panel">
            <table>
              <thead>
                <tr><th>需求</th><th>交付日</th><th>節點數</th><th>更新時間</th><th></th></tr>
              </thead>
              <tbody>
                {drafts.map((d) => (
                  <tr key={d.id}>
                    <td>{d.requirement_text}</td>
                    <td>{d.delivery_date ?? "—"}</td>
                    <td>{d.node_count}</td>
                    <td className="muted">{d.updated_at?.slice(0, 19).replace("T", " ")}</td>
                    <td><button className="secondary" onClick={() => nav(`/wbs/${d.id}`)}>開啟</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  if (error) return <div className="error">{error}</div>;
  if (!draft) return <p className="spinner">載入中…</p>;

  const rows = flatten(draft.nodes);
  const stages = draft.workflow?.stages ?? [];
  const units = draft.org_units ?? [];

  function patch(nodeId: string, p: Partial<WbsNode>) {
    setDraft((d) => (d ? { ...d, nodes: updateNode(d.nodes, nodeId, p) } : d));
  }

  async function save() {
    if (!draft) return;
    setSaving(true);
    setError("");
    try {
      const updated = await api.saveWbs(draft);
      setDraft(updated);
      setSavedAt(new Date().toLocaleTimeString());
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h1>WBS 檢視與編輯</h1>
      <p className="muted">{draft.requirement_text.slice(0, 120)}</p>

      {draft.milestones.length > 0 && (
        <div className="panel">
          <h2>階段性里程碑</h2>
          <div className="milestone-bar">
            {draft.milestones.map((m) => (
              <div className="milestone-chip" key={m.id}>
                <div className="date">{m.date ?? "未定"}</div>
                <div>{m.name}</div>
                {m.deliverables.length > 0 && (
                  <div className="muted">{m.deliverables.join("、")}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel">
        <h2>工作分解結構（{rows.length} 項）</h2>
        <p className="muted">可直接編輯標題、負責單位、初始階段、日期與估時。</p>
        <table>
          <thead>
            <tr>
              <th style={{ width: "30%" }}>工作項</th>
              <th>負責單位</th>
              <th>初始階段</th>
              <th>開始</th>
              <th>到期</th>
              <th>估時(天)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ node, depth }) => (
              <tr key={node.id}>
                <td>
                  <div style={{ paddingLeft: depth * 16, display: "flex", gap: 6, alignItems: "center" }}>
                    <span className={`type-pill type-${node.type}`}>{node.type}</span>
                    <input
                      type="text"
                      value={node.title}
                      onChange={(e) => patch(node.id, { title: e.target.value })}
                      style={{ flex: 1 }}
                    />
                  </div>
                  {node.deliverable && <div className="muted" style={{ paddingLeft: depth * 16 + 8 }}>交付物：{node.deliverable}</div>}
                </td>
                <td>
                  <select
                    value={node.owner_unit ?? ""}
                    onChange={(e) => patch(node.id, { owner_unit: e.target.value || null })}
                  >
                    <option value="">— 未指派 —</option>
                    {units.map((u) => <option key={u} value={u}>{u}</option>)}
                    {node.owner_unit && !units.includes(node.owner_unit) && (
                      <option value={node.owner_unit}>{node.owner_unit}</option>
                    )}
                  </select>
                </td>
                <td>
                  <select
                    value={node.workflow_stage ?? ""}
                    onChange={(e) => patch(node.id, { workflow_stage: e.target.value || null })}
                  >
                    <option value="">—</option>
                    {stages.map((s) => <option key={s} value={s}>{s}</option>)}
                    {node.workflow_stage && !stages.includes(node.workflow_stage) && (
                      <option value={node.workflow_stage}>{node.workflow_stage}</option>
                    )}
                  </select>
                </td>
                <td>
                  <input type="date" value={node.start_date ?? ""} onChange={(e) => patch(node.id, { start_date: e.target.value || null })} />
                </td>
                <td>
                  <input type="date" value={node.due_date ?? ""} onChange={(e) => patch(node.id, { due_date: e.target.value || null })} />
                </td>
                <td>
                  <input
                    type="text"
                    value={node.estimate_days ?? ""}
                    onChange={(e) => patch(node.id, { estimate_days: e.target.value ? Number(e.target.value) : null })}
                    style={{ width: 60 }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {error && <div className="error">{error}</div>}

      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <button onClick={save} disabled={saving}>{saving ? "儲存中…" : "💾 儲存 WBS"}</button>
        <button className="secondary" onClick={() => nav(`/deploy/${draft.id}`)}>前往部署 Jira →</button>
        {savedAt && <span className="muted">已於 {savedAt} 儲存</span>}
      </div>
    </div>
  );
}
