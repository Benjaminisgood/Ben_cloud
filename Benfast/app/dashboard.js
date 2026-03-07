import {
  bookHref,
  escapeHtml,
  handleError,
  loadBooks,
  loadCurrentUser,
  setStatus,
} from "/app/core.js";

const els = {
  metricBooks: document.getElementById("metricBooks"),
  metricPublished: document.getElementById("metricPublished"),
  metricDrafts: document.getElementById("metricDrafts"),
  recentBooks: document.getElementById("recentBooks"),
};

function renderRecentDocuments(documents) {
  els.recentBooks.innerHTML = "";
  if (!documents.length) {
    const empty = document.createElement("div");
    empty.className = "record-item";
    empty.textContent = "还没有文档，先去文档库创建第一份文档。";
    els.recentBooks.appendChild(empty);
    return;
  }

  documents.slice(0, 6).forEach((doc) => {
    const item = document.createElement("a");
    item.className = "list-card";
    item.href = bookHref(doc.id);
    item.innerHTML = `
      <strong>${escapeHtml(doc.title)}</strong>
      <span>${escapeHtml(doc.slug)}</span>
      <small>${escapeHtml(doc.summary || doc.description || "暂无简介")}</small>
    `;
    els.recentBooks.appendChild(item);
  });
}

async function init() {
  setStatus("正在装载文档后台...", "neutral");
  await loadCurrentUser();
  const documents = await loadBooks();
  const published = documents.filter((doc) => Boolean(doc.published_url));
  const drafts = documents.length - published.length;

  els.metricBooks.textContent = String(documents.length);
  els.metricPublished.textContent = String(published.length);
  els.metricDrafts.textContent = String(drafts);
  renderRecentDocuments(documents);
  setStatus("文档后台已就绪。", "success");
}

init().catch(handleError);
