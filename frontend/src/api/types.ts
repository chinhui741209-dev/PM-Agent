export type NodeType = "epic" | "story" | "task" | "subtask";

export interface WbsNode {
  id: string;
  type: NodeType;
  title: string;
  description: string;
  deliverable: string | null;
  owner_unit: string | null;
  assignee_account_id: string | null;
  estimate_days: number | null;
  start_date: string | null;
  due_date: string | null;
  milestone_id: string | null;
  workflow_stage: string | null;
  dependencies: string[];
  children: WbsNode[];
}

export interface Milestone {
  id: string;
  name: string;
  date: string | null;
  deliverables: string[];
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  stages: string[];
  description: string;
}

export interface WbsDraft {
  id: string;
  requirement_text: string;
  deliverables: string[];
  delivery_date: string | null;
  conditions: string;
  org_units: string[];
  workflow: WorkflowTemplate | null;
  milestones: Milestone[];
  nodes: WbsNode[];
  created_at: string | null;
  updated_at: string | null;
}

export interface IntakeResponse {
  requirement_text: string;
  source: string;
  extracted_deliverables: string[];
  note: string;
}

export interface JiraProject {
  id: string;
  key: string;
  name: string;
}

export interface JiraMeta {
  key: string;
  id: string;
  issue_types: { id: string; name: string; subtask: boolean }[];
  statuses: string[];
  users: { accountId: string; displayName: string }[];
}

export interface DeployedIssue {
  node_id: string;
  title: string;
  issue_key: string | null;
  url: string | null;
  status_applied: string | null;
  error: string | null;
}

export interface DeployResult {
  project_key: string;
  created: DeployedIssue[];
  milestones_created: string[];
  suggested_board_columns: string[];
  warnings: string[];
}
