const DRAFT_PREFIX = "benben:draft:";
const NEW_DRAFT_KEY = `${DRAFT_PREFIX}__new__`;
const VIEW_NAMES = ["overview", "write", "present"];

const state = {
    currentFile: "",
    currentVersion: null,
    currentUser: null,
    isDirty: false,
    autoSaveTimer: null,
    cachedFiles: [],
    previewMode: "document",
    slides: [],
    activeSlideIndex: 0,
    overlayOpen: false,
    statusTimer: null,
    activeView: "overview",
};

const els = {
    overviewView: document.getElementById("overview-view"),
    writeView: document.getElementById("write-view"),
    presentView: document.getElementById("present-view"),
    viewOverviewBtn: document.getElementById("view-overview-btn"),
    viewWriteBtn: document.getElementById("view-write-btn"),
    viewPresentBtn: document.getElementById("view-present-btn"),
    goWriteBtn: document.getElementById("go-write-btn"),
    goPresentBtn: document.getElementById("go-present-btn"),
    editor: document.getElementById("editor"),
    preview: document.getElementById("preview"),
    fileList: document.getElementById("file-list"),
    fileFilter: document.getElementById("file-filter"),
    templateSelect: document.getElementById("template-select"),
    templateProject: document.getElementById("template-project"),
    newFilePath: document.getElementById("new-file-path"),
    exportFormat: document.getElementById("export-format"),
    versionState: document.getElementById("version-state"),
    editorState: document.getElementById("editor-state"),
    editorTitle: document.getElementById("editor-title"),
    currentPath: document.getElementById("current-path"),
    wordCount: document.getElementById("word-count"),
    slideCount: document.getElementById("slide-count"),
    readTime: document.getElementById("read-time"),
    overviewFileName: document.getElementById("overview-file-name"),
    overviewFileState: document.getElementById("overview-file-state"),
    overviewCurrentPath: document.getElementById("overview-current-path"),
    overviewWordCount: document.getElementById("overview-word-count"),
    overviewSlideCount: document.getElementById("overview-slide-count"),
    overviewReadTime: document.getElementById("overview-read-time"),
    overviewSummary: document.getElementById("overview-summary"),
    sessionMeta: document.getElementById("session-meta"),
    autosaveMeta: document.getElementById("autosave-meta"),
    draftState: document.getElementById("draft-state"),
    status: document.getElementById("status"),
    deleteBtn: document.getElementById("delete-btn"),
    imageUpload: document.getElementById("image-upload"),
    documentMode: document.getElementById("document-preview-mode"),
    slidesMode: document.getElementById("slides-preview-mode"),
    modeDocumentBtn: document.getElementById("mode-document-btn"),
    modeSlidesBtn: document.getElementById("mode-slides-btn"),
    slideStage: document.getElementById("slide-stage"),
    slideStrip: document.getElementById("slide-strip"),
    slidePosition: document.getElementById("slide-position"),
    presentationOverlay: document.getElementById("presentation-overlay"),
    presentationStage: document.getElementById("presentation-stage"),
    presentationPosition: document.getElementById("presentation-position"),
    presentationCloseBtn: document.getElementById("presentation-close-btn"),
    prevSlideBtn: document.getElementById("prev-slide-btn"),
    nextSlideBtn: document.getElementById("next-slide-btn"),
    presentationPrevBtn: document.getElementById("presentation-prev-btn"),
    presentationNextBtn: document.getElementById("presentation-next-btn"),
    refreshFilesBtn: document.getElementById("refresh-files-btn"),
    templateCreateBtn: document.getElementById("template-create-btn"),
    insertReportBtn: document.getElementById("insert-report-btn"),
    insertSlideBtn: document.getElementById("insert-slide-btn"),
    insertHeadingBtn: document.getElementById("insert-heading-btn"),
    insertSummaryBtn: document.getElementById("insert-summary-btn"),
    insertChecklistBtn: document.getElementById("insert-checklist-btn"),
    uploadImageBtn: document.getElementById("upload-image-btn"),
    focusSlideBtn: document.getElementById("focus-slide-btn"),
    exportBtn: document.getElementById("export-btn"),
};

if (window.marked && typeof window.marked.setOptions === "function") {
    window.marked.setOptions({
        breaks: true,
        gfm: true,
    });
}

function normalizeView(view) {
    return VIEW_NAMES.includes(view) ? view : "overview";
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
            summary: markdownToPlainText(rawMarkdown).slice(0, 82) || "继续补充这一页的要点",
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

function updateDocumentMeta() {
    const displayPath = state.currentFile || els.newFilePath.value.trim();
    const title = baseName(displayPath) || (els.editor.value.trim() ? "未命名文档" : "未选择文件");
    const stateText = describeDocState(displayPath);

    els.editorTitle.textContent = title;
    els.editorState.textContent = stateText;
    els.currentPath.textContent = displayPath || "未保存";

    els.overviewFileName.textContent = title;
    els.overviewFileState.textContent = state.currentFile
        ? stateText
        : (els.editor.value.trim() ? "你有一份未保存草稿。" : "从文档库打开一个 Markdown，或者直接新建。");
    els.overviewCurrentPath.textContent = displayPath || "未保存";
    els.deleteBtn.disabled = !state.currentFile;
}

function setDirty(nextDirty) {
    state.isDirty = nextDirty;
    updateDocumentMeta();
}

function updateMetrics(content) {
    const density = countContentDensity(content);
    const totalSlides = state.slides.length || 1;
    const readLabel = `${estimateReadMinutes(density)} 分钟`;
    const densityLabel = density ? `${density} 字` : "0";

    els.wordCount.textContent = densityLabel;
    els.slideCount.textContent = String(totalSlides);
    els.readTime.textContent = readLabel;

    els.overviewWordCount.textContent = densityLabel;
    els.overviewSlideCount.textContent = String(totalSlides);
    els.overviewReadTime.textContent = readLabel;
    els.overviewSummary.textContent = markdownToPlainText(content).slice(0, 220)
        || "这里会显示当前文档的摘要。当前还没有打开任何笔记。";
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

    els.slidePosition.textContent = `第 ${state.activeSlideIndex + 1} / ${totalSlides} 页`;
    els.presentationPosition.textContent = `第 ${state.activeSlideIndex + 1} / ${totalSlides} 页`;
    els.modeSlidesBtn.textContent = totalSlides > 1 ? `幻灯片 (${totalSlides})` : "幻灯片";

    renderSlideStage(
        els.slideStage,
        activeSlide,
        "## 空白页\n\n继续在写作页补这一页内容。",
    );
    renderSlideStage(
        els.presentationStage,
        activeSlide,
        "# 空白页\n\n继续在写作页补充内容。",
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
    els.overviewView.classList.toggle("hidden", state.activeView !== "overview");
    els.writeView.classList.toggle("hidden", state.activeView !== "write");
    els.presentView.classList.toggle("hidden", state.activeView !== "present");

    els.viewOverviewBtn.classList.toggle("active", state.activeView === "overview");
    els.viewWriteBtn.classList.toggle("active", state.activeView === "write");
    els.viewPresentBtn.classList.toggle("active", state.activeView === "present");

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
    const format = els.exportFormat.value || "txt";
    if (format === "png") {
        exportAsPng();
        return;
    }

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
    background.addColorStop(0, "#fbf6ef");
    background.addColorStop(1, "#ecf4ef");
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, width, height);

    let y = padding;
    ctx.fillStyle = "#1b1814";
    ctx.font = "bold 38px 'PingFang SC', 'Microsoft YaHei', sans-serif";
    ctx.fillText(title, padding, y);
    y += lineHeight + 12;

    ctx.font = "18px 'PingFang SC', 'Microsoft YaHei', sans-serif";
    ctx.fillStyle = "#6f6458";
    ctx.fillText(`导出时间：${new Date().toLocaleString("zh-CN")}`, padding, y);
    y += lineHeight + 8;

    ctx.strokeStyle = "#d2c9ba";
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();
    y += lineHeight;

    ctx.fillStyle = "#1b1814";
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

async function loadTemplates() {
    const { res, data } = await requestJSON("/api/templates");
    if (!res.ok) {
        showStatus(`加载模板失败：${extractErrorDetail(data, "未知错误")}`, "error");
        return;
    }

    els.templateSelect.innerHTML = '<option value="">选择模板...</option>';
    for (const tpl of data.templates || []) {
        const option = document.createElement("option");
        option.value = tpl.id;
        option.textContent = `${tpl.name} · ${tpl.description}`;
        els.templateSelect.appendChild(option);
    }
}

function renderFileList() {
    const keyword = els.fileFilter.value.trim().toLowerCase();
    const filtered = state.cachedFiles.filter((file) => file.toLowerCase().includes(keyword));
    els.fileList.innerHTML = "";

    if (!filtered.length) {
        const empty = document.createElement("div");
        empty.className = "empty-list";
        empty.textContent = keyword ? "没有匹配的文件" : "还没有 Markdown 文件";
        els.fileList.appendChild(empty);
        return;
    }

    filtered.forEach((file) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `file-item${file === state.currentFile ? " active" : ""}`;
        button.innerHTML = `
            <strong>${escapeHtml(baseName(file) || file)}</strong>
            <small>${escapeHtml(file)}</small>
        `;
        button.addEventListener("click", () => {
            openFile(file);
        });
        els.fileList.appendChild(button);
    });
}

async function loadFileList() {
    const { res, data } = await requestJSON("/api/files");
    if (!res.ok) {
        const detail = extractErrorDetail(data, "未知错误");
        els.fileList.innerHTML = `<div class="empty-list">${escapeHtml(detail)}</div>`;
        showStatus(`加载文件列表失败：${detail}`, "error");
        return;
    }
    state.cachedFiles = data.files || [];
    renderFileList();
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

async function openFile(path) {
    if (state.isDirty && !window.confirm("当前内容未保存，确认切换文件？")) {
        return;
    }

    if (!path) {
        state.currentFile = "";
        els.newFilePath.value = "";
        updateVersion(null);
        els.editor.value = "";
        setDirty(false);
        setDraftLabel("草稿未缓存");
        refreshDerivedState("");
        renderFileList();
        setActiveView("overview");
        return;
    }

    const { res, data } = await requestJSON(`/api/files/${encodeURIComponent(path)}`);
    if (!res.ok) {
        showStatus(`加载失败：${extractErrorDetail(data, "未知错误")}`, "error");
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
    renderFileList();
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
    showStatus("已创建空白草稿", "success");
}

async function createFromTemplate() {
    if (state.isDirty && !window.confirm("当前内容未保存，确认使用模板新建？")) {
        return;
    }

    const templateId = els.templateSelect.value;
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

function uploadImage() {
    els.imageUpload.click();
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

    insertAtCursor(`![${file.name}](${data.url})`);
    showStatus("图片已上传", "success");
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
    setActiveView("overview");
    showStatus("文件已删除", "success");
}

function handleEditorInput() {
    refreshDerivedState(els.editor.value);
    setDirty(true);
    scheduleDraftAutoSave();
}

function insertAtCursor(snippet) {
    const start = els.editor.selectionStart;
    const end = els.editor.selectionEnd;
    const before = els.editor.value.slice(0, start);
    const after = els.editor.value.slice(end);
    const nextValue = before + snippet + after;

    els.editor.value = nextValue;
    const nextCursor = start + snippet.length;
    els.editor.focus();
    els.editor.setSelectionRange(nextCursor, nextCursor);
    handleEditorInput();
}

function insertSlideBreak() {
    if (state.activeView !== "write") {
        setActiveView("write");
    }
    const needsLeadingBreak = els.editor.selectionStart > 0
        && !els.editor.value.slice(0, els.editor.selectionStart).endsWith("\n\n");
    const prefix = needsLeadingBreak ? "\n\n" : "";
    insertAtCursor(`${prefix}---\n\n`);
}

function insertHeadingBlock() {
    setActiveView("write");
    insertAtCursor("## 小节标题\n\n- 要点 1\n- 要点 2\n");
}

function insertSummaryBlock() {
    setActiveView("write");
    insertAtCursor("> 核心结论：\n> \n");
}

function insertChecklistBlock() {
    setActiveView("write");
    insertAtCursor("- [ ] 待办项 1\n- [ ] 待办项 2\n");
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
        els.editor.value = deck;
        els.editor.focus();
        handleEditorInput();
        showStatus("已插入汇报骨架", "success");
        return;
    }

    const append = window.confirm("当前文档已有内容。要把汇报骨架插入到光标位置吗？");
    if (!append) {
        return;
    }
    insertAtCursor(`\n\n${deck}`);
    showStatus("已插入汇报骨架", "success");
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
    const documentActive = mode === "document";
    els.documentMode.classList.toggle("hidden", !documentActive);
    els.slidesMode.classList.toggle("hidden", documentActive);
    els.modeDocumentBtn.classList.toggle("active", documentActive);
    els.modeSlidesBtn.classList.toggle("active", !documentActive);
    els.modeDocumentBtn.setAttribute("aria-pressed", documentActive ? "true" : "false");
    els.modeSlidesBtn.setAttribute("aria-pressed", documentActive ? "false" : "true");
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
}

function startPresentation() {
    if (!els.editor.value.trim()) {
        showStatus("当前内容为空，无法放映", "warn");
        return;
    }

    setActiveView("present");
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
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        saveFile();
        return;
    }

    if (event.altKey && event.shiftKey && event.key.toLowerCase() === "s") {
        event.preventDefault();
        insertSlideBreak();
        return;
    }

    if (event.altKey && event.shiftKey && event.key.toLowerCase() === "p") {
        event.preventDefault();
        startPresentation();
        return;
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
    els.viewOverviewBtn.addEventListener("click", () => setActiveView("overview"));
    els.viewWriteBtn.addEventListener("click", () => setActiveView("write"));
    els.viewPresentBtn.addEventListener("click", () => setActiveView("present"));
    els.goWriteBtn.addEventListener("click", () => setActiveView("write"));
    els.goPresentBtn.addEventListener("click", () => {
        setActiveView("present");
        if (state.slides.length > 1) {
            setPreviewMode("slides");
        }
    });

    document.querySelectorAll("[data-switch-view]").forEach((button) => {
        button.addEventListener("click", () => {
            const target = normalizeView(button.getAttribute("data-switch-view"));
            setActiveView(target);
        });
    });
}

function bindEvents() {
    bindActionButtons();
    bindViewButtons();

    els.fileFilter.addEventListener("input", renderFileList);
    els.refreshFilesBtn.addEventListener("click", loadFileList);
    els.templateCreateBtn.addEventListener("click", createFromTemplate);
    els.insertReportBtn.addEventListener("click", insertReportDeck);
    els.insertSlideBtn.addEventListener("click", insertSlideBreak);
    els.insertHeadingBtn.addEventListener("click", insertHeadingBlock);
    els.insertSummaryBtn.addEventListener("click", insertSummaryBlock);
    els.insertChecklistBtn.addEventListener("click", insertChecklistBlock);
    els.uploadImageBtn.addEventListener("click", uploadImage);
    els.deleteBtn.addEventListener("click", deleteFile);
    els.exportBtn.addEventListener("click", exportCurrentNote);
    els.focusSlideBtn.addEventListener("click", focusCurrentSlideInEditor);

    els.modeDocumentBtn.addEventListener("click", () => setPreviewMode("document"));
    els.modeSlidesBtn.addEventListener("click", () => setPreviewMode("slides"));

    els.prevSlideBtn.addEventListener("click", () => changeSlide(-1));
    els.nextSlideBtn.addEventListener("click", () => changeSlide(1));
    els.presentationPrevBtn.addEventListener("click", () => changeSlide(-1));
    els.presentationNextBtn.addEventListener("click", () => changeSlide(1));
    els.presentationCloseBtn.addEventListener("click", stopPresentation);

    els.editor.addEventListener("input", handleEditorInput);
    els.editor.addEventListener("click", syncActiveSlideFromCursor);
    els.editor.addEventListener("keyup", syncActiveSlideFromCursor);
    els.imageUpload.addEventListener("change", handleImageUpload);

    document.addEventListener("selectionchange", syncActiveSlideFromCursor);
    document.addEventListener("keydown", handleGlobalShortcuts);
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
    setActiveView(normalizeView(window.location.hash.replace("#", "")), { updateHash: false });
    await loadSession();
    await loadTemplates();
    await loadFileList();
    maybeRestoreUnsavedDraft();
}

bootstrap();
