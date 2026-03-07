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
  previewHref,
  publishHref,
  primeDocumentCrumb,
  renderDocumentCrumb,
  renderPublishList,
  setStatus,
  toast,
  withBusy,
} from "/app/core.js";

const bookId = getBookIdFromPath();

const els = {
  bookTitleHeading: document.getElementById("bookTitleHeading"),
  bookMetaLine: document.getElementById("bookMetaLine"),
  tabSettingsLink: document.getElementById("tabSettingsLink"),
  tabOutlineLink: document.getElementById("tabOutlineLink"),
  tabRootEditorLink: document.getElementById("tabRootEditorLink"),
  tabRootPreviewLink: document.getElementById("tabRootPreviewLink"),
  tabPublishLink: document.getElementById("tabPublishLink"),
  saveBookBtn: document.getElementById("saveBookBtn"),
  bookTitleInput: document.getElementById("bookTitleInput"),
  bookSlugInput: document.getElementById("bookSlugInput"),
  bookSummaryInput: document.getElementById("bookSummaryInput"),
  bookTagsInput: document.getElementById("bookTagsInput"),
  bookDescriptionInput: document.getElementById("bookDescriptionInput"),
  metaPageCount: document.getElementById("metaPageCount"),
  metaUpdatedAt: document.getElementById("metaUpdatedAt"),
  metaPublishState: document.getElementById("metaPublishState"),
  publishedLink: document.getElementById("publishedLink"),
  publishList: document.getElementById("publishList"),
};

function setText(el, value) {
  if (!el) {
    return;
  }
  el.textContent = value;
}

function renderDocument(doc, publishes) {
  document.title = `${doc.title} | Benfast 文档设置`;
  setText(els.bookTitleHeading, doc.title);
  renderDocumentCrumb(doc.id, doc.title);
  setText(els.bookMetaLine, `slug=${doc.slug} · ${doc.page_count || 0} 页 · updated_at=${doc.updated_at || "-"}`);

  els.tabSettingsLink.href = bookHref(doc.id);
  els.tabOutlineLink.href = outlineHref(doc.id);
  els.tabRootEditorLink.href = editorHref(doc.id, doc.root_page_id);
  els.tabRootPreviewLink.href = previewHref(doc.id, doc.root_page_id);
  els.tabPublishLink.href = publishHref(doc.id);

  els.bookTitleInput.value = doc.title || "";
  els.bookSlugInput.value = doc.slug || "";
  els.bookSummaryInput.value = doc.summary || "";
  const keywords = Array.isArray(doc.keywords) ? doc.keywords : [];
  els.bookTagsInput.value = keywords.join(", ");
  els.bookDescriptionInput.value = doc.description || "";

  setText(els.metaPageCount, `${doc.page_count || 0} 页`);
  setText(els.metaUpdatedAt, doc.updated_at || "-");
  setText(els.metaPublishState, doc.published_url ? "已发布" : "未发布");
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
  const { book, publishes } = await loadBookContext(bookId);
  renderDocument(book, publishes);
}

async function saveDocument() {
  const updated = await apiFetch(`${apiBase}/books/${bookId}`, {
    method: "PUT",
    body: JSON.stringify({
      title: els.bookTitleInput.value.trim(),
      slug: els.bookSlugInput.value.trim(),
      summary: els.bookSummaryInput.value.trim(),
      description: els.bookDescriptionInput.value.trim(),
      keywords: els.bookTagsInput.value.split(",").map((item) => item.trim()).filter(Boolean),
    }),
  });
  toast("文档设置已保存");
  const { publishes } = await loadBookContext(bookId);
  renderDocument(updated, publishes);
  setStatus(`《${updated.title}》设置已更新。`, "success");
}

function bindEvents() {
  els.saveBookBtn.addEventListener("click", () => {
    withBusy(els.saveBookBtn, "保存中...", saveDocument).catch(handleError);
  });
}

async function init() {
  if (!bookId) {
    throw new Error("缺少文档 ID。");
  }
  primeDocumentCrumb(bookId);
  setStatus("正在载入文档设置...", "neutral");
  await loadCurrentUser();
  bindEvents();
  await refresh();
  setStatus("文档设置页已就绪。", "success");
}

init().catch(handleError);
