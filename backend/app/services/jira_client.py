"""Jira Cloud REST API v3 封裝（httpx + Basic Auth）。"""
from __future__ import annotations

import base64

import httpx

from ..config import get_settings


class JiraError(RuntimeError):
    pass


def _client() -> httpx.Client:
    s = get_settings()
    if not s.jira_configured:
        raise JiraError("尚未設定 Jira 憑證，請在 backend/.env 填入 JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN。")
    token = base64.b64encode(f"{s.jira_email}:{s.jira_api_token}".encode()).decode()
    return httpx.Client(
        base_url=s.jira_base_url.rstrip("/"),
        headers={
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )


def _raise_for(resp: httpx.Response, action: str):
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:  # noqa: BLE001
            detail = resp.text
        raise JiraError(f"{action} 失敗（HTTP {resp.status_code}）：{detail}")


# ---- meta ----

def list_projects() -> list[dict]:
    with _client() as c:
        resp = c.get("/rest/api/3/project/search", params={"maxResults": 100})
        _raise_for(resp, "查詢專案")
        return [
            {"id": p["id"], "key": p["key"], "name": p["name"]}
            for p in resp.json().get("values", [])
        ]


def get_project_meta(project_key: str) -> dict:
    """回傳該專案的 issue types、狀態清單、可指派使用者。"""
    with _client() as c:
        # issue types
        resp = c.get(f"/rest/api/3/project/{project_key}")
        _raise_for(resp, "查詢專案資訊")
        project = resp.json()
        issue_types = [
            {"id": it["id"], "name": it["name"], "subtask": it.get("subtask", False)}
            for it in project.get("issueTypes", [])
        ]

        # statuses（依 issue type 分組，這裡攤平成不重複清單）
        resp = c.get(f"/rest/api/3/project/{project_key}/statuses")
        _raise_for(resp, "查詢狀態")
        status_names: list[str] = []
        for entry in resp.json():
            for st in entry.get("statuses", []):
                if st["name"] not in status_names:
                    status_names.append(st["name"])

        # assignable users
        users: list[dict] = []
        try:
            resp = c.get(
                "/rest/api/3/user/assignable/search",
                params={"project": project_key, "maxResults": 50},
            )
            if resp.status_code < 400:
                users = [
                    {"accountId": u["accountId"], "displayName": u.get("displayName", "")}
                    for u in resp.json()
                ]
        except httpx.HTTPError:
            users = []

        return {
            "key": project_key,
            "id": project.get("id"),
            "issue_types": issue_types,
            "statuses": status_names,
            "users": users,
        }


# ---- deploy helpers ----

def ensure_version(project_id: str, name: str, release_date: str | None) -> str | None:
    """建立（或取得既有）版本，回傳 version id。用來對應里程碑。"""
    with _client() as c:
        resp = c.get(f"/rest/api/3/project/{project_id}/versions")
        if resp.status_code < 400:
            for v in resp.json():
                if v.get("name") == name:
                    return v.get("id")
        payload = {"name": name, "projectId": int(project_id)}
        if release_date:
            payload["releaseDate"] = release_date
        resp = c.post("/rest/api/3/version", json=payload)
        if resp.status_code >= 400:
            return None
        return resp.json().get("id")


def _adf(text: str) -> dict:
    """把純文字包成 Atlassian Document Format。"""
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": ([{"type": "text", "text": text}] if text else [])}
        ],
    }


def create_issue(fields: dict) -> dict:
    with _client() as c:
        resp = c.post("/rest/api/3/issue", json={"fields": fields})
        _raise_for(resp, "建立 issue")
        return resp.json()


def get_transitions(issue_key: str) -> list[dict]:
    with _client() as c:
        resp = c.get(f"/rest/api/3/issue/{issue_key}/transitions")
        if resp.status_code >= 400:
            return []
        return resp.json().get("transitions", [])


def transition_issue(issue_key: str, status_name: str) -> bool:
    """把 issue 推進到指定狀態（若該 transition 存在）。"""
    for t in get_transitions(issue_key):
        if t.get("to", {}).get("name", "").lower() == status_name.lower():
            with _client() as c:
                resp = c.post(
                    f"/rest/api/3/issue/{issue_key}/transitions",
                    json={"transition": {"id": t["id"]}},
                )
                return resp.status_code < 400
    return False


def build_fields(
    project_key: str,
    issue_type_name: str,
    summary: str,
    description: str = "",
    labels: list[str] | None = None,
    assignee_account_id: str | None = None,
    parent_key: str | None = None,
    version_id: str | None = None,
) -> dict:
    fields: dict = {
        "project": {"key": project_key},
        "issuetype": {"name": issue_type_name},
        "summary": summary[:255],
    }
    if description:
        fields["description"] = _adf(description)
    if labels:
        # Jira label 不可含空白，轉成底線
        fields["labels"] = [l.replace(" ", "_") for l in labels]
    if assignee_account_id:
        fields["assignee"] = {"accountId": assignee_account_id}
    if parent_key:
        fields["parent"] = {"key": parent_key}
    if version_id:
        fields["fixVersions"] = [{"id": version_id}]
    return fields
