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

const body = document.body;
const pendingCount = document.querySelector('[data-count-role="pending"]');
const approvedCount = document.querySelector('[data-count-role="approved"]');
const activeCounter = document.querySelector("[data-active-counter]");
const approvedList = document.querySelector("[data-approved-list]");
const emptyStates = Array.from(document.querySelectorAll("[data-empty-state]"));
const clipStack = document.querySelector("[data-clip-stack]");
const clipFooter = document.querySelector("[data-clip-footer]");

let activeIndex = 0;

function frames() {
  return Array.from(document.querySelectorAll(".clip-frame"));
}

function thumbs() {
  return Array.from(document.querySelectorAll(".thumb"));
}

function setEmptyState(show) {
  emptyStates.forEach((node) => {
    node.classList.toggle("is-hidden", !show);
  });

  if (clipStack) {
    clipStack.classList.toggle("is-hidden", show);
  }

  if (clipFooter) {
    clipFooter.classList.toggle("is-hidden", show);
  }
}

function updateCounts(deltaPending, deltaApproved) {
  if (pendingCount) {
    pendingCount.textContent = String(Math.max(0, Number(pendingCount.textContent) + deltaPending));
  }

  if (approvedCount) {
    approvedCount.textContent = String(Math.max(0, Number(approvedCount.textContent) + deltaApproved));
  }
}

function prependArchive(frame) {
  if (!approvedList) {
    return;
  }

  approvedList.querySelector(".archive-empty")?.remove();

  const anchor = document.createElement("a");
  anchor.className = "archive-card";
  anchor.href = `/links/${frame.dataset.linkId}`;
  anchor.innerHTML = `
    <strong>${frame.dataset.title}</strong>
    <span>${frame.dataset.subtitle}</span>
    <em>${frame.dataset.tail}</em>
  `;
  approvedList.prepend(anchor);
}

function syncFrames(nextIndex = activeIndex) {
  const list = frames();
  const strip = thumbs();

  if (!list.length) {
    body.dataset.priority = "normal";
    setEmptyState(true);
    if (activeCounter) {
      activeCounter.textContent = "00 / 00";
    }
    return;
  }

  setEmptyState(false);
  activeIndex = Math.max(0, Math.min(nextIndex, list.length - 1));

  list.forEach((frame, index) => {
    frame.classList.remove("is-active", "is-next", "is-back", "is-past", "is-hidden");

    if (index < activeIndex) {
      frame.classList.add("is-past");
    } else if (index === activeIndex) {
      frame.classList.add("is-active");
    } else if (index === activeIndex + 1) {
      frame.classList.add("is-next");
    } else if (index === activeIndex + 2) {
      frame.classList.add("is-back");
    } else {
      frame.classList.add("is-hidden");
    }
  });

  strip.forEach((thumb, index) => {
    thumb.classList.toggle("is-active", index === activeIndex);
  });

  body.dataset.priority = list[activeIndex].dataset.priority || "normal";

  if (activeCounter) {
    activeCounter.textContent = `${String(activeIndex + 1).padStart(2, "0")} / ${String(list.length).padStart(2, "0")}`;
  }
}

async function approveFrame(frame, button) {
  if (!frame || !button) {
    return;
  }

  button.disabled = true;
  button.textContent = "保留中";
  frame.classList.add("is-approving");

  try {
    await postJson(`/api/v1/links/${frame.dataset.linkId}/review`, {
      review_status: "approved",
      reviewed_by: "admin",
    });

    prependArchive(frame);
    updateCounts(-1, 1);

    const thumb = thumbs()[Number(frame.dataset.cardIndex)];
    thumb?.remove();

    window.setTimeout(() => {
      frame.remove();
      frames().forEach((item, index) => {
        item.dataset.cardIndex = String(index);
      });
      thumbs().forEach((item, index) => {
        item.dataset.cardTarget = String(index);
      });
      syncFrames(activeIndex);
    }, 280);
  } catch (error) {
    frame.classList.remove("is-approving");
    button.disabled = false;
    button.textContent = "保留";
    window.alert(`审核失败: ${error.message}`);
  }
}

document.addEventListener("click", (event) => {
  const thumb = event.target.closest("[data-card-target]");
  if (thumb) {
    syncFrames(Number(thumb.dataset.cardTarget));
    return;
  }

  const approveButton = event.target.closest('[data-action="approve"]');
  if (approveButton) {
    approveFrame(approveButton.closest(".clip-frame"), approveButton);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.defaultPrevented) {
    return;
  }

  if (event.key === "ArrowRight") {
    syncFrames(activeIndex + 1);
  } else if (event.key === "ArrowLeft") {
    syncFrames(activeIndex - 1);
  } else if (event.key.toLowerCase() === "a") {
    const frame = frames()[activeIndex];
    const button = frame?.querySelector('[data-action="approve"]');
    if (button instanceof HTMLButtonElement) {
      approveFrame(frame, button);
    }
  }
});

syncFrames(0);
window.requestAnimationFrame(() => {
  document.body.classList.add("is-ready");
});
