const DRAFT_PREFIX = "benben:draft:";
const NEW_DRAFT_KEY = `${DRAFT_PREFIX}__new__`;
const VIEW_NAMES = ["template", "write", "document", "slides"];
const FILE_SWITCHER_NONE = "__none__";

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
        aliases: ["module", "templates"],
        description: "切换到模版模块",
        kind: "switch",
        target: "template",
    },
];

const state = {
    currentFile: "",
    currentVersion: null,
    currentUser: null,
    isDirty: false,
    autoSaveTimer: null,
    cachedFiles: [],
    templates: [],
    selectedTemplateId: "",
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
};

const els = {
    appShell: document.querySelector(".app-shell"),
    templateView: document.getElementById("template-view"),
    writeView: document.getElementById("write-view"),
    documentView: document.getElementById("document-view"),
    slidesView: document.getElementById("slides-view"),
    viewTemplateBtn: document.getElementById("view-template-btn"),
    viewWriteBtn: document.getElementById("view-write-btn"),
    viewDocumentBtn: document.getElementById("view-document-btn"),
    viewSlidesBtn: document.getElementById("view-slides-btn"),
    fileSwitcher: document.getElementById("file-switcher"),
    refreshFilesBtn: document.getElementById("refresh-files-btn"),
    currentPathChip: document.getElementById("current-path-chip"),
    sessionMeta: document.getElementById("session-meta"),
    autosaveMeta: document.getElementById("autosave-meta"),
    deleteBtn: document.getElementById("delete-btn"),
    templateCatalog: document.getElementById("template-catalog"),
    templateSelect: document.getElementById("template-select"),
    selectedTemplateName: document.getElementById("selected-template-name"),
    selectedTemplateDesc: document.getElementById("selected-template-desc"),
    selectedTemplateCategory: document.getElementById("selected-template-category"),
    selectedTemplateVariables: document.getElementById("selected-template-variables"),
    newFilePath: document.getElementById("new-file-path"),
    templateProject: document.getElementById("template-project"),
    templateCreateBtn: document.getElementById("template-create-btn"),
    insertReportBtn: document.getElementById("insert-report-btn"),
    editor: document.getElementById("editor"),
    editorTitle: document.getElementById("editor-title"),
    editorState: document.getElementById("editor-state"),
    versionState: document.getElementById("version-state"),
    draftState: document.getElementById("draft-state"),
    wordCount: document.getElementById("word-count"),
    slideCount: document.getElementById("slide-count"),
    readTime: document.getElementById("read-time"),
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

function resolveExportMode() {
    if (state.activeView === "write") {
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

function draftKey(path) {
    return `${DRAFT_PREFIX}${path || "__new__"}`;
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

function describeDocState(displayPath) {
    if (state.currentFile) {
        return `${state.currentFile}${state.isDirty ? " · 未保存" : " · 已同步"}`;
    }
    if (state.isDirty && displayPath) {
        return `${displayPath} · 未保存`;
    }
    if (state.isDirty) {
        return "未命名草稿 · 待保存";
    }
    return "未选择文件";
}

function renderFileSwitcher() {
    const currentValue = state.currentFile || FILE_SWITCHER_NONE;
    const options = [{ value: FILE_SWITCHER_NONE, label: "未选择文件" }];

    state.cachedFiles.forEach((file) => {
        options.push({
            value: file,
            label: file,
        });
    });

    if (state.currentFile && !state.cachedFiles.includes(state.currentFile)) {
        options.push({
            value: state.currentFile,
            label: `${state.currentFile}（当前）`,
        });
    }

    els.fileSwitcher.innerHTML = options.map((item) => (
        `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`
    )).join("");
    els.fileSwitcher.value = currentValue;
}

function updateDocumentMeta() {
    const displayPath = state.currentFile || els.newFilePath.value.trim();
    const title = baseName(displayPath) || (els.editor.value.trim() ? "未命名文档" : "未选择文件");
    const stateText = describeDocState(displayPath);

    els.editorTitle.textContent = title;
    els.editorState.textContent = stateText;
    els.currentPathChip.textContent = displayPath || "未保存";
    els.deleteBtn.disabled = !state.currentFile;
    renderFileSwitcher();
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

    els.templateView.classList.toggle("hidden", state.activeView !== "template");
    els.writeView.classList.toggle("hidden", state.activeView !== "write");
    els.documentView.classList.toggle("hidden", state.activeView !== "document");
    els.slidesView.classList.toggle("hidden", state.activeView !== "slides");

    els.viewTemplateBtn.classList.toggle("active", state.activeView === "template");
    els.viewWriteBtn.classList.toggle("active", state.activeView === "write");
    els.viewDocumentBtn.classList.toggle("active", state.activeView === "document");
    els.viewSlidesBtn.classList.toggle("active", state.activeView === "slides");

    if (state.activeView !== "write") {
        closeSlashMenu();
    }

    const exportMode = resolveExportMode();
    els.exportBtn.disabled = !exportMode;
    els.exportBtn.textContent = exportMode ? `导出 ${exportMode.toUpperCase()}` : "导出";

    if (updateHash) {
        history.replaceState(null, "", `${window.location.pathname}#${state.activeView}`);
    }
}

function saveDraftToLocal() {
    const payload = {
        path: state.currentFile || "",
        content: els.editor.value,
        version: state.currentVersion,
        updated_at: Date.now(),
    };
    localStorage.setItem(draftKey(state.currentFile), JSON.stringify(payload));
    setDraftLabel(`草稿已缓存 ${formatTimeLabel(payload.updated_at)}`);
}

function clearDraft(path) {
    localStorage.removeItem(draftKey(path));
}

function maybeRestoreDraftForPath(path, serverContent) {
    const raw = localStorage.getItem(draftKey(path));
    if (!raw) {
        return { content: serverContent, restored: false };
    }

    try {
        const draft = JSON.parse(raw);
        if (draft.content === serverContent) {
            clearDraft(path);
            return { content: serverContent, restored: false };
        }

        const recover = window.confirm(
            `检测到本地草稿（${new Date(draft.updated_at).toLocaleString("zh-CN")}），是否恢复？`,
        );
        if (recover) {
            setDraftLabel(`已恢复草稿 ${formatTimeLabel(draft.updated_at)}`);
            return { content: draft.content || serverContent, restored: true };
        }
        clearDraft(path);
    } catch (_error) {
        clearDraft(path);
    }

    return { content: serverContent, restored: false };
}

function maybeRestoreUnsavedDraft() {
    const raw = localStorage.getItem(NEW_DRAFT_KEY);
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

        state.currentFile = "";
        updateVersion(null);
        els.editor.value = draft.content;
        setDirty(true);
        setDraftLabel(`已恢复草稿 ${formatTimeLabel(draft.updated_at)}`);
        refreshDerivedState(draft.content);
        setActiveView("write");
        showStatus("已恢复未命名草稿", "warn");
    } catch (_error) {
        localStorage.removeItem(NEW_DRAFT_KEY);
    }
}

function scheduleDraftAutoSave() {
    if (state.autoSaveTimer) {
        clearTimeout(state.autoSaveTimer);
    }
    state.autoSaveTimer = window.setTimeout(() => {
        saveDraftToLocal();
    }, 1200);
}

async function requestJSON(url, options = {}) {
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    return { res, data };
}

function resolveTargetPath(defaultValue, promptMessage) {
    const inlineValue = els.newFilePath.value.trim();
    const initial = inlineValue || defaultValue;
    const picked = inlineValue || window.prompt(promptMessage, initial);
    if (!picked) {
        return "";
    }
    return picked.endsWith(".md") ? picked : `${picked}.md`;
}

function resolveExportBaseName() {
    if (state.currentFile) {
        const fileName = baseName(state.currentFile) || "note.md";
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
        exportAsPng();
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

function exportAsPng() {
    const sourceText = (
        state.previewMode === "slides"
            ? els.slideStage.innerText
            : els.preview.innerText || els.editor.value
    ).trim();
    if (!sourceText) {
        showStatus("当前内容为空，无法导出图片", "warn");
        return;
    }

    const canvas = document.createElement("canvas");
    const width = 1600;
    const padding = 64;
    const maxTextWidth = width - padding * 2;
    const lineHeight = state.previewMode === "slides" ? 42 : 32;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
        showStatus("当前浏览器不支持图片导出", "error");
        return;
    }

    const title = state.previewMode === "slides"
        ? `${resolveExportBaseName()} - slide-${state.activeSlideIndex + 1}`
        : resolveExportBaseName();

    ctx.font = state.previewMode === "slides"
        ? "28px 'PingFang SC', 'Microsoft YaHei', sans-serif"
        : "20px 'PingFang SC', 'Microsoft YaHei', sans-serif";
    const lines = buildWrappedLines(ctx, sourceText, maxTextWidth);
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
    ctx.font = state.previewMode === "slides"
        ? "26px 'PingFang SC', 'Microsoft YaHei', sans-serif"
        : "20px 'PingFang SC', 'Microsoft YaHei', sans-serif";

    for (const line of lines) {
        if (y > height - padding) {
            break;
        }
        ctx.fillText(line || " ", padding, y);
        y += lineHeight;
    }

    canvas.toBlob((blob) => {
        if (!blob) {
            showStatus("图片导出失败", "error");
            return;
        }
        const suffix = state.previewMode === "slides" ? `-slide-${state.activeSlideIndex + 1}` : "";
        const fileName = `${resolveExportBaseName()}${suffix}.png`;
        triggerDownload(blob, fileName);
        showStatus(`已导出 ${fileName}`, "success");
    }, "image/png");
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

function selectTemplate(templateId) {
    state.selectedTemplateId = templateId || "";
    els.templateSelect.value = templateId || "";

    const selected = state.templates.find((template) => template.id === templateId);
    if (!selected) {
        els.selectedTemplateName.textContent = "选择一个模板";
        els.selectedTemplateDesc.textContent = "选择左侧模板后，在这里填写路径并创建文稿。";
        els.selectedTemplateCategory.textContent = "-";
        els.selectedTemplateVariables.innerHTML = '<span class="token-chip">暂无</span>';
        return;
    }

    els.selectedTemplateName.textContent = selected.name;
    els.selectedTemplateDesc.textContent = selected.description;
    els.selectedTemplateCategory.textContent = selected.category;
    els.selectedTemplateVariables.innerHTML = selected.variables.map((item) => (
        `<span class="token-chip">${escapeHtml(item)}</span>`
    )).join("");
}

function renderTemplateCatalog() {
    els.templateCatalog.innerHTML = "";
    if (!state.templates.length) {
        els.templateCatalog.innerHTML = '<div class="panel-copy">暂无模板</div>';
        selectTemplate("");
        return;
    }

    state.templates.forEach((template) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `template-card${template.id === state.selectedTemplateId ? " active" : ""}`;
        button.innerHTML = `
            <strong>${escapeHtml(template.name)}</strong>
            <p>${escapeHtml(template.description)}</p>
            <small>${escapeHtml(template.category)} · ${template.variables.length} 个变量</small>
        `;
        button.addEventListener("click", () => {
            selectTemplate(template.id);
            renderTemplateCatalog();
        });
        els.templateCatalog.appendChild(button);
    });
}

async function loadTemplates() {
    const { res, data } = await requestJSON("/api/templates");
    if (!res.ok) {
        showStatus(`加载模板失败：${extractErrorDetail(data, "未知错误")}`, "error");
        return;
    }

    state.templates = data.templates || [];
    els.templateSelect.innerHTML = '<option value="">选择模板...</option>';
    state.templates.forEach((template) => {
        const option = document.createElement("option");
        option.value = template.id;
        option.textContent = `${template.name} · ${template.description}`;
        els.templateSelect.appendChild(option);
    });

    if (!state.selectedTemplateId && state.templates.length) {
        state.selectedTemplateId = state.templates[0].id;
    }

    selectTemplate(state.selectedTemplateId);
    renderTemplateCatalog();
}

async function loadFileList() {
    const { res, data } = await requestJSON("/api/files");
    if (!res.ok) {
        showStatus(`加载文件失败：${extractErrorDetail(data, "未知错误")}`, "error");
        return;
    }
    state.cachedFiles = data.files || [];
    renderFileSwitcher();
}

async function openFile(path) {
    if (!path || path === FILE_SWITCHER_NONE) {
        renderFileSwitcher();
        return;
    }

    if (state.isDirty && !window.confirm("当前内容未保存，确认切换文件？")) {
        renderFileSwitcher();
        return;
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

    const restored = maybeRestoreDraftForPath(state.currentFile, data.content);
    els.editor.value = restored.content;
    setDirty(restored.restored);
    if (!restored.restored) {
        setDraftLabel("草稿未缓存");
    }

    refreshDerivedState(restored.content);
    setActiveView("write");
}

async function saveFile(force = false) {
    let targetPath = state.currentFile;
    if (!targetPath) {
        targetPath = resolveTargetPath(
            "untitled.md",
            "请输入文件名（例如：notes.md）",
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
    const { res, data } = await requestJSON("/api/files", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (res.status === 409) {
        const detail = data.detail || {};
        const overwrite = window.confirm("检测到并发修改冲突。是否覆盖远端版本（谨慎）？");
        if (overwrite) {
            return saveFile(true);
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

    state.currentFile = data.path;
    els.newFilePath.value = state.currentFile;
    updateVersion(data.version);
    setDirty(false);
    clearDraft(state.currentFile);
    clearDraft("");
    setDraftLabel(`已保存 ${formatTimeLabel(Date.now())}`);
    refreshDerivedState(els.editor.value);
    await loadFileList();
    showStatus("已保存", "success");
}

async function createBlankFile() {
    if (state.isDirty && !window.confirm("当前内容未保存，确认新建空白草稿？")) {
        return;
    }

    const filePath = resolveTargetPath(
        "scratch/untitled.md",
        "请输入目标文件名（例如：notes.md）",
    );
    if (!filePath) {
        return;
    }

    const title = baseName(filePath).replace(/\.md$/i, "") || "untitled";
    const initialContent = `# ${title}\n\n一句话结论：\n\n## 记录\n- `;

    state.currentFile = "";
    els.newFilePath.value = filePath;
    updateVersion(null);
    els.editor.value = initialContent;
    setDirty(true);
    setDraftLabel("草稿未缓存");
    refreshDerivedState(initialContent);
    setActiveView("write");
    els.editor.focus();
    showStatus("已创建空白草稿", "success");
}

async function createFromTemplate() {
    if (state.isDirty && !window.confirm("当前内容未保存，确认使用模板新建？")) {
        return;
    }

    const templateId = state.selectedTemplateId || els.templateSelect.value;
    if (!templateId) {
        showStatus("请先选择模板", "warn");
        return;
    }

    const filePath = resolveTargetPath(
        "weekly/new.md",
        "请输入新文件名（例如：weekly/2026w10.md）",
    );
    if (!filePath) {
        return;
    }

    const project = els.templateProject.value.trim() || null;
    const createPayload = {
        path: filePath,
        template_id: templateId,
        project,
        force: false,
    };

    let { res, data } = await requestJSON("/api/files/from-template", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(createPayload),
    });

    if (res.status === 409) {
        const overwrite = window.confirm("文件已存在且版本不一致，是否覆盖创建？");
        if (!overwrite) {
            return;
        }
        ({ res, data } = await requestJSON("/api/files/from-template", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...createPayload, force: true }),
        }));
    }

    if (!res.ok) {
        showStatus(`模板创建失败：${extractErrorDetail(data, "未知错误")}`, "error");
        return;
    }

    showStatus("模板文档已创建", "success");
    await loadFileList();
    await openFile(filePath);
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
    if (!state.currentFile) {
        showStatus("请先选择文件", "warn");
        return;
    }

    if (!window.confirm(`确定删除 ${state.currentFile} 吗？`)) {
        return;
    }

    const { res, data } = await requestJSON(`/api/files/${encodeURIComponent(state.currentFile)}`, {
        method: "DELETE",
    });
    if (!res.ok) {
        showStatus(`删除失败：${extractErrorDetail(data, "未知错误")}`, "error");
        return;
    }

    clearDraft(state.currentFile);
    state.currentFile = "";
    els.newFilePath.value = "";
    updateVersion(null);
    els.editor.value = "";
    setDirty(false);
    setDraftLabel("草稿未缓存");
    refreshDerivedState("");
    await loadFileList();
    setActiveView("template");
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
    els.editor.focus();
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

    if (targetCommand.kind === "switch") {
        replaceEditorRange(range.start, range.end, "");
        setActiveView(targetCommand.target || "template");
    }
}

async function handleImageUpload(event) {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) {
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const { res, data } = await requestJSON("/api/upload", {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        showStatus(`上传失败：${extractErrorDetail(data, "未知错误")}`, "error");
        return;
    }

    const markdown = `![${file.name}](${data.url})`;
    if (state.pendingInsertRange) {
        insertPendingAsset(markdown);
    } else {
        replaceEditorRange(els.editor.selectionStart, els.editor.selectionEnd, markdown);
    }
    showStatus("图片已上传", "success");
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
    els.viewTemplateBtn.addEventListener("click", () => setActiveView("template"));
    els.viewWriteBtn.addEventListener("click", () => {
        setActiveView("write");
        els.editor.focus();
    });
    els.viewDocumentBtn.addEventListener("click", () => {
        setPreviewMode("document");
        setActiveView("document");
    });
    els.viewSlidesBtn.addEventListener("click", () => {
        setPreviewMode("slides");
        setActiveView("slides");
    });
}

function bindEvents() {
    bindActionButtons();
    bindViewButtons();

    els.refreshFilesBtn.addEventListener("click", loadFileList);
    els.fileSwitcher.addEventListener("change", () => {
        openFile(els.fileSwitcher.value);
    });
    els.templateCreateBtn.addEventListener("click", createFromTemplate);
    els.insertReportBtn.addEventListener("click", insertReportDeck);
    els.deleteBtn.addEventListener("click", deleteFile);
    els.exportBtn.addEventListener("click", exportCurrentNote);
    els.presentationPrevBtn.addEventListener("click", () => changeSlide(-1));
    els.presentationNextBtn.addEventListener("click", () => changeSlide(1));
    els.presentationCloseBtn.addEventListener("click", stopPresentation);

    els.editor.addEventListener("input", handleEditorInput);
    els.editor.addEventListener("click", syncActiveSlideFromCursor);
    els.editor.addEventListener("keyup", syncActiveSlideFromCursor);

    els.assetInsertBtn.addEventListener("click", insertRemoteAsset);
    els.assetUploadBtn.addEventListener("click", () => {
        els.imageUpload.click();
    });
    els.assetCancelBtn.addEventListener("click", () => {
        closeAssetModal();
        state.pendingInsertRange = null;
    });
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
    setActiveView(normalizeView(window.location.hash.replace("#", "")), { updateHash: false });
    await loadSession();
    await loadTemplates();
    await loadFileList();
    maybeRestoreUnsavedDraft();
}

bootstrap();
