from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from apps.core.config import settings
from apps.core.http_clients import build_openai_client
from apps.providers.base import ProviderQuery

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]

PlanLog = Callable[[str], None] | None

_EXCLUDE_HINTS = (
    "排除",
    "不含",
    "不包括",
    "不要",
    "剔除",
    "exclude",
    "excluding",
    "without",
    "except",
)
_SHOULD_HINTS = ("或", "或者", "or", "any of", "任选")
_STOP_TERMS = {
    "文献",
    "论文",
    "文章",
    "主题",
    "相关",
    "帮我",
    "检索",
    "搜索",
    "find",
    "search",
    "papers",
    "articles",
}
_FIELD_PREFIXES = (
    "all:",
    "title:",
    "ti:",
    "abs:",
    "abstract:",
    "keyword:",
    "keywords:",
    "kw:",
)
_FIELD_SUFFIXES = (
    "[title/abstract]",
    "[title]",
    "[abstract]",
    "[tiab]",
)
_PROVIDER_QUERY_FIELDS = {
    "crossref": "query.bibliographic",
    "openalex": "filter",
    "elsevier": "query",
    "pubmed": "term",
    "springer": "q",
    "arxiv": "search_query",
}
_TAP_SCOPE_TERMS = ["TAP", "temporal analysis of products"]
_CATALYSIS_SCOPE_TERMS = [
    "catalysis",
    "catalyst",
    "catalytic",
    "microkinetic",
    "kinetics",
    "reaction",
    "reactor",
]
_TAP_HINTS = (
    "tap",
    "temporal analysis of products",
)
_CATALYSIS_HINTS = (
    "catalys",
    "catalyst",
    "microkinetic",
    "kinetic",
    "reactor",
    "reaction",
    "催化",
    "反应",
    "动力学",
)


@dataclass(slots=True)
class QueryPlan:
    raw_input: str
    must_terms: list[str]
    should_terms: list[str]
    exclude_terms: list[str]
    phrases: list[str]
    used_ai: bool = False
    passthrough_query: str | None = None
    domain_objective: str = ""

    def required_terms(self) -> list[str]:
        return _normalize_terms([*self.phrases, *self.must_terms])


@dataclass(slots=True)
class QueryBooleanExpression:
    operator: str
    value: str = ""
    children: list["QueryBooleanExpression"] = field(default_factory=list)

    def matches(self, text_blob: str) -> bool:
        haystack = str(text_blob or "").lower()
        if self.operator == "term":
            return self.value.lower() in haystack
        if self.operator == "and":
            return all(child.matches(haystack) for child in self.children)
        if self.operator == "or":
            return any(child.matches(haystack) for child in self.children)
        if self.operator == "not":
            return not self.children[0].matches(haystack) if self.children else True
        return False

    def describe(self) -> str:
        if self.operator == "term":
            if re.fullmatch(r"[A-Za-z0-9_.:+/-]+", self.value):
                return self.value
            return f'"{self.value}"'
        if self.operator == "not":
            child = self.children[0].describe() if self.children else ""
            return f"NOT {child}".strip()
        joiner = f" {self.operator.upper()} "
        rendered = [child.describe() for child in self.children if child.describe()]
        if not rendered:
            return ""
        if len(rendered) == 1:
            return rendered[0]
        return "(" + joiner.join(rendered) + ")"


@dataclass(slots=True)
class QueryBooleanFilter:
    source: str
    expression: QueryBooleanExpression

    def matches(self, text_blob: str) -> bool:
        return self.expression.matches(text_blob)

    def describe(self) -> str:
        return self.expression.describe()


@dataclass(slots=True)
class QueryScopeGroup:
    label: str
    terms: list[str] = field(default_factory=list)


@dataclass(slots=True)
class QueryDomainScope:
    profile: str = ""
    reason: str = ""
    groups: list[QueryScopeGroup] = field(default_factory=list)

    def all_terms(self) -> list[str]:
        merged: list[str] = []
        for group in self.groups:
            merged.extend(group.terms)
        return _normalize_terms(merged)


def _emit(logger: PlanLog, message: str) -> None:
    if logger is not None:
        logger(message)


def _parse_json_object(raw: str) -> dict[str, object]:
    if not raw:
        return {}
    text = raw.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _normalize_terms(items: Iterable[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip().strip(".,;:，；：。")
        text = re.sub(r"\s+", " ", text)
        if not text:
            continue
        lowered = text.lower()
        if lowered in _STOP_TERMS:
            continue
        if len(text) == 1 and not text.isdigit():
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(text)
    return result


def _merge_scope_groups(groups: Iterable[QueryScopeGroup]) -> list[QueryScopeGroup]:
    merged: list[QueryScopeGroup] = []
    index_by_label: dict[str, int] = {}
    for group in groups:
        label = str(group.label or "").strip()
        terms = _normalize_terms(group.terms)
        if not label or not terms:
            continue
        existing_index = index_by_label.get(label)
        if existing_index is None:
            index_by_label[label] = len(merged)
            merged.append(QueryScopeGroup(label=label, terms=terms))
            continue
        current = merged[existing_index]
        current.terms = _normalize_terms([*current.terms, *terms])
    return merged


def _clean_boolean_term(term: str) -> str:
    text = str(term or "").strip().strip(".,;:，；：。")
    text = re.sub(r"\s+", " ", text)
    lowered = text.lower()
    for prefix in _FIELD_PREFIXES:
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip()
            lowered = text.lower()
            break
    for suffix in _FIELD_SUFFIXES:
        if lowered.endswith(suffix):
            text = text[: -len(suffix)].strip()
            break
    return text


def _make_term_expression(term: str) -> QueryBooleanExpression | None:
    cleaned = _clean_boolean_term(term)
    if not cleaned:
        return None
    return QueryBooleanExpression(operator="term", value=cleaned)


def _combine_expression(
    operator: str,
    children: Iterable[QueryBooleanExpression | None],
) -> QueryBooleanExpression | None:
    flattened: list[QueryBooleanExpression] = []
    for child in children:
        if child is None:
            continue
        if child.operator == operator and operator in {"and", "or"}:
            flattened.extend(child.children)
            continue
        flattened.append(child)
    if not flattened:
        return None
    if len(flattened) == 1:
        return flattened[0]
    return QueryBooleanExpression(operator=operator, children=flattened)


def _build_filter_from_plan_terms(plan: QueryPlan) -> QueryBooleanFilter | None:
    required_terms = plan.required_terms()
    required_set = {term.lower() for term in required_terms}
    optional_terms = [
        term for term in _normalize_terms(plan.should_terms) if term.lower() not in required_set
    ]
    excluded_terms = _normalize_terms(plan.exclude_terms)

    include_parts: list[QueryBooleanExpression | None] = [
        _make_term_expression(term) for term in required_terms
    ]
    if optional_terms:
        include_parts.append(
            _combine_expression(
                "or",
                (_make_term_expression(term) for term in optional_terms),
            )
        )

    exclude_parts = [
        QueryBooleanExpression(
            operator="not",
            children=[term_expr],
        )
        for term in excluded_terms
        if (term_expr := _make_term_expression(term)) is not None
    ]

    expression = _combine_expression("and", [*include_parts, *exclude_parts])
    if expression is None:
        return None
    return QueryBooleanFilter(source="query_plan", expression=expression)


_BOOLEAN_TOKEN_RE = re.compile(
    r'"([^"\\]*(?:\\.[^"\\]*)*)"|\(|\)|\bAND\b|\bOR\b|\bNOT\b|&&|\|\||[^\s()]+',
    flags=re.IGNORECASE,
)
_STRUCTURED_BOOLEAN_RE = re.compile(
    r'(?i)\b(and|or|not)\b|&&|\|\||["()]',
)


class _BooleanTokenStream:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.index = 0

    def peek(self) -> str | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def pop(self) -> str | None:
        token = self.peek()
        if token is not None:
            self.index += 1
        return token


def _tokenize_boolean_query(text: str) -> list[str]:
    normalized = (
        str(text or "")
        .replace("（", "(")
        .replace("）", ")")
        .replace("&&", " AND ")
        .replace("||", " OR ")
    )
    output: list[str] = []
    for match in _BOOLEAN_TOKEN_RE.finditer(normalized):
        token = match.group(0)
        upper = token.upper()
        if upper in {"AND", "OR", "NOT"}:
            output.append(upper)
            continue
        if token.startswith('"') and token.endswith('"'):
            token = token[1:-1].replace('\\"', '"')
        cleaned = _clean_boolean_term(token)
        if cleaned:
            output.append(cleaned)
    return output


def _parse_boolean_primary(stream: _BooleanTokenStream) -> QueryBooleanExpression | None:
    token = stream.pop()
    if token is None:
        return None
    if token == "(":
        nested = _parse_boolean_or(stream)
        if stream.peek() == ")":
            stream.pop()
        return nested
    if token == ")":
        return None
    if stream.peek() == "(" and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]*", token):
        stream.pop()
        nested = _parse_boolean_or(stream)
        if stream.peek() == ")":
            stream.pop()
        return nested
    return _make_term_expression(token)


def _parse_boolean_not(stream: _BooleanTokenStream) -> QueryBooleanExpression | None:
    if stream.peek() == "NOT":
        stream.pop()
        child = _parse_boolean_not(stream)
        if child is None:
            return None
        return QueryBooleanExpression(operator="not", children=[child])
    return _parse_boolean_primary(stream)


def _parse_boolean_and(stream: _BooleanTokenStream) -> QueryBooleanExpression | None:
    children: list[QueryBooleanExpression | None] = [_parse_boolean_not(stream)]
    while True:
        token = stream.peek()
        if token == "AND":
            stream.pop()
            children.append(_parse_boolean_not(stream))
            continue
        if token is None or token in {"OR", ")"}:
            break
        children.append(_parse_boolean_not(stream))
    return _combine_expression("and", children)


def _parse_boolean_or(stream: _BooleanTokenStream) -> QueryBooleanExpression | None:
    children: list[QueryBooleanExpression | None] = [_parse_boolean_and(stream)]
    while stream.peek() == "OR":
        stream.pop()
        children.append(_parse_boolean_and(stream))
    return _combine_expression("or", children)


def _parse_boolean_query(text: str) -> QueryBooleanExpression | None:
    if not _STRUCTURED_BOOLEAN_RE.search(str(text or "")):
        return None
    tokens = _tokenize_boolean_query(text)
    if not tokens:
        return None
    stream = _BooleanTokenStream(tokens)
    expression = _parse_boolean_or(stream)
    if expression is None:
        return None
    if stream.peek() is not None:
        return None
    return expression


def looks_structured_query(text: str) -> bool:
    candidate = str(text or "").strip()
    if not candidate:
        return False
    return _parse_boolean_query(candidate) is not None


def _build_filter_from_plain_query(text: str) -> QueryBooleanFilter | None:
    candidate = _clean_boolean_term(text)
    if not candidate:
        return None
    if re.search(r"[\u4e00-\u9fff]", candidate):
        return None
    lowered = candidate.lower()
    if any(stop in lowered for stop in _STOP_TERMS):
        return None
    if any(hint in lowered for hint in _EXCLUDE_HINTS):
        return None
    if any(hint == lowered for hint in _SHOULD_HINTS):
        return None
    if len(candidate) > 80 or candidate.count(" ") > 8:
        return None
    expression = _make_term_expression(candidate)
    if expression is None:
        return None
    return QueryBooleanFilter(source="plain_query", expression=expression)


def build_query_boolean_filter(plan: QueryPlan) -> QueryBooleanFilter | None:
    filter_from_plan = _build_filter_from_plan_terms(plan)
    if filter_from_plan is not None:
        return filter_from_plan

    candidate = str(plan.passthrough_query or plan.raw_input or "").strip()
    if not candidate:
        return None
    expression = _parse_boolean_query(candidate)
    if expression is not None:
        return QueryBooleanFilter(source="structured_query", expression=expression)
    return _build_filter_from_plain_query(candidate)


def _collect_positive_terms_from_expression(expression: QueryBooleanExpression | None) -> list[str]:
    if expression is None:
        return []
    if expression.operator == "term":
        return _normalize_terms([expression.value])
    if expression.operator == "not":
        return []

    result: list[str] = []
    for child in expression.children:
        result.extend(_collect_positive_terms_from_expression(child))
    return _normalize_terms(result)


def build_query_embedding_text(plan: QueryPlan) -> str:
    raw = re.sub(r"\s+", " ", str(plan.raw_input or "")).strip()
    include_terms = _normalize_terms([*plan.required_terms(), *plan.should_terms])
    if raw and not looks_structured_query(raw):
        pieces = [raw]
        if include_terms:
            pieces.append("key concepts: " + "; ".join(include_terms))
        return " || ".join(piece for piece in pieces if piece)[:600]

    if include_terms:
        return "; ".join(include_terms)[:600]

    candidate = str(plan.passthrough_query or plan.raw_input or "").strip()
    if not candidate:
        return ""

    expression = _parse_boolean_query(candidate)
    positive_terms = _collect_positive_terms_from_expression(expression)
    if positive_terms:
        return "; ".join(positive_terms)[:600]

    return re.sub(r"\s+", " ", candidate).strip()[:600]


def _ai_plan(
    text: str,
    logger: PlanLog,
    *,
    domain_objective: str = "",
) -> QueryPlan | None:
    api_key = (settings.aliyun_ai_api_key or "").strip().strip("'\"")
    base_url = (settings.aliyun_ai_api_base_url or "").strip().strip("'\"")
    normalized_domain_objective = re.sub(r"\s+", " ", str(domain_objective or "")).strip()

    if not api_key:
        _emit(logger, "query_planner: AI key 未配置，回退为原词检索。")
        return None
    if OpenAI is None:
        _emit(logger, "query_planner: openai SDK 不可用，回退为原词检索。")
        return None

    payload = {
        "task": "Convert a literature search request into a provider-agnostic query plan.",
        "input": text,
        "planning_constraints": {
            "domain_objective": normalized_domain_objective,
        },
        "output_schema": {
            "mode": "passthrough or parse",
            "passthrough_query": "Use only when mode=passthrough.",
            "must_terms": ["Required keywords or phrases joined with AND."],
            "should_terms": ["Helpful narrowing keywords or phrases joined with OR."],
            "exclude_terms": ["Keywords or phrases that should be excluded with NOT."],
            "phrases": ["Exact phrases that must be preserved verbatim."],
        },
        "rules": [
            "Return JSON only. Do not add explanations.",
            "If the input is already a structured search expression with boolean operators or field syntax, return mode=passthrough and copy it into passthrough_query.",
            "Arrays may be empty when the input does not support a confident extraction.",
            "Prefer chemistry and catalysis terminology over generic filler words.",
            "The input query or tag is the primary retrieval target and must remain central.",
            "If domain_objective is provided, use it only to narrow the search context and to add a small number of broad, high-signal domain concepts when helpful.",
            "Do not let the domain objective replace, dilute, or overshadow the main query or tag.",
            "For short standalone labels, keep the label itself in must_terms or phrases and use should_terms for contextual narrowing when needed.",
        ],
    }

    model_name = (settings.aliyun_ai_model or "qwen-plus").strip().strip("'\"") or "qwen-plus"

    client = None
    try:
        client = build_openai_client(
            api_key=api_key,
            base_url=base_url,
            timeout=max(1.0, float(settings.request_timeout_seconds)),
        )
        if client is None:
            _emit(logger, "query_planner: openai HTTP client 初始化失败，回退为原词检索。")
            return None
        resp = client.chat.completions.create(
            model=model_name,
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a literature-search query planner."},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # pragma: no cover - 网络容错
        _emit(logger, f"query_planner: AI 解析失败，回退为原词检索。原因: {exc}")
        return None
    finally:
        if client is not None:
            client.close()

    content = ""
    if resp.choices:
        content = str((resp.choices[0].message.content or "")).strip()

    parsed = _parse_json_object(content)
    if not parsed:
        _emit(logger, "query_planner: AI 返回不可解析，回退为原词检索。")
        return None

    mode = str(parsed.get("mode") or "").strip().lower()
    if mode == "passthrough":
        passthrough = str(parsed.get("passthrough_query") or "").strip() or str(text or "").strip()
        return QueryPlan(
            raw_input=str(text or "").strip(),
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=True,
            passthrough_query=passthrough,
            domain_objective=normalized_domain_objective,
        )

    must_terms = _normalize_terms(parsed.get("must_terms") or [])
    should_terms = _normalize_terms(parsed.get("should_terms") or [])
    exclude_terms = _normalize_terms(parsed.get("exclude_terms") or [])
    phrases = _normalize_terms(parsed.get("phrases") or [])

    if not must_terms and not should_terms and not phrases:
        return None

    return QueryPlan(
        raw_input=str(text or "").strip(),
        must_terms=must_terms,
        should_terms=should_terms,
        exclude_terms=exclude_terms,
        phrases=phrases,
        used_ai=True,
        passthrough_query=None,
        domain_objective=normalized_domain_objective,
    )


def plan_natural_language_query(
    text: str,
    *,
    logger: PlanLog = None,
    domain_objective: str = "",
) -> QueryPlan:
    raw = str(text or "").strip()
    normalized_domain_objective = re.sub(r"\s+", " ", str(domain_objective or "")).strip()
    if not raw:
        return QueryPlan(
            raw_input="",
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query="",
            domain_objective=normalized_domain_objective,
        )

    if normalized_domain_objective:
        _emit(logger, f"query_planner: 已注入 domain_objective={normalized_domain_objective}")

    ai_plan = _ai_plan(
        raw,
        logger,
        domain_objective=normalized_domain_objective,
    )
    if ai_plan is not None:
        if ai_plan.passthrough_query:
            _emit(logger, "query_planner: AI 判断为结构化检索，直接透传。")
        else:
            _emit(logger, "query_planner: 已使用 AI 完成 NL->DSL 解析。")
        return ai_plan

    _emit(logger, "query_planner: 回退为原词检索。")
    return QueryPlan(
        raw_input=raw,
        must_terms=[],
        should_terms=[],
        exclude_terms=[],
        phrases=[],
        used_ai=False,
        passthrough_query=raw,
        domain_objective=normalized_domain_objective,
    )


def _quote_term(term: str) -> str:
    safe = re.sub(r"\s+", " ", str(term or "").strip()).replace('"', "")
    if not safe:
        return ""
    if re.fullmatch(r"[A-Za-z0-9_.:+-]+", safe):
        return safe
    return f'"{safe}"'


def _lowered_blob(items: Iterable[object]) -> str:
    normalized = [re.sub(r"\s+", " ", str(item or "")).strip().lower() for item in items]
    return " ".join(item for item in normalized if item)


def _contains_any_hint(blob: str, hints: Iterable[str]) -> bool:
    haystack = str(blob or "").lower()
    return any(str(hint or "").strip().lower() in haystack for hint in hints if str(hint or "").strip())


def _is_freeform_passthrough_query(text: str) -> bool:
    candidate = re.sub(r"\s+", " ", str(text or "")).strip()
    if not candidate or looks_structured_query(candidate):
        return False
    if re.search(r"[\u4e00-\u9fff]", candidate):
        return True
    return len(candidate) > 120 or candidate.count(" ") > 10


def _build_domain_scope(plan: QueryPlan, context_texts: Iterable[str] | None = None) -> QueryDomainScope:
    normalized_contexts = _normalize_terms(context_texts or [])
    if not normalized_contexts:
        return QueryDomainScope()

    query_blob = _lowered_blob(
        [
            plan.raw_input,
            plan.passthrough_query,
            *plan.required_terms(),
            *plan.should_terms,
            *plan.exclude_terms,
            *plan.phrases,
        ]
    )
    context_blob = _lowered_blob(normalized_contexts)
    groups: list[QueryScopeGroup] = []
    reasons: list[str] = []
    profile_parts: list[str] = []

    if _contains_any_hint(context_blob, _TAP_HINTS) and not _contains_any_hint(query_blob, _TAP_HINTS):
        groups.append(QueryScopeGroup(label="tap_method", terms=list(_TAP_SCOPE_TERMS)))
        reasons.append("context_tap")

    if _contains_any_hint(context_blob, _CATALYSIS_HINTS) and not _contains_any_hint(query_blob, _CATALYSIS_HINTS):
        groups.append(QueryScopeGroup(label="catalysis_domain", terms=list(_CATALYSIS_SCOPE_TERMS)))
        reasons.append("context_catalysis")

    if not groups:
        return QueryDomainScope()

    if normalized_contexts and any(reason.startswith("context_") for reason in reasons):
        profile_parts.append("context_scope")

    return QueryDomainScope(
        profile="+".join(profile_parts) or "context_scope",
        reason=",".join(reasons),
        groups=_merge_scope_groups(groups),
    )


def _render_boolean_expression(
    expression: QueryBooleanExpression | None,
    render_term: Callable[[str], str],
) -> str:
    if expression is None:
        return ""
    if expression.operator == "term":
        return render_term(expression.value)
    if expression.operator == "not":
        child = _render_boolean_expression(expression.children[0] if expression.children else None, render_term)
        return f"NOT {child}".strip() if child else ""

    rendered_children = [
        _render_boolean_expression(child, render_term) for child in expression.children if child is not None
    ]
    rendered_children = [item for item in rendered_children if item]
    if not rendered_children:
        return ""
    if len(rendered_children) == 1:
        return rendered_children[0]
    joiner = f" {expression.operator.upper()} "
    return "(" + joiner.join(rendered_children) + ")"


def _append_scope_to_boolean_query(
    query: str,
    *,
    scope: QueryDomainScope,
    render_term: Callable[[str], str],
) -> str:
    output = str(query or "").strip()
    for group in scope.groups:
        parts = [render_term(term) for term in _normalize_terms(group.terms)]
        parts = [part for part in parts if part]
        if not parts:
            continue
        clause = " OR ".join(parts)
        if len(parts) > 1:
            clause = f"({clause})"
        output = f"{output} AND {clause}" if output else clause
    return output.strip()


def _compile_boolean_query(
    *,
    required: list[str],
    optional: list[str],
    excluded: list[str],
    render_term: Callable[[str], str],
    fallback_raw: str,
) -> str:
    normalized_required = _normalize_terms(required)
    required_set = {term.lower() for term in normalized_required}
    normalized_optional = [term for term in _normalize_terms(optional) if term.lower() not in required_set]
    normalized_excluded = _normalize_terms(excluded)

    groups: list[str] = []

    if normalized_required:
        required_parts = []
        for term in normalized_required:
            expr = render_term(term)
            if expr:
                required_parts.append(expr)
        required_expr = " AND ".join(required_parts)
        if required_expr:
            groups.append(required_expr)

    if normalized_optional:
        optional_parts = []
        for term in normalized_optional:
            expr = render_term(term)
            if expr:
                optional_parts.append(expr)
        optional_expr = " OR ".join(optional_parts)
        if optional_expr:
            groups.append(f"({optional_expr})")

    query = " AND ".join(f"({group})" if " AND " in group and len(groups) > 1 else group for group in groups if group)
    if not query:
        fallback = render_term(fallback_raw) if fallback_raw else ""
        query = fallback or _quote_term(fallback_raw)

    for term in normalized_excluded:
        expr = render_term(term)
        if not expr:
            continue
        query = f"{query} AND NOT {expr}" if query else f"NOT {expr}"
    return query.strip()


def _compile_boolean_provider_query(
    plan: QueryPlan,
    *,
    render_term: Callable[[str], str],
    fallback_raw: str,
    scope: QueryDomainScope,
) -> str:
    passthrough = str(plan.passthrough_query or "").strip()
    if passthrough:
        expression = _parse_boolean_query(passthrough)
        if expression is not None:
            base_query = _render_boolean_expression(expression, render_term)
        elif _is_freeform_passthrough_query(passthrough):
            base_query = passthrough
        else:
            base_query = _compile_boolean_query(
                required=plan.required_terms(),
                optional=plan.should_terms,
                excluded=plan.exclude_terms,
                render_term=render_term,
                fallback_raw=passthrough,
            )
    else:
        base_query = _compile_boolean_query(
            required=plan.required_terms(),
            optional=plan.should_terms,
            excluded=plan.exclude_terms,
            render_term=render_term,
            fallback_raw=fallback_raw,
        )

    if not base_query:
        return ""
    if _is_freeform_passthrough_query(base_query):
        return base_query
    return _append_scope_to_boolean_query(base_query, scope=scope, render_term=render_term)


def _collect_text_search_terms(plan: QueryPlan) -> list[str]:
    include_terms = _normalize_terms([*plan.required_terms(), *plan.should_terms])
    if include_terms:
        return include_terms

    candidate = str(plan.passthrough_query or plan.raw_input or "").strip()
    if not candidate:
        return []
    if _is_freeform_passthrough_query(candidate):
        return [re.sub(r"\s+", " ", candidate).strip()]

    expression = _parse_boolean_query(candidate)
    if expression is not None:
        positive_terms = _collect_positive_terms_from_expression(expression)
        if positive_terms:
            return positive_terms
    return _normalize_terms([candidate])


def _compile_text_provider(plan: QueryPlan, *, scope: QueryDomainScope) -> str:
    pieces = _collect_text_search_terms(plan)
    combined = _normalize_terms([*pieces, *scope.all_terms()])
    quoted = [_quote_term(term) for term in combined]
    quoted = [term for term in quoted if term]
    if quoted:
        return " ".join(quoted)[:600]
    candidate = re.sub(r"\s+", " ", str(plan.passthrough_query or plan.raw_input or "")).strip()
    return candidate[:600]


def _compile_openalex(plan: QueryPlan, *, scope: QueryDomainScope) -> str:
    compiled_text = _compile_text_provider(plan, scope=scope)
    if not compiled_text:
        return ""
    return f"title_and_abstract.search:{compiled_text}"[:640]


def _compile_generic(plan: QueryPlan, *, scope: QueryDomainScope) -> str:
    return _compile_boolean_provider_query(
        plan,
        render_term=_quote_term,
        fallback_raw=plan.raw_input,
        scope=scope,
    )


def _compile_pubmed(plan: QueryPlan, *, scope: QueryDomainScope) -> str:
    def _render(term: str) -> str:
        quoted = _quote_term(term)
        if not quoted:
            return ""
        return f"{quoted}[Title/Abstract]"

    return _compile_boolean_provider_query(
        plan,
        render_term=_render,
        fallback_raw=plan.raw_input,
        scope=scope,
    )


def _compile_scopus(plan: QueryPlan, *, scope: QueryDomainScope) -> str:
    def _render(term: str) -> str:
        quoted = _quote_term(term)
        if not quoted:
            return ""
        return f"TITLE-ABS-KEY({quoted})"

    return _compile_boolean_provider_query(
        plan,
        render_term=_render,
        fallback_raw=plan.raw_input,
        scope=scope,
    )


def _compile_arxiv(plan: QueryPlan, *, scope: QueryDomainScope) -> str:
    def _render(term: str) -> str:
        quoted = _quote_term(term)
        if not quoted:
            return ""
        return f"(ti:{quoted} OR abs:{quoted})"

    compiled = _compile_boolean_provider_query(
        plan,
        render_term=_render,
        fallback_raw=plan.raw_input,
        scope=scope,
    )
    return re.sub(r"\bAND\s+NOT\b", "ANDNOT", compiled)


def compile_query_for_provider(
    provider_key: str,
    plan: QueryPlan,
    *,
    context_texts: Iterable[str] | None = None,
) -> ProviderQuery:
    key = str(provider_key or "").strip().lower()
    scope = _build_domain_scope(plan, context_texts)
    query_field = _PROVIDER_QUERY_FIELDS.get(key, "query")
    if key == "pubmed":
        compiled_query = _compile_pubmed(plan, scope=scope)
    elif key == "elsevier":
        compiled_query = _compile_scopus(plan, scope=scope)
    elif key == "arxiv":
        compiled_query = _compile_arxiv(plan, scope=scope)
    elif key == "openalex":
        compiled_query = _compile_openalex(plan, scope=scope)
    elif key in {"crossref", "springer"}:
        compiled_query = _compile_text_provider(plan, scope=scope)
    else:
        compiled_query = _compile_generic(plan, scope=scope)

    return ProviderQuery(
        provider=key,
        raw_query=str(plan.raw_input or "").strip(),
        compiled_query=compiled_query,
        query_field=query_field,
        query_contexts=_normalize_terms(context_texts or []),
        domain_scope_name=scope.profile,
        domain_scope_reason=scope.reason,
        domain_scope_terms=scope.all_terms(),
    )


def build_provider_queries(
    plan: QueryPlan,
    provider_keys: Iterable[str],
    *,
    context_texts: Iterable[str] | None = None,
) -> dict[str, ProviderQuery]:
    result: dict[str, ProviderQuery] = {}
    for provider_key in provider_keys:
        key = str(provider_key or "").strip().lower()
        if not key:
            continue
        query = compile_query_for_provider(key, plan, context_texts=context_texts)
        if query.compiled_query:
            result[key] = query
    return result
