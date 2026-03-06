"use strict";

(function () {
  // ─── 状态 ───────────────────────────────────────────────────
  const state = {
    userId: null,
    username: "",
    role: "",
  };

  // ─── DOM 引用 ────────────────────────────────────────────────
  const el = {
    // Hero
    heroSession: document.getElementById("hero-session"),
    heroSessionText: document.getElementById("hero-session-text"),
    heroLogoutBtn: document.getElementById("hero-logout-btn"),
    benbotSsoBtn: document.getElementById("benbot-sso-btn"),
    flashBanner: document.getElementById("flash-banner"),

    // 房源
    propertyList: document.getElementById("property-list"),
    reloadProperties: document.getElementById("reload-properties"),
    cityFilter: document.getElementById("city-filter"),

    // 账号区
    accountPanel: document.getElementById("account-panel"),
    accountSummaryText: document.getElementById("account-summary-text"),
    registerForm: document.getElementById("register-form"),
    loginForm: document.getElementById("login-form"),
    sessionBox: document.getElementById("session-box"),
    sessionText: document.getElementById("session-text"),
    logoutBtn: document.getElementById("logout-btn"),

    // Toast & 模板
    toast: document.getElementById("toast"),
    propertyCardTemplate: document.getElementById("property-card-template"),
  };

  // ─── Toast ───────────────────────────────────────────────────
  function showToast(message, isError) {
    if (!el.toast) return;
    el.toast.textContent = message;
    el.toast.classList.remove("hidden", "toast-ok", "toast-err");
    el.toast.classList.add(isError ? "toast-err" : "toast-ok");
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(() => {
      el.toast.classList.add("hidden");
    }, 3000);
  }

  // ─── Flash banner（SSO 跳转后） ─────────────────────────
  function checkFlash() {
    try {
      const raw = sessionStorage.getItem("benome_flash");
      if (!raw) return;
      sessionStorage.removeItem("benome_flash");
      const { msg, err } = JSON.parse(raw);
      if (!msg) return;
      el.flashBanner.textContent = msg;
      el.flashBanner.classList.remove("hidden", "flash-ok", "flash-err");
      el.flashBanner.classList.add(err ? "flash-err" : "flash-ok");
      setTimeout(() => el.flashBanner.classList.add("hidden"), 4000);
    } catch (_) {}
  }

  // ─── Session ─────────────────────────────────────────────────
  function loadSession() {
    try {
      const raw = localStorage.getItem("benome_session_v1");
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (!parsed || !parsed.userId) return;
      state.userId = Number(parsed.userId);
      state.username = String(parsed.username || "");
      state.role = String(parsed.role || "");
    } catch (_) {
      localStorage.removeItem("benome_session_v1");
    }
  }

  function persistSession() {
    if (!state.userId) {
      localStorage.removeItem("benome_session_v1");
      return;
    }
    localStorage.setItem(
      "benome_session_v1",
      JSON.stringify({ userId: state.userId, username: state.username, role: state.role })
    );
  }

  function clearSession() {
    state.userId = null;
    state.username = "";
    state.role = "";
    persistSession();
    renderSession();
  }

  // ─── UI 渲染 ─────────────────────────────────────────────────
  function renderSession() {
    const loggedIn = Boolean(state.userId);

    // Hero 区域会话信息
    if (loggedIn) {
      const roleLabel = state.role === "admin" ? "管理员" : "客户";
      el.heroSessionText.textContent = `${state.username}（${roleLabel}）`;
      el.heroSession.classList.remove("hidden");
    } else {
      el.heroSession.classList.add("hidden");
    }

    // 账号面板内
    if (loggedIn) {
      el.sessionText.textContent = `当前：${state.username}（${state.role}，ID=${state.userId}）`;
      el.sessionBox.classList.remove("hidden");
      el.accountSummaryText.textContent = `账号管理 · 已登录 ${state.username}`;
    } else {
      el.sessionBox.classList.add("hidden");
      el.accountSummaryText.textContent = "账号管理";
    }
  }

  // ─── HTTP 封装 ───────────────────────────────────────────────
  async function request(path, options) {
    const init = options ? { ...options } : {};
    init.headers = { "Content-Type": "application/json", ...(init.headers || {}) };
    if (state.userId) {
      init.headers["X-User-Id"] = String(state.userId);
    }

    const response = await fetch(path, init);
    let payload = null;
    try {
      payload = await response.json();
    } catch (_) {}

    if (!response.ok) {
      const detail = payload && payload.detail ? String(payload.detail) : `${response.status} ${response.statusText}`;
      const err = new Error(detail);
      err.status = response.status;
      throw err;
    }
    return payload;
  }

  // ─── 工具函数 ────────────────────────────────────────────────
  function isoDate(offsetDays) {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + offsetDays);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  function parseForm(form) {
    return Object.fromEntries(new FormData(form).entries());
  }

  function bookingStatusText(status) {
    return { pending_review: "待审核", confirmed: "已确认", rejected: "已拒绝" }[status] || status;
  }

  function statusBadgeClass(status) {
    return { pending_review: "badge-pending", confirmed: "badge-ok", rejected: "badge-bad" }[status] || "";
  }

  // ─── Benbot SSO ──────────────────────────────────────────────
  function benbotSsoUrl() {
    const host = window.location.hostname;
    const proto = window.location.protocol;
    return `${proto}//${host}/goto/benome`;
  }

  // ─── 房源加载 ────────────────────────────────────────────────
  let _allProperties = [];

  async function loadProperties() {
    try {
      const properties = await request("/api/properties", { method: "GET" });
      _allProperties = Array.isArray(properties) ? properties : [];
      renderProperties(_allProperties);
    } catch (err) {
      el.propertyList.innerHTML = `<p class="muted">加载房源失败：${err.message}</p>`;
    }
  }

  function renderProperties(list) {
    if (!list || list.length === 0) {
      el.propertyList.innerHTML = '<p class="muted">暂无房源，管理员可先发布房源。</p>';
      return;
    }
    el.propertyList.innerHTML = "";
    list.forEach((item) => el.propertyList.appendChild(buildPropertyCard(item)));
  }

  function buildPropertyCard(item) {
    const node = el.propertyCardTemplate.content.firstElementChild.cloneNode(true);

    node.querySelector(".property-title").textContent = item.title;
    node.querySelector(".pill").textContent = `¥${item.price_per_night}/晚`;
    node.querySelector(".property-meta").textContent =
      `${item.city || "未填城市"} · 最多 ${item.max_guests} 人 · ID ${item.id}`;
    node.querySelector(".property-desc").textContent = item.description || "暂无描述";

    const checkInInput = node.querySelector(".check-in");
    const checkOutInput = node.querySelector(".check-out");
    const availResult = node.querySelector(".availability-result");
    const checkBtn = node.querySelector(".check-availability");
    const bookingForm = node.querySelector(".booking-form");

    checkInInput.value = isoDate(1);
    checkOutInput.value = isoDate(2);

    // 查档期
    checkBtn.addEventListener("click", async () => {
      checkBtn.disabled = true;
      try {
        const payload = await request(
          `/api/properties/${item.id}/availability?check_in_date=${checkInInput.value}&check_out_date=${checkOutInput.value}`,
          { method: "GET" }
        );
        if (payload.available) {
          availResult.textContent = `✓ 可预订（${payload.total_nights} 晚）`;
          availResult.className = "availability-result good";
        } else {
          availResult.textContent = `✗ 已被锁定：${payload.conflict_dates.join("、")}`;
          availResult.className = "availability-result bad";
        }
      } catch (err) {
        availResult.textContent = err.message;
        availResult.className = "availability-result bad";
      } finally {
        checkBtn.disabled = false;
      }
    });

    // 预订提交（无需登录）
    bookingForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      // 如果以管理员身份登录，拒绝用管理员账号下单
      if (state.role === "admin") {
        showToast("管理员账号无法预订，请退出后以访客或客户身份操作", true);
        return;
      }

      const fd = parseForm(bookingForm);
      const btn = bookingForm.querySelector("button[type=submit]");
      btn.disabled = true;

      try {
        await request("/api/bookings", {
          method: "POST",
          body: JSON.stringify({
            property_id: item.id,
            check_in_date: checkInInput.value,
            check_out_date: checkOutInput.value,
            guest_count: Number(fd.guest_count || 1),
            guest_name: String(fd.guest_name || ""),
            guest_phone: String(fd.guest_phone || ""),
            note: String(fd.note || ""),
          }),
        });
        bookingForm.reset();
        showToast("预订已提交，等待管理员审核 ✓", false);
      } catch (err) {
        showToast(`预订失败：${err.message}`, true);
      } finally {
        btn.disabled = false;
      }
    });

    return node;
  }

  // 城市筛选
  function applyFilter() {
    const q = (el.cityFilter.value || "").trim().toLowerCase();
    if (!q) {
      renderProperties(_allProperties);
      return;
    }
    renderProperties(_allProperties.filter((p) => (p.city || "").toLowerCase().includes(q)));
  }

  // ─── 注册 / 登录 ─────────────────────────────────────────────
  async function onRegister(event) {
    event.preventDefault();
    const fd = parseForm(el.registerForm);
    try {
      await request("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          username: String(fd.username || ""),
          password: String(fd.password || ""),
          full_name: String(fd.full_name || ""),
          phone: String(fd.phone || ""),
        }),
      });
      el.registerForm.reset();
      showToast("注册成功，请使用新账号登录 ✓", false);
    } catch (err) {
      showToast(`注册失败：${err.message}`, true);
    }
  }

  async function onLogin(event) {
    event.preventDefault();
    const fd = parseForm(el.loginForm);
    try {
      const payload = await request("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          username: String(fd.username || ""),
          password: String(fd.password || ""),
        }),
      });
      state.userId = Number(payload.user_id);
      state.username = String(payload.username || "");
      state.role = String(payload.role || "");
      persistSession();
      renderSession();
      showToast(`登录成功：${state.username} ✓`, false);
      
      // 根据角色跳转到对应的 dashboard
      const redirectPath = state.role === "admin" ? "/admin/dashboard" : "/dashboard";
      console.log('[Login] 用户角色:', state.role, '跳转路径:', redirectPath);
      
      setTimeout(() => {
        console.log('[Login] 执行跳转:', redirectPath);
        window.location.href = redirectPath;
      }, 500);
    } catch (err) {
      showToast(`登录失败：${err.message}`, true);
    }
  }

  async function onLogout() {
    clearSession();
    showToast("已退出账号", false);
    await loadProperties();
  }

  // ─── 事件绑定 ────────────────────────────────────────────────
  function bindEvents() {
    // 账号
    el.registerForm.addEventListener("submit", onRegister);
    el.loginForm.addEventListener("submit", onLogin);
    el.logoutBtn.addEventListener("click", onLogout);
    el.heroLogoutBtn.addEventListener("click", onLogout);

    // 房源
    el.reloadProperties.addEventListener("click", loadProperties);
    el.cityFilter.addEventListener("input", applyFilter);

    // Benbot SSO
    el.benbotSsoBtn.addEventListener("click", () => {
      window.location.href = benbotSsoUrl();
    });
  }

  // ─── 启动 ────────────────────────────────────────────────────
  async function bootstrap() {
    loadSession();
    renderSession();
    bindEvents();
    checkFlash();
    await loadProperties();
  }

  bootstrap();
})();
