import {
  apiBase,
  apiFetch,
  bookHref,
  defaultInsertParentId,
  editorHref,
  fillParentSelect,
  getBookIdFromPath,
  handleError,
  loadBookContext,
  loadCurrentUser,
  outlineHref,
  primeDocumentCrumb,
  previewHref,
  publishHref,
  renderDocumentCrumb,
  renderOutlineList,
  renderPublishList,
  setStatus,
  slugify,
  toast,
  withBusy,
} from "/app/core.js";

const bookId = getBookIdFromPath();

const state = {
  slugTouched: false,
  currentDocument: null,
  currentTree: [],
};

const els = {
  bookTitleHeading: document.getElementById("bookTitleHeading"),
  bookMetaLine: document.getElementById("bookMetaLine"),
  tabSettingsLink: document.getElementById("tabSettingsLink"),
  tabOutlineLink: document.getElementById("tabOutlineLink"),
  tabRootEditorLink: document.getElementById("tabRootEditorLink"),
  tabRootPreviewLink: document.getElementById("tabRootPreviewLink"),
  tabPublishLink: document.getElementById("tabPublishLink"),
  newPageForm: document.getElementById("newPageForm"),
  newPageTitle: document.getElementById("newPageTitle"),
  newPageSlug: document.getElementById("newPageSlug"),
  newPageKind: document.getElementById("newPageKind"),
  newPageParent: document.getElementById("newPageParent"),
  newPageOrder: document.getElementById("newPageOrder"),
  createPageBtn: document.getElementById("createPageBtn"),
  outlineTree: document.getElementById("outlineTree"),
  publishedLink: document.getElementById("publishedLink"),
  publishList: document.getElementById("publishList"),
};

function setText(el, value) {
  if (!el) {
    return;
  }
  el.textContent = value;
}

function renderDocument(doc, tree, publishes) {
  state.currentDocument = doc;
  state.currentTree = tree;
  document.title = `${doc.title} | Benfast 目录管理`;
  setText(els.bookTitleHeading, doc.title);
  renderDocumentCrumb(doc.id, doc.title);
  setText(els.bookMetaLine, `slug=${doc.slug} · ${doc.page_count || 0} 页 · updated_at=${doc.updated_at || "-"}`);

  els.tabSettingsLink.href = bookHref(doc.id);
  els.tabOutlineLink.href = outlineHref(doc.id);
  els.tabRootEditorLink.href = editorHref(doc.id, doc.root_page_id);
  els.tabRootPreviewLink.href = previewHref(doc.id, doc.root_page_id);
  els.tabPublishLink.href = publishHref(doc.id);

  renderOutlineList(els.outlineTree, tree, { activeBookId: doc.id });
  fillParentSelect(els.newPageParent, tree, {
    selectedId: defaultInsertParentId(doc, null),
  });
  if (els.publishedLink) {
    els.publishedLink.innerHTML = doc.published_url
      ? `正式站入口：<a class="inline-link" href="${doc.published_url}" target="_blank" rel="noreferrer">${doc.published_url}</a>`
      : "当前还没有发布记录。";
  }
  if (els.publishList) {
    renderPublishList(els.publishList, publishes);
  }
}

async function refresh() {
  const { book, tree, publishes } = await loadBookContext(bookId);
  renderDocument(book, tree, publishes);
}

async function createPage() {
  if (!state.currentDocument) {
    return;
  }
  const title = els.newPageTitle.value.trim();
  const slug = els.newPageSlug.value.trim();
  const kind = els.newPageKind.value;
  if (!title || !slug) {
    throw new Error("新增节点至少需要标题和 slug。");
  }
  const starter = kind === "chapter"
    ? `# ${title}\n\n本章节用于组织一组相关页面，也可以在这里写章节导语。`
    : `# ${title}\n\n请在这里继续编写正文。`;
  const page = await apiFetch(`${apiBase}/books/${bookId}/pages`, {
    method: "POST",
    body: JSON.stringify({
      parent_id: els.newPageParent.value || null,
      title,
      slug,
      kind,
      order: Number(els.newPageOrder.value || 20),
      content: starter,
    }),
  });
  toast("目录节点已创建");
  window.location.href = editorHref(bookId, page.id);
}

function bindEvents() {
  els.newPageTitle.addEventListener("input", () => {
    if (!state.slugTouched) {
      els.newPageSlug.value = slugify(els.newPageTitle.value);
    }
  });
  els.newPageSlug.addEventListener("input", () => {
    state.slugTouched = Boolean(els.newPageSlug.value.trim());
  });
  els.newPageForm.addEventListener("submit", (event) => {
    event.preventDefault();
    withBusy(els.createPageBtn, "创建中...", createPage).catch(handleError);
  });
}

async function init() {
  if (!bookId) {
    throw new Error("缺少文档 ID。");
  }
  primeDocumentCrumb(bookId);
  setStatus("正在载入目录管理...", "neutral");
  await loadCurrentUser();
  bindEvents();
  await refresh();
  setStatus("目录管理页已就绪。", "success");
}

init().catch(handleError);
