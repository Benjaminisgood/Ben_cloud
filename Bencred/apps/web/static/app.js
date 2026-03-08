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
const approvedList = document.querySelector("[data-approved-list]");
const pendingCount = document.querySelector('[data-count-role="pending"]');
const approvedCount = document.querySelector('[data-count-role="approved"]');
const activeCounter = document.querySelector("[data-active-counter]");
const emptyStates = Array.from(document.querySelectorAll("[data-empty-state]"));
const deckStack = document.querySelector("[data-deck-stack]");
const stageFooter = document.querySelector("[data-stage-footer]");

let activeIndex = 0;

function cards() {
  return Array.from(document.querySelectorAll(".vault-card"));
}

function dots() {
  return Array.from(document.querySelectorAll(".reel-dot"));
}

function updateCounts(deltaPending, deltaApproved) {
  if (pendingCount) {
    pendingCount.textContent = String(Math.max(0, Number(pendingCount.textContent) + deltaPending));
  }

  if (approvedCount) {
    approvedCount.textContent = String(Math.max(0, Number(approvedCount.textContent) + deltaApproved));
  }
}

function mountApprovedCard(card) {
  if (!approvedList) {
    return;
  }

  approvedList.querySelector(".memory-empty")?.remove();

  const link = document.createElement("a");
  link.className = "memory-item";
  link.href = `/credentials/${card.dataset.credentialId}`;
  link.innerHTML = `
    <strong>${card.dataset.title}</strong>
    <span>${card.dataset.subtitle}</span>
    <em>${card.dataset.tail}</em>
  `;
  approvedList.prepend(link);
}

function toggleEmptyState(show) {
  emptyStates.forEach((node) => {
    node.classList.toggle("is-hidden", !show);
  });

  if (deckStack) {
    deckStack.classList.toggle("is-hidden", show);
  }

  if (stageFooter) {
    stageFooter.classList.toggle("is-hidden", show);
  }
}

function syncDeck(nextIndex = activeIndex) {
  const list = cards();
  const reel = dots();

  if (!list.length) {
    body.dataset.tone = "neutral";
    toggleEmptyState(true);
    if (activeCounter) {
      activeCounter.textContent = "00 / 00";
    }
    return;
  }

  toggleEmptyState(false);
  activeIndex = Math.max(0, Math.min(nextIndex, list.length - 1));

  list.forEach((card, index) => {
    card.classList.remove("is-active", "is-next", "is-back", "is-past", "is-hidden");

    if (index < activeIndex) {
      card.classList.add("is-past");
    } else if (index === activeIndex) {
      card.classList.add("is-active");
    } else if (index === activeIndex + 1) {
      card.classList.add("is-next");
    } else if (index === activeIndex + 2) {
      card.classList.add("is-back");
    } else {
      card.classList.add("is-hidden");
    }
  });

  reel.forEach((button, index) => {
    button.classList.toggle("is-active", index === activeIndex);
  });

  body.dataset.tone = list[activeIndex].dataset.tone || "neutral";

  if (activeCounter) {
    activeCounter.textContent = `${String(activeIndex + 1).padStart(2, "0")} / ${String(list.length).padStart(2, "0")}`;
  }
}

async function approveCard(card, button) {
  if (!card || !button) {
    return;
  }

  button.disabled = true;
  button.textContent = "处理中";
  card.classList.add("is-approving");

  try {
    await postJson(`/api/v1/credentials/${card.dataset.credentialId}/review`, {
      review_status: "approved",
      reviewed_by: "admin",
    });

    mountApprovedCard(card);
    updateCounts(-1, 1);

    const reelButton = dots()[Number(card.dataset.cardIndex)];
    reelButton?.remove();

    window.setTimeout(() => {
      card.remove();
      cards().forEach((item, index) => {
        item.dataset.cardIndex = String(index);
      });
      dots().forEach((item, index) => {
        item.dataset.cardTarget = String(index);
      });
      syncDeck(activeIndex);
    }, 260);
  } catch (error) {
    card.classList.remove("is-approving");
    button.disabled = false;
    button.textContent = "同意";
    window.alert(`审核失败: ${error.message}`);
  }
}

document.addEventListener("click", (event) => {
  const targetButton = event.target.closest("[data-card-target]");
  if (targetButton) {
    syncDeck(Number(targetButton.dataset.cardTarget));
    return;
  }

  const approveButton = event.target.closest('[data-action="approve"]');
  if (approveButton) {
    approveCard(approveButton.closest(".vault-card"), approveButton);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.defaultPrevented) {
    return;
  }

  if (event.key === "ArrowRight") {
    syncDeck(activeIndex + 1);
  } else if (event.key === "ArrowLeft") {
    syncDeck(activeIndex - 1);
  } else if (event.key.toLowerCase() === "a") {
    const activeCard = cards()[activeIndex];
    const button = activeCard?.querySelector('[data-action="approve"]');
    if (button instanceof HTMLButtonElement) {
      approveCard(activeCard, button);
    }
  }
});

syncDeck(0);
window.requestAnimationFrame(() => {
  document.body.classList.add("is-ready");
});
