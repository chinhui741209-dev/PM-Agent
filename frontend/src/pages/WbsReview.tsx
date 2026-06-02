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

// 節點自身 + 所有子孫的數量（刪除確認用）
function countSubtree(node: WbsNode): number {
  return 1 + (node.children ?? []).reduce((sum, c) => sum + countSubtree(c), 0);
}

function updateNode(nodes: WbsNode[], id: string, patch: Partial<WbsNode>): WbsNode[] {
  return nodes.map((n) => {
    if (n.id === id) return { ...n, ...patch };
    if (n.children?.length) return { ...n, children: updateNode(n.children, id, patch) };
    return n;
  });
}

// ---- 結構編輯（新增 / 刪除 / 上下移 / 升降級）----
// 後端 PUT /api/wbs/{id} 會整份覆寫，故結構調整只需在前端重組樹，存檔即生效。

const TYPES: WbsNode["type"][] = ["epic", "story", "task", "subtask"];
const typeForDepth = (d: number): WbsNode["type"] => TYPES[Math.min(d, TYPES.length - 1)];

function newNode(depth: number): WbsNode {
  return {
    id: crypto.randomUUID(),
    type: typeForDepth(depth),
    title: "新工作項",
    description: "",
    deliverable: null,
    owner_unit: null,
    assignee_account_id: null,
    estimate_days: null,
    start_date: null,
    due_date: null,
    milestone_id: null,
    workflow_stage: null,
    dependencies: [],
    children: [],
  };
}

function addChild(nodes: WbsNode[], parentId: string, depth = 0): WbsNode[] {
  return nodes.map((n) => {
    if (n.id === parentId) return { ...n, children: [...(n.children ?? []), newNode(depth + 1)] };
    if (n.children?.length) return { ...n, children: addChild(n.children, parentId, depth + 1) };
    return n;
  });
}

function removeNode(nodes: WbsNode[], id: string): WbsNode[] {
  return nodes
    .filter((n) => n.id !== id)
    .map((n) => (n.children?.length ? { ...n, children: removeNode(n.children, id) } : n));
}

// 在同層的兄弟間上移(-1)/下移(+1)；到邊界則不動
function moveNode(nodes: WbsNode[], id: string, dir: -1 | 1): WbsNode[] {
  const idx = nodes.findIndex((n) => n.id === id);
  if (idx !== -1) {
    const j = idx + dir;
    if (j < 0 || j >= nodes.length) return nodes;
    const copy = [...nodes];
    [copy[idx], copy[j]] = [copy[j], copy[idx]];
    return copy;
  }
  return nodes.map((n) => (n.children?.length ? { ...n, children: moveNode(n.children, id, dir) } : n));
}

// 降級：成為前一個兄弟的子節點（最上面一個無前兄弟，無法降級）
function indentNode(nodes: WbsNode[], id: string, depth = 0): WbsNode[] {
  const idx = nodes.findIndex((n) => n.id === id);
  if (idx > 0) {
    const node = { ...nodes[idx], type: typeForDepth(depth + 1) };
    const prev = nodes[idx - 1];
    const copy = [...nodes];
    copy[idx - 1] = { ...prev, children: [...(prev.children ?? []), node] };
    copy.splice(idx, 1);
    return copy;
  }
  return nodes.map((n) => (n.children?.length ? { ...n, children: indentNode(n.children, id, depth + 1) } : n));
}

// 升級：脫離父節點，成為父節點的下一個兄弟（頂層節點無父，無法升級）
function outdentNode(nodes: WbsNode[], id: string, depth = 0): WbsNode[] {
  const out: WbsNode[] = [];
  for (const n of nodes) {
    const childIdx = (n.children ?? []).findIndex((c) => c.id === id);
    if (childIdx !== -1) {
      const child = { ...n.children[childIdx], type: typeForDepth(depth) };
      out.push({ ...n, children: n.children.filter((_, i) => i !== childIdx) });
      out.push(child);
    } else {
      out.push(n.children?.length ? { ...n, children: outdentNode(n.children, id, depth + 1) } : n);
    }
  }
  return out;
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

  // 結構操作：改完只更新前端狀態，按「儲存」才寫回後端（與欄位編輯一致）
  const mutate = (fn: (nodes: WbsNode[]) => WbsNode[]) =>
    setDraft((d) => (d ? { ...d, nodes: fn(d.nodes) } : d));

  function addChildRow(node: WbsNode) {
    mutate((nodes) => addChild(nodes, node.id));
  }
  function addRoot() {
    setDraft((d) => (d ? { ...d, nodes: [...d.nodes, newNode(0)] } : d));
  }
  function deleteRow(node: WbsNode) {
    const n = node.children?.length ? countSubtree(node) : 1;
    if (n > 1 && !window.confirm(`確定刪除「${node.title}」及其 ${n - 1} 個子項？`)) return;
    mutate((nodes) => removeNode(nodes, node.id));
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

  async function downloadExcel() {
    if (!draft) return;
    setError("");
    try {
      // 先存檔，確保下載到的是最新編輯內容
      await api.saveWbs(draft);
      const a = document.createElement("a");
      a.href = `/api/wbs/${draft.id}/export.xlsx`;
      a.download = `WBS-${draft.id}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      setError(String(e));
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h2>工作分解結構（{rows.length} 項）</h2>
          <button className="secondary" onClick={addRoot}>＋ 新增主項目</button>
        </div>
        <p className="muted">可直接編輯欄位；用最右側按鈕新增子項、調整層級或刪除。改完記得按「儲存」。</p>
        <table>
          <thead>
            <tr>
              <th style={{ width: "30%" }}>工作項</th>
              <th>負責單位</th>
              <th>初始階段</th>
              <th>開始</th>
              <th>到期</th>
              <th>估時(天)</th>
              <th style={{ width: 1, whiteSpace: "nowrap" }}>操作</th>
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
                <td>
                  <div className="row-actions">
                    <button className="ghost" title="新增子項" onClick={() => addChildRow(node)}>＋</button>
                    <button className="ghost" title="上移" onClick={() => mutate((n) => moveNode(n, node.id, -1))}>↑</button>
                    <button className="ghost" title="下移" onClick={() => mutate((n) => moveNode(n, node.id, 1))}>↓</button>
                    <button className="ghost" title="升級（往左移一層）" disabled={depth === 0} onClick={() => mutate((n) => outdentNode(n, node.id))}>⬅</button>
                    <button className="ghost" title="降級（成為前一項的子項）" onClick={() => mutate((n) => indentNode(n, node.id))}>➡</button>
                    <button className="ghost danger" title="刪除" onClick={() => deleteRow(node)}>🗑</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {error && <div className="error">{error}</div>}

      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <button onClick={save} disabled={saving}>{saving ? "儲存中…" : "💾 儲存 WBS"}</button>
        <button className="secondary" onClick={downloadExcel}>⬇️ 下載 Excel</button>
        <button className="secondary" onClick={() => nav(`/deploy/${draft.id}`)}>前往部署 Jira →</button>
        {savedAt && <span className="muted">已於 {savedAt} 儲存</span>}
      </div>
    </div>
  );
}
