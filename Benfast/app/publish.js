import {
  apiBase,
  apiFetch,
  bookHref,
  editorHref,
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
  toast,
  withBusy,
} from "/app/core.js";

const bookId = getBookIdFromPath();

const els = {
  publishBookTitle: document.getElementById("publishBookTitle"),
  publishBookMeta: document.getElementById("publishBookMeta"),
  tabSettingsLink: document.getElementById("tabSettingsLink"),
  tabOutlineLink: document.getElementById("tabOutlineLink"),
  tabRootEditorLink: document.getElementById("tabRootEditorLink"),
  tabRootPreviewLink: document.getElementById("tabRootPreviewLink"),
  tabPublishLink: document.getElementById("tabPublishLink"),
  openPublishedLink: document.getElementById("openPublishedLink"),
  publishMessageInput: document.getElementById("publishMessageInput"),
  publishBookBtn: document.getElementById("publishBookBtn"),
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

async function refresh() {
  const { book, tree, publishes } = await loadBookContext(bookId);
  document.title = `${book.title} | Benfast 文档发布`;
  renderDocumentCrumb(book.id, book.title);
  setText(els.publishBookTitle, `发布《${book.title}》`);
  setText(els.publishBookMeta, `slug=${book.slug} · ${book.page_count || 0} 页`);
  els.tabSettingsLink.href = bookHref(book.id);
  els.tabOutlineLink.href = outlineHref(book.id);
  els.tabRootEditorLink.href = editorHref(book.id, book.root_page_id);
  els.tabRootPreviewLink.href = previewHref(book.id, book.root_page_id);
  els.tabPublishLink.href = publishHref(book.id);
  renderOutlineList(els.outlineTree, tree, { activeBookId: book.id });
  renderPublishList(els.publishList, publishes);

  if (book.published_url) {
    els.openPublishedLink.classList.remove("hidden-link");
    els.openPublishedLink.href = book.published_url;
    els.publishedLink.innerHTML = `正式站入口：<a class="inline-link" href="${book.published_url}" target="_blank" rel="noreferrer">${book.published_url}</a>`;
  } else {
    els.openPublishedLink.classList.add("hidden-link");
    els.publishedLink.textContent = "当前还没有发布记录。";
  }
}

async function publishDocument() {
  const message = els.publishMessageInput.value.trim() || "发布新的正式版本";
  const publish = await apiFetch(`${apiBase}/books/${bookId}/publish`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
  toast("正式站已发布");
  els.publishMessageInput.value = "";
  await refresh();
  window.open(publish.published_url, "_blank", "noopener,noreferrer");
}

function bindEvents() {
  if (els.publishBookBtn) {
    els.publishBookBtn.addEventListener("click", () => {
      withBusy(els.publishBookBtn, "发布中...", publishDocument).catch(handleError);
    });
  }
}

async function init() {
  if (!bookId) {
    throw new Error("缺少文档 ID。");
  }
  primeDocumentCrumb(bookId);
  setStatus("正在载入发布页...", "neutral");
  await loadCurrentUser();
  bindEvents();
  await refresh();
  setStatus("发布页已就绪。", "success");
}

init().catch(handleError);
