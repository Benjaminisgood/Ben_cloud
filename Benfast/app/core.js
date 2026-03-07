const apiBase = "/api/v1/labdocs";

export { apiBase };

export function escapeHtml(raw) {
  return String(raw ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function slugify(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-+/g, "-");
}

export function toast(message, isError = false) {
  const el = document.getElementById("toast");
  if (!el) {
    return;
  }
  el.textContent = message;
  el.classList.add("show");
  el.classList.toggle("error", isError);
  window.clearTimeout(toast._timer);
  toast._timer = window.setTimeout(() => {
    el.classList.remove("show");
  }, 2600);
}

export function setStatus(message, tone = "neutral") {
  const el = document.getElementById("appStatus");
  if (!el) {
    return;
  }
  el.textContent = message;
  el.dataset.tone = tone;
}

function initShellChrome() {
  const header = document.querySelector(".shell-header");
  if (!header || header.dataset.chromeReady === "1") {
    return;
  }
  header.dataset.chromeReady = "1";

  let lastY = window.scrollY;
  let ticking = false;

  const sync = () => {
    const currentY = window.scrollY;
    if (currentY <= 24) {
      header.classList.remove("is-condensed");
      lastY = currentY;
      ticking = false;
      return;
    }

    if (currentY > lastY + 10 && currentY > 72) {
      header.classList.add("is-condensed");
    } else if (currentY < lastY - 10) {
      header.classList.remove("is-condensed");
    }

    lastY = currentY;
    ticking = false;
  };

  window.addEventListener(
    "scroll",
    () => {
      if (ticking) {
        return;
      }
      ticking = true;
      window.requestAnimationFrame(sync);
    },
    { passive: true },
  );
}

export async function apiFetch(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(path, {
    credentials: "include",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let errorMessage = `请求失败: ${response.status}`;
    if (response.status === 401) {
      errorMessage = "会话已失效，请从 Benbot 门户重新进入 Benfast。";
    }
    if (response.status === 403) {
      errorMessage = "当前账号没有执行该操作的权限。";
    }
    try {
      const body = await response.json();
      errorMessage = body.msg || body.detail || errorMessage;
    } catch (_error) {
      // ignore parse errors
    }
    throw new Error(errorMessage);
  }

  const body = await response.json();
  if (body.code && body.code !== 200) {
    throw new Error(body.msg || "请求失败");
  }
  return body.data;
}

export async function loadCurrentUser() {
  const user = await apiFetch("/api/v1/base/userinfo");
  const badge = document.getElementById("currentUserBadge");
  if (badge) {
    badge.textContent = `${user.username} · ${user.is_superuser ? "管理员" : "成员"}`;
  }
  return user;
}

export function withBusy(button, pendingLabel, fn) {
  const originalLabel = button.dataset.label || button.textContent;
  button.dataset.label = originalLabel;
  button.disabled = true;
  button.textContent = pendingLabel;
  return Promise.resolve()
    .then(fn)
    .finally(() => {
      button.disabled = false;
      button.textContent = originalLabel;
    });
}

function headingSlug(text, seen = {}) {
  const base = String(text || "")
    .trim()
    .toLowerCase()
    .replace(/[^0-9a-z\u4e00-\u9fff]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "") || "section";
  const count = (seen[base] || 0) + 1;
  seen[base] = count;
  return count === 1 ? base : `${base}-${count}`;
}

function tagHref(tag) {
  return `/kb/tags/${String(tag || "").trim()}/`;
}

function findReferenceNode(tree, query) {
  const raw = String(query || "").trim();
  const nodes = flattenTree(tree || []);
  if (raw === "" || raw === "/" || raw === "index" || raw === "首页") {
    return nodes.find((node) => !String(node.path || "").trim()) || null;
  }

  const normalized = raw.replace(/^\/+|\/+$/g, "");
  let match = nodes.find((node) => String(node.path || "").replace(/^\/+|\/+$/g, "") === normalized);
  if (match) {
    return match;
  }

  const titleMatches = nodes.filter((node) => String(node.title || "").trim() === raw);
  if (titleMatches.length === 1) {
    return titleMatches[0];
  }

  const slugMatches = nodes.filter((node) => String(node.slug || "").trim() === normalized);
  if (slugMatches.length === 1) {
    return slugMatches[0];
  }

  match = nodes.find((node) => String(node.title || "").trim().toLowerCase() === raw.toLowerCase());
  return match || null;
}

function resolveHeadingAnchor(node, title) {
  const wanted = String(title || "").trim();
  const headings = Array.isArray(node?.headings) ? node.headings : [];
  const exact = headings.find((item) => String(item?.title || "").trim() === wanted);
  if (exact?.anchor) {
    return String(exact.anchor);
  }
  const lowered = wanted.toLowerCase();
  const relaxed = headings.find((item) => String(item?.title || "").trim().toLowerCase() === lowered);
  if (relaxed?.anchor) {
    return String(relaxed.anchor);
  }
  return headingSlug(wanted, {});
}

function resolveReferenceToken(token, options = {}) {
  const raw = String(token || "").trim();
  const bookId = options.bookId;
  const currentPage = options.currentPage || null;
  const tree = options.tree || [];
  if (!raw) {
    return null;
  }

  if (raw.toLowerCase().startsWith("tag:") || raw.startsWith("标签:")) {
    const tag = raw.split(":", 2)[1]?.trim();
    return tag ? `[#${tag}](${tagHref(tag)})` : null;
  }

  if (raw.startsWith("#")) {
    const heading = raw.slice(1).trim();
    if (!heading || !currentPage) {
      return null;
    }
    return `[${heading}](#${resolveHeadingAnchor(currentPage, heading)})`;
  }

  const [pageQuery, headingQuery = ""] = raw.split("#", 2);
  const target = findReferenceNode(tree, pageQuery);
  if (!target || !bookId) {
    return null;
  }

  let href = previewHref(bookId, target.id);
  const heading = String(headingQuery || "").trim();
  if (!heading) {
    return `[${String(target.title || raw)}](${href})`;
  }
  href = `${href}#${resolveHeadingAnchor(target, heading)}`;
  if (currentPage && String(target.id) === String(currentPage.id)) {
    return `[${heading}](${href})`;
  }
  return `[${String(target.title || raw)} / ${heading}](${href})`;
}

function linkifyInlineTagsInLine(line) {
  return String(line || "").replace(
    /(^|[^0-9A-Za-z_\-/\u4e00-\u9fff])#([0-9A-Za-z\u4e00-\u9fff][0-9A-Za-z_\-/\u4e00-\u9fff]{0,39})/g,
    (_match, prefix, tag) => `${prefix}[#${tag}](${tagHref(tag)})`,
  );
}

function rewriteCustomMarkdown(raw, options = {}) {
  const lines = String(raw || "").split("\n");
  const output = [];
  let inCode = false;

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (trimmed.startsWith("```")) {
      inCode = !inCode;
      output.push(line);
      return;
    }

    if (inCode) {
      output.push(line);
      return;
    }

    if (/^#{1,6}\s/.test(trimmed)) {
      output.push(line);
      return;
    }

    const tokens = [];
    const lineWithPlaceholders = line.replace(/\[\[([^\[\]]+)\]\]/g, (_match, token) => {
      tokens.push(String(token || ""));
      return `__BENFAST_REF_${tokens.length - 1}__`;
    });

    let rewritten = linkifyInlineTagsInLine(lineWithPlaceholders);
    tokens.forEach((token, index) => {
      rewritten = rewritten.replace(
        `__BENFAST_REF_${index}__`,
        resolveReferenceToken(token, options) || `[[${token}]]`,
      );
    });
    output.push(rewritten);
  });

  return output.join("\n");
}

export function markdownToHtml(raw, options = {}) {
  const lines = rewriteCustomMarkdown(raw, options).split("\n");
  const blocks = [];
  let paragraph = [];
  let listItems = [];
  let inCode = false;
  let codeLines = [];
  const seenHeadings = {};

  const inline = (text) =>
    escapeHtml(text)
      .replace(
        /!\[([^\]]*)\]\(([^)]+)\)/g,
        '<img class="preview-inline-image" src="$2" alt="$1" loading="lazy" />',
      )
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>")
      .replace(
        /\[([^\]]+)\]\(([^)]+)\)/g,
        '<a href="$2" target="_blank" rel="noreferrer">$1</a>',
      );

  const flushParagraph = () => {
    if (!paragraph.length) {
      return;
    }
    blocks.push(`<p>${paragraph.map((item) => inline(item)).join("<br />")}</p>`);
    paragraph = [];
  };

  const flushList = () => {
    if (!listItems.length) {
      return;
    }
    blocks.push(`<ul>${listItems.map((item) => `<li>${inline(item)}</li>`).join("")}</ul>`);
    listItems = [];
  };

  const placeholderMeta = (line) => {
    const match = line.match(/^\[\[benfast-upload\|([^|\]]+)\|([^|\]]*)\]\]$/);
    if (!match) {
      return null;
    }
    return {
      id: match[1],
      label: decodeURIComponent(match[2] || "clipboard-image"),
    };
  };

  lines.forEach((line) => {
    if (line.startsWith("```")) {
      flushParagraph();
      flushList();
      if (inCode) {
        blocks.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        codeLines = [];
        inCode = false;
      } else {
        inCode = true;
      }
      return;
    }

    if (inCode) {
      codeLines.push(line);
      return;
    }

    const trimmed = line.trim();
    if (!trimmed) {
      flushParagraph();
      flushList();
      return;
    }

    const uploadPlaceholder = placeholderMeta(trimmed);
    if (uploadPlaceholder) {
      flushParagraph();
      flushList();
      blocks.push(
        `<div class="preview-upload-placeholder"><strong>正在上传图片</strong><span>${escapeHtml(uploadPlaceholder.label)}</span></div>`,
      );
      return;
    }

    if (trimmed.startsWith("# ")) {
      flushParagraph();
      flushList();
      const title = trimmed.slice(2);
      blocks.push(`<h1 id="${headingSlug(title, seenHeadings)}">${inline(title)}</h1>`);
      return;
    }
    if (trimmed.startsWith("## ")) {
      flushParagraph();
      flushList();
      const title = trimmed.slice(3);
      blocks.push(`<h2 id="${headingSlug(title, seenHeadings)}">${inline(title)}</h2>`);
      return;
    }
    if (trimmed.startsWith("### ")) {
      flushParagraph();
      flushList();
      const title = trimmed.slice(4);
      blocks.push(`<h3 id="${headingSlug(title, seenHeadings)}">${inline(title)}</h3>`);
      return;
    }
    if (trimmed.startsWith("- ")) {
      flushParagraph();
      listItems.push(trimmed.slice(2));
      return;
    }

    flushList();
    paragraph.push(trimmed);
  });

  flushParagraph();
  flushList();
  if (codeLines.length) {
    blocks.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  }
  return blocks.join("\n");
}

export function renderPreview(el, content, options = {}) {
  el.innerHTML = markdownToHtml(content || "", options);
}

export function getPathParts() {
  return window.location.pathname.replace(/^\/app\/?/, "").split("/").filter(Boolean);
}

export function getBookIdFromPath() {
  const parts = getPathParts();
  if (parts[0] !== "books" || parts.length < 2) {
    return null;
  }
  return parts[1];
}

export function getPageIdFromPath() {
  const parts = getPathParts();
  if (parts[0] !== "books" || parts[2] !== "pages" || parts.length < 4) {
    return null;
  }
  return parts[3];
}

export function bookHref(bookId) {
  return `/app/books/${bookId}/settings/`;
}

const documentTitleCachePrefix = "benfast:document-title:";

function documentTitleCacheKey(bookId) {
  return `${documentTitleCachePrefix}${bookId}`;
}

function readDocumentTitleCache(bookId) {
  if (!bookId) {
    return "";
  }
  try {
    return window.sessionStorage.getItem(documentTitleCacheKey(bookId)) || "";
  } catch (_error) {
    return "";
  }
}

export function writeDocumentTitleCache(bookId, title) {
  if (!bookId || !title) {
    return;
  }
  try {
    window.sessionStorage.setItem(documentTitleCacheKey(bookId), String(title));
  } catch (_error) {
    // ignore session storage errors
  }
}

export function primeDocumentCrumb(bookId, fallback = "当前文档") {
  const crumb = document.getElementById("documentCrumbLink");
  if (!crumb) {
    return;
  }
  if (bookId) {
    crumb.href = bookHref(bookId);
  }
  crumb.textContent = readDocumentTitleCache(bookId) || fallback;
}

export function renderDocumentCrumb(bookId, title) {
  const crumb = document.getElementById("documentCrumbLink");
  if (!crumb) {
    return;
  }
  crumb.href = bookHref(bookId);
  crumb.textContent = title;
  writeDocumentTitleCache(bookId, title);
}

export function outlineHref(bookId) {
  return `/app/books/${bookId}/outline/`;
}

export function editorHref(bookId, pageId) {
  return `/app/books/${bookId}/pages/${pageId}/`;
}

export function previewHref(bookId, pageId) {
  return `/app/books/${bookId}/pages/${pageId}/preview/`;
}

export function publishHref(bookId) {
  return `/app/books/${bookId}/publish/`;
}

export async function loadBooks(query = "") {
  const params = new URLSearchParams();
  if (query.trim()) {
    params.set("q", query.trim());
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiFetch(`${apiBase}/books${suffix}`);
}

export async function loadBookContext(bookId) {
  const [book, tree, publishes] = await Promise.all([
    apiFetch(`${apiBase}/books/${bookId}`),
    apiFetch(`${apiBase}/books/${bookId}/tree`),
    apiFetch(`${apiBase}/books/${bookId}/publishes`),
  ]);
  return { book, tree, publishes };
}

export async function loadPageContext(pageId) {
  const [page, revisions, comments, lock] = await Promise.all([
    apiFetch(`${apiBase}/pages/${pageId}`),
    apiFetch(`${apiBase}/pages/${pageId}/revisions?limit=30`),
    apiFetch(`${apiBase}/pages/${pageId}/comments`),
    apiFetch(`${apiBase}/pages/${pageId}/lock`),
  ]);
  return { page, revisions, comments, lock };
}

export function flattenTree(nodes, depth = 0, acc = []) {
  nodes.forEach((node) => {
    acc.push({ ...node, depth });
    flattenTree(node.children || [], depth + 1, acc);
  });
  return acc;
}

export function isRootNode(node) {
  return Boolean(node?.is_root) || String(node?.kind || "") === "root";
}

export function allowsChildren(node) {
  if (!node) {
    return false;
  }
  if (typeof node.allows_children === "boolean") {
    return node.allows_children;
  }
  return isRootNode(node) || String(node.kind || "") === "chapter";
}

export function kindLabel(node) {
  if (!node) {
    return "节点";
  }
  if (node.kind_label) {
    return node.kind_label === "书籍首页" ? "文档首页" : node.kind_label;
  }
  if (isRootNode(node)) {
    return "文档首页";
  }
  return String(node.kind || "") === "chapter" ? "章节" : "正文页";
}

export function getRootNode(nodes) {
  return flattenTree(nodes).find((node) => isRootNode(node)) || null;
}

export function visibleOutlineNodes(nodes) {
  const root = getRootNode(nodes);
  if (!root) {
    return nodes;
  }
  return nodes.length === 1 && nodes[0].id === root.id
    ? root.children || []
    : nodes.filter((node) => node.id !== root.id);
}

export function defaultInsertParentId(book, currentPage) {
  if (!book) {
    return "";
  }
  if (!currentPage) {
    return book.root_page_id;
  }
  if (allowsChildren(currentPage)) {
    return currentPage.id;
  }
  return currentPage.parent_id || book.root_page_id;
}

export function collectDescendantIds(nodes, targetId) {
  const descendants = new Set();

  function walk(list) {
    list.forEach((node) => {
      if (node.id === targetId) {
        const collect = (children) => {
          children.forEach((child) => {
            descendants.add(child.id);
            collect(child.children || []);
          });
        };
        collect(node.children || []);
      } else {
        walk(node.children || []);
      }
    });
  }

  walk(nodes);
  return descendants;
}

export function fillParentSelect(selectEl, nodes, options = {}) {
  const {
    currentPageId = null,
    excludedDescendants = new Set(),
    selectedId = "",
  } = options;

  selectEl.innerHTML = "";

  flattenTree(nodes).forEach((node) => {
    if (node.id === currentPageId || excludedDescendants.has(node.id) || !allowsChildren(node)) {
      return;
    }
    const option = document.createElement("option");
    option.value = node.id;
    const label = isRootNode(node)
      ? "文档首页"
      : `${"· ".repeat(Math.max(0, node.depth - 1))}${node.title}`;
    option.textContent = `${label} · ${kindLabel(node)}`;
    selectEl.appendChild(option);
  });

  if (selectedId) {
    selectEl.value = selectedId;
  }
}

export function renderOutlineList(target, nodes, options = {}) {
  const {
    activePageId = null,
    activeBookId = null,
    hrefBuilder = null,
    showRoot = false,
  } = options;

  target.innerHTML = "";
  const outlineNodes = showRoot ? nodes : visibleOutlineNodes(nodes);
  if (!outlineNodes.length) {
    const li = document.createElement("li");
    li.className = "record-item";
    li.textContent = "当前还没有可展示的目录节点。";
    target.appendChild(li);
    return;
  }

  function build(list) {
    const ul = document.createElement("ul");
    ul.className = "tree-list";
    list.forEach((node) => {
      const li = document.createElement("li");
      li.className = "tree-item";
      const link = document.createElement("a");
      link.className = "tree-link";
      if (activePageId && node.id === activePageId) {
        link.classList.add("is-active");
      }
      link.href = hrefBuilder
        ? hrefBuilder(node)
        : activeBookId
          ? editorHref(activeBookId, node.id)
          : "#";
      const childHint = allowsChildren(node) ? "可包含子节点" : "正文内容页";
      link.innerHTML = `<strong>${escapeHtml(node.title)}</strong><span>${escapeHtml(kindLabel(node))} · ${childHint} · v${node.version} · ${escapeHtml(node.path || "/")}</span>`;
      li.appendChild(link);

      if (node.children && node.children.length) {
        li.appendChild(build(node.children));
      }
      ul.appendChild(li);
    });
    return ul;
  }

  const tree = build(outlineNodes);
  Array.from(tree.children).forEach((item) => target.appendChild(item));
}

export function renderPublishList(target, publishes) {
  target.innerHTML = "";
  if (!publishes.length) {
    const li = document.createElement("li");
    li.className = "record-item";
    li.textContent = "当前还没有发布记录。";
    target.appendChild(li);
    return;
  }

  publishes.forEach((item) => {
    const li = document.createElement("li");
    li.className = "record-item";
    li.innerHTML = `
      <strong>${escapeHtml(item.message || "publish document")}</strong>
      <span>${escapeHtml(item.published_at)} · ${escapeHtml(item.published_by_name)}</span>
      <a class="tiny-link" href="${item.published_url}" target="_blank" rel="noreferrer">${item.published_url}</a>
    `;
    target.appendChild(li);
  });
}

export function renderCommentList(target, comments) {
  target.innerHTML = "";
  if (!comments.length) {
    const li = document.createElement("li");
    li.className = "record-item";
    li.textContent = "当前页面还没有评论。";
    target.appendChild(li);
    return;
  }
  comments.forEach((item) => {
    const li = document.createElement("li");
    li.className = "record-item";
    li.innerHTML = `
      <strong>${escapeHtml(item.author_name)}</strong>
      <span>${escapeHtml(item.created_at)}</span>
      <p>${escapeHtml(item.content)}</p>
      <small>${item.anchor ? `锚点：${escapeHtml(item.anchor)}` : ""}</small>
    `;
    target.appendChild(li);
  });
}

export function renderRevisionList(target, revisions) {
  target.innerHTML = "";
  if (!revisions.length) {
    const li = document.createElement("li");
    li.className = "record-item";
    li.textContent = "当前页面还没有修订记录。";
    target.appendChild(li);
    return;
  }
  revisions.forEach((item) => {
    const li = document.createElement("li");
    li.className = "record-item";
    li.innerHTML = `
      <strong>v${item.version} · ${escapeHtml(item.editor_name)}</strong>
      <span>${escapeHtml(item.change_note || "update")} · ${escapeHtml(item.edited_at)}</span>
    `;
    target.appendChild(li);
  });
}

export function handleError(error) {
  const message = error instanceof Error ? error.message : String(error || "未知错误");
  toast(message, true);
  setStatus(message, "error");
}

initShellChrome();
