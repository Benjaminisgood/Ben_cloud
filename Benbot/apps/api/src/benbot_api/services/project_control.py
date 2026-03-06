from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from ..core.config import get_settings

_ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
_SERVICE_STATES = {"running", "stopped", "unknown"}
_ALLOWED_ACTIONS = {"start", "stop", "restart", "status"}
_OUTPUT_MAX_CHARS = 2000
_COMMAND_TIMEOUT_SECONDS = 25


@dataclass
class ProjectControlResult:
    project_id: str
    action: str
    ok: bool
    service_state: str
    output: str
    exit_code: int


def _workspace_root() -> Path:
    return get_settings().REPO_ROOT.parent


def _ben_script_path() -> Path:
    return _workspace_root() / "Ben.sh"


def _clean_output(raw_output: str) -> str:
    cleaned = _ANSI_ESCAPE_RE.sub("", raw_output).strip()
    if len(cleaned) <= _OUTPUT_MAX_CHARS:
        return cleaned
    return f"{cleaned[:_OUTPUT_MAX_CHARS]}..."


def _run_ben_script(action: str, target: str) -> subprocess.CompletedProcess[str]:
    normalized_action = action.strip().lower()
    if normalized_action not in _ALLOWED_ACTIONS:
        raise ValueError(f"Unsupported action: {action}")

    script_path = _ben_script_path()
    if not script_path.exists():
        raise RuntimeError(f"Ben.sh not found: {script_path}")

    try:
        return subprocess.run(
            ["bash", str(script_path), normalized_action, target],
            cwd=str(_workspace_root()),
            capture_output=True,
            text=True,
            check=False,
            timeout=_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Ben.sh command timed out after {_COMMAND_TIMEOUT_SECONDS}s") from exc


def _parse_states_from_status(output: str, project_ids: Iterable[str]) -> dict[str, str]:
    states = {project_id: "unknown" for project_id in project_ids}
    for line in output.splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        app_id = parts[0].lower()
        state = parts[1].lower()
        if app_id in states and state in _SERVICE_STATES:
            states[app_id] = state
    return states


def _parse_single_state(output: str, project_id: str) -> str:
    target = project_id.strip().lower()
    for line in output.splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        app_id = parts[0].lower()
        state = parts[1].lower()
        if app_id == target and state in _SERVICE_STATES:
            return state
    return "unknown"


def get_project_runtime_states(project_ids: Iterable[str]) -> dict[str, str]:
    normalized_ids = [project_id.strip().lower() for project_id in project_ids if project_id.strip()]
    if not normalized_ids:
        return {}

    result = _run_ben_script("status", "all")
    output = _clean_output(f"{result.stdout}\n{result.stderr}")
    return _parse_states_from_status(output, normalized_ids)


def _get_project_runtime_state(project_id: str) -> str:
    result = _run_ben_script("status", project_id)
    output = _clean_output(f"{result.stdout}\n{result.stderr}")
    return _parse_single_state(output, project_id)


def run_project_control_action(
    project_id: str,
    action: str,
    db: Optional[Session] = None,
    operator: str = "admin",
) -> ProjectControlResult:
    normalized_project = project_id.strip().lower()
    normalized_action = action.strip().lower()

    result = _run_ben_script(normalized_action, normalized_project)
    output = _clean_output(f"{result.stdout}\n{result.stderr}")
    service_state = _get_project_runtime_state(normalized_project)
    ok = result.returncode == 0

    # 写入操作日志
    if db is not None:
        from .logs import add_log  # 延迟导入避免循环依赖
        action_label = {"start": "启动", "stop": "停止", "restart": "重启", "status": "状态查询"}.get(
            normalized_action, normalized_action
        )
        level = "INFO" if ok else "ERROR"
        msg = (
            f"[{operator}] 执行操作: {action_label} | "
            f"退出码: {result.returncode} | "
            f"服务状态: {service_state}"
        )
        if output:
            msg += f"\n输出:\n{output}"
        add_log(db, normalized_project, msg, level=level, source="project_control")

    return ProjectControlResult(
        project_id=normalized_project,
        action=normalized_action,
        ok=ok,
        service_state=service_state,
        output=output,
        exit_code=result.returncode,
    )
