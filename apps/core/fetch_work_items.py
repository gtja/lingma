import argparse
import csv
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

try:
    from django.conf import settings
except Exception:  # pragma: no cover
    settings = None


TIMEOUT = (5, 20)
RETRIES = 3
BACKOFF_SECONDS = 1.0
PROGRESS_EVERY = 25
PAGE_LIMIT = 20
MAX_PAGES_PER_PROJECT = 50
MAX_SECONDS_PER_PROJECT = 120
DEFAULT_MAX_ITEMS = 0
DEFAULT_ALLOWED_STATES = {
    "积压",
    "未开始",
    "进行中",
    "开发阶段",
    "测试阶段",
}


def _get_plane_config(
    base_url: Optional[str] = None,
    workspace_slug: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Tuple[str, str, str, Set[str]]:
    conf = getattr(settings, "PLANE_CONFIG", {}) if settings else {}
    cfg_base_url = (base_url or conf.get("base_url") or os.getenv("PLANE_BASE_URL", "")).strip()
    cfg_workspace = (workspace_slug or conf.get("workspace_slug") or os.getenv("PLANE_WORKSPACE_SLUG", "")).strip()
    cfg_api_key = (api_key or conf.get("api_key") or os.getenv("PLANE_API_KEY", "")).strip()
    allowed_states = conf.get("allowed_states") or DEFAULT_ALLOWED_STATES
    if not cfg_base_url or not cfg_workspace or not cfg_api_key:
        raise RuntimeError(
            "Plane配置缺失，请在config/settings.py配置PLANE_CONFIG，"
            "或设置环境变量 PLANE_BASE_URL/PLANE_WORKSPACE_SLUG/PLANE_API_KEY。"
        )
    return cfg_base_url.rstrip("/"), cfg_workspace, cfg_api_key, set(allowed_states)


def _parse_json_response(resp: requests.Response) -> Any:
    # Some upstream responses declare a wrong charset; parse from bytes first.
    for enc in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return json.loads(resp.content.decode(enc))
        except Exception:
            continue
    return resp.json()


def _get_json(
    url: str,
    headers: Dict[str, str],
    params: Optional[Dict[str, Any]] = None,
    retries: int = RETRIES,
    backoff_seconds: float = BACKOFF_SECONDS,
    session: Optional[requests.Session] = None,
) -> Any:
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            sess = session or requests
            resp = sess.get(url, headers=headers, params=params, timeout=TIMEOUT)
            if resp.ok:
                return _parse_json_response(resp)
            if resp.status_code in (429, 502, 503, 504) or resp.status_code >= 500:
                last_err = RuntimeError(
                    f"GET {url} failed: {resp.status_code} {resp.text}"
                )
                if attempt < retries:
                    time.sleep(backoff_seconds * (2 ** attempt))
                    continue
            raise RuntimeError(f"GET {url} failed: {resp.status_code} {resp.text}")
        except requests.RequestException as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(backoff_seconds * (2 ** attempt))
                continue
            raise RuntimeError(f"GET {url} failed: {exc}") from exc
    if last_err:
        raise RuntimeError(f"GET {url} failed after retries: {last_err}")
    raise RuntimeError("GET failed after retries")


def _normalize_list(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "results" in payload and isinstance(payload["results"], list):
            return payload["results"]
    return []


def list_projects(base_url: str, workspace_slug: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    url = f"{base_url}/api/v1/workspaces/{workspace_slug}/projects/"
    with requests.Session() as session:
        payload = _get_json(url, headers=headers, session=session)
    return _normalize_list(payload)


def list_work_items(
    base_url: str,
    workspace_slug: str,
    headers: Dict[str, str],
    project_id: str,
) -> List[Dict[str, Any]]:
    url = f"{base_url}/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/"
    items: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    offset = 0
    limit = PAGE_LIMIT
    page = 0
    start_time = time.time()

    with requests.Session() as session:
        while True:
            if page >= MAX_PAGES_PER_PROJECT:
                print(
                    f"Warning: project {project_id} reached max pages "
                    f"({MAX_PAGES_PER_PROJECT}), skipping remaining.",
                    file=sys.stderr,
                )
                break
            if time.time() - start_time > MAX_SECONDS_PER_PROJECT:
                print(
                    f"Warning: project {project_id} exceeded max seconds "
                    f"({MAX_SECONDS_PER_PROJECT}s), skipping remaining.",
                    file=sys.stderr,
                )
                break

            page += 1
            print(
                f"Listing page {page} for project {project_id} "
                f"(offset={offset}, limit={limit})...",
                file=sys.stderr,
            )

            try:
                payload = _get_json(
                    url,
                    headers=headers,
                    params={"limit": limit, "offset": offset},
                    session=session,
                )
            except RuntimeError as exc:
                print(
                    f"Warning: failed to list work items for project {project_id}: {exc}",
                    file=sys.stderr,
                )
                break

            batch = _normalize_list(payload)
            print(
                f"Listed page {page} for project {project_id} "
                f"(received {len(batch)} items).",
                file=sys.stderr,
            )
            if not batch:
                break

            new_batch: List[Dict[str, Any]] = []
            for wi in batch:
                wi_id = wi.get("id")
                if isinstance(wi_id, str):
                    if wi_id in seen_ids:
                        continue
                    seen_ids.add(wi_id)
                new_batch.append(wi)

            if not new_batch:
                break

            items.extend(new_batch)
            if len(new_batch) < limit:
                break
            offset += limit

    return items


def list_project_states(
    base_url: str,
    workspace_slug: str,
    headers: Dict[str, str],
    project_id: str,
) -> Dict[str, str]:
    url = f"{base_url}/api/v1/workspaces/{workspace_slug}/projects/{project_id}/states/"
    try:
        with requests.Session() as session:
            payload = _get_json(url, headers=headers, session=session)
    except RuntimeError as exc:
        print(
            f"Warning: failed to list states for project {project_id}: {exc}",
            file=sys.stderr,
        )
        return {}

    states = _normalize_list(payload)
    state_map: Dict[str, str] = {}
    for state in states:
        sid = state.get("id")
        sname = state.get("name")
        if isinstance(sid, str) and isinstance(sname, str):
            state_map[sid.strip()] = sname.strip()
    return state_map


def get_work_item_detail(
    base_url: str,
    workspace_slug: str,
    headers: Dict[str, str],
    project_id: str,
    work_item_id: str,
) -> Dict[str, Any]:
    url = (
        f"{base_url}/api/v1/workspaces/{workspace_slug}/projects/"
        f"{project_id}/work-items/{work_item_id}/"
    )
    try:
        with requests.Session() as session:
            payload = _get_json(url, headers=headers, session=session)
    except RuntimeError as exc:
        print(
            f"Warning: failed to fetch work item {work_item_id} in project {project_id}: {exc}",
            file=sys.stderr,
        )
        return {}

    if isinstance(payload, dict):
        return payload
    return {}


def _extract_state_name(work_item: Dict[str, Any]) -> str:
    state = work_item.get("state")
    if isinstance(state, dict):
        name = state.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    if isinstance(state, str) and state.strip():
        return state.strip()

    for key in ("state_detail", "status_detail"):
        obj = work_item.get(key)
        if isinstance(obj, dict):
            name = obj.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()

    for key in ("state_name", "status_name", "status"):
        value = work_item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def _extract_state_id(work_item: Dict[str, Any]) -> str:
    state = work_item.get("state")
    if isinstance(state, str) and state.strip():
        return state.strip()
    if isinstance(state, dict):
        state_id = state.get("id")
        if isinstance(state_id, str) and state_id.strip():
            return state_id.strip()

    for key in ("state_id", "status_id"):
        value = work_item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _write_csv(rows: List[Dict[str, Any]], output_path: Optional[str]) -> None:
    fieldnames = [
        "project_id",
        "project_name",
        "work_item_id",
        "work_item_name",
        "work_item_content",
    ]

    if output_path:
        # utf-8-sig improves compatibility with Excel/IDE on Windows.
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", newline="")
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)


def fetch_work_items_data(
    max_items: int = DEFAULT_MAX_ITEMS,
    base_url: Optional[str] = None,
    workspace_slug: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    cfg_base_url, cfg_workspace, cfg_api_key, allowed_states = _get_plane_config(
        base_url=base_url,
        workspace_slug=workspace_slug,
        api_key=api_key,
    )
    headers = {"X-API-Key": cfg_api_key}
    projects = list_projects(cfg_base_url, cfg_workspace, headers)
    output: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    max_items = max(0, max_items)
    reached_limit = False

    for idx, project in enumerate(projects, start=1):
        if reached_limit:
            break
        project_id = project.get("id")
        project_name = project.get("name")
        if not project_id:
            continue

        print(
            f"[{idx}/{len(projects)}] Fetching work items for project "
            f"{project_name} ({project_id})",
            file=sys.stderr,
        )

        state_id_to_name = list_project_states(cfg_base_url, cfg_workspace, headers, project_id)
        allowed_state_ids = {
            sid for sid, sname in state_id_to_name.items() if sname in allowed_states
        }

        work_items = list_work_items(cfg_base_url, cfg_workspace, headers, project_id)
        print(
            f"[{idx}/{len(projects)}] Found {len(work_items)} work items for "
            f"{project_name} ({project_id})",
            file=sys.stderr,
        )

        for wi_idx, wi in enumerate(work_items, start=1):
            if reached_limit:
                break
            wi_id = wi.get("id")
            if not wi_id:
                failures.append(
                    {
                        "project_id": project_id,
                        "project_name": project_name,
                        "work_item_id": None,
                        "reason": "missing_work_item_id",
                    }
                )
                continue

            state_id = _extract_state_id(wi)
            if allowed_state_ids and state_id and state_id not in allowed_state_ids:
                continue

            detail = get_work_item_detail(
                cfg_base_url,
                cfg_workspace,
                headers,
                project_id,
                wi_id,
            )
            if not detail:
                failures.append(
                    {
                        "project_id": project_id,
                        "project_name": project_name,
                        "work_item_id": wi_id,
                        "reason": "detail_fetch_failed",
                    }
                )
                continue

            if not state_id:
                state_id = _extract_state_id(detail)
            state_name = state_id_to_name.get(state_id, "") if state_id else ""
            if not state_name:
                state_name = _extract_state_name(wi) or _extract_state_name(detail)
            if not state_name or state_name not in allowed_states:
                continue

            name = detail.get("name") or detail.get("title")
            content = (
                detail.get("description")
                or detail.get("description_html")
                or detail.get("content")
            )
            output.append(
                {
                    "project_id": project_id,
                    "project_name": project_name,
                    "work_item_id": wi_id,
                    "work_item_name": name,
                    "work_item_content": content,
                }
            )
            if max_items and len(output) >= max_items:
                reached_limit = True
                print(
                    f"Reached max items limit: {max_items}. Stopping crawl.",
                    file=sys.stderr,
                )
                break

            if wi_idx % PROGRESS_EVERY == 0:
                print(
                    f"[{idx}/{len(projects)}] Processed {wi_idx}/"
                    f"{len(work_items)} work items for {project_name} "
                    f"({project_id})",
                    file=sys.stderr,
                )

    return {
        "items": output,
        "failures": failures,
        "project_count": len(projects),
        "item_count": len(output),
    }


def sync_work_items_to_db(
    max_items: int = DEFAULT_MAX_ITEMS,
    base_url: Optional[str] = None,
    workspace_slug: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    手动刷新 Plane 工作项并落库。
    仅在 Django 项目上下文中调用。
    """
    result = fetch_work_items_data(
        max_items=max_items,
        base_url=base_url,
        workspace_slug=workspace_slug,
        api_key=api_key,
    )
    items = result.get("items", [])

    from django.db import transaction
    from .models import PlaneWorkItem

    created_count = 0
    updated_count = 0

    with transaction.atomic():
        for item in items:
            defaults = {
                "project_id": str(item.get("project_id") or ""),
                "project_name": str(item.get("project_name") or ""),
                "work_item_name": str(item.get("work_item_name") or ""),
                "work_item_content": str(item.get("work_item_content") or ""),
                "raw_payload": json.dumps(item, ensure_ascii=False),
            }
            obj, created = PlaneWorkItem.objects.update_or_create(
                work_item_id=str(item.get("work_item_id") or ""),
                defaults=defaults,
            )
            _ = obj
            if created:
                created_count += 1
            else:
                updated_count += 1

    result["created_count"] = created_count
    result["updated_count"] = updated_count
    result["synced_count"] = len(items)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Output CSV file path (recommended on Windows).")
    parser.add_argument(
        "--max-items",
        type=int,
        default=DEFAULT_MAX_ITEMS,
        help=f"Maximum rows to export (default: {DEFAULT_MAX_ITEMS}).",
    )
    parser.add_argument("--base-url", help="Plane base URL, e.g. http://plane.example.com:3238")
    parser.add_argument("--workspace-slug", help="Plane workspace slug")
    parser.add_argument("--api-key", help="Plane API key")
    args = parser.parse_args()

    result = fetch_work_items_data(
        max_items=args.max_items,
        base_url=args.base_url,
        workspace_slug=args.workspace_slug,
        api_key=args.api_key,
    )
    _write_csv(result["items"], args.output)
    failures = result["failures"]
    if failures:
        print(f"Failures: {len(failures)} work items failed. Sample: {failures[:5]}", file=sys.stderr)


if __name__ == "__main__":
    main()
