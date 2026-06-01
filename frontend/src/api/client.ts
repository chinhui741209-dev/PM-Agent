import type {
  DeployResult,
  IntakeResponse,
  JiraMeta,
  JiraProject,
  WbsDraft,
  WorkflowTemplate,
} from "./types";

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  async health() {
    return handle<{ openai_configured: boolean; jira_configured: boolean }>(
      await fetch("/api/health")
    );
  },

  async workflows() {
    return handle<WorkflowTemplate[]>(await fetch("/api/templates/workflows"));
  },

  async orgUnits() {
    return handle<string[]>(await fetch("/api/templates/org-units"));
  },

  async intakeText(text: string) {
    const fd = new FormData();
    fd.append("text", text);
    return handle<IntakeResponse>(await fetch("/api/intake", { method: "POST", body: fd }));
  },

  async intakeFile(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    return handle<IntakeResponse>(await fetch("/api/intake", { method: "POST", body: fd }));
  },

  async generateWbs(payload: {
    requirement_text: string;
    deliverables: string[];
    delivery_date: string | null;
    conditions: string;
    org_units: string[];
    workflow_template_id: string | null;
  }) {
    return handle<WbsDraft>(
      await fetch("/api/wbs/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  },

  async getWbs(id: string) {
    return handle<WbsDraft>(await fetch(`/api/wbs/${id}`));
  },

  async saveWbs(draft: WbsDraft) {
    return handle<WbsDraft>(
      await fetch(`/api/wbs/${draft.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      })
    );
  },

  async jiraProjects() {
    return handle<JiraProject[]>(await fetch("/api/jira/projects"));
  },

  async jiraMeta(projectKey: string) {
    return handle<JiraMeta>(await fetch(`/api/jira/meta?project_key=${encodeURIComponent(projectKey)}`));
  },

  async deploy(payload: { draft_id: string; project_key: string; apply_initial_status: boolean }) {
    return handle<DeployResult>(
      await fetch("/api/jira/deploy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  },
};
