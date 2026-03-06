from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from ..core.config import get_settings

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


@dataclass(frozen=True)
class TemplateDefinition:
    id: str
    name: str
    description: str
    category: str
    variables: list[str]
    content: str


_TEMPLATES: dict[str, TemplateDefinition] = {
    "weekly_report": TemplateDefinition(
        id="weekly_report",
        name="周报模板",
        description="标准实验室周报（进展、风险、下周计划）",
        category="weekly",
        variables=["date", "week_number", "week_start", "week_end", "member", "project"],
        content="""# {{project}} 周报（第 {{week_number}} 周）\n\n- 日期：{{date}}\n- 周期：{{week_start}} ~ {{week_end}}\n- 成员：{{member}}\n\n## 本周进展\n\n1. \n2. \n3. \n\n## 本周问题与风险\n\n- \n\n## 下周计划\n\n1. \n2. \n3. \n\n## 需要协助\n\n- \n""",
    ),
    "meeting_notes": TemplateDefinition(
        id="meeting_notes",
        name="会议纪要模板",
        description="组会/项目会纪要，含行动项追踪",
        category="meeting",
        variables=["date", "member", "project"],
        content="""# {{project}} 会议纪要\n\n- 日期：{{date}}\n- 记录人：{{member}}\n\n## 参会人员\n\n- \n\n## 讨论要点\n\n1. \n2. \n3. \n\n## 决策\n\n- \n\n## Action Items\n\n| 事项 | 负责人 | 截止日期 | 状态 |\n| --- | --- | --- | --- |\n|  |  |  | 待办 |\n""",
    ),
    "experiment_log": TemplateDefinition(
        id="experiment_log",
        name="实验记录模板",
        description="实验目标、步骤、结果与复盘",
        category="research",
        variables=["date", "member", "project"],
        content="""# {{project}} 实验记录\n\n- 日期：{{date}}\n- 记录人：{{member}}\n\n## 实验目标\n\n- \n\n## 实验环境\n\n- \n\n## 实验步骤\n\n1. \n2. \n3. \n\n## 结果与数据\n\n- \n\n## 结论\n\n- \n\n## 后续优化\n\n- \n""",
    ),
}


def list_templates() -> list[TemplateDefinition]:
    return sorted(_TEMPLATES.values(), key=lambda t: t.id)


def get_template(template_id: str) -> TemplateDefinition:
    template = _TEMPLATES.get(template_id)
    if not template:
        raise ValueError("template_not_found")
    return template


def _week_range(today: date) -> tuple[date, date]:
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


def build_template_variables(*, username: str, project: str | None, member: str | None, file_path: str | None = None) -> dict[str, str]:
    settings = get_settings()
    today = date.today()
    week_start, week_end = _week_range(today)

    resolved_member = (member or "").strip() or username
    resolved_project = (project or "").strip() or settings.default_project

    title = ""
    if file_path:
        title = file_path.rsplit("/", 1)[-1].removesuffix(".md")

    return {
        "date": today.isoformat(),
        "week_number": str(today.isocalendar().week),
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "year": str(today.year),
        "month": f"{today.month:02d}",
        "day": f"{today.day:02d}",
        "member": resolved_member,
        "project": resolved_project,
        "title": title,
    }


def render_template_content(template_id: str, *, variables: dict[str, str]) -> str:
    template = get_template(template_id)

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return variables.get(key, "")

    return _PLACEHOLDER_RE.sub(_replace, template.content)
