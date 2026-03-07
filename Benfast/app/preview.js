import {
  apiBase,
  apiFetch,
  bookHref,
  editorHref,
  getBookIdFromPath,
  getPageIdFromPath,
  handleError,
  kindLabel,
  loadBookContext,
  loadCurrentUser,
  loadPageContext,
  markdownToHtml,
  outlineHref,
  primeDocumentCrumb,
  previewHref,
  publishHref,
  renderDocumentCrumb,
  renderCommentList,
  renderOutlineList,
  renderRevisionList,
  setStatus,
  toast,
  withBusy,
} from "/app/core.js";

const bookId = getBookIdFromPath();
const pageId = getPageIdFromPath();

const state = {
  currentDocument: null,
  currentTree: [],
  currentPage: null,
  currentLock: null,
  currentUser: null,
};

const els = {
  pageTitleHeading: document.getElementById("pageTitleHeading"),
  pageMetaHeading: document.getElementById("pageMetaHeading"),
  pageSummaryLine: document.getElementById("pageSummaryLine"),
  pageCrumbTitle: document.getElementById("pageCrumbTitle"),
  tabSettingsLink: document.getElementById("tabSettingsLink"),
  tabOutlineLink: document.getElementById("tabOutlineLink"),
  tabEditorLink: document.getElementById("tabEditorLink"),
  tabPreviewLink: document.getElementById("tabPreviewLink"),
  tabPublishLink: document.getElementById("tabPublishLink"),
  bookTitleLabel: document.getElementById("bookTitleLabel"),
  outlineTree: document.getElementById("outlineTree"),
  preview: document.getElementById("preview"),
  lockSummary: document.getElementById("lockSummary"),
  commentInput: document.getElementById("commentInput"),
  commentAnchorInput: document.getElementById("commentAnchorInput"),
  postCommentBtn: document.getElementById("postCommentBtn"),
  commentList: document.getElementById("commentList"),
  revisionList: document.getElementById("revisionList"),
};

function setText(el, value) {
  if (!el) {
    return;
  }
  el.textContent = value;
}

function renderDocument(doc) {
  state.currentDocument = doc;
  renderDocumentCrumb(doc.id, doc.title);
  setText(els.bookTitleLabel, doc.title);
  els.tabSettingsLink.href = bookHref(doc.id);
  els.tabOutlineLink.href = outlineHref(doc.id);
  els.tabEditorLink.href = editorHref(doc.id, pageId);
  els.tabPreviewLink.href = previewHref(doc.id, pageId);
  els.tabPublishLink.href = publishHref(doc.id);
}

function renderTree(tree) {
  state.currentTree = tree;
  renderOutlineList(els.outlineTree, tree, {
    activePageId: state.currentPage?.id || null,
    hrefBuilder: (node) => previewHref(bookId, node.id),
  });
}

function renderPage(page) {
  state.currentPage = page;
  document.title = `${page.title} | Benfast 文档预览`;
  setText(els.pageTitleHeading, page.title);
  setText(els.pageCrumbTitle, page.title);
  setText(
    els.pageMetaHeading,
    `${kindLabel(page)} · path=${page.path || "/"} · version=${page.version} · updated_at=${page.updated_at || "-"}`,
  );
  setText(els.pageSummaryLine, "这里只做阅读与审阅；正文修改请切回写作页。");
  els.preview.innerHTML = markdownToHtml(page.content || "", {
    bookId,
    currentPage: page,
    tree: state.currentTree,
  });
}

function renderLock(lock) {
  state.currentLock = lock || null;
  const currentUserId = Number(state.currentUser?.id || 0);
  const holderId = Number(lock?.holder_id || 0);

  if (!lock) {
    setText(els.lockSummary, "当前无人占用此页。需要修改正文时，请先去写作页点击“开始编辑”。");
    return;
  }
  if (holderId === currentUserId) {
    setText(els.lockSummary, `当前由你在编辑此页，锁定到 ${lock.expires_at}。预览页仍可用来核对排版和评论。`);
    return;
  }
  setText(els.lockSummary, `当前由 ${lock.holder_name} 在编辑此页，锁定到 ${lock.expires_at}。这能避免多人同时覆盖正文。`);
}

async function postComment() {
  const content = els.commentInput.value.trim();
  if (!content) {
    throw new Error("评论内容不能为空。");
  }
  await apiFetch(`${apiBase}/pages/${pageId}/comments`, {
    method: "POST",
    body: JSON.stringify({
      content,
      anchor: els.commentAnchorInput.value.trim() || null,
    }),
  });
  els.commentInput.value = "";
  els.commentAnchorInput.value = "";
  toast("评论已发送");
  const comments = await apiFetch(`${apiBase}/pages/${pageId}/comments`);
  renderCommentList(els.commentList, comments);
}

async function refresh() {
  const [{ book, tree }, { page, revisions, comments, lock }] = await Promise.all([
    loadBookContext(bookId),
    loadPageContext(pageId),
  ]);
  renderDocument(book);
  renderTree(tree);
  renderPage(page);
  renderLock(lock);
  renderCommentList(els.commentList, comments);
  renderRevisionList(els.revisionList, revisions);
  setStatus("预览页已就绪。", "success");
}

function bindEvents() {
  els.postCommentBtn.addEventListener("click", () => {
    withBusy(els.postCommentBtn, "发送中...", postComment).catch(handleError);
  });
}

async function init() {
  if (!bookId || !pageId) {
    throw new Error("缺少文档或页面 ID。");
  }
  primeDocumentCrumb(bookId);
  setStatus("正在载入预览页...", "neutral");
  state.currentUser = await loadCurrentUser();
  bindEvents();
  await refresh();
}

init().catch(handleError);
