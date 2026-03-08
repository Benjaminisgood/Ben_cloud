function submitPost(action) {
  const form = document.createElement("form");
  form.method = "post";
  form.action = action;
  document.body.appendChild(form);
  form.submit();
}

document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-photo-scene]");
  if (!root) {
    return;
  }

  const drawer = document.querySelector("[data-photo-drawer]");
  const toggle = document.querySelector("[data-scene-toggle='photo-drawer']");
  const trashZone = document.querySelector("[data-trash-zone='true']");

  const setDrawer = (open) => {
    if (!drawer || !toggle) {
      return;
    }
    drawer.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
  };

  toggle?.addEventListener("click", () => {
    const isOpen = toggle.getAttribute("aria-expanded") === "true";
    setDrawer(!isOpen);
  });

  document.querySelectorAll("[data-scene-close='photo-drawer']").forEach((button) => {
    button.addEventListener("click", () => setDrawer(false));
  });

  document.querySelectorAll("[data-submit-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.submitAction || "";
      if (action) {
        submitPost(action);
      }
    });
  });

  document.querySelectorAll("[data-restore-url]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.restoreUrl || "";
      if (action) {
        submitPost(action);
      }
    });
  });

  if (!trashZone) {
    return;
  }

  let currentAction = "";

  document.querySelectorAll("[data-trash-url]").forEach((card) => {
    card.addEventListener("dragstart", (event) => {
      currentAction = card.dataset.trashUrl || "";
      card.classList.add("is-dragging");
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", currentAction);
      }
    });

    card.addEventListener("dragend", () => {
      currentAction = "";
      card.classList.remove("is-dragging");
      trashZone.classList.remove("is-over");
    });
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    trashZone.addEventListener(eventName, (event) => {
      if (!currentAction) {
        return;
      }
      event.preventDefault();
      trashZone.classList.add("is-over");
    });
  });

  ["dragleave", "dragend"].forEach((eventName) => {
    trashZone.addEventListener(eventName, () => {
      trashZone.classList.remove("is-over");
    });
  });

  trashZone.addEventListener("drop", (event) => {
    if (!currentAction) {
      return;
    }
    event.preventDefault();
    trashZone.classList.remove("is-over");
    submitPost(currentAction);
  });
});
