function parseTags(raw) {
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "request failed");
  }
  return response.json();
}

async function reviewLink(button, reviewStatus) {
  const card = button.closest("[data-link-id]");
  const linkId = card.dataset.linkId;
  const payload = {
    review_status: reviewStatus,
    review_notes: card.querySelector("[name='review_notes']").value || null,
    reviewed_by: card.querySelector("[name='reviewed_by']").value || null,
    category: card.querySelector("[name='category']").value || null,
    priority: card.querySelector("[name='priority']").value || null,
  };

  try {
    button.disabled = true;
    await postJson(`/api/v1/links/${linkId}/review`, payload);
    window.location.reload();
  } catch (error) {
    button.disabled = false;
    window.alert(`审核失败: ${error.message}`);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("link-create-form");
  if (!form) {
    return;
  }

  const message = document.getElementById("link-create-message");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const fetchMetadata = formData.get("fetch_metadata") === "on";
    const payload = {
      url: String(formData.get("url") || "").trim(),
      title: String(formData.get("title") || "").trim() || null,
      category: String(formData.get("category") || "").trim() || null,
      tags: parseTags(String(formData.get("tags") || "")),
      notes: String(formData.get("notes") || "").trim() || null,
      priority: String(formData.get("priority") || "normal"),
      source: String(formData.get("source") || "agent"),
      source_detail: String(formData.get("source_detail") || "").trim() || null,
      review_status: "pending",
    };

    try {
      message.textContent = "正在提交...";
      await postJson(`/api/v1/links?fetch_metadata=${fetchMetadata}`, payload);
      window.location.href = "/?view=pending";
    } catch (error) {
      message.textContent = `提交失败: ${error.message}`;
    }
  });
});
