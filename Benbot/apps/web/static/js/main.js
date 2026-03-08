'use strict';

const STATUS_LABELS = { up: '运行中', down: '不可达', unknown: '检测中' };
const SERVICE_LABELS = { running: '已开启', stopped: '已关闭', unknown: '未知' };
const ACTION_LABELS = { start: '启动', stop: '停止', status: '刷新' };

// ── Auto-fade flash messages ────────────────────────────────────
document.querySelectorAll('.flash').forEach(el => {
  setTimeout(() => {
    el.style.transition = 'opacity .4s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 400);
  }, 4000);
});

function showClientFlash(message, category = 'info') {
  let stack = document.querySelector('.flash-stack');
  if (!stack) {
    stack = document.createElement('div');
    stack.className = 'flash-stack';
    const main = document.querySelector('.page-main');
    if (main && main.parentElement) {
      main.parentElement.insertBefore(stack, main);
    } else {
      document.body.prepend(stack);
    }
  }

  const flash = document.createElement('div');
  flash.className = `flash flash-${category}`;
  flash.textContent = message;
  stack.appendChild(flash);
  setTimeout(() => {
    flash.style.transition = 'opacity .4s';
    flash.style.opacity = '0';
    setTimeout(() => flash.remove(), 400);
  }, 3500);
}

function setCardBusy(card, busy) {
  if (!card) return;
  card.classList.toggle('control-busy', busy);
  const toggle = card.querySelector('[data-project-toggle]');
  if (toggle) toggle.disabled = busy;
}

function applyProjectStatus(card, proj) {
  if (!card) return;

  const badge = card.querySelector('.status-badge');
  if (badge) {
    badge.className = `status-badge status-${proj.status}`;
    const text = badge.querySelector('.status-text');
    if (text) text.textContent = STATUS_LABELS[proj.status] || STATUS_LABELS.unknown;

    let ms = badge.querySelector('.status-ms');
    if (proj.response_ms && proj.status === 'up') {
      if (!ms) {
        ms = document.createElement('span');
        ms.className = 'status-ms';
        badge.appendChild(ms);
      }
      ms.textContent = `${proj.response_ms}ms`;
    } else if (ms) {
      ms.remove();
    }
  }

  const statVal = card.querySelector('.stat-val');
  if (statVal) statVal.textContent = proj.total_clicks;

  if (typeof proj.service_state === 'string') {
    card.dataset.serviceState = proj.service_state;
    const toggle = card.querySelector('[data-project-toggle]');
    if (toggle && !card.classList.contains('control-busy')) {
      toggle.checked = proj.service_state === 'running';
    }
    const stateText = card.querySelector('.power-state-text');
    if (stateText) stateText.textContent = SERVICE_LABELS[proj.service_state] || SERVICE_LABELS.unknown;
  }
}

// ── Health status live refresh ──────────────────────────────────
async function refreshStatus(showSpinner = true) {
  const btn = document.getElementById('refresh-btn');
  if (showSpinner && btn) {
    btn.classList.add('spinning');
    btn.disabled = true;
  }

  try {
    const res = await fetch('/api/projects/status');
    if (!res.ok) throw new Error('status_request_failed');

    const data = await res.json();
    if (!data.projects) return;

    data.projects.forEach(proj => {
      const card = document.querySelector(`[data-project-id="${proj.id}"]`);
      if (!card) return;
      applyProjectStatus(card, proj);
    });
  } catch (e) {
    console.warn('Failed to refresh status', e);
    if (showSpinner) showClientFlash('刷新状态失败，请稍后重试', 'error');
  } finally {
    if (showSpinner && btn) {
      btn.classList.remove('spinning');
      btn.disabled = false;
    }
  }
}

async function controlProject(card, action) {
  const projectId = card?.dataset?.projectId;
  if (!projectId) return false;

  setCardBusy(card, true);
  try {
    const res = await fetch(`/api/projects/${projectId}/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    });
    const data = await res.json().catch(() => ({}));

    if (!res.ok || !data.ok) {
      const errorMessage = data?.detail || data?.error || '控制命令执行失败';
      throw new Error(errorMessage);
    }

    showClientFlash(`${projectId} ${ACTION_LABELS[action] || action}成功`, 'success');
    await refreshStatus(false);
    return true;
  } catch (e) {
    console.warn('Project control failed', e);
    showClientFlash(e?.message || '操作失败', 'error');
    return false;
  } finally {
    setCardBusy(card, false);
  }
}

function bindAdminControls() {
  document.querySelectorAll('.project-card').forEach(card => {
    const toggle = card.querySelector('[data-project-toggle]');

    if (toggle) {
      toggle.addEventListener('change', async () => {
        const intendedState = toggle.checked;
        const action = intendedState ? 'start' : 'stop';
        const ok = await controlProject(card, action);
        if (!ok) toggle.checked = !intendedState;
      });
    }
  });
}

// Auto-refresh every 60s on portal page
if (document.querySelector('.project-grid')) {
  bindAdminControls();
  setInterval(() => {
    void refreshStatus(false);
  }, 60_000);
}

// ── 项目日志弹窗（管理员专属）──────────────────────────────────
(function initLogModal() {
  const overlay  = document.getElementById('log-modal-overlay');
  if (!overlay) return;   // 非管理员不渲染弹窗

  const modalBody    = document.getElementById('log-modal-body');
  const modalTitle   = document.getElementById('log-modal-project-name');
  const countBadge   = document.getElementById('log-count-badge');
  const closeBtn     = document.getElementById('log-modal-close');
  const refreshBtn   = document.getElementById('log-refresh-btn');
  const loadMoreBtn  = document.getElementById('log-load-more');
  const levelTabs    = document.querySelectorAll('.log-tab');

  let _projectId  = null;
  let _level      = '';
  let _offset     = 0;
  const _limit    = 80;
  let _total      = 0;
  let _loading    = false;

  // ── 工具 ────────────────────────────────────────────
  function escLog(str) {
    return String(str)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function levelClass(level) {
    if (level === 'ERROR')   return 'log-level-error';
    if (level === 'WARNING') return 'log-level-warn';
    return 'log-level-info';
  }

  function sourceLabel(source) {
    const map = { health_check:'健康检查', project_control:'运行控制', env_editor:'环境配置', system:'系统' };
    return map[source] || source;
  }

  function renderEntry(entry) {
    return `<div class="log-entry ${levelClass(entry.level)}">` +
      `<span class="log-entry-level">${escLog(entry.level)}</span>` +
      `<span class="log-entry-source">${escLog(sourceLabel(entry.source))}</span>` +
      `<span class="log-entry-time">${escLog(entry.created_at)}</span>` +
      `<pre class="log-entry-msg">${escLog(entry.message)}</pre>` +
      `</div>`;
  }

  // ── 数据加载 ─────────────────────────────────────────
  async function loadLogs(append) {
    if (!_projectId || _loading) return;
    _loading = true;
    if (!append) {
      modalBody.innerHTML = '<p class="log-empty-hint">加载中…</p>';
      _offset = 0;
    }
    if (refreshBtn) refreshBtn.classList.add('spinning');
    try {
      const params = new URLSearchParams({ limit: _limit, offset: _offset });
      if (_level) params.set('level', _level);
      const res = await fetch(`/api/projects/${_projectId}/logs?${params}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      _total = data.total || 0;
      if (countBadge) countBadge.textContent = `${_total} 条`;
      if (!append) modalBody.innerHTML = '';
      if (!data.logs || data.logs.length === 0) {
        if (!append) modalBody.innerHTML = '<p class="log-empty-hint">暂无日志记录</p>';
      } else {
        const html = data.logs.map(renderEntry).join('');
        const tmp  = document.createElement('div');
        tmp.innerHTML = html;
        while (tmp.firstChild) modalBody.appendChild(tmp.firstChild);
        _offset += data.logs.length;
      }
      if (loadMoreBtn) {
        loadMoreBtn.style.display = (_offset < _total) ? 'block' : 'none';
      }
    } catch (e) {
      if (!append) {
        modalBody.innerHTML = `<p class="log-empty-hint log-load-error">加载失败: ${escLog(e.message)}</p>`;
      } else {
        showClientFlash('加载更多日志失败', 'error');
      }
    } finally {
      _loading = false;
      if (refreshBtn) refreshBtn.classList.remove('spinning');
    }
  }

  // ── 打开/关闭 ────────────────────────────────────────
  function openModal(projectId, projectName) {
    _projectId = projectId;
    _level = '';
    if (modalTitle) modalTitle.textContent = projectName ? `${projectName} — 日志` : '项目日志';
    levelTabs.forEach(t => t.classList.toggle('active', t.dataset.level === ''));
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    loadLogs(false);
  }

  function closeModal() {
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    _projectId = null;
    if (loadMoreBtn) loadMoreBtn.style.display = 'none';
  }

  // ── 事件 ─────────────────────────────────────────────
  if (closeBtn)    closeBtn.addEventListener('click', closeModal);
  if (refreshBtn)  refreshBtn.addEventListener('click', () => loadLogs(false));
  if (loadMoreBtn) loadMoreBtn.addEventListener('click', () => loadLogs(true));
  overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && overlay.classList.contains('open')) closeModal();
  });
  levelTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      levelTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      _level = tab.dataset.level;
      loadLogs(false);
    });
  });

  // 绑定每张卡片上的日志按钮
  document.querySelectorAll('[data-project-logs]').forEach(btn => {
    const card = btn.closest('.project-card');
    if (!card) return;
    btn.addEventListener('click', () => {
      const projectId   = card.dataset.projectId;
      const nameEl      = card.querySelector('.card-name');
      const projectName = nameEl ? nameEl.textContent.trim() : projectId;
      openModal(projectId, projectName);
    });
  });
})();

// ── 项目 .env 编辑器（管理员专属）───────────────────────────────
(function initProjectEnvModal() {
  const overlay = document.getElementById('env-modal-overlay');
  if (!overlay) return;

  const titleEl = document.getElementById('env-modal-title');
  const descEl = document.getElementById('env-modal-desc');
  const updatedAtEl = document.getElementById('env-updated-at');
  const hintEl = document.getElementById('env-hint');
  const editorEl = document.getElementById('env-editor');
  const statusEl = document.getElementById('env-save-status');
  const closeBtn = document.getElementById('env-modal-close');
  const reloadBtn = document.getElementById('env-reload-btn');
  const saveBtn = document.getElementById('env-save-btn');

  let currentProjectId = null;
  let currentProjectName = '';
  let loading = false;
  let saving = false;
  let activeLoadToken = 0;

  function modalBusy() {
    return loading || saving;
  }

  function formatDateTime(value) {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString('zh-CN', { hour12: false });
  }

  function sourceHint(source) {
    if (source === 'env') {
      return '当前已加载真实 `.env` 内容；保存会先备份旧文件，再原子写回。';
    }
    if (source === 'example') {
      return '当前 `.env` 不存在，已载入 `.env.example` 模板；点击保存后会在项目根目录创建 `.env`。';
    }
    return '当前项目既没有 `.env` 也没有 `.env.example`，可直接从空白内容开始创建。';
  }

  function applyEnvMeta(data) {
    if (titleEl) {
      titleEl.textContent = currentProjectName ? `${currentProjectName} · .env` : '项目 .env 配置';
    }
    if (descEl) {
      descEl.textContent = currentProjectName
        ? `直接编辑 ${currentProjectName} 项目根目录的环境变量配置。`
        : '直接读取和保存项目根目录下的 `.env` 文件。';
    }
    if (updatedAtEl) updatedAtEl.textContent = `更新时间：${formatDateTime(data?.updated_at)}`;
    if (hintEl) hintEl.textContent = sourceHint(data?.source);
  }

  function syncBusyState() {
    const busy = modalBusy();
    if (editorEl) editorEl.disabled = busy || !currentProjectId;
    if (reloadBtn) reloadBtn.disabled = busy || !currentProjectId;
    if (saveBtn) {
      saveBtn.disabled = busy || !currentProjectId;
      saveBtn.textContent = saving ? '保存中…' : '保存 .env';
    }
  }

  async function loadEnvFile(showErrorFlash = true) {
    if (!currentProjectId || modalBusy()) return;

    const loadToken = ++activeLoadToken;
    loading = true;
    syncBusyState();
    if (statusEl) statusEl.textContent = '加载中…';
    if (editorEl) {
      editorEl.value = '';
      editorEl.placeholder = '加载中…';
    }

    try {
      const res = await fetch(`/api/projects/${currentProjectId}/env`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || `HTTP ${res.status}`);
      }
      if (loadToken !== activeLoadToken || !currentProjectId) return;

      applyEnvMeta(data);
      if (editorEl) {
        editorEl.value = typeof data.content === 'string' ? data.content : '';
        editorEl.placeholder = '';
      }
      if (statusEl) {
        if (data.source === 'env') {
          statusEl.textContent = '已载入当前 .env';
        } else if (data.source === 'example') {
          statusEl.textContent = '已载入 .env.example，保存后会生成 .env';
        } else {
          statusEl.textContent = '当前无配置文件，可直接创建新的 .env';
        }
      }
    } catch (e) {
      if (loadToken !== activeLoadToken || !currentProjectId) return;
      applyEnvMeta({ source: 'empty', path: '—', loaded_from: '', updated_at: null });
      if (editorEl) {
        editorEl.value = '';
        editorEl.placeholder = '加载失败';
      }
      if (statusEl) statusEl.textContent = '加载失败';
      if (showErrorFlash) {
        showClientFlash(`加载 ${currentProjectId} 的 .env 失败：${e?.message || 'unknown_error'}`, 'error');
      }
    } finally {
      if (loadToken === activeLoadToken) {
        loading = false;
        syncBusyState();
      }
    }
  }

  async function saveEnvFile() {
    if (!currentProjectId || modalBusy() || !editorEl) return;

    saving = true;
    syncBusyState();
    if (statusEl) statusEl.textContent = '保存中…';

    try {
      const res = await fetch(`/api/projects/${currentProjectId}/env`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: editorEl.value }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) {
        throw new Error(data?.detail || `HTTP ${res.status}`);
      }

      applyEnvMeta(data);
      if (statusEl) {
        statusEl.textContent = data.backup_path
          ? `已保存，变更ID: ${data.change_id}，原文件已备份`
          : `已保存，变更ID: ${data.change_id}`;
      }
      showClientFlash(
        `${currentProjectId} .env 已保存（变更ID: ${data.change_id}）`,
        'success',
      );
    } catch (e) {
      if (statusEl) statusEl.textContent = '保存失败';
      showClientFlash(`保存 ${currentProjectId} 的 .env 失败：${e?.message || 'unknown_error'}`, 'error');
    } finally {
      saving = false;
      syncBusyState();
    }
  }

  function openModal(projectId, projectName) {
    activeLoadToken += 1;
    currentProjectId = projectId;
    currentProjectName = projectName || projectId;
    applyEnvMeta({ source: 'empty', path: '—', loaded_from: '', updated_at: null });
    if (statusEl) statusEl.textContent = '准备加载…';
    if (editorEl) {
      editorEl.value = '';
      editorEl.placeholder = '加载中…';
    }
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    syncBusyState();
    void loadEnvFile();
  }

  function closeModal() {
    if (saving) return;
    activeLoadToken += 1;
    loading = false;
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    currentProjectId = null;
    currentProjectName = '';
    applyEnvMeta({ source: 'empty', path: '—', loaded_from: '', updated_at: null });
    if (editorEl) {
      editorEl.value = '';
      editorEl.placeholder = '加载中…';
    }
    if (statusEl) statusEl.textContent = '未加载';
    syncBusyState();
  }

  document.querySelectorAll('[data-project-env]').forEach(btn => {
    const card = btn.closest('.project-card');
    if (!card) return;

    btn.addEventListener('click', () => {
      const projectId = card.dataset.projectId;
      const nameEl = card.querySelector('.card-name');
      const projectName = nameEl ? nameEl.textContent.trim() : projectId;
      openModal(projectId, projectName);
    });
  });

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (reloadBtn) reloadBtn.addEventListener('click', () => {
    void loadEnvFile();
  });
  if (saveBtn) saveBtn.addEventListener('click', () => {
    void saveEnvFile();
  });
  overlay.addEventListener('click', e => {
    if (e.target === overlay) closeModal();
  });
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's' && overlay.classList.contains('open')) {
      e.preventDefault();
      void saveEnvFile();
      return;
    }
    if (e.key === 'Escape' && overlay.classList.contains('open')) {
      closeModal();
    }
  });
})();

// ── 用户项目可见性管理（管理员专属）────────────────────────────
(function initUserAccessPanel() {
  const panel = document.getElementById('user-access-panel');
  const listEl = document.getElementById('user-access-list');
  if (!panel || !listEl) return;

  let projects = [];
  let users = [];

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function accessSummary(projectIds) {
    const selected = projects.filter(project => projectIds.has(project.id));
    if (!selected.length) return '未分配项目';

    const preview = selected.slice(0, 2).map(project => project.name).join(' / ');
    return `已开放 ${selected.length} 个项目${preview ? ` · ${preview}${selected.length > 2 ? ' 等' : ''}` : ''}`;
  }

  function render() {
    if (!users.length) {
      listEl.innerHTML = '<p class="access-admin-empty">当前暂无用户</p>';
      return;
    }

    listEl.innerHTML = users.map(user => {
      const isAdmin = user.role === 'admin';
      if (isAdmin) {
        return `
          <div class="access-user-row is-admin" data-user-id="${user.id}">
            <div class="access-user-header">
              <div class="access-user-meta">
                <span class="access-user-name">@${escHtml(user.username)}</span>
                <span class="access-user-role">管理员</span>
              </div>
              <span class="access-admin-fixed">固定全量可见</span>
            </div>
          </div>`;
      }

      const granted = Array.isArray(user.project_ids) ? new Set(user.project_ids) : new Set();
      const summary = accessSummary(granted);
      const checkboxes = projects.map(project => `
        <label class="access-project-item">
          <input type="checkbox" value="${escHtml(project.id)}" ${granted.has(project.id) ? 'checked' : ''}>
          <span>${escHtml(project.name)}</span>
        </label>`).join('');

      return `
        <div class="access-user-row" data-user-id="${user.id}" data-username="${escHtml(user.username)}">
          <div class="access-user-header">
            <button class="access-user-toggle" type="button" aria-expanded="false">
              <span class="access-user-meta">
                <span class="access-user-name">@${escHtml(user.username)}</span>
                <span class="access-user-role">${user.is_active ? '普通用户' : '已禁用账号'}</span>
              </span>
              <span class="access-user-summary-wrap">
                <span class="access-user-summary">${escHtml(summary)}</span>
                <span class="access-user-toggle-icon">⌄</span>
              </span>
            </button>
          </div>
          <div class="access-user-body">
            <div class="access-project-grid">
              ${checkboxes || '<span class="access-admin-empty">暂无可配置项目</span>'}
            </div>
            <div class="access-user-actions">
              <button class="access-save-btn" type="button">保存权限</button>
            </div>
          </div>
        </div>`;
    }).join('');

    bindRowActions();
  }

  function selectedProjectIds(row) {
    return Array.from(row.querySelectorAll('input[type="checkbox"]:checked'))
      .map(input => input.value.trim().toLowerCase())
      .filter(Boolean)
      .sort();
  }

  async function saveRow(row, button) {
    const userId = Number(row.dataset.userId);
    const username = row.dataset.username || String(userId);
    const projectIds = selectedProjectIds(row);

    row.classList.add('saving');
    if (button) button.disabled = true;
    try {
      const res = await fetch(`/api/admin/users/${userId}/project-access`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_ids: projectIds }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) {
        throw new Error(data?.detail || `HTTP ${res.status}`);
      }

      users = users.map(user => (
        user.id === userId
          ? { ...user, project_ids: Array.isArray(data.project_ids) ? data.project_ids : [] }
          : user
      ));
      showClientFlash(`已保存 @${username} 的项目权限（变更ID: ${data.change_id}）`, 'success');
    } catch (e) {
      console.warn('Failed to save project access', e);
      showClientFlash(`保存 @${username} 权限失败：${e?.message || 'unknown_error'}`, 'error');
    } finally {
      row.classList.remove('saving');
      if (button) button.disabled = false;
    }
  }

  function updateRowSummary(row) {
    const summaryEl = row.querySelector('.access-user-summary');
    if (!summaryEl) return;

    const checkedIds = new Set(selectedProjectIds(row));
    summaryEl.textContent = accessSummary(checkedIds);
  }

  function bindRowActions() {
    listEl.querySelectorAll('.access-user-toggle').forEach(toggle => {
      const row = toggle.closest('.access-user-row');
      if (!row) return;
      toggle.addEventListener('click', () => {
        const expanded = !row.classList.contains('expanded');
        row.classList.toggle('expanded', expanded);
        toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
      });
    });

    listEl.querySelectorAll('.access-user-row input[type="checkbox"]').forEach(input => {
      const row = input.closest('.access-user-row');
      if (!row) return;
      input.addEventListener('change', () => {
        updateRowSummary(row);
      });
    });

    listEl.querySelectorAll('.access-save-btn').forEach(button => {
      const row = button.closest('.access-user-row');
      if (!row) return;
      button.addEventListener('click', () => {
        void saveRow(row, button);
      });
    });
  }

  async function loadOverview() {
    listEl.innerHTML = '<p class="access-admin-empty">加载中…</p>';
    try {
      const res = await fetch('/api/admin/users/project-access');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      projects = Array.isArray(data.projects) ? data.projects : [];
      users = Array.isArray(data.users) ? data.users : [];
      render();
    } catch (e) {
      console.warn('Failed to load project access overview', e);
      listEl.innerHTML = '<p class="access-admin-empty">加载失败，请刷新后重试</p>';
    }
  }

  void loadOverview();
})();

// ── Bug 反馈区 ──────────────────────────────────────────────────
(function initBugSection() {
  const section = document.getElementById('bug-section');
  if (!section) return;

  const isAdmin = section.dataset.isAdmin === 'true';
  const loggedIn = section.dataset.loggedIn === 'true';
  if (!loggedIn) return;

  const submitBtn = document.getElementById('bug-submit-btn');
  const bodyEl = document.getElementById('bug-body');
  const pendingList = document.getElementById('pending-bug-list');
  const approvedList = document.getElementById('approved-bug-list');
  const archivedList = document.getElementById('archived-bug-list');
  const archivedSection = document.getElementById('bug-archive-section');
  const archivedToggle = document.getElementById('bug-archive-toggle');
  const archivedCount = document.getElementById('archived-bug-count');
  const clearArchivedBtn = document.getElementById('clear-archived-bugs-btn');
  let approvedBugs = [];
  let archivedTotal = 0;
  let clearingArchived = false;

  function emptyHtml(msg) {
    return `<p class="bug-empty">${msg}</p>`;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/\n/g, '<br>');
  }

  async function copyText(text) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }

    const input = document.createElement('textarea');
    input.value = text;
    input.setAttribute('readonly', 'readonly');
    input.style.position = 'absolute';
    input.style.left = '-9999px';
    document.body.appendChild(input);
    input.select();
    document.execCommand('copy');
    input.remove();
  }

  function pendingCardHtml(bug) {
    return `
      <div class="bug-card bug-card-pending" data-bug-id="${bug.id}">
        <div class="bug-card-meta">
          <span class="bug-reporter">@${bug.reporter}</span>
          <span class="bug-date">${bug.created_at}</span>
        </div>
        <p class="bug-body-text">${escapeHtml(bug.body)}</p>
        <div class="bug-actions">
          <button class="btn-bug-approve" data-bug-approve="${bug.id}">✔ 通过并收录</button>
          <button class="btn-bug-reject"  data-bug-reject="${bug.id}">✘ 拒绝</button>
        </div>
      </div>`;
  }

  function approvedCardHtml(bug, showCopyButton = false) {
    const actionButtons = showCopyButton
      ? `
        <div class="bug-actions">
          <button class="btn-bug-copy" type="button" data-bug-copy="${bug.id}">复制给 Agent</button>
          <button class="btn-bug-archive" type="button" data-bug-archive="${bug.id}">标记已归档</button>
        </div>`
      : '';

    return `
      <div class="bug-card bug-card-approved" data-bug-id="${bug.id}">
        <div class="bug-card-header">
          <div class="bug-card-meta">
            <span class="bug-reporter">@${bug.reporter}</span>
            <span class="bug-date">${bug.approved_at || bug.created_at}</span>
          </div>
          <span class="bug-approved-badge">已收录</span>
        </div>
        <p class="bug-body-text">${escapeHtml(bug.body)}</p>
        ${actionButtons}
      </div>`;
  }

  function archivedCardHtml(bug) {
    return `
      <div class="bug-card bug-card-archived" data-bug-id="${bug.id}">
        <div class="bug-card-header">
          <div class="bug-card-meta">
            <span class="bug-reporter">@${bug.reporter}</span>
            <span class="bug-date">${bug.approved_at || bug.created_at}</span>
          </div>
          <span class="bug-archived-badge">已归档</span>
        </div>
        <p class="bug-body-text">${escapeHtml(bug.body)}</p>
      </div>`;
  }

  function updateArchivedSummary(count) {
    archivedTotal = count;
    if (archivedCount) archivedCount.textContent = String(count);
    if (clearArchivedBtn) {
      clearArchivedBtn.disabled = clearingArchived || count === 0;
      clearArchivedBtn.textContent = clearingArchived ? '清空中…' : '清空已归档';
    }
  }

  async function loadPendingBugs() {
    if (!pendingList) return;
    try {
      const res = await fetch('/api/bugs/pending');
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      if (!Array.isArray(data) || data.length === 0) {
        pendingList.innerHTML = emptyHtml('暂无待审核反馈');
        return;
      }
      pendingList.innerHTML = data.map(pendingCardHtml).join('');
      bindBugAdminButtons();
    } catch (e) {
      pendingList.innerHTML = emptyHtml('加载失败，请刷新重试');
    }
  }

  async function loadApprovedBugs() {
    if (!approvedList) return;
    try {
      const res = await fetch('/api/bugs/approved');
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      if (!Array.isArray(data) || data.length === 0) {
        approvedBugs = [];
        approvedList.innerHTML = emptyHtml('暂无已收录 Bug');
        return;
      }

      approvedBugs = data;
      approvedList.innerHTML = data.map(bug => approvedCardHtml(bug, isAdmin)).join('');
      if (isAdmin) bindApprovedBugButtons();
    } catch (e) {
      approvedBugs = [];
      approvedList.innerHTML = emptyHtml('加载失败，请刷新重试');
    }
  }

  async function loadArchivedBugs() {
    if (!archivedList) return;
    try {
      const res = await fetch('/api/bugs/archived');
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      if (!Array.isArray(data) || data.length === 0) {
        updateArchivedSummary(0);
        archivedList.innerHTML = emptyHtml('暂无已归档 Bug');
        return;
      }

      updateArchivedSummary(data.length);
      archivedList.innerHTML = data.map(archivedCardHtml).join('');
    } catch (e) {
      updateArchivedSummary(0);
      archivedList.innerHTML = emptyHtml('加载失败，请刷新重试');
    }
  }

  async function clearArchivedBugs() {
    if (clearingArchived || archivedTotal === 0) return;
    if (!window.confirm('确认清空所有已归档 Bug 吗？该操作不可撤销。')) return;

    clearingArchived = true;
    updateArchivedSummary(archivedTotal);
    try {
      const res = await fetch('/api/bugs/archived', { method: 'DELETE' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) {
        throw new Error(data?.detail || '清空失败');
      }
      showClientFlash(`已清空 ${data.cleared_count || 0} 条已归档 Bug`, 'success');
      await loadArchivedBugs();
    } catch (e) {
      showClientFlash(e?.message || '清空失败', 'error');
    } finally {
      clearingArchived = false;
      updateArchivedSummary(archivedTotal);
    }
  }

  async function submitBug() {
    const body = bodyEl ? bodyEl.value.trim() : '';
    if (!body) {
      showClientFlash('请填写 Bug 描述后再提交', 'error');
      return;
    }
    if (submitBtn) submitBtn.disabled = true;
    try {
      const res = await fetch('/api/bugs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || '提交失败');
      if (bodyEl) bodyEl.value = '';
      showClientFlash('反馈已提交，等待管理员审核 ✓', 'success');
      if (isAdmin) await loadPendingBugs();
    } catch (e) {
      showClientFlash(e?.message || '提交失败', 'error');
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  async function doApprove(bugId) {
    try {
      const res = await fetch(`/api/bugs/${bugId}/approve`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || '操作失败');
      showClientFlash('已通过并写入 bug.md ✓', 'success');
      await Promise.all([loadPendingBugs(), loadApprovedBugs()]);
    } catch (e) {
      showClientFlash(e?.message || '操作失败', 'error');
    }
  }

  async function doReject(bugId) {
    try {
      const res = await fetch(`/api/bugs/${bugId}/reject`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || '操作失败');
      showClientFlash('已拒绝该反馈', 'success');
      await loadPendingBugs();
    } catch (e) {
      showClientFlash(e?.message || '操作失败', 'error');
    }
  }

  async function copyApprovedBug(bugId) {
    const bug = approvedBugs.find(item => Number(item.id) === Number(bugId));
    if (!bug) {
      showClientFlash('未找到要复制的 Bug 内容', 'error');
      return;
    }

    const payload = [
      `【Benbot 已收录 Bug #${bug.id}】`,
      `提交人: @${bug.reporter}`,
      `收录时间: ${bug.approved_at || bug.created_at || '-'}`,
      '',
      '请根据以下描述进行人工修复，并在完成后自行回归验证：',
      bug.body,
    ].join('\n');

    try {
      await copyText(payload);
      showClientFlash(`已复制 Bug #${bug.id}，可直接粘贴给 Agent`, 'success');
    } catch (e) {
      showClientFlash(e?.message || '复制失败', 'error');
    }
  }

  async function doArchive(bugId) {
    try {
      const res = await fetch(`/api/bugs/${bugId}/archive`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || '操作失败');
      const archivedId = data?.bug?.id ?? bugId;
      showClientFlash(`已归档 Bug #${archivedId}`, 'success');
      await Promise.all([loadApprovedBugs(), loadArchivedBugs()]);
    } catch (e) {
      showClientFlash(e?.message || '归档失败', 'error');
    }
  }

  function bindBugAdminButtons() {
    if (!pendingList) return;
    pendingList.querySelectorAll('[data-bug-approve]').forEach(btn => {
      btn.addEventListener('click', () => doApprove(Number(btn.dataset.bugApprove)));
    });
    pendingList.querySelectorAll('[data-bug-reject]').forEach(btn => {
      btn.addEventListener('click', () => doReject(Number(btn.dataset.bugReject)));
    });
  }

  function bindApprovedBugButtons() {
    if (!approvedList) return;
    approvedList.querySelectorAll('[data-bug-copy]').forEach(btn => {
      btn.addEventListener('click', () => {
        void copyApprovedBug(Number(btn.dataset.bugCopy));
      });
    });
    approvedList.querySelectorAll('[data-bug-archive]').forEach(btn => {
      btn.addEventListener('click', () => {
        void doArchive(Number(btn.dataset.bugArchive));
      });
    });
  }

  if (submitBtn) submitBtn.addEventListener('click', submitBug);
  if (archivedToggle && archivedSection) {
    archivedToggle.addEventListener('click', () => {
      const nextCollapsed = !archivedSection.classList.contains('collapsed');
      archivedSection.classList.toggle('collapsed', nextCollapsed);
      archivedToggle.setAttribute('aria-expanded', nextCollapsed ? 'false' : 'true');
    });
  }
  if (clearArchivedBtn) {
    clearArchivedBtn.addEventListener('click', () => {
      void clearArchivedBugs();
    });
  }
  if (isAdmin) void loadPendingBugs();
  if (isAdmin || approvedList) void loadApprovedBugs();
  if (isAdmin || archivedList) void loadArchivedBugs();
})();
