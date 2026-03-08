(() => {
  const root = document.querySelector("[data-dashboard-root]");
  if (!root) {
    return;
  }

  const isAdmin = root.dataset.admin === "1";
  const player = document.querySelector("#program-player");
  const playerSource = player?.querySelector("source");
  const titleNode = document.querySelector("#program-title");
  const summaryNode = document.querySelector("#program-summary");
  const slotNode = document.querySelector("#program-slot");
  const durationNode = document.querySelector("#program-duration");
  const reelButtons = Array.from(document.querySelectorAll("[data-action='switch-video']"));
  const trashToggle = document.querySelector("[data-trash-toggle]");
  const trashClose = document.querySelector("[data-trash-close]");
  const trashDrawer = document.querySelector("[data-trash-drawer]");

  const activateReel = (button) => {
    reelButtons.forEach((item) => item.classList.toggle("is-active", item === button));
    if (!player || !playerSource) {
      return;
    }

    playerSource.src = button.dataset.videoSrc || "";
    player.poster = button.dataset.videoPoster || "";
    player.load();

    if (titleNode) {
      titleNode.textContent = button.dataset.videoTitle || "";
    }
    if (summaryNode) {
      summaryNode.textContent = button.dataset.videoSummary || "这卷片子没有额外说明，就让画面自己说话。";
    }
    if (slotNode) {
      slotNode.textContent = button.dataset.videoSlot || "";
    }
    if (durationNode) {
      durationNode.textContent = button.dataset.videoDuration || "时长未标注";
    }
  };

  reelButtons.forEach((button) => {
    button.addEventListener("click", () => activateReel(button));
  });

  const setTrashDrawer = (open) => {
    if (!trashDrawer || !trashToggle) {
      return;
    }
    trashDrawer.hidden = !open;
    trashToggle.setAttribute("aria-expanded", String(open));
  };

  if (trashToggle && isAdmin) {
    trashToggle.addEventListener("click", () => {
      const isOpen = trashToggle.getAttribute("aria-expanded") === "true";
      setTrashDrawer(!isOpen);
    });
  }

  if (trashClose) {
    trashClose.addEventListener("click", () => setTrashDrawer(false));
  }

  const patchVideo = async (videoId, status) => {
    const response = await fetch(`/api/videos/${videoId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status }),
    });

    if (response.status === 401) {
      window.location.href = "/login?next=/";
      return;
    }

    if (!response.ok) {
      return;
    }

    window.location.reload();
  };

  if (!isAdmin || !trashToggle) {
    return;
  }

  const markDropTarget = (state) => {
    trashToggle.classList.toggle("is-drop-target", state);
  };

  const bindDragSource = (node) => {
    node.addEventListener("dragstart", (event) => {
      event.dataTransfer?.setData("text/plain", node.dataset.mediaId || "");
      event.dataTransfer?.setData("application/x-benreel-action", "trash");
      markDropTarget(true);
    });
    node.addEventListener("dragend", () => markDropTarget(false));
  };

  reelButtons.forEach(bindDragSource);

  trashToggle.addEventListener("dragover", (event) => {
    event.preventDefault();
    markDropTarget(true);
  });

  trashToggle.addEventListener("dragleave", () => markDropTarget(false));

  trashToggle.addEventListener("drop", (event) => {
    event.preventDefault();
    markDropTarget(false);
    const videoId = event.dataTransfer?.getData("text/plain");
    if (videoId) {
      patchVideo(videoId, "trashed");
    }
  });

  document.querySelectorAll("[data-action='restore-video']").forEach((button) => {
    button.addEventListener("click", () => {
      const videoId = button.dataset.mediaId;
      if (videoId) {
        patchVideo(videoId, "active");
      }
    });
  });
})();
