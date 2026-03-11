const DRAFT_PREFIX = "benben:draft:";
const VIEW_NAMES = ["template", "write", "document", "slides"];
const FILE_SWITCHER_NONE = "__none__";
const TEMPLATE_SWITCHER_NONE = "__none_template__";
const FILE_SWITCHER_NEW = "__new__";
const TEMPLATE_SWITCHER_NEW = "__new_template__";
const TEMPLATE_PREFIX = "templates/";

const SLASH_COMMANDS = [
    {
        id: "assets",
        label: "/assets",
        aliases: ["asset", "image", "img", "essets"],
        description: "插入资源或上传图片",
        kind: "asset",
    },
    {
        id: "slide",
        label: "/slide",
        aliases: ["page", "split"],
        description: "插入分页符 ---",
        kind: "insert",
        snippet: "---\n\n",
    },
    {
        id: "heading",
        label: "/heading",
        aliases: ["section", "title"],
        description: "插入小节标题和要点",
        kind: "insert",
        snippet: "## 小节标题\n\n- 要点 1\n- 要点 2\n",
    },
    {
        id: "summary",
        label: "/summary",
        aliases: ["result", "conclusion"],
        description: "插入结论块",
        kind: "insert",
        snippet: "> 核心结论：\n> \n",
    },
    {
        id: "checklist",
        label: "/checklist",
        aliases: ["todo", "tasks", "check"],
        description: "插入待办清单",
        kind: "insert",
        snippet: "- [ ] 待办项 1\n- [ ] 待办项 2\n",
    },
    {
        id: "deck",
        label: "/deck",
        aliases: ["report", "slides"],
        description: "插入汇报骨架",
        kind: "deck",
    },
    {
        id: "template",
        label: "/template",
        aliases: ["tpl", "templates"],
        description: "插入模版内容",
        kind: "template",
    },
];

const state = {
    currentFile: "",
    currentVersion: null,
    currentTemplate: "",
    currentUser: null,
    isDirty: false,
    autoSaveTimer: null,
    remoteSaveTimer: null,
    cachedFiles: [],
    templateFiles: [],
    previewMode: "document",
    slides: [],
    activeSlideIndex: 0,
    overlayOpen: false,
    activeView: "template",
    statusTimer: null,
    slashOpen: false,
    slashRange: null,
    slashMatches: [],
    slashActiveIndex: 0,
    pendingInsertRange: null,
    editorDragDepth: 0,
};

const els = {
    appShell: document.querySelector(".app-shell"),
    writeView: document.getElementById("write-view"),
    documentView: document.getElementById("document-view"),
    slidesView: document.getElementById("slides-view"),
    viewTemplateBtn: document.getElementById("view-template-btn"),
    viewWriteBtn: document.getElementById("view-write-btn"),
    viewDocumentBtn: document.getElementById("view-document-btn"),
    viewSlidesBtn: document.getElementById("view-slides-btn"),
    fileSwitcherField: document.getElementById("file-switcher-field"),
    fileSwitcher: document.getElementById("file-switcher"),
    templateSwitcherField: document.getElementById("template-switcher-field"),
    templateSwitcher: document.getElementById("template-switcher"),
    sessionMeta: document.getElementById("session-meta"),
    autosaveMeta: document.getElementById("autosave-meta"),
    newFilePath: document.getElementById("new-file-path"),
    editor: document.getElementById("editor"),
    editorTitle: document.getElementById("editor-title"),
    versionState: document.getElementById("version-state"),
    draftState: document.getElementById("draft-state"),
    wordCount: document.getElementById("word-count"),
    slideCount: document.getElementById("slide-count"),
    readTime: document.getElementById("read-time"),
    editorFrame: document.getElementById("editor-frame"),
    slashPanel: document.getElementById("slash-panel"),
    slashQuery: document.getElementById("slash-query"),
    slashList: document.getElementById("slash-list"),
    preview: document.getElementById("preview"),
    slideStage: document.getElementById("slide-stage"),
    slideStrip: document.getElementById("slide-strip"),
    exportBtn: document.getElementById("export-btn"),
    imageUpload: document.getElementById("image-upload"),
    assetModal: document.getElementById("asset-modal"),
    assetUrl: document.getElementById("asset-url"),
    assetAlt: document.getElementById("asset-alt"),
    assetInsertBtn: document.getElementById("asset-insert-btn"),
    assetUploadBtn: document.getElementById("asset-upload-btn"),
    assetCancelBtn: document.getElementById("asset-cancel-btn"),
    assetDropzone: document.getElementById("asset-dropzone"),
    templateModal: document.getElementById("template-modal"),
    templateInsertSelect: document.getElementById("template-insert-select"),
    templateInsertBtn: document.getElementById("template-insert-btn"),
    templateCancelBtn: document.getElementById("template-cancel-btn"),
    status: document.getElementById("status"),
    presentationOverlay: document.getElementById("presentation-overlay"),
    presentationStage: document.getElementById("presentation-stage"),
    presentationPosition: document.getElementById("presentation-position"),
    presentationCloseBtn: document.getElementById("presentation-close-btn"),
    presentationPrevBtn: document.getElementById("presentation-prev-btn"),
    presentationNextBtn: document.getElementById("presentation-next-btn"),
};

if (window.marked && typeof window.marked.setOptions === "function") {
    window.marked.setOptions({
        breaks: true,
        gfm: true,
    });
}

function normalizeView(view) {
    return VIEW_NAMES.includes(view) ? view : "template";
}

function isTemplateView() {
    return state.activeView === "template";
}

function activeScope() {
    return isTemplateView() ? "template" : "file";
}

function getActivePath() {
    return isTemplateView() ? state.currentTemplate : state.currentFile;
}

function setActivePath(path) {
    if (isTemplateView()) {
        state.currentTemplate = path;
    } else {
        state.currentFile = path;
    }
}

function normalizeTemplatePath(rawPath) {
    const trimmed = String(rawPath || "").trim();
    if (!trimmed) {
        return "";
    }
    const suffix = trimmed.endsWith(".md") ? trimmed : `${trimmed}.md`;
    if (suffix.startsWith(TEMPLATE_PREFIX)) {
        return suffix;
    }
    return `${TEMPLATE_PREFIX}${suffix.replace(/^\/+/, "")}`;
}

function isTemplatePath(path) {
    return String(path || "").startsWith(TEMPLATE_PREFIX);
}

function resolveExportMode() {
    if (state.activeView === "write" || state.activeView === "template") {
        return "md";
    }
    if (state.activeView === "document") {
        return "html";
    }
    if (state.activeView === "slides") {
        return "png";
    }
    return "";
}

function escapeHtml(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function renderMarkdown(markdown) {
    if (window.marked && typeof window.marked.parse === "function") {
        return window.marked.parse(markdown || "");
    }
    return `<pre>${escapeHtml(markdown || "")}</pre>`;
}

function baseName(path) {
    return (path || "").split("/").pop() || "";
}

function draftKey(path, scope) {
    const bucket = scope || "file";
    return `${DRAFT_PREFIX}${bucket}:${path || "__new__"}`;
}

function formatTimeLabel(timestamp) {
    return new Date(timestamp).toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
    });
}

function showStatus(message, type = "success") {
    if (state.statusTimer) {
        clearTimeout(state.statusTimer);
    }

    els.status.textContent = message;
    els.status.className = `status show ${type}`;
    state.statusTimer = window.setTimeout(() => {
        els.status.classList.remove("show");
    }, 2600);
}

function extractErrorDetail(data, fallback) {
    if (!data) {
        return fallback;
    }
    if (typeof data.detail === "string" && data.detail.trim()) {
        return data.detail.trim();
    }
    if (typeof data.message === "string" && data.message.trim()) {
        return data.message.trim();
    }
    return fallback;
}

function setDraftLabel(text) {
    els.draftState.textContent = text;
    els.autosaveMeta.textContent = text;
}

function updateVersion(version) {
    state.currentVersion = version;
    els.versionState.textContent = `version: ${version || "-"}`;
}

function countContentDensity(content) {
    return (content || "").replace(/\s+/g, "").length;
}

function estimateReadMinutes(charCount) {
    if (!charCount) {
        return 0;
    }
    return Math.max(1, Math.ceil(charCount / 320));
}

function markdownToPlainText(markdown) {
    return (markdown || "")
        .replace(/```[\s\S]*?```/g, "代码块")
        .replace(/`([^`]+)`/g, "$1")
        .replace(/!\[[^\]]*]\([^)]*\)/g, "图片")
        .replace(/\[([^\]]+)]\([^)]*\)/g, "$1")
        .replace(/^#{1,6}\s+/gm, "")
        .replace(/^>\s?/gm, "")
        .replace(/[*_~|]/g, "")
        .replace(/\n+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function deriveSlideTitle(markdown, index) {
    const lines = (markdown || "")
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);

    for (const line of lines) {
        const headingMatch = line.match(/^#{1,6}\s+(.*)$/);
        if (headingMatch && headingMatch[1]) {
            return headingMatch[1].slice(0, 42);
        }
    }

    const firstLine = (lines[0] || "")
        .replace(/^[>\-*+\d.\[\]\s]+/, "")
        .replace(/`/g, "")
        .trim();
    return firstLine ? firstLine.slice(0, 42) : `第 ${index} 页`;
}

function parseSlides(content) {
    const normalized = (content || "").replace(/\r\n/g, "\n");
    if (!normalized) {
        return [{
            index: 0,
            rawMarkdown: "",
            title: "第 1 页",
            summary: "从这里开始记录或临时汇报",
            startLine: 1,
            startOffset: 0,
        }];
    }

    const lines = normalized.split("\n");
    const slides = [];
    let currentLines = [];
    let startLine = 1;
    let startOffset = 0;
    let offset = 0;
    let fenceMarker = "";

    const pushSlide = () => {
        const rawMarkdown = currentLines.join("\n");
        slides.push({
            index: slides.length,
            rawMarkdown,
            title: deriveSlideTitle(rawMarkdown, slides.length + 1),
            summary: markdownToPlainText(rawMarkdown).slice(0, 88) || "继续补充这一页的要点",
            startLine,
            startOffset,
        });
    };

    lines.forEach((line, index) => {
        const trimmed = line.trim();
        const fenceMatch = trimmed.match(/^(```|~~~)/);
        if (fenceMatch) {
            if (!fenceMarker) {
                fenceMarker = fenceMatch[1];
            } else if (trimmed.startsWith(fenceMarker)) {
                fenceMarker = "";
            }
        }

        const nextOffset = offset + line.length + 1;
        if (!fenceMarker && trimmed === "---") {
            if (currentLines.length || slides.length) {
                pushSlide();
            }
            currentLines = [];
            startLine = index + 2;
            startOffset = nextOffset;
            offset = nextOffset;
            return;
        }

        currentLines.push(line);
        offset = nextOffset;
    });

    pushSlide();
    return slides;
}

function getSlideIndexForCursor(cursorPosition) {
    for (let index = state.slides.length - 1; index >= 0; index -= 1) {
        if (cursorPosition >= state.slides[index].startOffset) {
            return index;
        }
    }
    return 0;
}

function clampSlideIndex(index) {
    return Math.min(Math.max(index, 0), Math.max(state.slides.length - 1, 0));
}

function renderFileSwitcher() {
    const currentValue = state.currentFile || FILE_SWITCHER_NONE;
    const options = [
        { value: FILE_SWITCHER_NONE, label: "未选择文件" },
        { value: FILE_SWITCHER_NEW, label: "新建文件..." },
    ];

    state.cachedFiles.forEach((file) => {
        options.push({
            value: file,
            label: baseName(file),
        });
    });

    if (state.currentFile && !state.cachedFiles.includes(state.currentFile)) {
        options.push({
            value: state.currentFile,
            label: `${baseName(state.currentFile)}（当前）`,
        });
    }

    els.fileSwitcher.innerHTML = options.map((item) => (
        `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`
    )).join("");
    els.fileSwitcher.value = currentValue;
}

function renderTemplateSwitcher() {
    const currentValue = state.currentTemplate || TEMPLATE_SWITCHER_NONE;
    const options = [
        { value: TEMPLATE_SWITCHER_NONE, label: "未选择模版" },
        { value: TEMPLATE_SWITCHER_NEW, label: "新建模版..." },
    ];

    state.templateFiles.forEach((file) => {
        options.push({
            value: file,
            label: baseName(file),
        });
    });

    if (state.currentTemplate && !state.templateFiles.includes(state.currentTemplate)) {
        options.push({
            value: state.currentTemplate,
            label: `${baseName(state.currentTemplate)}（当前）`,
        });
    }

    const optionHtml = options.map((item) => (
        `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`
    )).join("");
    const insertHtml = options.filter((item) => item.value !== TEMPLATE_SWITCHER_NEW).map((item) => (
        `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`
    )).join("");
    els.templateSwitcher.innerHTML = optionHtml;
    els.templateSwitcher.value = currentValue;
    els.templateInsertSelect.innerHTML = insertHtml;
    els.templateInsertSelect.value = currentValue === TEMPLATE_SWITCHER_NEW ? TEMPLATE_SWITCHER_NONE : currentValue;
}

function updateDocumentMeta() {
    const activePath = getActivePath();
    const displayPath = activePath || els.newFilePath.value.trim();
    const title = baseName(displayPath) || (els.editor.value.trim() ? "未命名文档" : "未选择文件");
    els.editorTitle.textContent = title;
    renderFileSwitcher();
    renderTemplateSwitcher();
}

function syncViewChrome() {
    const templateMode = isTemplateView();
    els.fileSwitcherField.classList.toggle("hidden", templateMode);
    els.templateSwitcherField.classList.toggle("hidden", !templateMode);
    updateDocumentMeta();
}

function setDirty(nextDirty) {
    state.isDirty = nextDirty;
    updateDocumentMeta();
}

function updateMetrics(content) {
    const density = countContentDensity(content);
    const totalSlides = state.slides.length || 1;
    const readLabel = `${estimateReadMinutes(density)} 分钟`;
    const densityLabel = density ? `${density}` : "0";

    els.wordCount.textContent = densityLabel;
    els.slideCount.textContent = String(totalSlides);
    els.readTime.textContent = readLabel;
}

function renderDocumentPreview(content) {
    const scrollContainer = els.preview.parentElement;
    const previousScrollTop = scrollContainer.scrollTop;
    els.preview.innerHTML = renderMarkdown(content || "");
    scrollContainer.scrollTop = previousScrollTop;
}

function renderSlideStage(target, slide, fallbackMarkdown) {
    const markdown = slide && slide.rawMarkdown.trim()
        ? slide.rawMarkdown
        : fallbackMarkdown;
    target.innerHTML = `<div class="markdown-body">${renderMarkdown(markdown)}</div>`;
    target.scrollTop = 0;
}

function renderSlideWorkspace() {
    if (!state.slides.length) {
        state.slides = parseSlides("");
    }

    state.activeSlideIndex = clampSlideIndex(state.activeSlideIndex);
    const activeSlide = state.slides[state.activeSlideIndex];
    const totalSlides = state.slides.length;

    els.presentationPosition.textContent = `第 ${state.activeSlideIndex + 1} / ${totalSlides} 页`;

    renderSlideStage(
        els.slideStage,
        activeSlide,
        "## 空白页\n\n继续在写作模块补这一页内容。",
    );
    renderSlideStage(
        els.presentationStage,
        activeSlide,
        "# 空白页\n\n继续在写作模块补充内容。",
    );

    els.slideStrip.innerHTML = "";
    state.slides.forEach((slide, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `slide-card${index === state.activeSlideIndex ? " active" : ""}`;
        button.innerHTML = `
            <span class="index">第 ${index + 1} 页</span>
            <h3>${escapeHtml(slide.title)}</h3>
            <p>${escapeHtml(slide.summary)}</p>
        `;
        button.addEventListener("click", () => {
            jumpToSlide(index);
        });
        els.slideStrip.appendChild(button);
    });
}

function refreshDerivedState(content) {
    state.slides = parseSlides(content);
    state.activeSlideIndex = clampSlideIndex(getSlideIndexForCursor(els.editor.selectionStart || 0));
    renderDocumentPreview(content);
    renderSlideWorkspace();
    updateMetrics(content);
    updateDocumentMeta();
}

function setActiveView(view, { updateHash = true } = {}) {
    state.activeView = normalizeView(view);
    if (state.activeView === "document") {
        state.previewMode = "document";
    } else if (state.activeView === "slides") {
        state.previewMode = "slides";
    }
    els.appShell.dataset.view = state.activeView;

    const showEditor = state.activeView === "write" || state.activeView === "template";
    els.writeView.classList.toggle("hidden", !showEditor);
    els.documentView.classList.toggle("hidden", state.activeView !== "document");
    els.slidesView.classList.toggle("hidden", state.activeView !== "slides");

    els.viewTemplateBtn.classList.toggle("active", state.activeView === "template");
    els.viewWriteBtn.classList.toggle("active", state.activeView === "write");
    els.viewDocumentBtn.classList.toggle("active", state.activeView === "document");
    els.viewSlidesBtn.classList.toggle("active", state.activeView === "slides");

    if (state.activeView !== "write" && state.activeView !== "template") {
        closeSlashMenu();
    }

    const exportMode = resolveExportMode();
    els.exportBtn.disabled = !exportMode;
    els.exportBtn.textContent = exportMode ? `导出 ${exportMode.toUpperCase()}` : "导出";
    syncViewChrome();

    if (updateHash) {
        history.replaceState(null, "", `${window.location.pathname}#${state.activeView}`);
    }
}

function saveDraftToLocal() {
    const payload = {
        path: getActivePath() || "",
        content: els.editor.value,
        version: state.currentVersion,
        updated_at: Date.now(),
    };
    localStorage.setItem(draftKey(getActivePath(), activeScope()), JSON.stringify(payload));
    setDraftLabel(`草稿已缓存 ${formatTimeLabel(payload.updated_at)}`);
}

function clearDraft(path, scope) {
    localStorage.removeItem(draftKey(path, scope));
}

function maybeRestoreDraftForPath(path, serverContent, scope) {
    const raw = localStorage.getItem(draftKey(path, scope));
    if (!raw) {
        return { content: serverContent, restored: false };
    }

    try {
        const draft = JSON.parse(raw);
        if (draft.content === serverContent) {
            clearDraft(path, scope);
            return { content: serverContent, restored: false };
        }

        const recover = window.confirm(
            `检测到本地草稿（${new Date(draft.updated_at).toLocaleString("zh-CN")}），是否恢复？`,
        );
        if (recover) {
            setDraftLabel(`已恢复草稿 ${formatTimeLabel(draft.updated_at)}`);
            return { content: draft.content || serverContent, restored: true };
        }
        clearDraft(path, scope);
    } catch (_error) {
        clearDraft(path, scope);
    }

    return { content: serverContent, restored: false };
}

function maybeRestoreUnsavedDraft(scope) {
    const raw = localStorage.getItem(draftKey("", scope));
    if (!raw) {
        return;
    }

    try {
        const draft = JSON.parse(raw);
        if (!draft.content) {
            return;
        }
        const recover = window.confirm(
            `发现未命名草稿（${new Date(draft.updated_at).toLocaleString("zh-CN")}），是否恢复？`,
        );
        if (!recover) {
            return;
        }

        if (scope === "template") {
            state.currentTemplate = "";
        } else {
            state.currentFile = "";
        }
        updateVersion(null);
        els.editor.value = draft.content;
        setDirty(true);
        setDraftLabel(`已恢复草稿 ${formatTimeLabel(draft.updated_at)}`);
        refreshDerivedState(draft.content);
        setActiveView(scope === "template" ? "template" : "write");
        showStatus("已恢复未命名草稿", "warn");
    } catch (_error) {
        localStorage.removeItem(draftKey("", scope));
    }
}

function scheduleDraftAutoSave() {
    if (state.autoSaveTimer) {
        clearTimeout(state.autoSaveTimer);
    }
    state.autoSaveTimer = window.setTimeout(() => {
        saveDraftToLocal();
    }, 500);
}

function scheduleRemoteAutoSave() {
    if (state.remoteSaveTimer) {
        clearTimeout(state.remoteSaveTimer);
    }
    if (!getActivePath()) {
        return;
    }
    state.remoteSaveTimer = window.setTimeout(() => {
        if (!state.isDirty || !getActivePath()) {
            return;
        }
        saveFile(false, { auto: true, interactive: false });
    }, 800);
}

async function requestJSON(url, options = {}) {
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    return { res, data };
}

function resolveTargetPath(defaultValue, promptMessage, { scope = "file" } = {}) {
    const activePath = scope === "template" ? state.currentTemplate : state.currentFile;
    const initial = activePath || defaultValue;
    const picked = window.prompt(promptMessage, initial);
    if (!picked) {
        return "";
    }
    const normalized = picked.endsWith(".md") ? picked : `${picked}.md`;
    if (scope === "template") {
        return normalizeTemplatePath(normalized);
    }
    return normalized;
}

function resolveExportBaseName() {
    const activePath = getActivePath();
    if (activePath) {
        const fileName = baseName(activePath) || "note.md";
        return fileName.replace(/\.md$/i, "") || "note";
    }

    const displayPath = els.newFilePath.value.trim();
    if (displayPath) {
        return (baseName(displayPath) || "note").replace(/\.md$/i, "") || "note";
    }

    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, "0");
    const d = String(now.getDate()).padStart(2, "0");
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    return `note-${y}${m}${d}-${hh}${mm}`;
}

function triggerDownload(blob, fileName) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
}

function parseFilenameFromDisposition(disposition) {
    if (!disposition) {
        return "";
    }

    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match) {
        try {
            return decodeURIComponent(utf8Match[1]);
        } catch (_error) {
            return utf8Match[1];
        }
    }

    const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
    return plainMatch ? plainMatch[1] : "";
}

function buildWrappedLines(ctx, text, maxWidth) {
    const source = (text || "").replace(/\r\n/g, "\n");
    const result = [];

    for (const rawLine of source.split("\n")) {
        if (!rawLine) {
            result.push("");
            continue;
        }
        let current = "";
        for (const char of rawLine) {
            const next = current + char;
            if (ctx.measureText(next).width > maxWidth && current) {
                result.push(current);
                current = char;
            } else {
                current = next;
            }
        }
        result.push(current);
    }

    return result;
}

async function exportCurrentNote() {
    const format = resolveExportMode();
    if (!format) {
        showStatus("当前模块不支持导出", "warn");
        return;
    }

    if (format === "png") {
        state.previewMode = "slides";
        await exportAsPng();
        return;
    }

    state.previewMode = format === "html" ? "document" : state.previewMode;

    const payload = {
        format,
        content: els.editor.value,
        file_name: resolveExportBaseName(),
    };

    const res = await fetch("/api/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        showStatus(`导出失败：${detail.detail || "未知错误"}`, "error");
        return;
    }

    const blob = await res.blob();
    const fileName = parseFilenameFromDisposition(res.headers.get("content-disposition"))
        || `${resolveExportBaseName()}.${format}`;
    triggerDownload(blob, fileName);
    showStatus(`已导出 ${fileName}`, "success");
}

function buildPngBlobFromText({ sourceText, title, slideMode }) {
    const contentText = String(sourceText || "").trim();
    if (!contentText) {
        return Promise.resolve(null);
    }

    const canvas = document.createElement("canvas");
    const width = 1600;
    const padding = 64;
    const maxTextWidth = width - padding * 2;
    const lineHeight = slideMode ? 42 : 32;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
        return Promise.resolve(null);
    }

    ctx.font = slideMode
        ? "28px 'PingFang SC', 'Microsoft YaHei', sans-serif"
        : "20px 'PingFang SC', 'Microsoft YaHei', sans-serif";
    const lines = buildWrappedLines(ctx, contentText, maxTextWidth);
    const height = Math.min(16000, padding * 2 + lineHeight * (lines.length + 6));

    canvas.width = width;
    canvas.height = height;

    const background = ctx.createLinearGradient(0, 0, width, height);
    background.addColorStop(0, "#f7fbff");
    background.addColorStop(1, "#edf7f7");
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, width, height);

    let y = padding;
    ctx.fillStyle = "#15202b";
    ctx.font = "bold 38px 'PingFang SC', 'Microsoft YaHei', sans-serif";
    ctx.fillText(title, padding, y);
    y += lineHeight + 12;

    ctx.font = "18px 'PingFang SC', 'Microsoft YaHei', sans-serif";
    ctx.fillStyle = "#5b6876";
    ctx.fillText(`导出时间：${new Date().toLocaleString("zh-CN")}`, padding, y);
    y += lineHeight + 8;

    ctx.strokeStyle = "#c9d6e5";
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();
    y += lineHeight;

    ctx.fillStyle = "#15202b";
    ctx.font = slideMode
        ? "26px 'PingFang SC', 'Microsoft YaHei', sans-serif"
        : "20px 'PingFang SC', 'Microsoft YaHei', sans-serif";

    for (const line of lines) {
        if (y > height - padding) {
            break;
        }
        ctx.fillText(line || " ", padding, y);
        y += lineHeight;
    }

    return new Promise((resolve) => {
        canvas.toBlob((blob) => resolve(blob), "image/png");
    });
}

async function exportAllSlidesAsPng() {
    const slides = state.slides.length ? state.slides : parseSlides(els.editor.value);
    if (!slides.length) {
        showStatus("当前内容为空，无法导出图片", "warn");
        return;
    }

    const baseName = resolveExportBaseName();
    let exported = 0;
    for (let index = 0; index < slides.length; index += 1) {
        const slide = slides[index];
        const sourceText = (slide.rawMarkdown || "").trim();
        const blob = await buildPngBlobFromText({
            sourceText,
            title: `${baseName} - slide-${index + 1}`,
            slideMode: true,
        });
        if (!blob) {
            continue;
        }
        const fileName = `${baseName}-slide-${index + 1}.png`;
        triggerDownload(blob, fileName);
        exported += 1;
        await new Promise((resolve) => window.setTimeout(resolve, 50));
    }

    if (!exported) {
        showStatus("图片导出失败", "error");
        return;
    }
    showStatus(`已导出 ${exported} 张 PNG`, "success");
}

async function exportAsPng() {
    await exportAllSlidesAsPng();
}


async function loadSession() {
    const { res, data } = await requestJSON("/api/session");
    if (!res.ok) {
        els.sessionMeta.textContent = "未登录";
        return;
    }
    state.currentUser = data;
    els.sessionMeta.textContent = `${data.username} · ${data.role}`;
}

async function loadTemplateFiles() {
    const { res, data } = await requestJSON("/api/template-files");
    if (!res.ok) {
        showStatus(`加载模版失败：${extractErrorDetail(data, "未知错误")}`, "error");
        return;
    }

    state.templateFiles = data.files || [];
    renderTemplateSwitcher();
}

async function loadFileList() {
    const { res, data } = await requestJSON("/api/files");
    if (!res.ok) {
        showStatus(`加载文件失败：${extractErrorDetail(data, "未知错误")}`, "error");
        return;
    }
    state.cachedFiles = data.files || [];
    if (isTemplatePath(state.currentFile)) {
        state.currentFile = "";
    }
    renderFileSwitcher();
}

async function flushPendingChangesBeforeSwitch() {
    if (state.autoSaveTimer) {
        clearTimeout(state.autoSaveTimer);
        state.autoSaveTimer = null;
    }
    if (state.remoteSaveTimer) {
        clearTimeout(state.remoteSaveTimer);
        state.remoteSaveTimer = null;
    }

    if (!state.isDirty) {
        return;
    }

    saveDraftToLocal();
    if (!getActivePath()) {
        return;
    }

    await saveFile(false, { auto: true, interactive: false });
    if (state.isDirty) {
        showStatus("自动保存失败，已保留本地草稿", "warn");
    }
}

async function openFile(path, { skipDirtyCheck = false } = {}) {
    if (!path || path === FILE_SWITCHER_NONE) {
        renderFileSwitcher();
        return;
    }

    if (isTemplatePath(path)) {
        state.currentFile = "";
        renderFileSwitcher();
        showStatus("写作模式不允许打开模版文件", "warn");
        return;
    }

    if (!skipDirtyCheck) {
        await flushPendingChangesBeforeSwitch();
    }

    const { res, data } = await requestJSON(`/api/files/${encodeURIComponent(path)}`);
    if (!res.ok) {
        showStatus(`加载失败：${extractErrorDetail(data, "未知错误")}`, "error");
        renderFileSwitcher();
        return;
    }

    state.currentFile = data.path;
    els.newFilePath.value = state.currentFile;
    updateVersion(data.version);

    const restored = maybeRestoreDraftForPath(state.currentFile, data.content, "file");
    els.editor.value = restored.content;
    setDirty(restored.restored);
    if (!restored.restored) {
        setDraftLabel("草稿未缓存");
    }

    refreshDerivedState(restored.content);
    setActiveView("write");
}

async function openTemplate(path, { skipDirtyCheck = false } = {}) {
    if (!path || path === TEMPLATE_SWITCHER_NONE) {
        renderTemplateSwitcher();
        return;
    }

    if (!skipDirtyCheck) {
        await flushPendingChangesBeforeSwitch();
    }

    const { res, data } = await requestJSON(`/api/template-files/${encodeURIComponent(path)}`);
    if (!res.ok) {
        showStatus(`加载模版失败：${extractErrorDetail(data, "未知错误")}`, "error");
        renderTemplateSwitcher();
        return;
    }

    state.currentTemplate = data.path;
    els.newFilePath.value = state.currentTemplate;
    updateVersion(data.version);

    const restored = maybeRestoreDraftForPath(state.currentTemplate, data.content, "template");
    els.editor.value = restored.content;
    setDirty(restored.restored);
    if (!restored.restored) {
        setDraftLabel("草稿未缓存");
    }

    refreshDerivedState(restored.content);
    setActiveView("template");
}

async function saveFile(force = false, { auto = false, interactive = true } = {}) {
    const templateMode = isTemplateView();
    let targetPath = templateMode ? state.currentTemplate : state.currentFile;
    if (!templateMode && isTemplatePath(targetPath)) {
        state.currentFile = "";
        renderFileSwitcher();
        if (!auto || interactive) {
            showStatus("写作模式不允许保存到模版目录", "warn");
        }
        return;
    }

    if (!targetPath) {
        if (auto) {
            return;
        }
        targetPath = resolveTargetPath(
            templateMode ? "templates/untitled.md" : "untitled.md",
            templateMode
                ? "请输入模版文件名（例如：templates/weekly.md）"
                : "请输入文件名（将自动保存到本周目录，例如：notes.md）",
            { scope: templateMode ? "template" : "file" },
        );
        if (!targetPath) {
            return;
        }
    }

    const payload = {
        path: targetPath,
        content: els.editor.value,
        base_version: state.currentVersion,
        force,
    };
    const endpoint = templateMode ? "/api/template-files" : "/api/files";
    const { res, data } = await requestJSON(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (res.status === 409) {
        const detail = data.detail || {};
        if (!interactive) {
            return;
        }

        const overwrite = window.confirm("检测到并发修改冲突。是否覆盖远端版本（谨慎）？");
        if (overwrite) {
            return saveFile(true, { auto, interactive });
        }
        if (detail.current_content) {
            const reload = window.confirm("是否加载服务器最新内容？");
            if (reload) {
                els.editor.value = detail.current_content;
                updateVersion(detail.current_version || null);
                setDirty(true);
                refreshDerivedState(detail.current_content);
            }
        }
        return;
    }

    if (!res.ok) {
        showStatus(`保存失败：${extractErrorDetail(data, "未知错误")}`, "error");
        return;
    }

    if (templateMode) {
        state.currentTemplate = data.path;
    } else {
        state.currentFile = data.path;
    }
    els.newFilePath.value = data.path;
    updateVersion(data.version);
    setDirty(false);
    clearDraft(data.path, templateMode ? "template" : "file");
    clearDraft("", templateMode ? "template" : "file");
    const savedLabel = auto
        ? `已自动保存 ${formatTimeLabel(Date.now())}`
        : `已保存 ${formatTimeLabel(Date.now())}`;
    setDraftLabel(savedLabel);
    refreshDerivedState(els.editor.value);
    if (templateMode) {
        await loadTemplateFiles();
    } else {
        await loadFileList();
    }
    if (!auto) {
        showStatus("已保存", "success");
    }
}

async function createBlankFile(scopeOverride = null) {
    await flushPendingChangesBeforeSwitch();

    const templateMode = scopeOverride
        ? scopeOverride === "template"
        : isTemplateView();
    const filePath = resolveTargetPath(
        templateMode ? "templates/untitled.md" : "untitled.md",
        templateMode
            ? "请输入模版文件名（例如：templates/weekly.md）"
            : "请输入目标文件名（将自动保存到本周目录，例如：notes.md）",
        { scope: templateMode ? "template" : "file" },
    );
    if (!filePath) {
        return;
    }

    const title = baseName(filePath).replace(/\.md$/i, "") || "untitled";
    const initialContent = `# ${title}\n\n一句话结论：\n\n## 记录\n- `;

    if (templateMode) {
        state.currentTemplate = filePath;
    } else {
        state.currentFile = filePath;
    }
    els.newFilePath.value = filePath;
    updateVersion(null);
    els.editor.value = initialContent;
    setDirty(true);
    setDraftLabel("草稿未缓存");
    refreshDerivedState(initialContent);
    setActiveView(templateMode ? "template" : "write");
    els.editor.focus();
    scheduleRemoteAutoSave();
    showStatus("已创建空白草稿", "success");
}

function setEditorContent(content, { moveCursorToEnd = true } = {}) {
    els.editor.value = content;
    if (moveCursorToEnd) {
        const pos = content.length;
        els.editor.setSelectionRange(pos, pos);
    }
    refreshDerivedState(content);
    setDirty(true);
    scheduleDraftAutoSave();
}

function replaceEditorRange(start, end, replacement) {
    const before = els.editor.value.slice(0, start);
    const after = els.editor.value.slice(end);
    const nextValue = before + replacement + after;
    els.editor.value = nextValue;

    const nextCursor = start + replacement.length;
    els.editor.focus();
    els.editor.setSelectionRange(nextCursor, nextCursor);
    refreshDerivedState(nextValue);
    setDirty(true);
    scheduleDraftAutoSave();
}

function insertReportDeck() {
    const deck = [
        "# 临时汇报标题",
        "",
        "一句话结论：",
        "",
        "---",
        "",
        "## 关键进展",
        "- ",
        "",
        "---",
        "",
        "## 数据与证据",
        "- ",
        "",
        "---",
        "",
        "## 风险与阻塞",
        "- ",
        "",
        "---",
        "",
        "## 下一步",
        "- ",
    ].join("\n");

    setActiveView("write");
    if (!els.editor.value.trim()) {
        setEditorContent(deck);
        showStatus("已插入汇报骨架", "success");
        return;
    }

    const append = window.confirm("当前文档已有内容。要把汇报骨架插入到光标位置吗？");
    if (!append) {
        return;
    }

    replaceEditorRange(els.editor.selectionStart, els.editor.selectionEnd, `\n\n${deck}`);
    showStatus("已插入汇报骨架", "success");
}

async function deleteFile() {
    const templateMode = isTemplateView();
    const targetPath = templateMode ? state.currentTemplate : state.currentFile;
    if (!targetPath) {
        showStatus(templateMode ? "请先选择模版文件" : "请先选择文件", "warn");
        return;
    }

    if (!window.confirm(`确定删除 ${targetPath} 吗？`)) {
        return;
    }

    const endpoint = templateMode ? "/api/template-files" : "/api/files";
    const { res, data } = await requestJSON(`${endpoint}/${encodeURIComponent(targetPath)}`, {
        method: "DELETE",
    });
    if (!res.ok) {
        showStatus(`删除失败：${extractErrorDetail(data, "未知错误")}`, "error");
        return;
    }

    clearDraft(targetPath, templateMode ? "template" : "file");
    if (templateMode) {
        state.currentTemplate = "";
    } else {
        state.currentFile = "";
    }
    els.newFilePath.value = "";
    updateVersion(null);
    els.editor.value = "";
    setDirty(false);
    setDraftLabel("草稿未缓存");
    refreshDerivedState("");
    if (templateMode) {
        await loadTemplateFiles();
        setActiveView("template");
    } else {
        await loadFileList();
        setActiveView("write");
    }
    showStatus("文件已删除", "success");
}

function getSlashCommandMatches(query, { exact = false } = {}) {
    const normalized = String(query || "").trim().toLowerCase();
    const matches = SLASH_COMMANDS.filter((command) => {
        const keys = [command.id, ...(command.aliases || [])].map((item) => item.toLowerCase());
        return exact
            ? keys.includes(normalized)
            : (!normalized || keys.some((item) => item.includes(normalized)));
    });

    return matches.sort((left, right) => left.label.localeCompare(right.label, "zh-CN"));
}

function getSlashContext() {
    if (state.activeView !== "write") {
        return null;
    }
    if (els.editor.selectionStart !== els.editor.selectionEnd) {
        return null;
    }

    const cursor = els.editor.selectionStart || 0;
    const before = els.editor.value.slice(0, cursor);
    const match = before.match(/(^|\s)\/([a-zA-Z0-9_-]*)$/);
    if (!match) {
        return null;
    }

    return {
        query: match[2].toLowerCase(),
        start: cursor - match[2].length - 1,
        end: cursor,
    };
}

function getCompletedSlashContext() {
    const cursor = els.editor.selectionStart || 0;
    if (els.editor.selectionStart !== els.editor.selectionEnd) {
        return null;
    }

    const before = els.editor.value.slice(0, cursor);
    const match = before.match(/(^|\s)\/([a-zA-Z0-9_-]+)\s$/);
    if (!match) {
        return null;
    }

    const command = getSlashCommandMatches(match[2], { exact: true })[0];
    if (!command) {
        return null;
    }

    return {
        command,
        start: cursor - match[2].length - 2,
        end: cursor,
    };
}

function renderSlashMenu() {
    els.slashQuery.textContent = `/${state.slashRange?.query || ""}`;
    if (!state.slashMatches.length) {
        els.slashList.innerHTML = '<div class="slash-item"><div>#</div><div><strong>没有匹配命令</strong><br><small>继续输入或按 Esc 关闭</small></div></div>';
        return;
    }

    els.slashList.innerHTML = "";
    state.slashMatches.forEach((command, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `slash-item${index === state.slashActiveIndex ? " active" : ""}`;
        button.innerHTML = `
            <div>${escapeHtml(command.label)}</div>
            <div>
                <strong>${escapeHtml(command.description)}</strong><br>
                <small>${escapeHtml((command.aliases || []).join(" · ") || command.id)}</small>
            </div>
        `;
        button.addEventListener("click", () => {
            applySlashCommand(command);
        });
        els.slashList.appendChild(button);
    });
}

function openSlashMenu(context, matches) {
    state.slashOpen = true;
    state.slashRange = context;
    state.slashMatches = matches;
    state.slashActiveIndex = Math.min(state.slashActiveIndex, Math.max(matches.length - 1, 0));
    els.slashPanel.classList.remove("hidden");
    els.slashPanel.setAttribute("aria-hidden", "false");
    renderSlashMenu();
}

function closeSlashMenu() {
    state.slashOpen = false;
    state.slashRange = null;
    state.slashMatches = [];
    state.slashActiveIndex = 0;
    els.slashPanel.classList.add("hidden");
    els.slashPanel.setAttribute("aria-hidden", "true");
}

function syncSlashMenu() {
    const context = getSlashContext();
    if (!context) {
        closeSlashMenu();
        return;
    }

    const matches = getSlashCommandMatches(context.query);
    state.slashActiveIndex = 0;
    openSlashMenu({ ...context, query: context.query }, matches);
}

function moveSlashSelection(delta) {
    if (!state.slashMatches.length) {
        return;
    }
    const total = state.slashMatches.length;
    state.slashActiveIndex = (state.slashActiveIndex + delta + total) % total;
    renderSlashMenu();
}

function openAssetModal(range = null) {
    const cursor = els.editor.selectionStart || 0;
    state.pendingInsertRange = range
        ? { start: range.start, end: range.start }
        : { start: cursor, end: cursor };
    els.assetUrl.value = "";
    els.assetAlt.value = "";
    els.assetModal.classList.remove("hidden");
    els.assetModal.setAttribute("aria-hidden", "false");
    els.assetUrl.focus();
}

function closeAssetModal() {
    els.assetModal.classList.add("hidden");
    els.assetModal.setAttribute("aria-hidden", "true");
    setDropzoneActive(false);
    els.editor.focus();
}

function openTemplateInsertModal() {
    if (state.activeView !== "write") {
        showStatus("请在写作模式插入模版", "warn");
        return;
    }
    if (!state.templateFiles.length) {
        showStatus("暂无可用模版文件", "warn");
        return;
    }
    renderTemplateSwitcher();
    els.templateModal.classList.remove("hidden");
    els.templateModal.setAttribute("aria-hidden", "false");
    if (!els.templateInsertSelect.value || els.templateInsertSelect.value === TEMPLATE_SWITCHER_NONE) {
        els.templateInsertSelect.value = state.templateFiles[0] || TEMPLATE_SWITCHER_NONE;
    }
    els.templateInsertSelect.focus();
}

function closeTemplateInsertModal() {
    els.templateModal.classList.add("hidden");
    els.templateModal.setAttribute("aria-hidden", "true");
    els.editor.focus();
}

async function insertTemplateContent() {
    const path = els.templateInsertSelect.value;
    if (!path || path === TEMPLATE_SWITCHER_NONE) {
        showStatus("请先选择模版文件", "warn");
        return;
    }

    const { res, data } = await requestJSON(`/api/template-files/${encodeURIComponent(path)}`);
    if (!res.ok) {
        showStatus(`加载模版失败：${extractErrorDetail(data, "未知错误")}`, "error");
        return;
    }

    replaceEditorRange(els.editor.selectionStart, els.editor.selectionEnd, data.content || "");
    closeTemplateInsertModal();
    showStatus("已插入模版内容", "success");
}

function insertPendingAsset(markdown) {
    const range = state.pendingInsertRange || {
        start: els.editor.selectionStart || 0,
        end: els.editor.selectionEnd || 0,
    };
    replaceEditorRange(range.start, range.end, markdown);
    state.pendingInsertRange = null;
    closeAssetModal();
}

function insertRemoteAsset() {
    const url = els.assetUrl.value.trim();
    if (!url) {
        showStatus("请输入资源地址", "warn");
        return;
    }

    const alt = els.assetAlt.value.trim() || "asset";
    const isImage = /\.(png|jpe?g|gif|webp|svg)$/i.test(url);
    const markdown = isImage ? `![${alt}](${url})` : `[${alt}](${url})`;
    insertPendingAsset(markdown);
    showStatus("已插入资源", "success");
}

function setDropzoneActive(active) {
    if (!els.assetDropzone) {
        return;
    }
    els.assetDropzone.classList.toggle("drag-over", Boolean(active));
}

function setEditorDropActive(active) {
    if (!els.editorFrame) {
        return;
    }
    els.editorFrame.classList.toggle("drag-over", Boolean(active));
}

function isUploadableImage(file) {
    if (!file) {
        return false;
    }
    if ((file.type || "").startsWith("image/")) {
        return true;
    }
    return /\.(png|jpe?g|gif|webp)$/i.test(file.name || "");
}

async function uploadAssetFile(file, { source = "upload" } = {}) {
    if (!file) {
        return false;
    }

    const formData = new FormData();
    formData.append("file", file);

    const { res, data } = await requestJSON("/api/upload", {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        showStatus(`上传失败：${extractErrorDetail(data, "未知错误")}`, "error");
        return false;
    }

    const markdown = `![${file.name}](${data.url})`;
    if (state.pendingInsertRange) {
        insertPendingAsset(markdown);
    } else {
        replaceEditorRange(els.editor.selectionStart, els.editor.selectionEnd, markdown);
    }
    showStatus(source === "paste" ? "已粘贴并上传图片" : "图片已上传", "success");
    return true;
}

function applySlashCommand(command = null, explicitRange = null) {
    const targetCommand = command || state.slashMatches[state.slashActiveIndex];
    const range = explicitRange || state.slashRange;
    if (!targetCommand || !range) {
        closeSlashMenu();
        return;
    }

    closeSlashMenu();

    if (targetCommand.kind === "asset") {
        replaceEditorRange(range.start, range.end, "");
        openAssetModal({ start: range.start, end: range.start });
        return;
    }

    if (targetCommand.kind === "insert") {
        replaceEditorRange(range.start, range.end, targetCommand.snippet);
        return;
    }

    if (targetCommand.kind === "deck") {
        replaceEditorRange(range.start, range.end, "");
        insertReportDeck();
        return;
    }

    if (targetCommand.kind === "template") {
        replaceEditorRange(range.start, range.end, "");
        openTemplateInsertModal();
    }
}

async function handleImageUpload(event) {
    const file = event.target.files[0];
    event.target.value = "";
    await uploadAssetFile(file, { source: "upload" });
}

async function handleEditorPaste(event) {
    const clipboard = event.clipboardData;
    if (!clipboard) {
        return;
    }

    const items = Array.from(clipboard.items || []);
    const imageItem = items.find((item) => item.kind === "file" && item.type.startsWith("image/"));
    if (!imageItem) {
        return;
    }

    const file = imageItem.getAsFile();
    if (!file) {
        return;
    }

    event.preventDefault();
    state.pendingInsertRange = {
        start: els.editor.selectionStart || 0,
        end: els.editor.selectionEnd || 0,
    };
    await uploadAssetFile(file, { source: "paste" });
}

async function handleAssetDrop(event) {
    event.preventDefault();
    setDropzoneActive(false);
    const files = Array.from(event.dataTransfer?.files || []);
    const imageFile = files.find((file) => isUploadableImage(file));
    if (!imageFile) {
        showStatus("仅支持拖拽图片文件", "warn");
        return;
    }

    await uploadAssetFile(imageFile, { source: "drop" });
}

function handleEditorDragEnter(event) {
    if (!(event.dataTransfer && Array.from(event.dataTransfer.types || []).includes("Files"))) {
        return;
    }
    event.preventDefault();
    state.editorDragDepth += 1;
    setEditorDropActive(true);
}

function handleEditorDragOver(event) {
    if (!(event.dataTransfer && Array.from(event.dataTransfer.types || []).includes("Files"))) {
        return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    setEditorDropActive(true);
}

function handleEditorDragLeave(event) {
    if (!(event.dataTransfer && Array.from(event.dataTransfer.types || []).includes("Files"))) {
        return;
    }
    event.preventDefault();
    state.editorDragDepth = Math.max(0, state.editorDragDepth - 1);
    if (state.editorDragDepth === 0) {
        setEditorDropActive(false);
    }
}

async function handleEditorDrop(event) {
    if (!(event.dataTransfer && Array.from(event.dataTransfer.types || []).includes("Files"))) {
        return;
    }
    event.preventDefault();
    state.editorDragDepth = 0;
    setEditorDropActive(false);

    const files = Array.from(event.dataTransfer.files || []);
    const imageFile = files.find((file) => isUploadableImage(file));
    if (!imageFile) {
        showStatus("仅支持拖拽图片文件", "warn");
        return;
    }

    els.editor.focus();
    state.pendingInsertRange = {
        start: els.editor.selectionStart || 0,
        end: els.editor.selectionEnd || 0,
    };
    await uploadAssetFile(imageFile, { source: "drop" });
}

function handleEditorInput() {
    const completedSlash = getCompletedSlashContext();
    if (completedSlash) {
        applySlashCommand(completedSlash.command, {
            start: completedSlash.start,
            end: completedSlash.end,
        });
        return;
    }

    refreshDerivedState(els.editor.value);
    setDirty(true);
    scheduleDraftAutoSave();
    scheduleRemoteAutoSave();
    syncSlashMenu();
}

function jumpToSlide(index) {
    state.activeSlideIndex = clampSlideIndex(index);
    renderSlideWorkspace();
}

function changeSlide(delta) {
    jumpToSlide(state.activeSlideIndex + delta);
}

function setPreviewMode(mode) {
    state.previewMode = mode;
}

function focusCurrentSlideInEditor() {
    const activeSlide = state.slides[state.activeSlideIndex];
    if (!activeSlide) {
        return;
    }

    setActiveView("write");
    const offset = activeSlide.startOffset || 0;
    const lineHeight = 30;
    els.editor.focus();
    els.editor.setSelectionRange(offset, offset);
    els.editor.scrollTop = Math.max(0, (activeSlide.startLine - 3) * lineHeight);
}

function syncActiveSlideFromCursor() {
    if (document.activeElement !== els.editor) {
        return;
    }
    const index = getSlideIndexForCursor(els.editor.selectionStart || 0);
    if (index !== state.activeSlideIndex) {
        state.activeSlideIndex = clampSlideIndex(index);
        renderSlideWorkspace();
    }
    syncSlashMenu();
}

function startPresentation() {
    if (!els.editor.value.trim()) {
        showStatus("当前内容为空，无法放映", "warn");
        return;
    }

    setActiveView("slides");
    setPreviewMode(state.slides.length > 1 ? "slides" : "document");
    state.overlayOpen = true;
    els.presentationOverlay.classList.add("show");
    els.presentationOverlay.setAttribute("aria-hidden", "false");
    renderSlideWorkspace();

    if (document.fullscreenEnabled && !document.fullscreenElement) {
        els.presentationOverlay.requestFullscreen().catch(() => {});
    }
}

function stopPresentation() {
    state.overlayOpen = false;
    els.presentationOverlay.classList.remove("show");
    els.presentationOverlay.setAttribute("aria-hidden", "true");
    if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
    }
}

function handleGlobalShortcuts(event) {
    if (!els.assetModal.classList.contains("hidden") && event.key === "Escape") {
        event.preventDefault();
        closeAssetModal();
        state.pendingInsertRange = null;
        return;
    }

    if (!els.templateModal.classList.contains("hidden") && event.key === "Escape") {
        event.preventDefault();
        closeTemplateInsertModal();
        return;
    }

    if (state.slashOpen) {
        if (event.key === "ArrowDown") {
            event.preventDefault();
            moveSlashSelection(1);
            return;
        }
        if (event.key === "ArrowUp") {
            event.preventDefault();
            moveSlashSelection(-1);
            return;
        }
        if (event.key === "Enter" || event.key === "Tab") {
            event.preventDefault();
            applySlashCommand();
            return;
        }
        if (event.key === "Escape") {
            event.preventDefault();
            closeSlashMenu();
            return;
        }
    }

    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        saveFile();
        return;
    }

    if (event.altKey && event.shiftKey && event.key.toLowerCase() === "p") {
        event.preventDefault();
        startPresentation();
        return;
    }

    if (!state.overlayOpen && state.activeView === "slides") {
        if (event.key === "ArrowRight" || event.key === "PageDown") {
            event.preventDefault();
            changeSlide(1);
            return;
        }
        if (event.key === "ArrowLeft" || event.key === "PageUp") {
            event.preventDefault();
            changeSlide(-1);
            return;
        }
    }

    if (!state.overlayOpen) {
        return;
    }

    if (["ArrowRight", "PageDown", " "].includes(event.key)) {
        event.preventDefault();
        changeSlide(1);
    } else if (["ArrowLeft", "PageUp", "Backspace"].includes(event.key)) {
        event.preventDefault();
        changeSlide(-1);
    } else if (event.key === "Escape") {
        event.preventDefault();
        stopPresentation();
    } else if (event.key.toLowerCase() === "f") {
        event.preventDefault();
        if (document.fullscreenElement) {
            document.exitFullscreen().catch(() => {});
        } else if (document.fullscreenEnabled) {
            els.presentationOverlay.requestFullscreen().catch(() => {});
        }
    }
}

function bindActionButtons() {
    document.querySelectorAll('[data-action="new-blank"]').forEach((button) => {
        button.addEventListener("click", createBlankFile);
    });
    document.querySelectorAll('[data-action="save"]').forEach((button) => {
        button.addEventListener("click", () => saveFile(false));
    });
    document.querySelectorAll('[data-action="present"]').forEach((button) => {
        button.addEventListener("click", startPresentation);
    });
}

function bindViewButtons() {
    async function switchView(targetView) {
        if (state.isDirty) {
            await flushPendingChangesBeforeSwitch();
        }

        if (targetView === "write") {
            if (isTemplatePath(state.currentFile)) {
                state.currentFile = "";
            }
            setActiveView("write");
            if (state.currentFile) {
                await openFile(state.currentFile, { skipDirtyCheck: true });
            } else {
                els.newFilePath.value = "";
                updateVersion(null);
                els.editor.value = "";
                setDirty(false);
                setDraftLabel("草稿未缓存");
                refreshDerivedState("");
            }
            els.editor.focus();
            return;
        }

        if (targetView === "template") {
            setActiveView("template");
            if (state.currentTemplate) {
                await openTemplate(state.currentTemplate, { skipDirtyCheck: true });
            } else {
                els.newFilePath.value = "";
                updateVersion(null);
                els.editor.value = "";
                setDirty(false);
                setDraftLabel("草稿未缓存");
                refreshDerivedState("");
            }
            els.editor.focus();
            return;
        }

        if (targetView === "document") {
            setPreviewMode("document");
            setActiveView("document");
            return;
        }

        setPreviewMode("slides");
        setActiveView("slides");
    }

    els.viewTemplateBtn.addEventListener("click", () => switchView("template"));
    els.viewWriteBtn.addEventListener("click", () => switchView("write"));
    els.viewDocumentBtn.addEventListener("click", () => switchView("document"));
    els.viewSlidesBtn.addEventListener("click", () => switchView("slides"));
}

function bindEvents() {
    bindActionButtons();
    bindViewButtons();

    els.fileSwitcher.addEventListener("change", () => {
        const value = els.fileSwitcher.value;
        if (value === FILE_SWITCHER_NEW) {
            createBlankFile("file");
            renderFileSwitcher();
            return;
        }
        openFile(value);
    });
    els.templateSwitcher.addEventListener("change", () => {
        const value = els.templateSwitcher.value;
        if (value === TEMPLATE_SWITCHER_NEW) {
            createBlankFile("template");
            renderTemplateSwitcher();
            return;
        }
        openTemplate(value);
    });
    els.exportBtn.addEventListener("click", async () => {
        if (state.isDirty) {
            await flushPendingChangesBeforeSwitch();
        }
        await exportCurrentNote();
    });
    els.presentationPrevBtn.addEventListener("click", () => changeSlide(-1));
    els.presentationNextBtn.addEventListener("click", () => changeSlide(1));
    els.presentationCloseBtn.addEventListener("click", stopPresentation);

    els.editor.addEventListener("input", handleEditorInput);
    els.editor.addEventListener("click", syncActiveSlideFromCursor);
    els.editor.addEventListener("keyup", syncActiveSlideFromCursor);
    els.editor.addEventListener("paste", handleEditorPaste);
    if (els.editorFrame) {
        els.editorFrame.addEventListener("dragenter", handleEditorDragEnter);
        els.editorFrame.addEventListener("dragover", handleEditorDragOver);
        els.editorFrame.addEventListener("dragleave", handleEditorDragLeave);
        els.editorFrame.addEventListener("drop", handleEditorDrop);
    }

    els.assetInsertBtn.addEventListener("click", insertRemoteAsset);
    els.assetUploadBtn.addEventListener("click", () => {
        els.imageUpload.click();
    });
    els.assetCancelBtn.addEventListener("click", () => {
        closeAssetModal();
        state.pendingInsertRange = null;
    });
    if (els.assetDropzone) {
        els.assetDropzone.addEventListener("dragenter", (event) => {
            event.preventDefault();
            setDropzoneActive(true);
        });
        els.assetDropzone.addEventListener("dragover", (event) => {
            event.preventDefault();
            setDropzoneActive(true);
        });
        els.assetDropzone.addEventListener("dragleave", (event) => {
            if (event.target === els.assetDropzone) {
                setDropzoneActive(false);
            }
        });
        els.assetDropzone.addEventListener("drop", handleAssetDrop);
    }
    els.templateInsertBtn.addEventListener("click", insertTemplateContent);
    els.templateCancelBtn.addEventListener("click", closeTemplateInsertModal);
    els.imageUpload.addEventListener("change", handleImageUpload);

    document.addEventListener("selectionchange", syncActiveSlideFromCursor);
    document.addEventListener("keydown", handleGlobalShortcuts);
    document.addEventListener("click", (event) => {
        if (state.slashOpen && !els.slashPanel.contains(event.target) && event.target !== els.editor) {
            closeSlashMenu();
        }
        if (!els.assetModal.classList.contains("hidden") && event.target === els.assetModal) {
            closeAssetModal();
            state.pendingInsertRange = null;
        }
        if (!els.templateModal.classList.contains("hidden") && event.target === els.templateModal) {
            closeTemplateInsertModal();
        }
    });
    window.addEventListener("hashchange", () => {
        setActiveView(normalizeView(window.location.hash.replace("#", "")), { updateHash: false });
    });
    window.addEventListener("beforeunload", (event) => {
        if (!state.isDirty) {
            return;
        }
        event.preventDefault();
        event.returnValue = "";
    });
}

async function bootstrap() {
    bindEvents();
    updateVersion(null);
    setDraftLabel("草稿未缓存");
    refreshDerivedState("");
    renderFileSwitcher();
    renderTemplateSwitcher();
    setActiveView(normalizeView(window.location.hash.replace("#", "")), { updateHash: false });
    await loadSession();
    await loadTemplateFiles();
    await loadFileList();
    maybeRestoreUnsavedDraft(activeScope());
}

bootstrap();
