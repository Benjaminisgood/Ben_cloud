import {
  apiBase,
  apiFetch,
  bookHref,
  escapeHtml,
  getBookIdFromPath,
  getPageIdFromPath,
  handleError,
  kindLabel,
  loadBookContext,
  loadCurrentUser,
  outlineHref,
  primeDocumentCrumb,
  previewHref,
  publishHref,
  renderDocumentCrumb,
  renderOutlineList,
  setStatus,
  toast,
} from "/app/core.js";

const bookId = getBookIdFromPath();
const pageId = getPageIdFromPath();
const INLINE_TAG_RE = /(^|[^0-9A-Za-z_\-/\u4e00-\u9fff])#([0-9A-Za-z\u4e00-\u9fff][0-9A-Za-z_\-/\u4e00-\u9fff]{0,39})/g;

const state = {
  currentDocument: null,
  currentTree: [],
  currentPage: null,
  currentLock: null,
  currentUser: null,
  dragDepth: 0,
  referenceIndex: null,
  referenceCache: new Map(),
  activeTag: "",
  autocomplete: {
    visible: false,
    options: [],
    activeIndex: 0,
    context: null,
    groups: [],
  },
};

const els = {
  pageTitleHeading: document.getElementById("pageTitleHeading"),
  pageMetaHeading: document.getElementById("pageMetaHeading"),
  pageCrumbTitle: document.getElementById("pageCrumbTitle"),
  tabSettingsLink: document.getElementById("tabSettingsLink"),
  tabOutlineLink: document.getElementById("tabOutlineLink"),
  tabEditorLink: document.getElementById("tabEditorLink"),
  tabPreviewLink: document.getElementById("tabPreviewLink"),
  tabPublishLink: document.getElementById("tabPublishLink"),
  bookTitleLabel: document.getElementById("bookTitleLabel"),
  outlineTree: document.getElementById("outlineTree"),
  pageTagsPanel: document.getElementById("pageTagsPanel"),
  backlinksPanel: document.getElementById("backlinksPanel"),
  lockToggleBtn: document.getElementById("lockToggleBtn"),
  insertAssetBtn: document.getElementById("insertAssetBtn"),
  savePageBtn: document.getElementById("savePageBtn"),
  lockExplanation: document.getElementById("lockExplanation"),
  pageTitleInput: document.getElementById("pageTitleInput"),
  pageSlugInput: document.getElementById("pageSlugInput"),
  changeNoteInput: document.getElementById("changeNoteInput"),
  pageContentInput: document.getElementById("pageContentInput"),
  referenceAutocomplete: document.getElementById("referenceAutocomplete"),
  editorDropZone: document.getElementById("editorDropZone"),
  assetFileInput: document.getElementById("assetFileInput"),
};

function setText(el, value) {
  if (el) {
    el.textContent = value;
  }
}

function escapeRegExp(value) {
  return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function currentPreviewHref() {
  return previewHref(bookId, pageId);
}

function replaceSelectionWithText(text, options = {}) {
  const textarea = els.pageContentInput;
  const start = options.start ?? textarea.selectionStart ?? textarea.value.length;
  const end = options.end ?? textarea.selectionEnd ?? textarea.value.length;
  const before = textarea.value.slice(0, start);
  const after = textarea.value.slice(end);
  const padBefore = before && !before.endsWith("\n") ? "\n" : "";
  const padAfter = after && !after.startsWith("\n") ? "\n" : "";
  textarea.value = `${before}${padBefore}${text}${padAfter}${after}`;
  const insertedStart = before.length + padBefore.length;
  const insertedEnd = insertedStart + text.length;
  const cursor = insertedEnd;
  if (options.focus !== false) {
    textarea.focus();
  }
  if (options.moveCursor !== false) {
    textarea.setSelectionRange(cursor, cursor);
  }
  return { start: insertedStart, end: insertedEnd };
}

function insertTextAtCursor(text) {
  return replaceSelectionWithText(text);
}

function buildUploadPlaceholder(file) {
  const uploadId = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const label = encodeURIComponent(file.name || "clipboard-image");
  return {
    id: uploadId,
    token: `[[benfast-upload|${uploadId}|${label}]]`,
    filename: file.name || "clipboard-image",
  };
}

function replaceMarkerText(marker, replacement) {
  const textarea = els.pageContentInput;
  const index = textarea.value.indexOf(marker);
  if (index === -1) {
    return false;
  }

  const end = index + marker.length;
  const before = textarea.value.slice(0, index);
  const after = textarea.value.slice(end);
  const selectionStart = textarea.selectionStart ?? textarea.value.length;
  const selectionEnd = textarea.selectionEnd ?? textarea.value.length;
  textarea.value = `${before}${replacement}${after}`;

  const delta = replacement.length - marker.length;
  const adjust = (position) => {
    if (position <= index) {
      return position;
    }
    if (position <= end) {
      return index + replacement.length;
    }
    return position + delta;
  };

  textarea.setSelectionRange(adjust(selectionStart), adjust(selectionEnd));
  return true;
}

function hasDraggedFiles(event) {
  return Array.from(event.dataTransfer?.types || []).includes("Files");
}

function clipboardFilesFromEvent(event) {
  return Array.from(event.clipboardData?.items || [])
    .filter((item) => item.kind === "file")
    .map((item) => item.getAsFile())
    .filter(Boolean);
}

function setDropActive(active) {
  els.editorDropZone.classList.toggle("is-dragover", active);
}

function setEditable(enabled) {
  const disabled = !enabled;
  els.pageTitleInput.readOnly = disabled;
  els.pageSlugInput.readOnly = disabled;
  els.changeNoteInput.readOnly = disabled;
  els.pageContentInput.readOnly = disabled;
  els.insertAssetBtn.disabled = disabled;
  els.savePageBtn.disabled = disabled;
}

function renderDocument(doc) {
  state.currentDocument = doc;
  renderDocumentCrumb(doc.id, doc.title);
  setText(els.bookTitleLabel, doc.title);
  els.tabSettingsLink.href = bookHref(doc.id);
  els.tabOutlineLink.href = outlineHref(doc.id);
  els.tabEditorLink.href = window.location.pathname;
  els.tabPreviewLink.href = currentPreviewHref();
  els.tabPublishLink.href = publishHref(doc.id);
}

function renderTree(tree) {
  state.currentTree = tree;
  renderOutlineList(els.outlineTree, tree, {
    activeBookId: state.currentDocument.id,
    activePageId: state.currentPage?.id || null,
  });
}

function extractInlineTags(content) {
  const tags = [];
  const seen = new Set();
  const lines = String(content || "").split("\n");
  let inCode = false;

  for (const rawLine of lines) {
    const stripped = rawLine.trim();
    if (stripped.startsWith("```")) {
      inCode = !inCode;
      continue;
    }
    if (inCode || !stripped || /^#{1,6}\s/.test(stripped)) {
      continue;
    }
    const line = rawLine.replace(/\[\[[^\[\]]+\]\]/g, "");
    INLINE_TAG_RE.lastIndex = 0;
    for (const match of line.matchAll(INLINE_TAG_RE)) {
      const tag = String(match[2] || "").trim();
      if (tag && !seen.has(tag)) {
        seen.add(tag);
        tags.push(tag);
      }
    }
  }
  return tags;
}

function renderTagCards() {
  const localTags = extractInlineTags(els.pageContentInput.value);
  const tagEntries = Array.isArray(state.referenceIndex?.tags) ? state.referenceIndex.tags : [];
  const entryByTag = new Map(tagEntries.map((item) => [String(item.tag), item]));
  const activeTag = localTags.includes(state.activeTag) ? state.activeTag : localTags[0] || "";
  state.activeTag = activeTag;

  if (!localTags.length) {
    els.pageTagsPanel.innerHTML = '<p class="empty-inline">当前页还没有写入任何 <code>#标签</code>。</p>';
    return;
  }

  const chips = localTags
    .map((tag) => {
      const entry = entryByTag.get(tag);
      const isActive = tag === activeTag;
      return `
        <button class="tag-chip-button${isActive ? " is-active" : ""}" type="button" data-tag="${escapeHtml(tag)}">
          #${escapeHtml(tag)}${entry ? ` · ${entry.count}` : ""}
        </button>
      `;
    })
    .join("");

  const activeEntry = entryByTag.get(activeTag);
  const activeList = activeEntry?.entries?.length
    ? `
      <div class="mini-list">
        ${activeEntry.entries
          .map(
            (item) => `
              <a href="${previewHref(bookId, item.page_id)}">
                <strong>${escapeHtml(item.page_title)}</strong>
                <small>${escapeHtml(item.page_path || "/")}</small>
              </a>
            `,
          )
          .join("")}
      </div>
    `
    : '<p class="empty-inline">这个标签尚未出现在已保存页中。保存后会进入反向引用索引。</p>';

  els.pageTagsPanel.innerHTML = `
    <div class="tag-card">
      <div class="tag-chip-row">${chips}</div>
      <div>
        <strong>${activeTag ? `#${escapeHtml(activeTag)}` : "页内标签"}</strong>
        <small>${activeEntry ? `已在 ${activeEntry.count} 个页面中出现` : "当前只存在于本地草稿中"}</small>
      </div>
      ${activeList}
    </div>
  `;
}

function renderBacklinksPanel() {
  if (state.activeTag) {
    const tagEntry = (state.referenceIndex?.tags || []).find((item) => item.tag === state.activeTag);
    if (!tagEntry) {
      els.backlinksPanel.innerHTML = '<p class="empty-inline">保存后即可查看这个标签的反向引用。</p>';
      return;
    }
    els.backlinksPanel.innerHTML = `
      <div class="backlink-card">
        <strong>标签 #${escapeHtml(tagEntry.tag)}</strong>
        <small>这些页面写入了同一个标签。</small>
        <div class="mini-list">
          ${tagEntry.entries
            .map(
              (item) => `
                <a href="${previewHref(bookId, item.page_id)}">
                  <strong>${escapeHtml(item.page_title)}</strong>
                  <small>${escapeHtml(item.page_path || "/")}</small>
                </a>
              `,
            )
            .join("")}
        </div>
      </div>
    `;
    return;
  }

  const incoming = state.referenceIndex?.references?.incoming || [];
  if (!incoming.length) {
    els.backlinksPanel.innerHTML = '<p class="empty-inline">当前还没有其他页面引用这一页。</p>';
    return;
  }

  els.backlinksPanel.innerHTML = incoming
    .map(
      (item) => `
        <div class="backlink-card">
          <strong>${escapeHtml(item.source_page_title)}</strong>
          <small>${escapeHtml(item.heading ? `引用到标题 ${item.heading}` : "引用了当前页面")}</small>
          <a class="inline-link" href="${previewHref(bookId, item.source_page_id)}">打开来源页面</a>
        </div>
      `,
    )
    .join("");
}

function renderPage(page) {
  state.currentPage = page;
  document.title = `${page.title} | Benfast 文档写作`;
  setText(els.pageTitleHeading, page.title);
  setText(els.pageCrumbTitle, page.title);
  setText(
    els.pageMetaHeading,
    `${kindLabel(page)} · path=${page.path || "/"} · version=${page.version} · updated_at=${page.updated_at || "-"}`,
  );
  els.pageTitleInput.value = page.title || "";
  els.pageSlugInput.value = page.slug || "";
  els.changeNoteInput.value = "";
  els.pageContentInput.value = page.content || "";
  renderTagCards();
}

function renderLock(lock) {
  state.currentLock = lock || null;
  const currentUserId = Number(state.currentUser?.id || 0);
  const holderId = Number(lock?.holder_id || 0);
  const lockedBySelf = Boolean(lock) && holderId === currentUserId;

  if (!lock) {
    els.lockToggleBtn.disabled = false;
    els.lockToggleBtn.textContent = "开始编辑";
    els.lockToggleBtn.className = "secondary";
    els.lockExplanation.textContent = "开始编辑会为当前页面占用 15 分钟，避免多人同时覆盖正文。完成后请及时结束编辑。";
    setEditable(true);
    return;
  }

  if (lockedBySelf) {
    els.lockToggleBtn.disabled = false;
    els.lockToggleBtn.textContent = "结束编辑";
    els.lockToggleBtn.className = "danger";
    els.lockExplanation.textContent = `当前由你占用编辑席位，锁定到 ${lock.expires_at}。在此期间建议只由你提交本页正文。`;
    setEditable(true);
    return;
  }

  els.lockToggleBtn.disabled = true;
  els.lockToggleBtn.textContent = `由 ${lock.holder_name} 编辑中`;
  els.lockToggleBtn.className = "secondary";
  els.lockExplanation.textContent = `当前由 ${lock.holder_name} 在编辑此页，锁定到 ${lock.expires_at}。你仍可阅读，但不应继续覆盖提交。`;
  setEditable(false);
}

async function loadReferenceIndex(query = "") {
  const normalized = String(query || "").trim();
  const cacheKey = normalized.toLowerCase();
  if (state.referenceCache.has(cacheKey)) {
    return state.referenceCache.get(cacheKey);
  }
  const params = new URLSearchParams({ page_id: pageId });
  if (normalized) {
    params.set("q", normalized);
  }
  const data = await apiFetch(`${apiBase}/books/${bookId}/references?${params.toString()}`);
  state.referenceCache.set(cacheKey, data);
  if (!normalized) {
    state.referenceIndex = data;
    renderTagCards();
    renderBacklinksPanel();
  }
  return data;
}

function resetReferenceCache() {
  state.referenceCache = new Map();
}

function getAutocompleteContext() {
  const value = els.pageContentInput.value;
  const caret = els.pageContentInput.selectionStart ?? value.length;
  const beforeCaret = value.slice(0, caret);
  const openIndex = beforeCaret.lastIndexOf("[[");
  const lineStart = beforeCaret.lastIndexOf("\n") + 1;
  const lineBeforeCaret = beforeCaret.slice(lineStart);
  const hashMatch = lineBeforeCaret.match(/(?:^|\s)#([0-9A-Za-z\u4e00-\u9fff_\-/]{0,39})$/);

  if (openIndex === -1 && !hashMatch) {
    return null;
  }
  if (openIndex !== -1) {
    const lastClose = beforeCaret.lastIndexOf("]]");
    if (lastClose > openIndex) {
      return null;
    }
    const token = beforeCaret.slice(openIndex + 2);
    if (token.includes("\n")) {
      return null;
    }
    const end = value.slice(caret, caret + 2) === "]]" ? caret + 2 : caret;
    return {
      mode: "reference",
      start: openIndex + 2,
      end,
      token,
      caret,
    };
  }

  const tagText = hashMatch?.[1] || "";
  const triggerStart = caret - tagText.length - 1;
  return {
    mode: "tag",
    start: triggerStart,
    end: caret,
    token: tagText,
    caret,
  };
}

function matchText(haystack, query) {
  return String(haystack || "").toLowerCase().includes(String(query || "").toLowerCase());
}

function highlightMatch(text, query) {
  const source = String(text || "");
  const needle = String(query || "").trim();
  if (!needle) {
    return escapeHtml(source);
  }
  const pattern = new RegExp(`(${escapeRegExp(needle)})`, "ig");
  return escapeHtml(source).replace(pattern, "<mark>$1</mark>");
}

function buildSuggestionGroups(index, context) {
  const raw = String(context.token || "").trim();
  const pages = Array.isArray(index?.pages) ? index.pages : [];
  const tags = Array.isArray(index?.tags) ? index.tags : [];
  const currentPageId = String(index?.current_page_id || "");

  const groups = [];
  const pushGroup = (label, items) => {
    if (items.length) {
      groups.push({ label, items: items.slice(0, 8) });
    }
  };

  if (context.mode === "tag") {
    pushGroup(
      "标签",
      tags
        .filter((item) => !raw || matchText(item.tag, raw))
        .map((item) => ({
          token: `#${item.tag}`,
          title: `#${item.tag}`,
          detail: `${item.count} 个页面`,
          match: raw,
        })),
    );
    return groups;
  }

  if (raw.startsWith("标签:") || raw.toLowerCase().startsWith("tag:")) {
    const query = raw.split(":", 2)[1]?.trim() || "";
    pushGroup(
      "标签",
      tags
        .filter((item) => !query || matchText(item.tag, query))
        .map((item) => ({
          token: `标签:${item.tag}`,
          title: `#${item.tag}`,
          detail: `${item.count} 个页面`,
          match: query,
        })),
    );
    return groups;
  }

  if (raw.startsWith("#")) {
    const query = raw.slice(1).trim();
    const current = pages.find((item) => String(item.id) === currentPageId);
    pushGroup(
      "当前页标题",
      (current?.headings || [])
        .filter((item) => !query || matchText(item.title, query))
        .map((item) => ({
          token: `#${item.title}`,
          title: item.title,
          detail: "当前页锚点",
          match: query,
        })),
    );
    return groups;
  }

  const [pageQueryRaw, headingQueryRaw = ""] = raw.split("#", 2);
  const pageQuery = pageQueryRaw.trim();
  const headingQuery = headingQueryRaw.trim();

  if (raw.includes("#")) {
    const matchedPages = pages.filter((item) => {
      if (!pageQuery) {
        return String(item.id) === currentPageId;
      }
      return [item.title, item.slug, item.path, item.token].some((field) => matchText(field, pageQuery));
    });
    pushGroup(
      "标题",
      matchedPages.flatMap((item) =>
        (item.headings || [])
          .filter((heading) => !headingQuery || matchText(heading.title, headingQuery))
          .map((heading) => ({
            token: `${item.token}#${heading.title}`,
            title: `${item.title} / ${heading.title}`,
            detail: item.path || "/",
          })),
      ),
    );
    return groups;
  }

  pushGroup(
    "页面",
    pages
      .filter((item) => !pageQuery || [item.title, item.slug, item.path, item.token].some((field) => matchText(field, pageQuery)))
      .map((item) => ({
        token: item.token,
        title: item.title,
        detail: item.path || "/",
        match: pageQuery,
      })),
  );

  pushGroup(
    "常用标题",
    pages.flatMap((item) =>
      (item.headings || [])
        .filter((heading) => !pageQuery || [item.title, item.path, heading.title].some((field) => matchText(field, pageQuery)))
        .map((heading) => ({
          token: `${item.token}#${heading.title}`,
          title: `${item.title} / ${heading.title}`,
          detail: item.path || "/",
          match: pageQuery,
        })),
    ),
  );

  pushGroup(
    "标签",
    tags
      .filter((item) => !pageQuery || matchText(item.tag, pageQuery))
      .map((item) => ({
        token: `标签:${item.tag}`,
        title: `#${item.tag}`,
        detail: `${item.count} 个页面`,
        match: pageQuery,
      })),
  );

  return groups;
}

function flattenSuggestionGroups(groups) {
  return groups.flatMap((group) => group.items);
}

function hideAutocomplete() {
  state.autocomplete.visible = false;
  state.autocomplete.options = [];
  state.autocomplete.activeIndex = 0;
  state.autocomplete.context = null;
  state.autocomplete.groups = [];
  els.referenceAutocomplete.classList.add("is-hidden");
  els.referenceAutocomplete.innerHTML = "";
}

function getCaretCoordinates(textarea, position) {
  const mirror = document.createElement("div");
  const style = window.getComputedStyle(textarea);
  const properties = [
    "boxSizing",
    "width",
    "height",
    "overflowX",
    "overflowY",
    "borderTopWidth",
    "borderRightWidth",
    "borderBottomWidth",
    "borderLeftWidth",
    "paddingTop",
    "paddingRight",
    "paddingBottom",
    "paddingLeft",
    "fontStyle",
    "fontVariant",
    "fontWeight",
    "fontStretch",
    "fontSize",
    "fontSizeAdjust",
    "lineHeight",
    "fontFamily",
    "textAlign",
    "textTransform",
    "textIndent",
    "textDecoration",
    "letterSpacing",
    "wordSpacing",
    "tabSize",
    "MozTabSize",
    "whiteSpace",
    "wordWrap",
  ];
  mirror.style.position = "absolute";
  mirror.style.visibility = "hidden";
  mirror.style.whiteSpace = "pre-wrap";
  mirror.style.wordWrap = "break-word";
  properties.forEach((prop) => {
    mirror.style[prop] = style[prop];
  });

  mirror.textContent = textarea.value.slice(0, position);
  const span = document.createElement("span");
  span.textContent = textarea.value.slice(position) || ".";
  mirror.appendChild(span);
  document.body.appendChild(mirror);

  const rect = textarea.getBoundingClientRect();
  const top = span.offsetTop - textarea.scrollTop + rect.top;
  const left = span.offsetLeft - textarea.scrollLeft + rect.left;
  const height = parseFloat(style.lineHeight || "20");
  document.body.removeChild(mirror);
  return { top, left, height };
}

function positionAutocomplete() {
  const context = state.autocomplete.context;
  if (!context || !state.autocomplete.visible) {
    return;
  }
  const coords = getCaretCoordinates(els.pageContentInput, context.caret);
  const shellRect = els.editorDropZone.getBoundingClientRect();
  const top = Math.max(16, coords.top - shellRect.top + coords.height + 8);
  const left = Math.max(16, Math.min(coords.left - shellRect.left, shellRect.width - 320));
  els.referenceAutocomplete.style.top = `${top}px`;
  els.referenceAutocomplete.style.left = `${left}px`;
}

function renderAutocomplete(groups) {
  const options = flattenSuggestionGroups(groups);
  state.autocomplete.visible = options.length > 0;
  state.autocomplete.options = options;
  state.autocomplete.groups = groups;
  state.autocomplete.activeIndex = Math.min(state.autocomplete.activeIndex, Math.max(0, options.length - 1));
  if (!options.length) {
    hideAutocomplete();
    return;
  }

  let globalIndex = 0;
  els.referenceAutocomplete.innerHTML = groups
    .map((group) => {
      const items = group.items
        .map((item) => {
          const isActive = globalIndex === state.autocomplete.activeIndex;
          const html = `
            <button class="reference-option${isActive ? " is-active" : ""}" type="button" data-index="${globalIndex}">
              <strong>${highlightMatch(item.title, item.match)}</strong>
              <span>${highlightMatch(item.token, item.match)}</span>
              <small>${highlightMatch(item.detail, item.match)}</small>
            </button>
          `;
          globalIndex += 1;
          return html;
        })
        .join("");
      return `<section class="reference-autocomplete__section"><div class="reference-autocomplete__label">${escapeHtml(group.label)}</div>${items}</section>`;
    })
    .join("");
  els.referenceAutocomplete.classList.remove("is-hidden");
  positionAutocomplete();
}

async function updateAutocomplete() {
  const context = getAutocompleteContext();
  state.autocomplete.context = context;
  if (!context) {
    hideAutocomplete();
    return;
  }
  const index = await loadReferenceIndex(context.token);
  const groups = buildSuggestionGroups(index, context);
  renderAutocomplete(groups);
}

function applyAutocompleteSelection(index) {
  const option = state.autocomplete.options[index];
  const context = state.autocomplete.context;
  if (!option || !context) {
    return;
  }
  const before = els.pageContentInput.value.slice(0, context.start);
  const after = els.pageContentInput.value.slice(context.end);
  const inserted = context.mode === "tag" ? option.token : `${option.token}]]`;
  els.pageContentInput.value = `${before}${inserted}${after}`;
  const cursor = context.start + inserted.length;
  els.pageContentInput.focus();
  els.pageContentInput.setSelectionRange(cursor, cursor);
  hideAutocomplete();
  renderTagCards();
  renderBacklinksPanel();
}

async function refresh() {
  const [{ book, tree }, page, lock] = await Promise.all([
    loadBookContext(bookId),
    apiFetch(`${apiBase}/pages/${pageId}`),
    apiFetch(`${apiBase}/pages/${pageId}/lock`),
  ]);
  resetReferenceCache();
  renderDocument(book);
  renderPage(page);
  renderTree(tree);
  renderLock(lock);
  await loadReferenceIndex();
  if (lock && Number(lock.holder_id || 0) !== Number(state.currentUser?.id || 0)) {
    setStatus(`当前页面由 ${lock.holder_name} 占用编辑席位。`, "neutral");
  } else {
    setStatus("写作页已就绪。", "success");
  }
}

async function savePage() {
  const updated = await apiFetch(`${apiBase}/pages/${pageId}`, {
    method: "PUT",
    body: JSON.stringify({
      expected_version: state.currentPage.version,
      title: els.pageTitleInput.value.trim(),
      slug: els.pageSlugInput.value.trim(),
      content: els.pageContentInput.value,
      change_note: els.changeNoteInput.value.trim(),
    }),
  });
  toast("正文保存成功");
  state.currentPage = updated;
  renderPage(updated);
  resetReferenceCache();
  await loadReferenceIndex();
  setStatus("页面内容已保存。", "success");
}

async function startEditing() {
  const lock = await apiFetch(`${apiBase}/pages/${pageId}/lock/acquire`, {
    method: "POST",
    body: JSON.stringify({ ttl_minutes: 15 }),
  });
  renderLock(lock);
  toast(`已开始编辑：${lock.holder_name}`);
  setStatus("当前页面已由你占用 15 分钟。", "success");
}

async function stopEditing() {
  const released = await apiFetch(`${apiBase}/pages/${pageId}/lock/release`, { method: "POST" });
  renderLock(null);
  toast(released.released ? "已结束编辑" : "当前没有需要释放的编辑占用");
  setStatus("当前页面已释放，可由其他成员继续编辑。", "success");
}

async function toggleLock() {
  const currentUserId = Number(state.currentUser?.id || 0);
  const holderId = Number(state.currentLock?.holder_id || 0);
  if (state.currentLock && holderId === currentUserId) {
    await stopEditing();
    return;
  }
  await startEditing();
}

async function uploadAssetFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch(`${apiBase}/books/${bookId}/assets`, {
    method: "POST",
    body: formData,
  });
}

function insertUploadPlaceholders(files) {
  const placeholders = files.map((file) => buildUploadPlaceholder(file));
  replaceSelectionWithText(placeholders.map((item) => item.token).join("\n\n"));
  return placeholders;
}

async function uploadAssetBatch(files, { preservePosition = true } = {}) {
  if (!files.length) {
    throw new Error("请先选择至少一个文件。");
  }

  const placeholders = preservePosition ? insertUploadPlaceholders(files) : [];
  const uploaded = [];
  const failed = [];
  const unresolved = [];
  setStatus(`正在上传 ${files.length} 个附件...`, "neutral");

  for (const [index, file] of files.entries()) {
    try {
      const asset = await uploadAssetFile(file);
      uploaded.push(asset);
      if (preservePosition) {
        const replaced = replaceMarkerText(placeholders[index].token, asset.markdown);
        if (!replaced) {
          unresolved.push(placeholders[index].filename);
        }
      } else {
        insertTextAtCursor(asset.markdown);
      }
    } catch (error) {
      failed.push({ file, error });
      if (preservePosition) {
        replaceMarkerText(placeholders[index].token, `> 图片上传失败：${placeholders[index].filename}`);
      }
    }
  }

  els.assetFileInput.value = "";

  if (failed.length) {
    const message = `${uploaded.length} 个附件已上传，${failed.length} 个失败。`;
    toast(message, true);
    setStatus(message, "error");
    return;
  }

  if (unresolved.length) {
    const message = `${uploaded.length} 个附件已上传，但有 ${unresolved.length} 个未能回填到原始位置。`;
    toast(message, true);
    setStatus(message, "error");
    return;
  }

  toast(uploaded.length === 1 ? "附件已上传" : `${uploaded.length} 个附件已上传`);
  setStatus("附件已上传，并回填到原始插入位置。", "success");
}

async function uploadSelectedAssets() {
  const files = Array.from(els.assetFileInput.files || []);
  await uploadAssetBatch(files, { preservePosition: true });
}

async function handleClipboardPaste(event) {
  const files = clipboardFilesFromEvent(event);
  if (!files.length) {
    return;
  }
  event.preventDefault();
  await uploadAssetBatch(files, { preservePosition: true });
}

async function handleDrop(event) {
  event.preventDefault();
  state.dragDepth = 0;
  setDropActive(false);
  const files = Array.from(event.dataTransfer?.files || []);
  if (files.length) {
    await uploadAssetBatch(files, { preservePosition: true });
  }
}

function bindEvents() {
  els.lockToggleBtn.addEventListener("click", async () => {
    els.lockToggleBtn.disabled = true;
    const originalLabel = els.lockToggleBtn.textContent;
    els.lockToggleBtn.textContent = "处理中...";
    try {
      await toggleLock();
    } catch (error) {
      els.lockToggleBtn.textContent = originalLabel;
      handleError(error);
    }
  });

  els.savePageBtn.addEventListener("click", async () => {
    els.savePageBtn.disabled = true;
    els.savePageBtn.textContent = "保存中...";
    try {
      await savePage();
    } catch (error) {
      handleError(error);
    } finally {
      els.savePageBtn.disabled = false;
      els.savePageBtn.textContent = "保存正文";
    }
  });

  els.insertAssetBtn.addEventListener("click", () => {
    els.assetFileInput.click();
  });

  els.assetFileInput.addEventListener("change", () => {
    const original = els.insertAssetBtn.textContent;
    els.insertAssetBtn.disabled = true;
    els.insertAssetBtn.textContent = "上传中...";
    uploadSelectedAssets()
      .catch(handleError)
      .finally(() => {
        els.insertAssetBtn.disabled = false;
        els.insertAssetBtn.textContent = original;
      });
  });

  els.pageContentInput.addEventListener("paste", (event) => {
    if (!clipboardFilesFromEvent(event).length) {
      return;
    }
    const original = els.insertAssetBtn.textContent;
    els.insertAssetBtn.disabled = true;
    els.insertAssetBtn.textContent = "上传中...";
    handleClipboardPaste(event)
      .catch(handleError)
      .finally(() => {
        els.insertAssetBtn.disabled = false;
        els.insertAssetBtn.textContent = original;
      });
  });

  els.pageContentInput.addEventListener("input", () => {
    renderTagCards();
    renderBacklinksPanel();
    updateAutocomplete().catch(handleError);
  });
  els.pageContentInput.addEventListener("click", () => {
    updateAutocomplete().catch(handleError);
  });
  els.pageContentInput.addEventListener("scroll", () => {
    positionAutocomplete();
  });

  els.pageContentInput.addEventListener("keydown", (event) => {
    if (!state.autocomplete.visible) {
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      state.autocomplete.activeIndex = (state.autocomplete.activeIndex + 1) % state.autocomplete.options.length;
      renderAutocomplete(state.autocomplete.groups);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      state.autocomplete.activeIndex =
        (state.autocomplete.activeIndex - 1 + state.autocomplete.options.length) % state.autocomplete.options.length;
      renderAutocomplete(state.autocomplete.groups);
      return;
    }
    if (event.key === "Enter" || event.key === "Tab") {
      event.preventDefault();
      applyAutocompleteSelection(state.autocomplete.activeIndex);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      hideAutocomplete();
    }
  });

  els.referenceAutocomplete.addEventListener("mousedown", (event) => {
    const button = event.target.closest(".reference-option");
    if (!button) {
      return;
    }
    event.preventDefault();
    applyAutocompleteSelection(Number(button.dataset.index || 0));
  });

  els.pageTagsPanel.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tag]");
    if (!button) {
      return;
    }
    state.activeTag = String(button.dataset.tag || "");
    renderTagCards();
    renderBacklinksPanel();
  });

  document.addEventListener("click", (event) => {
    if (event.target === els.pageContentInput || els.referenceAutocomplete.contains(event.target)) {
      return;
    }
    hideAutocomplete();
  });
  window.addEventListener("resize", () => {
    positionAutocomplete();
  });

  els.editorDropZone.addEventListener("dragenter", (event) => {
    if (!hasDraggedFiles(event)) {
      return;
    }
    event.preventDefault();
    state.dragDepth += 1;
    setDropActive(true);
  });

  els.editorDropZone.addEventListener("dragover", (event) => {
    if (!hasDraggedFiles(event)) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    setDropActive(true);
  });

  els.editorDropZone.addEventListener("dragleave", (event) => {
    event.preventDefault();
    state.dragDepth = Math.max(0, state.dragDepth - 1);
    if (state.dragDepth === 0) {
      setDropActive(false);
    }
  });

  els.editorDropZone.addEventListener("drop", (event) => {
    const original = els.insertAssetBtn.textContent;
    els.insertAssetBtn.disabled = true;
    els.insertAssetBtn.textContent = "上传中...";
    handleDrop(event)
      .catch(handleError)
      .finally(() => {
        els.insertAssetBtn.disabled = false;
        els.insertAssetBtn.textContent = original;
      });
  });
}

async function init() {
  if (!bookId || !pageId) {
    throw new Error("缺少文档或页面 ID。");
  }
  primeDocumentCrumb(bookId);
  setStatus("正在载入写作页...", "neutral");
  state.currentUser = await loadCurrentUser();
  bindEvents();
  await refresh();
}

init().catch(handleError);
