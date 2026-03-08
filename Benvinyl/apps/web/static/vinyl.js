function submitPost(action) {
  const form = document.createElement("form");
  form.method = "post";
  form.action = action;
  document.body.appendChild(form);
  form.submit();
}

document.addEventListener("DOMContentLoaded", () => {
  const drawer = document.querySelector("[data-record-drawer]");
  const toggle = document.querySelector("[data-scene-toggle='record-drawer']");

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

  document.querySelectorAll("[data-scene-close='record-drawer']").forEach((button) => {
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

  const dropzone = document.querySelector("[data-trash-zone='true']");
  if (!dropzone) {
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
      card.classList.remove("is-dragging");
      dropzone.classList.remove("is-over");
      currentAction = "";
    });
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      if (!currentAction) {
        return;
      }
      event.preventDefault();
      dropzone.classList.add("is-over");
    });
  });

  ["dragleave", "dragend"].forEach((eventName) => {
    dropzone.addEventListener(eventName, () => {
      dropzone.classList.remove("is-over");
    });
  });

  dropzone.addEventListener("drop", (event) => {
    if (!currentAction) {
      return;
    }
    event.preventDefault();
    dropzone.classList.remove("is-over");
    submitPost(currentAction);
  });
});
