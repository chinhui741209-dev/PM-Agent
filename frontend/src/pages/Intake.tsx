import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { WorkflowTemplate } from "../api/types";

export default function Intake() {
  const nav = useNavigate();
  const [mode, setMode] = useState<"text" | "file">("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [deliverables, setDeliverables] = useState("");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [conditions, setConditions] = useState("");
  const [orgUnits, setOrgUnits] = useState("");
  const [workflows, setWorkflows] = useState<WorkflowTemplate[]>([]);
  const [workflowId, setWorkflowId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [phase, setPhase] = useState(-1);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    api.workflows().then((w) => {
      setWorkflows(w);
      if (w.length) setWorkflowId(w[0].id);
    });
    api.orgUnits().then((u) => setOrgUnits(u.join(", ")));
  }, []);

  async function parseFile() {
    if (!file) return;
    setBusy(true);
    setError("");
    setNote("");
    try {
      const res = await api.intakeFile(file);
      setText(res.requirement_text);
      if (res.extracted_deliverables.length) {
        setDeliverables(res.extracted_deliverables.join("\n"));
      }
      setNote(res.note || `已從 ${res.source} 解析出 ${res.requirement_text.length} 字。`);
      setMode("text");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function generate() {
    setBusy(true);
    setError("");
    setPhase(0);
    setElapsed(0);
    // 後端目前無進度回報；依經過時間推進階段標示，最後一階段停住等真正回應。
    const started = Date.now();
    const timer = setInterval(() => {
      const sec = Math.floor((Date.now() - started) / 1000);
      setElapsed(sec);
      setPhase(sec < 3 ? 0 : sec < 12 ? 1 : sec < 22 ? 2 : 3);
    }, 500);
    try {
      let requirementText = text;
      if (mode === "file" && file) {
        const res = await api.intakeFile(file);
        requirementText = res.requirement_text;
      }
      if (!requirementText.trim()) {
        throw new Error("請先輸入需求文字或上傳檔案");
      }
      const draft = await api.generateWbs({
        requirement_text: requirementText,
        deliverables: deliverables.split("\n").map((d) => d.trim()).filter(Boolean),
        delivery_date: deliveryDate || null,
        conditions,
        org_units: orgUnits.split(/[,，]/).map((u) => u.trim()).filter(Boolean),
        workflow_template_id: workflowId || null,
      });
      nav(`/wbs/${draft.id}`);
    } catch (e) {
      setError(String(e));
    } finally {
      clearInterval(timer);
      setBusy(false);
      setPhase(-1);
    }
  }

  const PHASES = [
    "解析需求內容",
    "AI 拆解工作項（Epic / Story / Task）",
    "計算排程與相依順序",
    "整理為繁體中文並組成樹狀結構",
  ];

  return (
    <div>
      <h1>輸入需求 / 技術規格</h1>
      <p className="muted">貼上需求或上傳文件，填入交付物與交付日，AI 會自動產生 WBS。</p>

      <div className="panel">
        <h2>需求來源</h2>
        <div className="tabs">
          <button className={mode === "text" ? "active" : ""} onClick={() => setMode("text")}>
            貼上文字
          </button>
          <button className={mode === "file" ? "active" : ""} onClick={() => setMode("file")}>
            上傳檔案
          </button>
        </div>

        {mode === "text" ? (
          <>
            <label>需求 / 技術規格內容</label>
            <textarea
              rows={10}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="例：開發一套內部請假系統，支援多層簽核、行事曆整合、報表匯出…"
            />
          </>
        ) : (
          <>
            <label>上傳 Word / PDF / Markdown / Excel</label>
            <input
              type="file"
              accept=".docx,.pdf,.md,.markdown,.txt,.xlsx,.xls"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <div style={{ marginTop: 12 }}>
              <button className="secondary" onClick={parseFile} disabled={!file || busy}>
                解析並預覽
              </button>
            </div>
          </>
        )}
        {note && <div className="info">{note}</div>}
      </div>

      <div className="panel">
        <h2>交付條件</h2>
        <div className="row">
          <div>
            <label>交付物（一行一個）</label>
            <textarea
              rows={5}
              value={deliverables}
              onChange={(e) => setDeliverables(e.target.value)}
              placeholder={"前端介面\n後端 API\n部署文件"}
            />
          </div>
          <div>
            <label>交付日</label>
            <input type="date" value={deliveryDate} onChange={(e) => setDeliveryDate(e.target.value)} />
            <label>相關條件 / 限制</label>
            <textarea
              rows={2}
              value={conditions}
              onChange={(e) => setConditions(e.target.value)}
              placeholder="例：須符合資安規範、預算限制、外包依賴…"
            />
          </div>
        </div>
        <div className="row">
          <div>
            <label>可用組織單位（逗號分隔，供 AI 指派負責單位）</label>
            <input type="text" value={orgUnits} onChange={(e) => setOrgUnits(e.target.value)} />
          </div>
          <div>
            <label>工作流模板</label>
            <select value={workflowId} onChange={(e) => setWorkflowId(e.target.value)}>
              {workflows.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}（{w.stages.join(" → ")}）
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {busy && phase >= 0 && (
        <div className="panel">
          <h2 style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <span>AI 產生 WBS 中…</span>
            <span className="muted">已耗時 {elapsed}s</span>
          </h2>
          <ol className="progress-steps">
            {PHASES.map((p, i) => (
              <li key={i} className={i < phase ? "done" : i === phase ? "active" : ""}>
                <span className="mark">{i < phase ? "✓" : i === phase ? "▶" : "○"}</span>
                {p}
              </li>
            ))}
          </ol>
          <p className="muted">本地模型約需 10–30 秒，請勿關閉頁面。</p>
        </div>
      )}

      <button onClick={generate} disabled={busy}>
        {busy ? "AI 產生 WBS 中…" : "🚀 產生 WBS"}
      </button>
    </div>
  );
}
