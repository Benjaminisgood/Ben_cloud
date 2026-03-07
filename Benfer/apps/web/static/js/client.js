const API_BASE = "/api";
const AUTH_BASE = "/auth";
let authToken = null;
let currentUserId = null;

window.addEventListener("DOMContentLoaded", async () => {
    setupEventListeners();
    await initializeSession();

    if (authToken) {
        await Promise.all([loadClipboardItems(), loadFiles()]);
    }
});

function setupEventListeners() {
    document.querySelectorAll(".tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(btn.dataset.tab).classList.add("active");
        });
    });

    document.getElementById("save-clipboard").addEventListener("click", saveClipboard);

    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");

    dropZone.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", (event) => handleFiles(event.target.files));

    dropZone.addEventListener("dragover", (event) => {
        event.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (event) => {
        event.preventDefault();
        dropZone.classList.remove("dragover");
        handleFiles(event.dataTransfer.files);
    });
}

async function initializeSession() {
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get("token");

    if (tokenFromUrl) {
        const established = await establishSession(tokenFromUrl);
        window.history.replaceState({}, document.title, window.location.pathname);
        if (established) {
            return;
        }
    }

    const storedToken = sessionStorage.getItem("benfer_token");
    const storedUserId = sessionStorage.getItem("benfer_user_id");
    if (storedToken && storedUserId) {
        authToken = storedToken;
        currentUserId = storedUserId;
        setAuthenticatedState(storedUserId);
        return;
    }

    setLoggedOutState();
}

async function establishSession(token) {
    try {
        const response = await fetch(`${AUTH_BASE}/sso?token=${encodeURIComponent(token)}`, {
            method: "POST",
        });
        if (!response.ok) {
            setLoggedOutState();
            return false;
        }

        const data = await response.json();
        const sessionToken = data.session_token || token;
        authToken = sessionToken;
        currentUserId = data.user_id;

        sessionStorage.setItem("benfer_token", sessionToken);
        sessionStorage.setItem("benfer_user_id", currentUserId);
        setAuthenticatedState(currentUserId);
        return true;
    } catch (error) {
        console.error("SSO auth failed:", error);
        setLoggedOutState();
        return false;
    }
}

function setAuthenticatedState(userId) {
    document.getElementById("user-info").textContent = `用户：${userId}`;
    document.getElementById("login-prompt").style.display = "none";
}

function setLoggedOutState() {
    authToken = null;
    currentUserId = null;
    sessionStorage.removeItem("benfer_token");
    sessionStorage.removeItem("benfer_user_id");

    document.getElementById("user-info").textContent = "未登录";
    document.getElementById("login-prompt").style.display = "block";
}

function handleUnauthorized() {
    setLoggedOutState();
    alert("登录已失效，请从 Benbot 重新进入 Benfer");
}

async function authorizedFetch(url, options = {}) {
    if (!authToken) {
        throw new Error("请先登录");
    }

    const headers = new Headers(options.headers || {});
    headers.set("Authorization", `Bearer ${authToken}`);

    const response = await fetch(url, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        handleUnauthorized();
    }

    return response;
}

async function saveClipboard() {
    const content = document.getElementById("clipboard-content").value;
    const isPublic = document.getElementById("clipboard-public").checked;
    const expiryHours = parseInt(document.getElementById("clipboard-expiry").value, 10);

    if (!content.trim()) {
        alert("请输入内容");
        return;
    }

    try {
        const response = await authorizedFetch(`${API_BASE}/clipboard`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                content,
                content_type: "text/plain",
                is_public: isPublic,
                expires_in_hours: Number.isNaN(expiryHours) ? null : expiryHours,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "保存失败");
        }

        const data = await response.json();
        const shareLink = `${window.location.origin}/api/clipboard/${data.access_token}`;
        alert(`剪贴板已保存！分享链接：${shareLink}`);
        document.getElementById("clipboard-content").value = "";
        await loadClipboardItems();
    } catch (error) {
        console.error("Save clipboard failed:", error);
        alert(error.message || "保存失败，请重试");
    }
}

async function loadClipboardItems() {
    if (!authToken) {
        document.getElementById("clipboard-list").innerHTML = "<p>请先登录</p>";
        return;
    }

    try {
        const response = await authorizedFetch(`${API_BASE}/clipboard`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "加载失败");
        }

        const items = await response.json();
        renderClipboardItems(items);
    } catch (error) {
        console.error("Load clipboard failed:", error);
        document.getElementById("clipboard-list").innerHTML = "<p>加载失败</p>";
    }
}

function renderClipboardItems(items) {
    const list = document.getElementById("clipboard-list");
    if (!items.length) {
        list.innerHTML = "<p>暂无剪贴板</p>";
        return;
    }

    list.innerHTML = "";
    items.forEach((item) => {
        const row = document.createElement("div");
        row.className = "list-item";
        row.innerHTML = `
            <div class="list-item-info">
                <div class="list-item-title">${escapeHtml(item.content.slice(0, 60) || "(空内容)")}</div>
                <div class="list-item-meta">
                    创建：${formatDate(item.created_at)} | 过期：${item.expires_at ? formatDate(item.expires_at) : "无"}
                    | ${item.is_public ? "公开" : "私有"}
                </div>
            </div>
            <div class="list-item-actions"></div>
        `;

        const actions = row.querySelector(".list-item-actions");

        const copyContentBtn = document.createElement("button");
        copyContentBtn.className = "btn btn-secondary btn-small";
        copyContentBtn.textContent = "复制内容";
        copyContentBtn.addEventListener("click", () => copyText(item.content));

        const copyLinkBtn = document.createElement("button");
        copyLinkBtn.className = "btn btn-secondary btn-small";
        copyLinkBtn.textContent = "复制链接";
        copyLinkBtn.addEventListener("click", () => {
            const link = `${window.location.origin}/api/clipboard/${item.access_token}`;
            copyText(link);
        });

        const deleteBtn = document.createElement("button");
        deleteBtn.className = "btn btn-danger btn-small";
        deleteBtn.textContent = "删除";
        deleteBtn.addEventListener("click", async () => {
            await deleteClipboardItem(item.access_token);
        });

        actions.appendChild(copyContentBtn);
        actions.appendChild(copyLinkBtn);
        actions.appendChild(deleteBtn);
        list.appendChild(row);
    });
}

async function deleteClipboardItem(accessToken) {
    try {
        const response = await authorizedFetch(`${API_BASE}/clipboard/${accessToken}`, {
            method: "DELETE",
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "删除失败");
        }
        await loadClipboardItems();
    } catch (error) {
        console.error("Delete clipboard failed:", error);
        alert(error.message || "删除失败");
    }
}

async function handleFiles(files) {
    if (!authToken) {
        alert("请先登录");
        return;
    }

    for (const file of files) {
        await uploadFile(file);
    }
}

async function uploadFile(file) {
    const isPublic = document.getElementById("file-public").checked;
    const expiryHours = parseInt(document.getElementById("file-expiry").value, 10);
    const progressDiv = document.getElementById("upload-progress");

    progressDiv.style.display = "block";
    progressDiv.textContent = `正在上传 ${file.name}...`;

    try {
        const uploadPlan = buildUploadPlan(file);
        const initResponse = await authorizedFetch(`${API_BASE}/files/init`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                filename: file.name,
                file_size: file.size,
                content_type: file.type,
                chunk_count: uploadPlan.chunkCount,
                is_public: isPublic,
                expires_in_hours: Number.isNaN(expiryHours) ? null : expiryHours,
            }),
        });

        if (!initResponse.ok) {
            const error = await initResponse.json();
            throw new Error(error.detail || "初始化上传失败");
        }

        const initData = await initResponse.json();
        if (uploadPlan.chunkCount === 1) {
            const formData = new FormData();
            formData.append("file", file, file.name);
            const uploadResponse = await authorizedFetch(`${API_BASE}/files/${initData.upload_id}/content`, {
                method: "POST",
                body: formData,
            });
            if (!uploadResponse.ok) {
                const error = await uploadResponse.json().catch(() => ({}));
                throw new Error(error.detail || "上传文件失败");
            }
        } else {
            if (!initData.multipart_upload_id) {
                throw new Error("缺少 multipart_upload_id");
            }
            let completePayload = null;
            const parts = [];
            for (let i = 0; i < uploadPlan.chunks.length; i += 1) {
                const chunk = uploadPlan.chunks[i];
                progressDiv.textContent = `正在上传 ${file.name} (${i + 1}/${uploadPlan.chunkCount})...`;
                const uploadResponse = await fetch(initData.chunk_upload_urls[i], {
                    method: "PUT",
                    body: file.slice(chunk.start, chunk.end),
                });
                if (!uploadResponse.ok) {
                    throw new Error(`第 ${i + 1} 片上传失败`);
                }

                const etag = uploadResponse.headers.get("etag") || uploadResponse.headers.get("ETag");
                if (!etag) {
                    throw new Error(`第 ${i + 1} 片缺少 ETag`);
                }
                parts.push({
                    part_number: i + 1,
                    etag: etag.replace(/^"+|"+$/g, ""),
                });
            }

            completePayload = {
                multipart_upload_id: initData.multipart_upload_id,
                parts,
            };

            const completeResponse = await authorizedFetch(`${API_BASE}/files/${initData.upload_id}/complete`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(completePayload),
            });

            if (!completeResponse.ok) {
                const error = await completeResponse.json();
                throw new Error(error.detail || "完成上传失败");
            }
        }

        progressDiv.textContent = `✅ ${file.name} 上传成功`;
        setTimeout(() => {
            progressDiv.style.display = "none";
        }, 3000);
        await loadFiles();
    } catch (error) {
        console.error("Upload failed:", error);
        progressDiv.textContent = `❌ 上传失败：${error.message}`;
        setTimeout(() => {
            progressDiv.style.display = "none";
        }, 5000);
    }
}

function buildUploadPlan(file) {
    return {
        chunkCount: 1,
        chunks: [{ start: 0, end: file.size }],
    };
}

async function loadFiles() {
    if (!authToken) {
        document.getElementById("file-list").innerHTML = "<p>请先登录</p>";
        return;
    }

    try {
        const response = await authorizedFetch(`${API_BASE}/files`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "加载失败");
        }

        const files = await response.json();
        renderFiles(files);
    } catch (error) {
        console.error("Load files failed:", error);
        document.getElementById("file-list").innerHTML = "<p>加载失败</p>";
    }
}

function renderFiles(files) {
    const list = document.getElementById("file-list");
    if (!files.length) {
        list.innerHTML = "<p>暂无文件</p>";
        return;
    }

    list.innerHTML = "";
    files.forEach((file) => {
        const row = document.createElement("div");
        row.className = "list-item";
        row.innerHTML = `
            <div class="list-item-info">
                <div class="list-item-title">${escapeHtml(file.filename)}</div>
                <div class="list-item-meta">
                    大小：${formatBytes(file.file_size)} | 创建：${formatDate(file.created_at)}
                    | 状态：${escapeHtml(file.upload_status)} | ${file.is_public ? "公开分享已开启" : "私有文件"}
                </div>
            </div>
            <div class="list-item-actions"></div>
        `;

        const actions = row.querySelector(".list-item-actions");
        const isCompleted = file.upload_status === "completed";

        const downloadBtn = document.createElement("a");
        downloadBtn.className = "btn btn-primary btn-small";
        downloadBtn.textContent = "下载";
        downloadBtn.href = buildPrivateDownloadLink(file.access_token);
        downloadBtn.target = "_blank";
        downloadBtn.rel = "noopener noreferrer";
        if (!isCompleted) {
            downloadBtn.classList.add("disabled");
            downloadBtn.removeAttribute("href");
        }

        const copyDownloadBtn = document.createElement("button");
        copyDownloadBtn.className = "btn btn-secondary btn-small";
        copyDownloadBtn.textContent = "复制下载链接";
        copyDownloadBtn.addEventListener("click", async () => {
            await copyDownloadLink(file.access_token);
        });
        if (!isCompleted) {
            copyDownloadBtn.disabled = true;
        }

        if (file.is_public) {
            const copyPublicBtn = document.createElement("button");
            copyPublicBtn.className = "btn btn-secondary btn-small";
            copyPublicBtn.textContent = "复制公开链接";
            copyPublicBtn.addEventListener("click", async () => {
                await copyText(buildPublicDownloadLink(file.access_token));
            });
            if (!isCompleted) {
                copyPublicBtn.disabled = true;
            }
            actions.appendChild(copyPublicBtn);
        }

        const deleteBtn = document.createElement("button");
        deleteBtn.className = "btn btn-danger btn-small";
        deleteBtn.textContent = "删除";
        deleteBtn.addEventListener("click", async () => {
            await deleteFileItem(file.access_token);
        });

        actions.appendChild(downloadBtn);
        actions.appendChild(copyDownloadBtn);
        actions.appendChild(deleteBtn);
        list.appendChild(row);
    });
}

async function copyDownloadLink(accessToken) {
    try {
        await copyText(buildPrivateDownloadLink(accessToken));
    } catch (error) {
        console.error("Copy download URL failed:", error);
        alert(error.message || "获取下载链接失败");
    }
}

function buildPrivateDownloadLink(accessToken) {
    return `${window.location.origin}${API_BASE}/files/${encodeURIComponent(accessToken)}/download/redirect`;
}

function buildPublicDownloadLink(accessToken) {
    return `${window.location.origin}${API_BASE}/files/public/${encodeURIComponent(accessToken)}/download`;
}

async function deleteFileItem(accessToken) {
    try {
        const response = await authorizedFetch(`${API_BASE}/files/${accessToken}`, {
            method: "DELETE",
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "删除失败");
        }
        await loadFiles();
    } catch (error) {
        console.error("Delete file failed:", error);
        alert(error.message || "删除失败");
    }
}

async function copyText(text) {
    try {
        await navigator.clipboard.writeText(text);
        alert("已复制");
    } catch (error) {
        console.error("Copy failed:", error);
        alert("复制失败");
    }
}

function formatDate(value) {
    return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

function formatBytes(size) {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`;
    return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
