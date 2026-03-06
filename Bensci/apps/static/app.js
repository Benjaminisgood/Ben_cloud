const apiPrefix = "/api";
const INGEST_POLL_INTERVAL_MS = 3000;
const AUTO_ENRICHMENT_POLL_INTERVAL_MS = 10000;
const AUTO_ENRICHMENT_LIST_REFRESH_INTERVAL_MS = 15000;

const state = {
  providers: [],
  articles: [],
  tags: [],
  selectedTagFiltersAnd: new Set(),
  selectedTagFiltersOr: new Set(),
  sortBy: "ingested_at",
  sortOrder: "desc",
  checkFilter: "all",
  total: 0,
  ingestJobId: null,
  ingestJobStatus: "idle",
  ingestLogCursor: 0,
  quickEnrichmentRunning: false,
  autoEnrichmentJobId: null,
  autoEnrichmentLogCursor: 0,
  autoEnrichmentEnabled: null,
  autoEnrichmentTogglePending: false,
  autoListRefreshInFlight: false,
  autoListLastRefreshAt: 0,
  autoListLastCompletedJobId: null,
  quickCsvHeaders: [],
  quickCsvRows: [],
  quickCsvSelectedTagColumns: new Set(),
  quickCsvSelectedNoteColumns: new Set(),
  quickCsvFileName: "",
  droppedDecisions: [],
  droppedDecisionTotal: 0,
};

const el = {
  providerList: document.getElementById("providerList"),
  ingestQuery: document.getElementById("ingestQuery"),
  ingestMaxResults: document.getElementById("ingestMaxResults"),
  ingestTags: document.getElementById("ingestTags"),
  queryFilterMode: document.getElementById("queryFilterMode"),
  querySimilarityThreshold: document.getElementById("querySimilarityThreshold"),
  llmScoringPrompt: document.getElementById("llmScoringPrompt"),
  llmReviewExistingArticles: document.getElementById("llmReviewExistingArticles"),
  llmReviewDroppedArticles: document.getElementById("llmReviewDroppedArticles"),
  publishedFrom: document.getElementById("publishedFrom"),
  publishedTo: document.getElementById("publishedTo"),
  minCitationCount: document.getElementById("minCitationCount"),
  minImpactFactor: document.getElementById("minImpactFactor"),
  requiredKeywords: document.getElementById("requiredKeywords"),
  optionalKeywords: document.getElementById("optionalKeywords"),
  excludedKeywords: document.getElementById("excludedKeywords"),
  journalWhitelist: document.getElementById("journalWhitelist"),
  journalBlacklist: document.getElementById("journalBlacklist"),
  runIngest: document.getElementById("runIngest"),
  pauseIngest: document.getElementById("pauseIngest"),
  resumeIngest: document.getElementById("resumeIngest"),
  cancelIngest: document.getElementById("cancelIngest"),
  applyIngestProviders: document.getElementById("applyIngestProviders"),
  ingestStatus: document.getElementById("ingestStatus"),
  ingestResult: document.getElementById("ingestResult"),
  viewDroppedPapers: document.getElementById("viewDroppedPapers"),
  quickDoi: document.getElementById("quickDoi"),
  quickTags: document.getElementById("quickTags"),
  quickNote: document.getElementById("quickNote"),
  quickCreate: document.getElementById("quickCreate"),
  quickCreateInsertOnly: document.getElementById("quickCreateInsertOnly"),
  quickBatchCreate: document.getElementById("quickBatchCreate"),
  quickBatchCreateInsertOnly: document.getElementById("quickBatchCreateInsertOnly"),
  quickCsvDropzone: document.getElementById("quickCsvDropzone"),
  quickCsvFile: document.getElementById("quickCsvFile"),
  quickCsvFileHint: document.getElementById("quickCsvFileHint"),
  quickCsvDoiColumn: document.getElementById("quickCsvDoiColumn"),
  quickBatchTags: document.getElementById("quickBatchTags"),
  quickBatchNote: document.getElementById("quickBatchNote"),
  quickCsvTagColumnChips: document.getElementById("quickCsvTagColumnChips"),
  quickCsvNoteColumnChips: document.getElementById("quickCsvNoteColumnChips"),
  quickCsvSummary: document.getElementById("quickCsvSummary"),
  toggleAutoEnrichment: document.getElementById("toggleAutoEnrichment"),
  autoEnrichmentToggleHint: document.getElementById("autoEnrichmentToggleHint"),
  enrichmentStatus: document.getElementById("enrichmentStatus"),
  enrichmentResult: document.getElementById("enrichmentResult"),

  editId: document.getElementById("editId"),
  doi: document.getElementById("doi"),
  title: document.getElementById("title"),
  keywords: document.getElementById("keywords"),
  abstract: document.getElementById("abstract"),
  journal: document.getElementById("journal"),
  correspondingAuthor: document.getElementById("correspondingAuthor"),
  affiliations: document.getElementById("affiliations"),
  source: document.getElementById("source"),
  publisher: document.getElementById("publisher"),
  checkStatus: document.getElementById("checkStatus"),
  publishedDate: document.getElementById("publishedDate"),
  url: document.getElementById("url"),
  note: document.getElementById("note"),
  impactFactor: document.getElementById("impactFactor"),
  citationCount: document.getElementById("citationCount"),
  tags: document.getElementById("tags"),
  saveArticle: document.getElementById("saveArticle"),
  resetForm: document.getElementById("resetForm"),
  editModal: document.getElementById("editModal"),
  closeEditModal: document.getElementById("closeEditModal"),
  editModalBackdrop: document.getElementById("editModalBackdrop"),
  dropCacheModal: document.getElementById("dropCacheModal"),
  closeDropCacheModal: document.getElementById("closeDropCacheModal"),
  dropCacheModalBackdrop: document.getElementById("dropCacheModalBackdrop"),
  dropCacheMeta: document.getElementById("dropCacheMeta"),
  dropCacheList: document.getElementById("dropCacheList"),
  refreshDropCache: document.getElementById("refreshDropCache"),

  searchText: document.getElementById("searchText"),
  journalFilter: document.getElementById("journalFilter"),
  tagSearch: document.getElementById("tagSearch"),
  tagFilterAndChips: document.getElementById("tagFilterAndChips"),
  tagFilterOrChips: document.getElementById("tagFilterOrChips"),
  tagFilterSummary: document.getElementById("tagFilterSummary"),
  applyFilter: document.getElementById("applyFilter"),
  clearFilter: document.getElementById("clearFilter"),
  exportCsv: document.getElementById("exportCsv"),

  tableMeta: document.getElementById("tableMeta"),
  refreshArticles: document.getElementById("refreshArticles"),
  articleTableHead: document.getElementById("articleTableHead"),
  articleTableBody: document.getElementById("articleTableBody"),
  articleCardList: document.getElementById("articleCardList"),
  mobileTableTools: document.getElementById("mobileTableTools"),
};

const SORT_LABELS = {
  published_date: "发布时间",
  impact_factor: "文章影响因子",
  ingested_at: "最近录入/更新",
};

const CHECK_FILTER_LABELS = {
  all: "全部",
  hide_correct: "隐藏正确",
  only_error: "仅看错误",
};

const DOI_COLUMN_CANDIDATES = new Set(["doi", "doi_id", "article_doi", "paper_doi"]);
const NOTE_COLUMN_HINT_WORDS = ["note", "remark", "comment", "memo", "annotation", "备注", "说明"];
const TAG_CELL_SPLIT_PATTERN = /[,;|，、]+/;

function parseCSV(text) {
  return String(text || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseCsvMatrix(text) {
  const source = String(text || "").replace(/^\uFEFF/, "");
  const rows = [];
  let row = [];
  let field = "";
  let idx = 0;
  let inQuotes = false;

  const pushField = () => {
    row.push(field);
    field = "";
  };
  const pushRow = () => {
    if (!row.length) return;
    rows.push(row);
    row = [];
  };

  while (idx < source.length) {
    const ch = source[idx];
    if (inQuotes) {
      if (ch === '"') {
        if (source[idx + 1] === '"') {
          field += '"';
          idx += 2;
          continue;
        }
        inQuotes = false;
        idx += 1;
        continue;
      }
      field += ch;
      idx += 1;
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
      idx += 1;
      continue;
    }
    if (ch === ",") {
      pushField();
      idx += 1;
      continue;
    }
    if (ch === "\r") {
      pushField();
      pushRow();
      idx += source[idx + 1] === "\n" ? 2 : 1;
      continue;
    }
    if (ch === "\n") {
      pushField();
      pushRow();
      idx += 1;
      continue;
    }
    field += ch;
    idx += 1;
  }

  pushField();
  if (row.length > 1 || String(row[0] || "").trim()) {
    pushRow();
  }
  return rows;
}

function normalizeHeaderKey(value) {
  return String(value || "").trim().toLowerCase();
}

function normalizeDoiInput(value) {
  let doi = String(value || "").trim();
  if (!doi) return "";
  doi = doi.replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "");
  doi = doi.replace(/^doi:\s*/i, "");
  return doi.trim().toLowerCase();
}

function splitTagCellValue(value) {
  return String(value || "")
    .split(TAG_CELL_SPLIT_PATTERN)
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinList(items) {
  return (items || []).join(", ");
}

function truncateText(text, limit = 220) {
  const value = String(text || "").trim();
  if (!value) return "";
  if (value.length <= limit) return value;
  return `${value.slice(0, limit).trimEnd()}...`;
}

function normalizeTagList(items) {
  const seen = new Set();
  const result = [];
  for (const item of items || []) {
    const value = String(item || "").trim().toLowerCase();
    if (!value || seen.has(value)) continue;
    seen.add(value);
    result.push(value);
  }
  return result;
}

function normalizeNoteLineList(lines) {
  const seen = new Set();
  const result = [];
  for (const line of lines || []) {
    const normalized = String(line || "").trim();
    if (!normalized) continue;
    const key = normalized.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(normalized);
  }
  return result;
}

function composeBatchNote(fixedNote, rowNoteLines) {
  const blocks = [];
  const normalizedFixedNote = String(fixedNote || "").trim();
  if (normalizedFixedNote) blocks.push(normalizedFixedNote);
  const normalizedRowLines = normalizeNoteLineList(rowNoteLines);
  if (normalizedRowLines.length) blocks.push(normalizedRowLines.join("\n"));
  return blocks.join("\n\n").trim();
}

function collectActiveTagFilters() {
  return {
    andTags: normalizeTagList(Array.from(state.selectedTagFiltersAnd.values())),
    orTags: normalizeTagList(Array.from(state.selectedTagFiltersOr.values())),
  };
}

function setSelectedTagSummary() {
  const { andTags, orTags } = collectActiveTagFilters();
  if (!andTags.length && !orTags.length) {
    el.tagFilterSummary.textContent = "当前未选择标签";
    return;
  }
  const parts = [];
  if (andTags.length) parts.push(`AND 全命中：${andTags.join(", ")}`);
  if (orTags.length) parts.push(`OR 任一命中：${orTags.join(", ")}`);
  el.tagFilterSummary.textContent = `当前标签筛选 ${parts.join(" | ")}`;
}

function getTagSelectionClass(name) {
  if (state.selectedTagFiltersAnd.has(name)) return "is-active-and";
  if (state.selectedTagFiltersOr.has(name)) return "is-active-or";
  return "";
}

function renderReadonlyTagChip(name) {
  const selectionClass = getTagSelectionClass(name);
  const extraClass = selectionClass ? ` ${selectionClass}` : "";
  return `<span class="tag-chip tag-chip-readonly${extraClass}">${escapeHtml(name)}</span>`;
}

function renderTagFilterChipSet(container, items, bucket) {
  container.innerHTML = "";
  if (!items.length) {
    const tip = document.createElement("p");
    tip.className = "tag-filter-empty";
    tip.textContent = (el.tagSearch.value || "").trim() ? "没有匹配标签" : "暂无标签";
    container.appendChild(tip);
    return;
  }

  const selected = bucket === "and" ? state.selectedTagFiltersAnd : state.selectedTagFiltersOr;
  const action = bucket === "and" ? "pick-tag-filter-and" : "pick-tag-filter-or";
  const activeClass = bucket === "and" ? "is-active-and" : "is-active-or";

  for (const item of items) {
    const name = String(item.name || "").trim().toLowerCase();
    const count = Number(item.article_count || 0);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `tag-chip ${selected.has(name) ? activeClass : ""}`.trim();
    btn.dataset.act = action;
    btn.dataset.tagName = name;
    btn.setAttribute("aria-pressed", selected.has(name) ? "true" : "false");
    btn.innerHTML = `<span>${escapeHtml(name)}</span><span class="tag-count">${escapeHtml(count)}</span>`;
    container.appendChild(btn);
  }
}

function renderTagFilterChips() {
  const q = (el.tagSearch.value || "").trim().toLowerCase();
  const items = state.tags.filter((tag) => !q || String(tag.name || "").includes(q));
  renderTagFilterChipSet(el.tagFilterAndChips, items, "and");
  renderTagFilterChipSet(el.tagFilterOrChips, items, "or");
}

function renderHeaderControls() {
  const sortButtons = document.querySelectorAll("button[data-sort-by]");
  for (const btn of sortButtons) {
    const sortBy = btn.dataset.sortBy;
    const isActive = sortBy === state.sortBy;
    btn.classList.toggle("is-active", isActive);
    btn.setAttribute("aria-pressed", isActive ? "true" : "false");
  }

  const indicators = document.querySelectorAll("[data-sort-indicator]");
  for (const indicator of indicators) {
    const sortBy = indicator.dataset.sortIndicator;
    if (sortBy === state.sortBy) {
      indicator.textContent = state.sortOrder === "asc" ? "↑" : "↓";
    } else {
      indicator.textContent = "↕";
    }
  }

  const filterButtons = document.querySelectorAll("button[data-check-filter]");
  for (const btn of filterButtons) {
    const isActive = btn.dataset.checkFilter === state.checkFilter;
    btn.classList.toggle("is-active", isActive);
    btn.setAttribute("aria-pressed", isActive ? "true" : "false");
  }
}

function renderIngestSummary(result) {
  if (!result) return "{}";
  return JSON.stringify(
    {
      query: result.query,
      inserted: result.inserted,
      updated: result.updated,
      skipped: result.skipped,
      merged_unique: result.merged_unique,
    },
    null,
    2
  );
}

async function loadTags() {
  const resp = await api("/tags?include_counts=true");
  state.tags = normalizeTagList((resp.items || []).map((item) => item.name)).map((name) => {
    const found = (resp.items || []).find((item) => String(item.name || "").trim().toLowerCase() === name);
    return {
      name,
      article_count: Number(found?.article_count || 0),
    };
  });
  renderTagFilterChips();
  setSelectedTagSummary();
}

function formatDateTime(value) {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return parsed.toLocaleString();
}

function escapeHtml(text) {
  return String(text || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatNumericScore(value) {
  if (value == null) return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return "-";
  return numeric.toFixed(4);
}

function renderDroppedDecisionCards() {
  el.dropCacheList.innerHTML = "";
  if (!state.droppedDecisions.length) {
    const empty = document.createElement("p");
    empty.className = "drop-cache-empty";
    empty.textContent = "当前没有 drop 缓存记录。";
    el.dropCacheList.appendChild(empty);
    return;
  }

  for (const item of state.droppedDecisions) {
    const articleTitle = String(item.article_title || "").trim();
    const doi = String(item.doi || "").trim();
    const doiUrl = doi ? `https://doi.org/${doi}` : "";
    const titleHtml = articleTitle ? escapeHtml(articleTitle) : `<span class="mono">${escapeHtml(doi || "(无 DOI)")}</span>`;
    const subtitle = doiUrl
      ? `<a class="doi-link mono" href="${escapeHtml(doiUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(doi)}</a>`
      : `<span class="mono">${escapeHtml(doi || "-")}</span>`;

    const card = document.createElement("article");
    card.className = "drop-cache-card";
    card.innerHTML = `
      <div class="drop-cache-head">
        <div>
          <p class="drop-cache-title">${titleHtml}</p>
          <p class="drop-cache-subtitle">${subtitle}</p>
        </div>
        <div class="drop-cache-actions">
          <button
            type="button"
            class="btn btn-primary"
            data-act="rescue-drop-entry"
            data-entry-id="${Number(item.id)}"
            data-doi="${escapeHtml(doi)}"
          >
            救回
          </button>
        </div>
      </div>
      <div class="drop-cache-meta-grid">
        <p class="drop-cache-meta-item"><span class="drop-cache-label">范围</span>${escapeHtml(item.scope_summary || "-")}</p>
        <p class="drop-cache-meta-item"><span class="drop-cache-label">时间</span>${escapeHtml(formatDateTime(item.decided_at))}</p>
        <p class="drop-cache-meta-item"><span class="drop-cache-label">模型</span>${escapeHtml(item.model_name || "-")}</p>
        <p class="drop-cache-meta-item"><span class="drop-cache-label">分数</span>${escapeHtml(formatNumericScore(item.score))}</p>
        <p class="drop-cache-meta-item"><span class="drop-cache-label">Prompt Tokens</span>${escapeHtml(item.prompt_tokens ?? "-")}</p>
        <p class="drop-cache-meta-item"><span class="drop-cache-label">Completion Tokens</span>${escapeHtml(item.completion_tokens ?? "-")}</p>
        <p class="drop-cache-meta-item"><span class="drop-cache-label">Total Tokens</span>${escapeHtml(item.total_tokens ?? "-")}</p>
        <p class="drop-cache-meta-item"><span class="drop-cache-label">Scope Hash</span><span class="mono">${escapeHtml(item.decision_scope_hash || "-")}</span></p>
      </div>
      <p class="drop-cache-reason">${escapeHtml(item.reason || "无理由")}</p>
    `;
    el.dropCacheList.appendChild(card);
  }
}

async function fetchDroppedDecisions() {
  el.dropCacheMeta.textContent = "正在读取 drop 缓存...";
  const result = await api("/articles/query-filter/dropped?limit=500");
  state.droppedDecisionTotal = Number(result.total || 0);
  state.droppedDecisions = result.items || [];
  el.dropCacheMeta.textContent = `当前共 ${state.droppedDecisionTotal} 条 drop 缓存。`;
  renderDroppedDecisionCards();
}

async function handleOpenDroppedPapers() {
  openDropCacheModal();
  el.dropCacheList.innerHTML = "";
  await fetchDroppedDecisions();
}

async function handleDropCacheClick(event) {
  const btn = event.target.closest("button[data-act='rescue-drop-entry']");
  if (!btn) return;
  const entryId = Number(btn.dataset.entryId || 0);
  const doi = String(btn.dataset.doi || "").trim();
  if (!entryId) return;
  if (!confirm(`确认救回 ${doi || `drop 记录 #${entryId}`} ?`)) return;

  btn.disabled = true;
  try {
    await api(`/articles/query-filter/dropped/${entryId}/rescue`, { method: "POST" });
    state.droppedDecisions = state.droppedDecisions.filter((item) => Number(item.id) !== entryId);
    state.droppedDecisionTotal = Math.max(0, state.droppedDecisionTotal - 1);
    el.dropCacheMeta.textContent = `当前共 ${state.droppedDecisionTotal} 条 drop 缓存。`;
    renderDroppedDecisionCards();
  } catch (error) {
    btn.disabled = false;
    alert(String(error.message || error));
  }
}

function renderKeywordList(keywords, limit = 8) {
  const items = (keywords || []).map((item) => String(item || "").trim()).filter(Boolean);
  if (!items.length) return "-";
  const visible = items.slice(0, limit);
  const chips = visible
    .map((item) => `<span class="keyword-chip" title="${escapeHtml(item)}">${escapeHtml(item)}</span>`)
    .join("");
  const more =
    items.length > limit
      ? `<span class="keyword-chip keyword-chip-more" title="${escapeHtml(joinList(items))}">+${items.length - limit}</span>`
      : "";
  return `<div class="keyword-list">${chips}${more}</div>`;
}

function renderAbstractSnippet(text, limit = 220) {
  const full = String(text || "").trim();
  if (!full) return "-";
  const display = truncateText(full, limit);
  return `<div class="text-snippet" title="${escapeHtml(full)}">${escapeHtml(display)}</div>`;
}

async function api(path, options) {
  const resp = await fetch(`${apiPrefix}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `HTTP ${resp.status}`);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

function setIngestStatus(text) {
  el.ingestStatus.textContent = text;
}

function resetIngestLog() {
  el.ingestResult.textContent = "";
}

function appendIngestLogLine(line) {
  const old = el.ingestResult.textContent;
  el.ingestResult.textContent = old ? `${old}\n${line}` : line;
  el.ingestResult.scrollTop = el.ingestResult.scrollHeight;
}

function isActiveIngestStatus(status) {
  return ["queued", "running", "paused", "cancel_requested"].includes(String(status || ""));
}

function syncIngestActionButtons() {
  const status = String(state.ingestJobStatus || "idle");
  const active = isActiveIngestStatus(status) && Boolean(state.ingestJobId);
  el.runIngest.disabled = active;
  el.pauseIngest.disabled = !(active && status === "running");
  el.resumeIngest.disabled = !(active && status === "paused");
  el.cancelIngest.disabled = !(active && status !== "cancel_requested");
  el.applyIngestProviders.disabled = !(active && status !== "cancel_requested");
  el.runIngest.textContent = active ? "执行中..." : "执行拉取";
}

function finalizeIngestUI() {
  state.ingestJobId = null;
  state.ingestJobStatus = "idle";
  state.ingestLogCursor = 0;
  syncIngestActionButtons();
}

function setEnrichmentStatus(text) {
  el.enrichmentStatus.textContent = text;
}

function resetEnrichmentLog() {
  el.enrichmentResult.textContent = "";
}

function appendEnrichmentLogLine(line) {
  const old = el.enrichmentResult.textContent;
  el.enrichmentResult.textContent = old ? `${old}\n${line}` : line;
  el.enrichmentResult.scrollTop = el.enrichmentResult.scrollHeight;
}

function formatFieldList(fields) {
  const items = Array.isArray(fields) ? fields.filter((field) => String(field || "").trim()) : [];
  return items.length ? items.join(", ") : "无";
}

function buildEnrichmentSummaryLines(result) {
  if (!result || typeof result !== "object") return [];

  const articleId = Number(result.article_id || 0);
  const doi = String(result.doi || "").trim();
  const hasError = Boolean(result.error);
  const skipped = Boolean(result.skipped);
  const insertOnly = Boolean(result.insert_only);
  let statusText = "已完成";
  if (hasError) {
    statusText = `失败（${String(result.error)}）`;
  } else if (insertOnly) {
    statusText = "仅录入（未自动补全）";
  } else if (skipped) {
    statusText = "已完成（无新增字段）";
  }

  const lines = [
    "[client] 补全摘要",
    `- article_id: ${articleId || "-"}`,
    `- 状态: ${statusText}`,
    `- 新增字段: ${formatFieldList(result.filled_fields)}`,
    `- DOI元数据新增: ${formatFieldList(result.metadata_filled)}`,
    `- AI新增: ${formatFieldList(result.ai_filled)}`,
  ];
  if (doi) {
    lines.splice(2, 0, `- DOI: ${doi}`);
  }
  if (Object.prototype.hasOwnProperty.call(result, "embedding_generated")) {
    lines.push(`- Embedding: ${result.embedding_generated ? "已生成/更新" : "未生成/未更新"}`);
  }
  return lines;
}

function finalizeEnrichmentUI() {
  state.quickEnrichmentRunning = false;
  if (el.quickCreate) {
    el.quickCreate.disabled = false;
    el.quickCreate.textContent = "录入并自动补全";
  }
  if (el.quickCreateInsertOnly) {
    el.quickCreateInsertOnly.disabled = false;
    el.quickCreateInsertOnly.textContent = "仅录入";
  }
  if (el.quickBatchCreate) {
    el.quickBatchCreate.disabled = false;
    el.quickBatchCreate.textContent = "开始批量录入并自动补全";
  }
  if (el.quickBatchCreateInsertOnly) {
    el.quickBatchCreateInsertOnly.disabled = false;
    el.quickBatchCreateInsertOnly.textContent = "开始批量仅录入";
  }
  if (el.quickCsvFile) el.quickCsvFile.disabled = false;
  if (el.quickCsvDoiColumn) el.quickCsvDoiColumn.disabled = !state.quickCsvHeaders.length;
  if (el.quickBatchTags) el.quickBatchTags.disabled = !state.quickCsvHeaders.length;
  if (el.quickBatchNote) el.quickBatchNote.disabled = !state.quickCsvHeaders.length;
  el.quickCsvDropzone?.classList.remove("is-disabled");
}

function setQuickControlsBusy(mode, runEnrichment) {
  state.quickEnrichmentRunning = true;
  if (el.quickCreate) el.quickCreate.disabled = true;
  if (el.quickCreateInsertOnly) el.quickCreateInsertOnly.disabled = true;
  if (el.quickBatchCreate) el.quickBatchCreate.disabled = true;
  if (el.quickBatchCreateInsertOnly) el.quickBatchCreateInsertOnly.disabled = true;
  if (el.quickCsvFile) el.quickCsvFile.disabled = true;
  if (el.quickCsvDoiColumn) el.quickCsvDoiColumn.disabled = true;
  if (el.quickBatchTags) el.quickBatchTags.disabled = true;
  if (el.quickBatchNote) el.quickBatchNote.disabled = true;
  el.quickCsvDropzone?.classList.add("is-disabled");
  if (mode === "single") {
    if (el.quickCreate) el.quickCreate.textContent = "录入并自动补全";
    if (el.quickCreateInsertOnly) el.quickCreateInsertOnly.textContent = "仅录入";
    if (runEnrichment) {
      if (el.quickCreate) el.quickCreate.textContent = "处理中...";
    } else if (el.quickCreateInsertOnly) {
      el.quickCreateInsertOnly.textContent = "处理中...";
    }
    if (el.quickBatchCreate) el.quickBatchCreate.textContent = "开始批量录入并自动补全";
    if (el.quickBatchCreateInsertOnly) el.quickBatchCreateInsertOnly.textContent = "开始批量仅录入";
    return;
  }
  if (el.quickCreate) el.quickCreate.textContent = "录入并自动补全";
  if (el.quickCreateInsertOnly) el.quickCreateInsertOnly.textContent = "仅录入";
  if (el.quickBatchCreate) el.quickBatchCreate.textContent = "开始批量录入并自动补全";
  if (el.quickBatchCreateInsertOnly) el.quickBatchCreateInsertOnly.textContent = "开始批量仅录入";
  if (runEnrichment) {
    if (el.quickBatchCreate) el.quickBatchCreate.textContent = "批量处理中...";
  } else if (el.quickBatchCreateInsertOnly) {
    el.quickBatchCreateInsertOnly.textContent = "批量处理中...";
  }
}

function parseApiErrorMessage(error) {
  const raw = String(error?.message || error || "").trim();
  if (!raw) return "未知错误";
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && typeof parsed.detail === "string") {
      return parsed.detail;
    }
  } catch (_) {
    // ignore JSON parse failure and return raw message.
  }
  return raw;
}

function setQuickCsvSummary(text) {
  if (el.quickCsvSummary) el.quickCsvSummary.textContent = text;
}

function setQuickCsvFileHint(text) {
  if (el.quickCsvFileHint) el.quickCsvFileHint.textContent = text;
}

function pickDefaultQuickCsvDoiColumn(headers) {
  for (const header of headers) {
    if (DOI_COLUMN_CANDIDATES.has(normalizeHeaderKey(header))) {
      return header;
    }
  }
  for (const header of headers) {
    if (normalizeHeaderKey(header).includes("doi")) {
      return header;
    }
  }
  return headers[0] || "";
}

function getSelectedQuickCsvTagColumns() {
  return Array.from(state.quickCsvSelectedTagColumns.values());
}

function getSelectedQuickCsvNoteColumns() {
  return Array.from(state.quickCsvSelectedNoteColumns.values());
}

function isLikelyNoteColumn(header) {
  const key = normalizeHeaderKey(header);
  return NOTE_COLUMN_HINT_WORDS.some((hint) => key.includes(hint));
}

function renderQuickCsvColumnChipList(container, selectedSet, emptyTip) {
  if (!container) return;
  container.innerHTML = "";
  if (!state.quickCsvHeaders.length) {
    const tip = document.createElement("p");
    tip.className = "tag-filter-empty";
    tip.textContent = emptyTip;
    container.appendChild(tip);
    return;
  }

  for (const header of state.quickCsvHeaders) {
    const selected = selectedSet.has(header);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `csv-column-chip ${selected ? "is-active" : ""}`.trim();
    btn.dataset.columnName = header;
    btn.setAttribute("aria-pressed", selected ? "true" : "false");
    btn.textContent = header;
    container.appendChild(btn);
  }
}

function renderQuickCsvTagColumnChips() {
  renderQuickCsvColumnChipList(el.quickCsvTagColumnChips, state.quickCsvSelectedTagColumns, "上传 CSV 后可选标签来源列");
}

function renderQuickCsvNoteColumnChips() {
  renderQuickCsvColumnChipList(el.quickCsvNoteColumnChips, state.quickCsvSelectedNoteColumns, "上传 CSV 后可选备注来源列");
}

function collectQuickCsvRowNoteLines(row, noteColumns) {
  const lines = [];
  for (const col of noteColumns) {
    const value = String(row[col] || "").trim();
    if (!value) continue;
    lines.push(`${col}: ${value}`);
  }
  return normalizeNoteLineList(lines);
}

function buildQuickCsvBatchPlan() {
  const doiColumn = String(el.quickCsvDoiColumn?.value || "").trim();
  const tagColumns = getSelectedQuickCsvTagColumns();
  const noteColumns = getSelectedQuickCsvNoteColumns();
  const fixedTags = parseCSV(el.quickBatchTags?.value || "");
  const fixedNote = String(el.quickBatchNote?.value || "").trim();
  const byDoi = new Map();
  let emptyDoiRows = 0;

  for (const item of state.quickCsvRows) {
    const row = item.data || {};
    const doi = normalizeDoiInput(row[doiColumn]);
    if (!doi) {
      emptyDoiRows += 1;
      continue;
    }

    const rowTags = [];
    for (const col of tagColumns) {
      rowTags.push(...splitTagCellValue(row[col]));
    }
    const rowNoteLines = collectQuickCsvRowNoteLines(row, noteColumns);

    const current = byDoi.get(doi) || { doi, tags: [], noteLines: [], rowNumbers: [] };
    current.rowNumbers.push(item.lineNumber);
    current.tags = normalizeTagList([...current.tags, ...fixedTags, ...rowTags]);
    current.noteLines = normalizeNoteLineList([...current.noteLines, ...rowNoteLines]);
    byDoi.set(doi, current);
  }

  const allItems = Array.from(byDoi.values()).map((item) => ({
    doi: item.doi,
    tags: item.tags,
    note: composeBatchNote(fixedNote, item.noteLines),
    rowNumbers: item.rowNumbers,
  }));
  const duplicateRows = Math.max(0, state.quickCsvRows.length - emptyDoiRows - allItems.length);
  return {
    items: allItems,
    totalRows: state.quickCsvRows.length,
    emptyDoiRows,
    duplicateRows,
    totalUniqueDois: allItems.length,
  };
}

function updateQuickCsvSummary() {
  if (!state.quickCsvRows.length || !state.quickCsvHeaders.length) {
    setQuickCsvSummary("未选择 CSV 文件。");
    return;
  }
  const doiColumn = String(el.quickCsvDoiColumn?.value || "").trim();
  if (!doiColumn) {
    setQuickCsvSummary(`已载入 CSV：${state.quickCsvRows.length} 行（未指定 DOI 列）`);
    return;
  }

  const plan = buildQuickCsvBatchPlan();
  const tagColumnCount = getSelectedQuickCsvTagColumns().length;
  const noteColumnCount = getSelectedQuickCsvNoteColumns().length;
  const fixedTags = parseCSV(el.quickBatchTags?.value || "");
  const fixedNote = String(el.quickBatchNote?.value || "").trim();
  setQuickCsvSummary(
    `已载入 CSV：${plan.totalRows} 行；有效 DOI ${plan.totalUniqueDois} 条；空 DOI 行 ${plan.emptyDoiRows}；重复 DOI 行 ${plan.duplicateRows}；标签列 ${tagColumnCount} 个；固定标签 ${fixedTags.length} 个；备注列 ${noteColumnCount} 个；固定备注${fixedNote ? "已填写" : "未填写"}。`
  );
}

function resetQuickCsvSelection(summary = "未选择 CSV 文件。") {
  state.quickCsvHeaders = [];
  state.quickCsvRows = [];
  state.quickCsvSelectedTagColumns = new Set();
  state.quickCsvSelectedNoteColumns = new Set();
  state.quickCsvFileName = "";
  el.quickCsvDropzone?.classList.remove("is-dragover");
  if (el.quickCsvDoiColumn) {
    el.quickCsvDoiColumn.innerHTML = "";
    const doiPlaceholder = document.createElement("option");
    doiPlaceholder.value = "";
    doiPlaceholder.textContent = "请先选择 CSV 文件";
    el.quickCsvDoiColumn.appendChild(doiPlaceholder);
    el.quickCsvDoiColumn.value = "";
    el.quickCsvDoiColumn.disabled = true;
  }
  if (el.quickBatchTags) {
    el.quickBatchTags.value = "";
    el.quickBatchTags.disabled = true;
  }
  if (el.quickBatchNote) {
    el.quickBatchNote.value = "";
    el.quickBatchNote.disabled = true;
  }
  if (el.quickCsvFile) el.quickCsvFile.value = "";
  renderQuickCsvTagColumnChips();
  renderQuickCsvNoteColumnChips();
  setQuickCsvFileHint("未选择 CSV 文件。");
  setQuickCsvSummary(summary);
}

function renderQuickCsvColumnSelectors() {
  const headers = state.quickCsvHeaders;
  if (!el.quickCsvDoiColumn) return;
  el.quickCsvDoiColumn.innerHTML = "";
  for (const header of headers) {
    const option = document.createElement("option");
    option.value = header;
    option.textContent = header;
    el.quickCsvDoiColumn.appendChild(option);
  }
  el.quickCsvDoiColumn.value = pickDefaultQuickCsvDoiColumn(headers);
  el.quickCsvDoiColumn.disabled = false;
  state.quickCsvSelectedTagColumns = new Set(
    headers.filter((header) => {
      const key = normalizeHeaderKey(header);
      return key.includes("tag") || key.includes("label") || key.includes("keyword") || key.startsWith("level");
    })
  );
  state.quickCsvSelectedNoteColumns = new Set(headers.filter((header) => isLikelyNoteColumn(header)));
  if (el.quickBatchTags) el.quickBatchTags.disabled = false;
  if (el.quickBatchNote) el.quickBatchNote.disabled = false;
  renderQuickCsvTagColumnChips();
  renderQuickCsvNoteColumnChips();
}

async function handleQuickCsvFileChange(explicitFile = null) {
  const file = explicitFile || ((el.quickCsvFile?.files || [])[0] ?? null);
  if (!file) {
    resetQuickCsvSelection();
    return;
  }

  try {
    const text = await file.text();
    const matrix = parseCsvMatrix(text);
    if (!matrix.length) {
      resetQuickCsvSelection("CSV 文件为空。");
      return;
    }

    const rawHeaders = matrix[0];
    const seen = new Map();
    const headers = rawHeaders.map((cell, index) => {
      let base = String(cell || "").trim().replace(/^\uFEFF/, "");
      if (!base) base = `column_${index + 1}`;
      const key = normalizeHeaderKey(base);
      const used = Number(seen.get(key) || 0);
      seen.set(key, used + 1);
      return used > 0 ? `${base}_${used + 1}` : base;
    });

    const rows = [];
    for (let rowIndex = 1; rowIndex < matrix.length; rowIndex += 1) {
      const cells = matrix[rowIndex];
      const data = {};
      let hasValue = false;
      headers.forEach((header, columnIndex) => {
        const value = String(cells[columnIndex] ?? "").trim();
        data[header] = value;
        if (value) hasValue = true;
      });
      if (!hasValue) continue;
      rows.push({
        lineNumber: rowIndex + 1,
        data,
      });
    }

    if (!rows.length) {
      resetQuickCsvSelection("CSV 只有表头，没有可用数据行。");
      return;
    }

    state.quickCsvHeaders = headers;
    state.quickCsvRows = rows;
    state.quickCsvFileName = file.name;
    renderQuickCsvColumnSelectors();
    setQuickCsvFileHint(`已选择：${file.name}`);
    updateQuickCsvSummary();
  } catch (error) {
    resetQuickCsvSelection(`CSV 读取失败：${parseApiErrorMessage(error)}`);
  }
}

function syncAutoEnrichmentToggleUI() {
  if (!el.toggleAutoEnrichment || !el.autoEnrichmentToggleHint) return;
  const known = typeof state.autoEnrichmentEnabled === "boolean";
  if (!known) {
    el.toggleAutoEnrichment.disabled = true;
    el.toggleAutoEnrichment.textContent = "后台自动补全开关读取中...";
    el.autoEnrichmentToggleHint.textContent = "后台自动补全开关读取中...";
    return;
  }

  const enabled = Boolean(state.autoEnrichmentEnabled);
  const pending = Boolean(state.autoEnrichmentTogglePending);

  if (pending) {
    el.toggleAutoEnrichment.disabled = true;
    el.toggleAutoEnrichment.textContent = enabled ? "正在关闭后台自动补全..." : "正在开启后台自动补全...";
  } else {
    el.toggleAutoEnrichment.disabled = false;
    el.toggleAutoEnrichment.textContent = enabled ? "关闭后台自动补全" : "开启后台自动补全";
  }

  el.autoEnrichmentToggleHint.textContent = enabled
    ? "当前：已开启（会按配置周期触发批量补空任务）"
    : "当前：已关闭（仅保留手动触发/快速录入补全）";
}

function getQuerySimilarityThreshold(mode) {
  if (mode === "boolean") return 1;
  if (mode === "none") return 0;
  return el.querySimilarityThreshold.value === "" ? 0.35 : Number(el.querySimilarityThreshold.value);
}

function syncQueryFilterControls() {
  const mode = (el.queryFilterMode.value || "").trim();
  const previousMode = (el.queryFilterMode.dataset.lastMode || "").trim();
  const wasScoreMode = previousMode === "embedding" || previousMode === "llm";
  const isScoreMode = mode === "embedding" || mode === "llm";

  if (wasScoreMode && !isScoreMode) {
    el.querySimilarityThreshold.dataset.lastScoreValue = el.querySimilarityThreshold.value || "0.35";
  }

  if (mode === "boolean") {
    el.querySimilarityThreshold.value = "1";
  } else if (mode === "none") {
    el.querySimilarityThreshold.value = "0";
  } else {
    el.querySimilarityThreshold.value =
      el.querySimilarityThreshold.dataset.lastScoreValue || el.querySimilarityThreshold.value || "0.35";
  }

  el.querySimilarityThreshold.disabled = !isScoreMode;
  const llmMode = mode === "llm";
  el.llmScoringPrompt.disabled = !llmMode;
  el.llmReviewExistingArticles.disabled = !llmMode;
  el.llmReviewDroppedArticles.disabled = !llmMode;
  el.queryFilterMode.dataset.lastMode = mode;
}

function selectedProviders() {
  const checked = Array.from(document.querySelectorAll("input[name='providerCheck']:checked"));
  return checked.map((input) => input.value);
}

function renderProviders() {
  el.providerList.innerHTML = "";
  state.providers.forEach((provider) => {
    const label = document.createElement("label");
    label.className = `provider-item ${provider.configured ? "" : "disabled"}`;

    const input = document.createElement("input");
    input.type = "checkbox";
    input.name = "providerCheck";
    input.value = provider.key;
    input.checked = provider.configured;

    const text = document.createElement("span");
    text.innerHTML = `<strong>${escapeHtml(provider.title)}</strong><small>${escapeHtml(provider.description)}</small>`;

    if (!provider.configured) {
      input.disabled = true;
      text.innerHTML += `<em>未配置 key</em>`;
    }

    label.appendChild(input);
    label.appendChild(text);
    el.providerList.appendChild(label);
  });
}

async function loadProviders() {
  const providers = await api("/providers");
  state.providers = providers;
  renderProviders();
}

function articlePayloadFromForm() {
  return {
    doi: el.doi.value.trim(),
    title: el.title.value.trim(),
    keywords: parseCSV(el.keywords.value),
    abstract: el.abstract.value.trim(),
    journal: el.journal.value.trim(),
    corresponding_author: el.correspondingAuthor.value.trim(),
    affiliations: parseCSV(el.affiliations.value),
    source: el.source.value.trim(),
    publisher: el.publisher.value.trim(),
    check_status: el.checkStatus.value,
    published_date: el.publishedDate.value.trim(),
    url: el.url.value.trim(),
    note: el.note.value.trim(),
    impact_factor: el.impactFactor.value === "" ? null : Number(el.impactFactor.value),
    citation_count: el.citationCount.value === "" ? null : Number(el.citationCount.value),
    tags: parseCSV(el.tags.value),
  };
}

function fillForm(article) {
  el.editId.value = article.id;
  el.doi.value = article.doi || "";
  el.title.value = article.title || "";
  el.keywords.value = joinList(article.keywords);
  el.abstract.value = article.abstract || "";
  el.journal.value = article.journal || "";
  el.correspondingAuthor.value = article.corresponding_author || "";
  el.affiliations.value = joinList(article.affiliations);
  el.source.value = article.source || "";
  el.publisher.value = article.publisher || "";
  el.checkStatus.value = article.check_status || "unchecked";
  el.publishedDate.value = article.published_date || "";
  el.url.value = article.url || "";
  el.note.value = article.note || "";
  el.impactFactor.value = article.impact_factor == null ? "" : String(article.impact_factor);
  el.citationCount.value = article.citation_count == null ? "" : String(article.citation_count);
  el.tags.value = joinList((article.tags || []).map((tag) => tag.name));
}

function resetForm() {
  el.editId.value = "";
  el.doi.value = "";
  el.title.value = "";
  el.keywords.value = "";
  el.abstract.value = "";
  el.journal.value = "";
  el.correspondingAuthor.value = "";
  el.affiliations.value = "";
  el.source.value = "";
  el.publisher.value = "";
  el.checkStatus.value = "unchecked";
  el.publishedDate.value = "";
  el.url.value = "";
  el.note.value = "";
  el.impactFactor.value = "";
  el.citationCount.value = "";
  el.tags.value = "";
}

function openEditModal() {
  el.editModal.classList.remove("hidden");
  document.body.classList.add("modal-open");
}

function closeEditModal() {
  el.editModal.classList.add("hidden");
  document.body.classList.remove("modal-open");
}

function openDropCacheModal() {
  el.dropCacheModal.classList.remove("hidden");
  document.body.classList.add("modal-open");
}

function closeDropCacheModal() {
  el.dropCacheModal.classList.add("hidden");
  if (el.editModal.classList.contains("hidden")) {
    document.body.classList.remove("modal-open");
  }
}

function renderTagChipGroup(tags) {
  if (!tags || !tags.length) return "-";
  return tags
    .map((tag) => {
      const name = String(tag.name || "").trim().toLowerCase();
      return renderReadonlyTagChip(name);
    })
    .join("");
}

function renderStatusFlag(articleId, value, currentStatus) {
  const isActive = currentStatus === value;
  const toneClass = value === "error" ? "status-flag-error" : "status-flag-correct";
  const activeClass = isActive ? " is-active" : "";
  const label = value === "error" ? "错误" : "正确";
  return `
    <button
      type="button"
      class="status-flag ${toneClass}${activeClass}"
      data-act="toggle-check"
      data-id="${articleId}"
      data-value="${value}"
      aria-pressed="${isActive ? "true" : "false"}"
    >
      ${label}
    </button>
  `;
}

function renderCardRows() {
  el.articleCardList.innerHTML = "";

  for (const article of state.articles) {
    const card = document.createElement("article");
    const doiUrl = article.doi ? `https://doi.org/${article.doi}` : "";
    const resolvedLink = (article.url || "").trim() || doiUrl;
    const checkStatus = article.check_status || "unchecked";
    const citationValue = Number(article.citation_count);
    const citationCount =
      article.citation_count == null || Number.isNaN(citationValue) ? "-" : String(Math.max(0, Math.trunc(citationValue)));
    const impactValue = Number(article.impact_factor);
    const impactFactor =
      article.impact_factor == null || Number.isNaN(impactValue)
        ? "-"
        : impactValue.toFixed(2).replace(/\.00$/, "");

    card.className = "article-card";
    card.innerHTML = `
      <div class="article-card-head">
        <p class="article-card-title">${escapeHtml(article.title || "(无标题)")}</p>
        <p class="article-card-meta">
          DOI:
          ${doiUrl
            ? `<a class="doi-link mono" href="${escapeHtml(doiUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(article.doi)}</a>`
            : `<span class="mono">${escapeHtml(article.doi || "-")}</span>`}
        </p>
      </div>
      <div class="article-card-block">
        <p class="article-card-label">关键词</p>
        ${renderKeywordList(article.keywords || [], 10)}
      </div>
      <div class="article-card-block">
        <p class="article-card-label">摘要</p>
        ${renderAbstractSnippet(article.abstract, 320)}
      </div>
      <div class="article-card-block">
        <p class="article-card-label">备注</p>
        ${renderAbstractSnippet(article.note, 200)}
      </div>
      <p class="article-card-row">期刊：${escapeHtml(article.journal || "-")}</p>
      <p class="article-card-row">通讯作者：${escapeHtml(article.corresponding_author || "-")}</p>
      <p class="article-card-row">来源：${escapeHtml(article.source || "-")} · 发布时间：${escapeHtml(article.published_date || "-")}</p>
      <p class="article-card-row">被引次数：${escapeHtml(citationCount)} · 文章影响因子：${escapeHtml(impactFactor)} · 最近录入/更新：${escapeHtml(formatDateTime(article.ingested_at))}</p>
      <div class="article-card-status">
        ${renderStatusFlag(article.id, "correct", checkStatus)}
        ${renderStatusFlag(article.id, "error", checkStatus)}
      </div>
      <div class="article-card-actions">
        <button data-act="edit" data-id="${article.id}">编辑</button>
        <button data-act="note" data-id="${article.id}">备注</button>
        <button data-act="tag" data-id="${article.id}">加标签</button>
        <button data-act="del" data-id="${article.id}" class="danger">删除</button>
        ${
          resolvedLink
            ? `<a class="external-link" href="${escapeHtml(resolvedLink)}" target="_blank" rel="noopener noreferrer">打开链接</a>`
            : ""
        }
      </div>
      <div class="cell-tags">${renderTagChipGroup(article.tags || [])}</div>
    `;
    el.articleCardList.appendChild(card);
  }
}

function renderRows() {
  el.articleTableBody.innerHTML = "";
  el.articleCardList.innerHTML = "";
  const hasNoteColumn = Boolean(el.articleTableHead?.querySelector("th.col-note"));
  const metaParts = [`当前 ${state.total} 条`, `排序：${SORT_LABELS[state.sortBy] || state.sortBy}${state.sortOrder === "asc" ? "↑" : "↓"}`];
  if (state.checkFilter !== "all") {
    metaParts.push(`核查：${CHECK_FILTER_LABELS[state.checkFilter] || state.checkFilter}`);
  }
  el.tableMeta.textContent = metaParts.join(" · ");

  for (const article of state.articles) {
    const tr = document.createElement("tr");

    const tags = renderTagChipGroup(article.tags || []);
    const doiUrl = article.doi ? `https://doi.org/${article.doi}` : "";
    const resolvedLink = (article.url || "").trim() || doiUrl;
    const linkCell = resolvedLink
      ? `<a class="external-link" href="${escapeHtml(resolvedLink)}" target="_blank" rel="noopener noreferrer">打开链接</a>`
      : "-";
    const doiCell = doiUrl
      ? `<a class="doi-link mono" href="${escapeHtml(doiUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(article.doi)}</a>`
      : `<span class="mono">${escapeHtml(article.doi)}</span>`;
    const checkStatus = article.check_status || "unchecked";
    const citationValue = Number(article.citation_count);
    const citationCount =
      article.citation_count == null || Number.isNaN(citationValue) ? "-" : String(Math.max(0, Math.trunc(citationValue)));
    const impactValue = Number(article.impact_factor);
    const impactFactor =
      article.impact_factor == null || Number.isNaN(impactValue)
        ? "-"
        : impactValue.toFixed(2).replace(/\.00$/, "");
    const ingestedAt = formatDateTime(article.ingested_at);
    const noteCell = hasNoteColumn ? `<td class="cell-note">${renderAbstractSnippet(article.note, 180)}</td>` : "";

    tr.innerHTML = `
      <td class="cell-doi">${doiCell}</td>
      <td class="cell-title">${escapeHtml(article.title)}</td>
      <td class="cell-keywords">${renderKeywordList(article.keywords || [])}</td>
      <td class="cell-abstract">${renderAbstractSnippet(article.abstract)}</td>
      <td class="cell-journal">${escapeHtml(article.journal)}</td>
      <td class="cell-author">${escapeHtml(article.corresponding_author)}</td>
      <td class="cell-aff">${escapeHtml(joinList(article.affiliations))}</td>
      <td class="cell-source">${escapeHtml(article.source)}</td>
      <td class="cell-date">${escapeHtml(article.published_date || "-")}</td>
      <td class="cell-citation">${escapeHtml(citationCount)}</td>
      <td class="cell-impact">${escapeHtml(impactFactor)}</td>
      <td class="cell-ingested">${escapeHtml(ingestedAt)}</td>
      <td class="cell-link">${linkCell}</td>
      ${noteCell}
      <td class="cell-actions">
        <div class="row-actions">
          <button data-act="edit" data-id="${article.id}">编辑</button>
          <button data-act="note" data-id="${article.id}">备注</button>
          <button data-act="tag" data-id="${article.id}">加标签</button>
          <button data-act="del" data-id="${article.id}" class="danger">删除</button>
        </div>
      </td>
      <td class="cell-check-flag">${renderStatusFlag(article.id, "correct", checkStatus)}</td>
      <td class="cell-check-flag">${renderStatusFlag(article.id, "error", checkStatus)}</td>
      <td class="cell-tags">${tags}</td>
    `;
    el.articleTableBody.appendChild(tr);
  }

  renderCardRows();
}

function buildArticleQueryParams() {
  const params = new URLSearchParams();
  const { andTags, orTags } = collectActiveTagFilters();
  if (el.searchText.value.trim()) params.set("search", el.searchText.value.trim());
  if (el.journalFilter.value.trim()) params.set("journal", el.journalFilter.value.trim());
  if (andTags.length) params.set("tags_and", andTags.join(","));
  if (orTags.length) params.set("tags_or", orTags.join(","));
  if (state.checkFilter !== "all") params.set("check_filter", state.checkFilter);
  params.set("sort_by", state.sortBy || "ingested_at");
  params.set("sort_order", state.sortOrder || "desc");
  return params;
}

async function fetchArticles() {
  const params = buildArticleQueryParams();
  params.set("limit", "200");

  const result = await api(`/articles?${params.toString()}`);
  state.total = result.total;
  state.articles = result.items;
  renderRows();
  renderHeaderControls();
}

async function handleRefreshArticles() {
  await fetchArticles();
  await loadTags();
}

function handleExportCsv() {
  const params = buildArticleQueryParams();
  const exportUrl = `${apiPrefix}/articles/export/csv?${params.toString()}`;
  window.open(exportUrl, "_blank", "noopener");
}

async function handleSaveArticle() {
  if (!el.editId.value) {
    alert("请从文献列表点击“编辑”后再保存。");
    return;
  }

  const payload = articlePayloadFromForm();
  if (payload.impact_factor !== null && Number.isNaN(payload.impact_factor)) {
    alert("文章影响因子必须是数字。");
    return;
  }
  if (payload.citation_count !== null && (Number.isNaN(payload.citation_count) || payload.citation_count < 0)) {
    alert("被引次数必须是非负数字。");
    return;
  }

  await api(`/articles/${el.editId.value}`, {
    method: "PUT",
    body: JSON.stringify({
      title: payload.title,
      keywords: payload.keywords,
      abstract: payload.abstract,
      journal: payload.journal,
      corresponding_author: payload.corresponding_author,
      affiliations: payload.affiliations,
      source: payload.source,
      publisher: payload.publisher,
      check_status: payload.check_status,
      published_date: payload.published_date,
      url: payload.url,
      note: payload.note,
      impact_factor: payload.impact_factor,
      citation_count: payload.citation_count,
      tags: payload.tags,
    }),
  });

  resetForm();
  closeEditModal();
  await fetchArticles();
  await loadTags();
}

async function pollIngestionJob(jobId) {
  if (state.ingestJobId !== jobId) return;
  try {
    const snapshot = await api(`/ingestion/jobs/${jobId}?from_line=${state.ingestLogCursor}`);
    for (const line of snapshot.logs || []) {
      appendIngestLogLine(line);
    }
    state.ingestLogCursor = Number(snapshot.next_line || state.ingestLogCursor);
    state.ingestJobStatus = String(snapshot.status || "running");
    syncIngestActionButtons();

    if (snapshot.status === "queued") {
      setIngestStatus(`任务排队中 · job=${jobId.slice(0, 8)}`);
      window.setTimeout(() => pollIngestionJob(jobId), INGEST_POLL_INTERVAL_MS);
      return;
    }
    if (snapshot.status === "running") {
      setIngestStatus(`任务执行中 · job=${jobId.slice(0, 8)}`);
      window.setTimeout(() => pollIngestionJob(jobId), INGEST_POLL_INTERVAL_MS);
      return;
    }
    if (snapshot.status === "paused") {
      setIngestStatus(`任务已暂停 · job=${jobId.slice(0, 8)}`);
      window.setTimeout(() => pollIngestionJob(jobId), INGEST_POLL_INTERVAL_MS);
      return;
    }
    if (snapshot.status === "cancel_requested") {
      setIngestStatus(`任务停止中 · job=${jobId.slice(0, 8)}`);
      window.setTimeout(() => pollIngestionJob(jobId), INGEST_POLL_INTERVAL_MS);
      return;
    }

    if (snapshot.status === "completed") {
      setIngestStatus("任务已完成");
      appendIngestLogLine("[client] 任务结果摘要:");
      appendIngestLogLine(renderIngestSummary(snapshot.result));
      await fetchArticles();
      await loadTags();
      finalizeIngestUI();
      return;
    }

    if (snapshot.status === "cancelled") {
      setIngestStatus("任务已取消");
      appendIngestLogLine("[client] 任务已取消。");
      finalizeIngestUI();
      return;
    }

    setIngestStatus("任务失败");
    appendIngestLogLine(`[client] ${snapshot.error || "未知错误"}`);
    finalizeIngestUI();
  } catch (error) {
    setIngestStatus("任务状态读取失败");
    appendIngestLogLine(`[client] ${String(error.message || error)}`);
    if (state.ingestJobId) {
      window.setTimeout(() => pollIngestionJob(jobId), INGEST_POLL_INTERVAL_MS);
    }
  }
}

async function handleIngest() {
  if (state.ingestJobId) {
    alert("已有任务在执行，请等待当前任务完成。");
    return;
  }

  const queryFilterMode = el.queryFilterMode.value || "embedding";
  const payload = {
    query: el.ingestQuery.value.trim() || null,
    max_results: Number(el.ingestMaxResults.value || 200),
    providers: selectedProviders(),
    save_tags: parseCSV(el.ingestTags.value),
    query_filter_mode: queryFilterMode,
    query_similarity_threshold: getQuerySimilarityThreshold(queryFilterMode),
    llm_scoring_prompt: el.llmScoringPrompt.value.trim() || null,
    llm_review_existing_articles: Boolean(el.llmReviewExistingArticles.checked),
    llm_review_dropped_articles: Boolean(el.llmReviewDroppedArticles.checked),
    published_from: el.publishedFrom.value.trim() || null,
    published_to: el.publishedTo.value.trim() || null,
    required_keywords: parseCSV(el.requiredKeywords.value),
    optional_keywords: parseCSV(el.optionalKeywords.value),
    excluded_keywords: parseCSV(el.excludedKeywords.value),
    journal_whitelist: parseCSV(el.journalWhitelist.value),
    journal_blacklist: parseCSV(el.journalBlacklist.value),
    min_citation_count: el.minCitationCount.value === "" ? null : Number(el.minCitationCount.value),
    min_impact_factor: el.minImpactFactor.value === "" ? null : Number(el.minImpactFactor.value),
  };

  if (!payload.providers.length) {
    alert("请至少选择一个数据源。");
    return;
  }
  if (payload.min_citation_count !== null && Number.isNaN(payload.min_citation_count)) {
    alert("最少被引次数必须是数字。");
    return;
  }
  if (payload.min_impact_factor !== null && Number.isNaN(payload.min_impact_factor)) {
    alert("最小文章影响因子必须是数字。");
    return;
  }
  if (
    Number.isNaN(payload.query_similarity_threshold) ||
    payload.query_similarity_threshold < 0 ||
    payload.query_similarity_threshold > 1
  ) {
    alert("关联度阈值必须是 0 到 1 之间的数字。");
    return;
  }

  resetIngestLog();
  setIngestStatus("正在创建任务...");
  appendIngestLogLine("[client] 已提交拉取请求。");
  state.ingestJobId = "__creating__";
  state.ingestJobStatus = "queued";
  syncIngestActionButtons();

  try {
    const created = await api("/ingestion/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.ingestJobId = created.job_id;
    state.ingestJobStatus = String(created.status || "queued");
    state.ingestLogCursor = 0;
    syncIngestActionButtons();
    appendIngestLogLine(`[client] 任务已创建: ${created.job_id}`);
    await pollIngestionJob(created.job_id);
  } catch (error) {
    setIngestStatus("任务创建失败");
    appendIngestLogLine(`[client] ${String(error.message || error)}`);
    finalizeIngestUI();
  }
}

async function handlePauseIngest() {
  const jobId = state.ingestJobId;
  if (!jobId) return;
  const result = await api(`/ingestion/jobs/${jobId}/pause`, { method: "POST" });
  state.ingestJobStatus = String(result.status || "paused");
  syncIngestActionButtons();
  appendIngestLogLine(`[client] ${result.message || "已发送暂停请求。"}`);
}

async function handleResumeIngest() {
  const jobId = state.ingestJobId;
  if (!jobId) return;
  const result = await api(`/ingestion/jobs/${jobId}/resume`, { method: "POST" });
  state.ingestJobStatus = String(result.status || "running");
  syncIngestActionButtons();
  appendIngestLogLine(`[client] ${result.message || "已发送继续请求。"}`);
}

async function handleCancelIngest() {
  const jobId = state.ingestJobId;
  if (!jobId) return;
  if (!confirm("确认停止当前拉取任务？")) return;
  const result = await api(`/ingestion/jobs/${jobId}/cancel`, { method: "POST" });
  state.ingestJobStatus = String(result.status || "cancel_requested");
  syncIngestActionButtons();
  appendIngestLogLine(`[client] ${result.message || "已发送停止请求。"}`);
}

async function handleApplyIngestProviders() {
  const jobId = state.ingestJobId;
  if (!jobId) return;
  const providers = selectedProviders();
  if (!providers.length) {
    alert("运行中至少保留一个 provider。");
    return;
  }
  const result = await api(`/ingestion/jobs/${jobId}/providers`, {
    method: "PATCH",
    body: JSON.stringify({ providers }),
  });
  appendIngestLogLine(`[client] ${result.message || "已更新任务 provider。"} providers=${(result.providers || []).join(",")}`);
}

async function handleQuickCreate(runEnrichment = true) {
  if (state.quickEnrichmentRunning) {
    alert("当前已有录入补全任务在执行，请等待完成。");
    return;
  }

  const doi = el.quickDoi.value.trim();
  if (!doi) {
    alert("请填写 DOI。");
    return;
  }
  const tags = parseCSV(el.quickTags.value);
  const note = String(el.quickNote?.value || "").trim();

  resetEnrichmentLog();
  setEnrichmentStatus(runEnrichment ? "正在录入并自动补全..." : "正在仅录入...");
  appendEnrichmentLogLine("[client] 已提交请求，正在处理...");
  setQuickControlsBusy("single", runEnrichment);

  try {
    const created = await api("/articles/quick", {
      method: "POST",
      body: JSON.stringify({ doi, tags, note, run_enrichment: runEnrichment }),
    });

    for (const line of created.logs || []) {
      appendEnrichmentLogLine(line);
    }
    if (created.enrichment_result) {
      for (const line of buildEnrichmentSummaryLines(created.enrichment_result)) {
        appendEnrichmentLogLine(line);
      }
    }
    appendEnrichmentLogLine(`[client] 完成，article_id=${created.article.id}`);
    setEnrichmentStatus(runEnrichment ? "录入并补全完成" : "仅录入完成");
    await fetchArticles();
    await loadTags();
  } catch (error) {
    setEnrichmentStatus(runEnrichment ? "录入并补全失败" : "仅录入失败");
    appendEnrichmentLogLine(`[client] ${parseApiErrorMessage(error)}`);
  } finally {
    finalizeEnrichmentUI();
  }
}

async function handleQuickBatchCreate(runEnrichment = true) {
  if (state.quickEnrichmentRunning) {
    alert("当前已有录入补全任务在执行，请等待完成。");
    return;
  }

  if (!state.quickCsvRows.length) {
    alert("请先选择包含 DOI 的 CSV 文件。");
    return;
  }
  if (!state.quickCsvHeaders.length || !el.quickCsvDoiColumn?.value) {
    alert("请先选择 DOI 列。");
    return;
  }

  const plan = buildQuickCsvBatchPlan();
  if (!plan.items.length) {
    alert("没有可导入的有效 DOI。请检查 DOI 列和 CSV 内容。");
    return;
  }

  if (plan.items.length > 300) {
    const ok = confirm(`即将批量录入 ${plan.items.length} 条 DOI，可能耗时较长，是否继续？`);
    if (!ok) return;
  }

  resetEnrichmentLog();
  const progressTitle = runEnrichment ? "正在批量录入并自动补全" : "正在批量仅录入";
  setEnrichmentStatus(`${progressTitle}（0/${plan.items.length}）...`);
  const selectedTagColumns = getSelectedQuickCsvTagColumns();
  const selectedNoteColumns = getSelectedQuickCsvNoteColumns();
  const fixedTags = parseCSV(el.quickBatchTags?.value || "");
  const fixedNote = String(el.quickBatchNote?.value || "").trim();
  appendEnrichmentLogLine(
    `[client] CSV 批量任务已开始：文件=${state.quickCsvFileName || "-"}, DOI列=${el.quickCsvDoiColumn?.value || "-"}, 总行数=${plan.totalRows}, 有效DOI=${plan.totalUniqueDois}, 空DOI行=${plan.emptyDoiRows}, 重复DOI行=${plan.duplicateRows}`
  );
  if (selectedTagColumns.length || fixedTags.length || selectedNoteColumns.length || fixedNote) {
    appendEnrichmentLogLine("[client] 补充信息策略：");
    appendEnrichmentLogLine(
      `  - 标签：固定=${fixedTags.length ? fixedTags.join(",") : "-"}；来源列=${selectedTagColumns.length ? selectedTagColumns.join(",") : "-"}`
    );
    appendEnrichmentLogLine(
      `  - 备注：固定=${fixedNote ? `${fixedNote.length} 字` : "-"}；来源列=${selectedNoteColumns.length ? selectedNoteColumns.join(",") : "-"}`
    );
  }
  setQuickControlsBusy("batch", runEnrichment);

  let success = 0;
  let failed = 0;
  for (let index = 0; index < plan.items.length; index += 1) {
    const item = plan.items[index];
    try {
      const created = await api("/articles/quick", {
        method: "POST",
        body: JSON.stringify({ doi: item.doi, tags: item.tags, note: item.note, run_enrichment: runEnrichment }),
      });
      success += 1;
      const articleId = Number(created?.article?.id || 0);
      appendEnrichmentLogLine(
        `[${index + 1}/${plan.items.length}] OK doi=${item.doi} article_id=${articleId || "-"} rows=${item.rowNumbers.join(",")}`
      );
    } catch (error) {
      failed += 1;
      appendEnrichmentLogLine(
        `[${index + 1}/${plan.items.length}] FAIL doi=${item.doi} rows=${item.rowNumbers.join(",")} error=${parseApiErrorMessage(error)}`
      );
    }
    setEnrichmentStatus(`${progressTitle}（${index + 1}/${plan.items.length}）...`);
  }

  try {
    await fetchArticles();
    await loadTags();
  } catch (error) {
    appendEnrichmentLogLine(`[client] 刷新文献列表失败：${parseApiErrorMessage(error)}`);
  } finally {
    appendEnrichmentLogLine(`[client] 批量任务完成：成功 ${success}，失败 ${failed}。`);
    if (failed) {
      setEnrichmentStatus(`批量完成（成功 ${success}，失败 ${failed}）`);
    } else {
      setEnrichmentStatus(runEnrichment ? `批量录入并补全完成（${success} 条）` : `批量仅录入完成（${success} 条）`);
    }
    finalizeEnrichmentUI();
  }
}

async function handleQuickCsvSelectionChanged() {
  if (!state.quickCsvRows.length) {
    setQuickCsvSummary("未选择 CSV 文件。");
    return;
  }
  updateQuickCsvSummary();
}

async function handleQuickBatchTagsChanged() {
  updateQuickCsvSummary();
}

async function handleQuickBatchNoteChanged() {
  updateQuickCsvSummary();
}

async function handleQuickCsvTagColumnChipClick(event) {
  const btn = event.target.closest("button[data-column-name]");
  if (!btn || !state.quickCsvHeaders.length || state.quickEnrichmentRunning) return;
  const name = String(btn.dataset.columnName || "").trim();
  if (!name) return;

  if (state.quickCsvSelectedTagColumns.has(name)) {
    state.quickCsvSelectedTagColumns.delete(name);
  } else {
    state.quickCsvSelectedTagColumns.add(name);
  }
  renderQuickCsvTagColumnChips();
  updateQuickCsvSummary();
}

async function handleQuickCsvNoteColumnChipClick(event) {
  const btn = event.target.closest("button[data-column-name]");
  if (!btn || !state.quickCsvHeaders.length || state.quickEnrichmentRunning) return;
  const name = String(btn.dataset.columnName || "").trim();
  if (!name) return;

  if (state.quickCsvSelectedNoteColumns.has(name)) {
    state.quickCsvSelectedNoteColumns.delete(name);
  } else {
    state.quickCsvSelectedNoteColumns.add(name);
  }
  renderQuickCsvNoteColumnChips();
  updateQuickCsvSummary();
}

async function handleQuickCsvDropzoneClick() {
  if (state.quickEnrichmentRunning) return;
  if (!el.quickCsvFile) return;
  el.quickCsvFile.click();
}

async function handleQuickCsvDropzoneKeydown(event) {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  if (state.quickEnrichmentRunning) return;
  if (!el.quickCsvFile) return;
  el.quickCsvFile.click();
}

async function handleQuickCsvDropzoneDragOver(event) {
  if (state.quickEnrichmentRunning) return;
  event.preventDefault();
  el.quickCsvDropzone?.classList.add("is-dragover");
}

async function handleQuickCsvDropzoneDragLeave(event) {
  if (!el.quickCsvDropzone) return;
  if (!event.relatedTarget || !el.quickCsvDropzone.contains(event.relatedTarget)) {
    el.quickCsvDropzone.classList.remove("is-dragover");
  }
}

async function handleQuickCsvDropzoneDrop(event) {
  if (state.quickEnrichmentRunning) return;
  event.preventDefault();
  el.quickCsvDropzone?.classList.remove("is-dragover");
  const files = Array.from(event.dataTransfer?.files || []);
  const [file] = files;
  if (!file) return;
  if (!/\.csv$/i.test(file.name)) {
    resetQuickCsvSelection("仅支持 CSV 文件。");
    return;
  }
  if (typeof DataTransfer !== "undefined") {
    const transfer = new DataTransfer();
    transfer.items.add(file);
    if (el.quickCsvFile) el.quickCsvFile.files = transfer.files;
  }
  await handleQuickCsvFileChange(file);
}

async function handleQuickCsvFilePicked() {
  await handleQuickCsvFileChange();
  if (!state.quickCsvRows.length) return;
  updateQuickCsvSummary();
}

async function handleToggleAutoEnrichment() {
  if (state.autoEnrichmentTogglePending) return;
  if (typeof state.autoEnrichmentEnabled !== "boolean") {
    alert("后台自动补全开关状态尚未读取完成，请稍后重试。");
    return;
  }

  const nextEnabled = !state.autoEnrichmentEnabled;
  state.autoEnrichmentTogglePending = true;
  syncAutoEnrichmentToggleUI();

  try {
    const result = await api("/enrichment/auto/enabled", {
      method: "POST",
      body: JSON.stringify({ enabled: nextEnabled }),
    });
    state.autoEnrichmentEnabled = Boolean(result.enabled);
    appendEnrichmentLogLine(
      `[auto] ${result.message || (state.autoEnrichmentEnabled ? "后台自动补全已开启。" : "后台自动补全已关闭。")}`
    );
    if (!state.quickEnrichmentRunning && state.autoEnrichmentEnabled === false) {
      setEnrichmentStatus("后台自动补全：已关闭");
    }
  } finally {
    state.autoEnrichmentTogglePending = false;
    syncAutoEnrichmentToggleUI();
  }
}

async function refreshArticlesFromAuto(reason) {
  if (state.autoListRefreshInFlight) return;
  state.autoListRefreshInFlight = true;
  try {
    await handleRefreshArticles();
    state.autoListLastRefreshAt = Date.now();
    appendEnrichmentLogLine(`[auto] 文献列表已刷新: ${reason}`);
  } catch (error) {
    appendEnrichmentLogLine(`[auto] 文献列表刷新失败: ${String(error.message || error)}`);
  } finally {
    state.autoListRefreshInFlight = false;
  }
}

async function pollAutoEnrichmentStatus() {
  try {
    const snapshot = await api(`/enrichment/auto/status?from_line=${state.autoEnrichmentLogCursor}`);
    if (typeof snapshot.auto_enabled === "boolean") {
      state.autoEnrichmentEnabled = snapshot.auto_enabled;
      syncAutoEnrichmentToggleUI();
    }
    if (!snapshot.has_job) {
      if (!state.quickEnrichmentRunning) {
        if (state.autoEnrichmentEnabled === false) {
          setEnrichmentStatus("后台自动补全：已关闭");
        } else {
          setEnrichmentStatus("后台自动补全：当前空闲");
        }
      }
      return;
    }

    const oldJobId = state.autoEnrichmentJobId;
    if (state.autoEnrichmentJobId !== snapshot.job_id) {
      state.autoEnrichmentJobId = snapshot.job_id;
      state.autoEnrichmentLogCursor = 0;
      appendEnrichmentLogLine(`[auto] 检测到新的后台补全任务: ${snapshot.job_id}`);
      return;
    }

    for (const line of snapshot.logs || []) {
      appendEnrichmentLogLine(`[auto] ${line}`);
    }
    const appendedLogs = Array.isArray(snapshot.logs) ? snapshot.logs.length : 0;
    state.autoEnrichmentLogCursor = Number(snapshot.next_line || state.autoEnrichmentLogCursor);

    if (!state.quickEnrichmentRunning) {
      const status = snapshot.status || "idle";
      const statusPrefix = state.autoEnrichmentEnabled === false ? "后台自动补全(已关闭)" : "后台自动补全";
      if (status === "queued") {
        setEnrichmentStatus(`${statusPrefix}：排队中 · job=${snapshot.job_id.slice(0, 8)}`);
      } else if (status === "running") {
        setEnrichmentStatus(`${statusPrefix}：执行中 · job=${snapshot.job_id.slice(0, 8)}`);
      } else if (status === "failed") {
        setEnrichmentStatus(`${statusPrefix}：失败 · job=${snapshot.job_id.slice(0, 8)}`);
      } else {
        setEnrichmentStatus(`${statusPrefix}：已完成 · job=${snapshot.job_id.slice(0, 8)}`);
      }

      const now = Date.now();
      const allowPeriodicRefresh = now - Number(state.autoListLastRefreshAt || 0) >= AUTO_ENRICHMENT_LIST_REFRESH_INTERVAL_MS;
      if ((status === "running" || status === "queued") && allowPeriodicRefresh) {
        if (appendedLogs > 0 || oldJobId !== snapshot.job_id) {
          await refreshArticlesFromAuto(`任务执行中 (${snapshot.job_id.slice(0, 8)})`);
        }
      }
      if (status === "completed" && state.autoListLastCompletedJobId !== snapshot.job_id) {
        state.autoListLastCompletedJobId = snapshot.job_id;
        await refreshArticlesFromAuto(`任务完成 (${snapshot.job_id.slice(0, 8)})`);
      }
    }
  } catch (error) {
    if (!state.quickEnrichmentRunning) {
      setEnrichmentStatus("后台自动补全状态读取失败");
    }
    appendEnrichmentLogLine(`[auto] ${String(error.message || error)}`);
  } finally {
    window.setTimeout(pollAutoEnrichmentStatus, AUTO_ENRICHMENT_POLL_INTERVAL_MS);
  }
}

async function handleTableClick(event) {
  const btn = event.target.closest("button[data-act]");
  if (!btn) return;

  const action = btn.dataset.act;
  if (action === "pick-tag-filter-and" || action === "pick-tag-filter-or") {
    const tagName = String(btn.dataset.tagName || "").trim().toLowerCase();
    if (!tagName) return;
    const isAndBucket = action === "pick-tag-filter-and";
    const primary = isAndBucket ? state.selectedTagFiltersAnd : state.selectedTagFiltersOr;
    const secondary = isAndBucket ? state.selectedTagFiltersOr : state.selectedTagFiltersAnd;
    if (primary.has(tagName)) {
      primary.delete(tagName);
    } else {
      primary.add(tagName);
      secondary.delete(tagName);
    }
    renderTagFilterChips();
    setSelectedTagSummary();
    await fetchArticles();
    return;
  }

  const articleId = Number(btn.dataset.id);
  const article = state.articles.find((item) => item.id === articleId);
  if (!article) return;

  if (action === "edit") {
    fillForm(article);
    openEditModal();
    return;
  }

  if (action === "note") {
    const current = String(article.note || "");
    const raw = prompt("编辑备注（留空表示清空）", current);
    if (raw === null) return;
    await api(`/articles/${article.id}`, {
      method: "PUT",
      body: JSON.stringify({ note: raw.trim() }),
    });
    await fetchArticles();
    return;
  }

  if (action === "del") {
    if (!confirm(`确认删除 ${article.doi} ?`)) return;
    await api(`/articles/${article.id}`, { method: "DELETE" });
    await fetchArticles();
    await loadTags();
    return;
  }

  if (action === "toggle-check") {
    const requested = String(btn.dataset.value || "").trim();
    const current = article.check_status || "unchecked";
    const nextStatus = current === requested ? "unchecked" : requested;
    await api(`/articles/${article.id}`, {
      method: "PUT",
      body: JSON.stringify({ check_status: nextStatus }),
    });
    await fetchArticles();
    return;
  }

  if (action === "tag") {
    const raw = prompt("输入要追加的标签（可逗号分隔）", "");
    if (!raw) return;
    const newTags = parseCSV(raw);
    const oldTags = (article.tags || []).map((tag) => tag.name);
    const merged = Array.from(new Set([...oldTags, ...newTags]));

    await api(`/articles/${article.id}/tags`, {
      method: "PUT",
      body: JSON.stringify({ tags: merged }),
    });
    await fetchArticles();
    await loadTags();
  }
}

async function handleHeaderControlClick(event) {
  const sortBtn = event.target.closest("button[data-sort-by]");
  if (sortBtn) {
    const nextSortBy = String(sortBtn.dataset.sortBy || "").trim();
    if (!nextSortBy) return;
    if (state.sortBy === nextSortBy) {
      state.sortOrder = state.sortOrder === "asc" ? "desc" : "asc";
    } else {
      state.sortBy = nextSortBy;
      state.sortOrder = "asc";
    }
    renderHeaderControls();
    await fetchArticles();
    return;
  }

  const filterBtn = event.target.closest("button[data-check-filter]");
  if (!filterBtn) return;
  const nextFilter = String(filterBtn.dataset.checkFilter || "").trim();
  if (!nextFilter) return;
  state.checkFilter = state.checkFilter === nextFilter ? "all" : nextFilter;
  renderHeaderControls();
  await fetchArticles();
}

function bindEvents() {
  el.runIngest.addEventListener("click", handleIngest);
  el.pauseIngest.addEventListener("click", () => {
    handlePauseIngest().catch((error) => {
      alert(String(error.message || error));
    });
  });
  el.resumeIngest.addEventListener("click", () => {
    handleResumeIngest().catch((error) => {
      alert(String(error.message || error));
    });
  });
  el.cancelIngest.addEventListener("click", () => {
    handleCancelIngest().catch((error) => {
      alert(String(error.message || error));
    });
  });
  el.applyIngestProviders.addEventListener("click", () => {
    handleApplyIngestProviders().catch((error) => {
      alert(String(error.message || error));
    });
  });
  el.viewDroppedPapers.addEventListener("click", () => {
    handleOpenDroppedPapers().catch((error) => {
      alert(String(error.message || error));
    });
  });
  if (el.quickCreate) {
    el.quickCreate.addEventListener("click", () => {
      handleQuickCreate(true).catch((error) => {
        alert(parseApiErrorMessage(error));
        finalizeEnrichmentUI();
      });
    });
  }
  if (el.quickCreateInsertOnly) {
    el.quickCreateInsertOnly.addEventListener("click", () => {
      handleQuickCreate(false).catch((error) => {
        alert(parseApiErrorMessage(error));
        finalizeEnrichmentUI();
      });
    });
  }
  if (el.quickBatchCreate) {
    el.quickBatchCreate.addEventListener("click", () => {
      handleQuickBatchCreate(true).catch((error) => {
        alert(parseApiErrorMessage(error));
        finalizeEnrichmentUI();
      });
    });
  }
  if (el.quickBatchCreateInsertOnly) {
    el.quickBatchCreateInsertOnly.addEventListener("click", () => {
      handleQuickBatchCreate(false).catch((error) => {
        alert(parseApiErrorMessage(error));
        finalizeEnrichmentUI();
      });
    });
  }
  if (el.quickCsvFile) {
    el.quickCsvFile.addEventListener("change", () => {
      handleQuickCsvFilePicked().catch((error) => {
        resetQuickCsvSelection(`CSV 读取失败：${parseApiErrorMessage(error)}`);
      });
    });
  }
  if (el.quickCsvDoiColumn) {
    el.quickCsvDoiColumn.addEventListener("change", () => {
      handleQuickCsvSelectionChanged().catch((error) => {
        alert(parseApiErrorMessage(error));
      });
    });
  }
  if (el.quickBatchTags) {
    el.quickBatchTags.addEventListener("input", () => {
      handleQuickBatchTagsChanged().catch((error) => {
        alert(parseApiErrorMessage(error));
      });
    });
  }
  if (el.quickBatchNote) {
    el.quickBatchNote.addEventListener("input", () => {
      handleQuickBatchNoteChanged().catch((error) => {
        alert(parseApiErrorMessage(error));
      });
    });
  }
  if (el.quickCsvTagColumnChips) {
    el.quickCsvTagColumnChips.addEventListener("click", (event) => {
      handleQuickCsvTagColumnChipClick(event).catch((error) => {
        alert(parseApiErrorMessage(error));
      });
    });
  }
  if (el.quickCsvNoteColumnChips) {
    el.quickCsvNoteColumnChips.addEventListener("click", (event) => {
      handleQuickCsvNoteColumnChipClick(event).catch((error) => {
        alert(parseApiErrorMessage(error));
      });
    });
  }
  if (el.quickCsvDropzone) {
    el.quickCsvDropzone.addEventListener("click", () => {
      handleQuickCsvDropzoneClick().catch((error) => {
        alert(parseApiErrorMessage(error));
      });
    });
    el.quickCsvDropzone.addEventListener("keydown", (event) => {
      handleQuickCsvDropzoneKeydown(event).catch((error) => {
        alert(parseApiErrorMessage(error));
      });
    });
    el.quickCsvDropzone.addEventListener("dragover", (event) => {
      handleQuickCsvDropzoneDragOver(event).catch((error) => {
        alert(parseApiErrorMessage(error));
      });
    });
    el.quickCsvDropzone.addEventListener("dragleave", (event) => {
      handleQuickCsvDropzoneDragLeave(event).catch((error) => {
        alert(parseApiErrorMessage(error));
      });
    });
    el.quickCsvDropzone.addEventListener("drop", (event) => {
      handleQuickCsvDropzoneDrop(event).catch((error) => {
        alert(parseApiErrorMessage(error));
        resetQuickCsvSelection(`CSV 读取失败：${parseApiErrorMessage(error)}`);
      });
    });
  }
  if (el.toggleAutoEnrichment) {
    el.toggleAutoEnrichment.addEventListener("click", () => {
      handleToggleAutoEnrichment().catch((error) => {
        alert(String(error.message || error));
      });
    });
  }
  el.queryFilterMode.addEventListener("change", syncQueryFilterControls);
  el.saveArticle.addEventListener("click", handleSaveArticle);
  el.resetForm.addEventListener("click", () => {
    const article = state.articles.find((item) => item.id === Number(el.editId.value));
    if (article) {
      fillForm(article);
      return;
    }
    resetForm();
  });
  el.closeEditModal.addEventListener("click", closeEditModal);
  el.editModalBackdrop.addEventListener("click", closeEditModal);
  el.closeDropCacheModal.addEventListener("click", closeDropCacheModal);
  el.dropCacheModalBackdrop.addEventListener("click", closeDropCacheModal);
  el.refreshDropCache.addEventListener("click", () => {
    fetchDroppedDecisions().catch((error) => {
      alert(String(error.message || error));
    });
  });
  el.applyFilter.addEventListener("click", fetchArticles);
  el.tagSearch.addEventListener("input", renderTagFilterChips);
  el.clearFilter.addEventListener("click", () => {
    el.searchText.value = "";
    el.journalFilter.value = "";
    el.tagSearch.value = "";
    state.selectedTagFiltersAnd = new Set();
    state.selectedTagFiltersOr = new Set();
    state.sortBy = "ingested_at";
    state.sortOrder = "desc";
    state.checkFilter = "all";
    renderTagFilterChips();
    setSelectedTagSummary();
    renderHeaderControls();
    fetchArticles();
  });
  el.refreshArticles.addEventListener("click", () => {
    handleRefreshArticles().catch((error) => {
      alert(String(error.message || error));
    });
  });
  el.exportCsv.addEventListener("click", handleExportCsv);
  el.articleTableHead.addEventListener("click", (event) => {
    handleHeaderControlClick(event).catch((error) => {
      alert(String(error.message || error));
    });
  });
  el.mobileTableTools.addEventListener("click", (event) => {
    handleHeaderControlClick(event).catch((error) => {
      alert(String(error.message || error));
    });
  });

  el.articleTableBody.addEventListener("click", (event) => {
    handleTableClick(event).catch((error) => {
      alert(String(error.message || error));
    });
  });
  el.articleCardList.addEventListener("click", (event) => {
    handleTableClick(event).catch((error) => {
      alert(String(error.message || error));
    });
  });
  el.tagFilterAndChips.addEventListener("click", (event) => {
    handleTableClick(event).catch((error) => {
      alert(String(error.message || error));
    });
  });
  el.tagFilterOrChips.addEventListener("click", (event) => {
    handleTableClick(event).catch((error) => {
      alert(String(error.message || error));
    });
  });
  el.dropCacheList.addEventListener("click", (event) => {
    handleDropCacheClick(event).catch((error) => {
      alert(String(error.message || error));
    });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !el.editModal.classList.contains("hidden")) {
      closeEditModal();
      return;
    }
    if (event.key === "Escape" && !el.dropCacheModal.classList.contains("hidden")) {
      closeDropCacheModal();
    }
  });
}

async function init() {
  bindEvents();
  resetQuickCsvSelection();
  syncQueryFilterControls();
  syncIngestActionButtons();
  syncAutoEnrichmentToggleUI();
  setIngestStatus("当前空闲");
  setEnrichmentStatus("后台自动补全初始化中...");
  await loadProviders();
  await loadTags();
  setSelectedTagSummary();
  renderHeaderControls();
  await fetchArticles();
  pollAutoEnrichmentStatus();
}

init().catch((error) => {
  el.ingestResult.textContent = String(error.message || error);
});
