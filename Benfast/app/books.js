import {
  bookHref,
  handleError,
  loadBooks,
  loadCurrentUser,
  setStatus,
  slugify,
  toast,
  withBusy,
  apiFetch,
  escapeHtml,
  apiBase,
} from "/app/core.js";

const els = {
  newBookForm: document.getElementById("newBookForm"),
  newBookTitle: document.getElementById("newBookTitle"),
  newBookSlug: document.getElementById("newBookSlug"),
  newBookSummary: document.getElementById("newBookSummary"),
  newBookDescription: document.getElementById("newBookDescription"),
  createBookBtn: document.getElementById("createBookBtn"),
  bookSearchInput: document.getElementById("bookSearchInput"),
  bookShelfMeta: document.getElementById("bookShelfMeta"),
  bookShelf: document.getElementById("bookShelf"),
};

const state = {
  slugTouched: false,
};

function renderDocuments(documents) {
  els.bookShelf.innerHTML = "";
  els.bookShelfMeta.textContent = documents.length
    ? `共 ${documents.length} 份文档。打开某份文档后，再进入设置、目录、写作和发布。`
    : "当前没有文档。先创建第一份文档。";

  if (!documents.length) {
    const empty = document.createElement("article");
    empty.className = "list-card";
    empty.innerHTML = "<strong>文档库为空</strong><span>先创建一份文档，再进入该文档的工作区。</span>";
    els.bookShelf.appendChild(empty);
    return;
  }

  documents.forEach((doc) => {
    const card = document.createElement("article");
    card.className = "document-card";
    const publishMeta = doc.published_url
      ? `<a class="tiny-link" href="${doc.published_url}" target="_blank" rel="noreferrer">查看文档站</a>`
      : `<span class="muted">尚未发布</span>`;
    card.innerHTML = `
      <div>
        <p class="eyebrow">${escapeHtml(doc.slug)}</p>
        <h3>${escapeHtml(doc.title)}</h3>
      </div>
      <p>${escapeHtml(doc.summary || doc.description || "暂无简介")}</p>
      <div class="meta-row">
        <span class="pill">${doc.page_count || 0} 页</span>
        <span class="pill ${doc.published_url ? "pill-success" : ""}">${doc.published_url ? "已发布" : "草稿"}</span>
      </div>
      <div class="meta-row">
        ${publishMeta}
      </div>
      <div class="card-actions">
        <a class="primary-link" href="${bookHref(doc.id)}">打开文档</a>
      </div>
    `;
    els.bookShelf.appendChild(card);
  });
}

async function refreshBooks() {
  const documents = await loadBooks(els.bookSearchInput.value || "");
  renderDocuments(documents);
}

async function createBook() {
  const title = els.newBookTitle.value.trim();
  const slug = els.newBookSlug.value.trim();
  if (!title || !slug) {
    throw new Error("创建文档至少需要标题和 slug。");
  }
  const doc = await apiFetch(`${apiBase}/books`, {
    method: "POST",
    body: JSON.stringify({
      title,
      slug,
      summary: els.newBookSummary.value.trim(),
      description: els.newBookDescription.value.trim(),
      keywords: [],
    }),
  });
  toast("文档创建成功");
  window.location.href = bookHref(doc.id);
}

function bindEvents() {
  els.newBookTitle.addEventListener("input", () => {
    if (!state.slugTouched) {
      els.newBookSlug.value = slugify(els.newBookTitle.value);
    }
  });
  els.newBookSlug.addEventListener("input", () => {
    state.slugTouched = Boolean(els.newBookSlug.value.trim());
  });
  els.newBookForm.addEventListener("submit", (event) => {
    event.preventDefault();
    withBusy(els.createBookBtn, "创建中...", createBook).catch(handleError);
  });
  els.bookSearchInput.addEventListener("input", () => {
    window.clearTimeout(bindEvents._searchTimer);
    bindEvents._searchTimer = window.setTimeout(() => {
      refreshBooks().catch(handleError);
    }, 220);
  });
}

async function init() {
  setStatus("正在载入文档库...", "neutral");
  await loadCurrentUser();
  bindEvents();
  await refreshBooks();
  setStatus("文档库已准备好。", "success");
}

init().catch(handleError);
