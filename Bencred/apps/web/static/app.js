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

async function reviewCredential(button, reviewStatus) {
  const card = button.closest("[data-credential-id]");
  const credentialId = card.dataset.credentialId;
  const payload = {
    review_status: reviewStatus,
    review_notes: card.querySelector("[name='review_notes']").value || null,
    reviewed_by: card.querySelector("[name='reviewed_by']").value || null,
    agent_access: card.querySelector("[name='agent_access']").value || null,
    sensitivity: card.querySelector("[name='sensitivity']").value || null,
  };

  try {
    button.disabled = true;
    await postJson(`/api/v1/credentials/${credentialId}/review`, payload);
    window.location.reload();
  } catch (error) {
    button.disabled = false;
    window.alert(`审核失败: ${error.message}`);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("credential-create-form");
  if (!form) {
    return;
  }

  const message = document.getElementById("credential-create-message");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = {
      name: String(formData.get("name") || "").trim(),
      credential_type: String(formData.get("credential_type") || "").trim(),
      secret_data: String(formData.get("secret_data") || ""),
      service_name: String(formData.get("service_name") || "").trim() || null,
      username: String(formData.get("username") || "").trim() || null,
      endpoint: String(formData.get("endpoint") || "").trim() || null,
      category: String(formData.get("category") || "").trim() || null,
      tags: parseTags(String(formData.get("tags") || "")),
      source: String(formData.get("source") || "agent"),
      source_detail: String(formData.get("source_detail") || "").trim() || null,
      sensitivity: String(formData.get("sensitivity") || "high"),
      agent_access: String(formData.get("agent_access") || "approval_required"),
      review_status: "pending",
    };

    try {
      message.textContent = "正在提交...";
      await postJson("/api/v1/credentials", payload);
      window.location.href = "/?view=pending";
    } catch (error) {
      message.textContent = `提交失败: ${error.message}`;
    }
  });
});
