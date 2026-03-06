'use strict';

const STATUS_LABELS = { up: '运行中', down: '不可达', unknown: '检测中' };
const SERVICE_LABELS = { running: '已开启', stopped: '已关闭', unknown: '未知' };
const ACTION_LABELS = { start: '启动', stop: '停止', restart: '重启', status: '刷新' };

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
  const restartBtn = card.querySelector('[data-project-restart]');
  if (toggle) toggle.disabled = busy;
  if (restartBtn) restartBtn.disabled = busy;
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
    const restartBtn = card.querySelector('[data-project-restart]');

    if (toggle) {
      toggle.addEventListener('change', async () => {
        const intendedState = toggle.checked;
        const action = intendedState ? 'start' : 'stop';
        const ok = await controlProject(card, action);
        if (!ok) toggle.checked = !intendedState;
      });
    }

    if (restartBtn) {
      restartBtn.addEventListener('click', async () => {
        await controlProject(card, 'restart');
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
    const map = { health_check:'健康检查', project_control:'运行控制', system:'系统' };
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

  // ── 渲染工具 ─────────────────────────────────────────
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

  function approvedCardHtml(bug, showVerifyBtn = false) {
    const repairedClass = bug.repaired ? ' bug-repaired' : '';
    const verifiedClass = bug.verified ? ' bug-verified' : '';
    const repairedBadge = bug.repaired ? '<span class="bug-repaired-badge">✅ 已修复</span>' : '';
    const verifiedBadge = bug.verified ? '<span class="bug-verified-badge">✓ 已确认</span>' : '';
    
    let actionButtons = '';
    if (showVerifyBtn) {
      if (!bug.verified && bug.repaired) {
        // Show both verify and reopen buttons for repaired but not verified bugs
        actionButtons = `
          <div class="bug-actions">
            <button class="btn-bug-verify" data-bug-verify="${bug.id}">✓ 确认修复</button>
            <button class="btn-bug-reopen" data-bug-reopen="${bug.id}">↺ 打回重修复</button>
          </div>`;
      } else if (!bug.repaired) {
        // Show waiting status for unrepaired bugs
        actionButtons = `
          <div class="bug-actions">
            <span class="bug-waiting-hint">⏳ 等待修复中…</span>
          </div>`;
      }
    }
    
    return `
      <div class="bug-card bug-card-approved${repairedClass}${verifiedClass}" data-bug-id="${bug.id}">
        <div class="bug-card-header">
          <div class="bug-card-meta">
            <span class="bug-reporter">@${bug.reporter}</span>
            <span class="bug-date">${bug.approved_at || bug.created_at}</span>
          </div>
          <div class="bug-badges">
            ${repairedBadge}
            ${verifiedBadge}
          </div>
        </div>
        <p class="bug-body-text">${escapeHtml(bug.body)}</p>
        ${actionButtons}
      </div>`;
  }

  // ── 数据加载 ──────────────────────────────────────────
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
        approvedList.innerHTML = emptyHtml('暂无已收录 Bug');
        return;
      }
      
      // Separate by repaired and verified status
      const unrepaired = data.filter(bug => !bug.repaired);
      const repairedNotVerified = data.filter(bug => bug.repaired && !bug.verified);
      const repairedVerified = data.filter(bug => bug.repaired && bug.verified);
      
      let html = '';
      
      // Show unrepaired bugs first
      if (unrepaired.length > 0) {
        html += unrepaired.map(bug => approvedCardHtml(bug, isAdmin)).join('');
      }
      
      // Show repaired but not verified bugs
      if (repairedNotVerified.length > 0) {
        html += repairedNotVerified.map(bug => approvedCardHtml(bug, isAdmin)).join('');
      }
      
      // Show verified bugs in a collapsible section
      if (repairedVerified.length > 0) {
        html += `
          <div class="bug-repaired-section">
            <button class="bug-repaired-toggle" onclick="this.parentElement.classList.toggle('collapsed')">
              <svg class="toggle-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
              <span>已确认修复的 Bug（${repairedVerified.length}）</span>
            </button>
            <div class="bug-repaired-list">
              ${repairedVerified.map(bug => approvedCardHtml(bug, false)).join('')}
            </div>
          </div>`;
      }
      
      approvedList.innerHTML = html;
      if (isAdmin) bindBugVerifyButtons();
    } catch (e) {
      approvedList.innerHTML = emptyHtml('加载失败，请刷新重试');
    }
  }

  // ── 提交 Bug ──────────────────────────────────────────
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

  // ── 管理员审核操作 ────────────────────────────────────
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

  async function doVerify(bugId) {
    try {
      const res = await fetch(`/api/bugs/${bugId}/verify`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || '操作失败');
      showClientFlash('已确认该 Bug 已修复 ✓', 'success');
      await loadApprovedBugs();
    } catch (e) {
      showClientFlash(e?.message || '操作失败', 'error');
    }
  }

  async function doReopen(bugId) {
    try {
      const res = await fetch(`/api/bugs/${bugId}/reopen`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || '操作失败');
      showClientFlash('已打回重新修复，nanobot 将重新处理', 'success');
      await Promise.all([loadPendingBugs(), loadApprovedBugs()]);
    } catch (e) {
      showClientFlash(e?.message || '操作失败', 'error');
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

  function bindBugVerifyButtons() {
    if (!approvedList) return;
    approvedList.querySelectorAll('[data-bug-verify]').forEach(btn => {
      btn.addEventListener('click', () => doVerify(Number(btn.dataset.bugVerify)));
    });
    approvedList.querySelectorAll('[data-bug-reopen]').forEach(btn => {
      btn.addEventListener('click', () => doReopen(Number(btn.dataset.bugReopen)));
    });
  }

  // ── 事件绑定 & 初始化加载 ─────────────────────────────
  if (submitBtn) submitBtn.addEventListener('click', submitBug);
  void loadApprovedBugs();
  if (isAdmin) void loadPendingBugs();
})();
