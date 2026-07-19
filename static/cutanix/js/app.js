(function() {
  'use strict';

  const API = '/api';
  let user = null;
  let currentTab = 'scan';
  let refreshPricingCards = null;
  let refreshProfileView = null;
  let pulseTier = null;

  function getInitData() {
    try {
      const tg = window.Telegram?.WebApp;
      if (tg) {
        if (tg.initDataRaw) return tg.initDataRaw;
        if (tg.initData) return tg.initData;
      }
    } catch(e) {}
    return '';
  }

  function initDataHeader() {
    const d = getInitData();
    const headers = {};
    if (d) headers['X-Telegram-Init-Data'] = d;
    return headers;
  }

  async function apiGet(path) {
    try {
      const r = await fetch(API + path, { headers: initDataHeader() });
      if (r.status === 401) return null;
      const ct = r.headers.get('content-type') || '';
      if (!ct.includes('json')) {
        console.warn('[Cutanix] Non-JSON response for', path, 'content-type:', ct);
        return null;
      }
      return r.json();
    } catch(e) {
      console.warn('[Cutanix] API error:', path, e.message);
      return null;
    }
  }

  async function apiPost(path, body) {
    try {
      const r = await fetch(API + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...initDataHeader() },
        body: JSON.stringify(body),
      });
      const ct = r.headers.get('content-type') || '';
      if (!ct.includes('json')) return null;
      return r.json();
    } catch(e) { return null; }
  }

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  async function postAnalysis(payload) {
    let r;
    if (payload instanceof FormData) {
      r = await fetch(API + '/analysis/', { method: 'POST', headers: initDataHeader(), body: payload });
    } else {
      r = await fetch(API + '/analysis/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...initDataHeader() },
        body: JSON.stringify(payload),
      });
    }
    if (!r.ok) {
      let msg = 'Ошибка анализа';
      try { const j = await r.json(); if (j.error) msg = j.error; } catch(e) {}
      throw new Error(msg);
    }
    const ct = r.headers.get('content-type') || '';
    if (!ct.includes('json')) return null;
    return r.json();
  }

  function progressCardHTML(label) {
    return `
      <div class="bg-card p-6 neon-border text-center fade-in">
        <p class="text-gray-200 text-sm font-medium mb-4">${label}</p>
        <div class="progress-bar progress-indeterminate">
          <div class="progress-fill"></div>
        </div>
        <p class="text-gray-500 text-xs mt-3">Распознаём состав и оцениваем безопасность…</p>
      </div>
    `;
  }

  async function pollAnalysis(taskId, resultEl) {
    for (let i = 0; i < 40; i++) {
      const data = await apiGet('/analysis/' + taskId + '/');
      if (data && data.status === 'ready' && data.result) {
        hapticOk();
        showResult(resultEl, data);
        await loadProfile();
        return;
      }
      if (data && data.status === 'failed') {
        resultEl.innerHTML = '<div class="bg-card p-4 text-center text-red-400 text-sm">Ошибка анализа</div>';
        return;
      }
      await sleep(1500);
    }
    resultEl.innerHTML = '<div class="bg-card p-4 text-center text-red-400 text-sm">Превышено время ожидания</div>';
  }

  async function loadProfile() {
    user = await apiGet('/user/profile/');
    if (!user) {
      user = {
        telegram_id: 0, username: '', first_name: 'Пользователь', last_name: '',
        photo_url: '', subscription_tier: 'free', subscription_expires: null,
        requests_used: 0, requests_limit: 3, is_subscription_active: true,
      };
    }
  }

  function hideLoading() {
    const el = document.getElementById('loading');
    if (el) el.remove();
  }

  function render() {
    const app = document.getElementById('app');
    app.innerHTML = `
      <div id="tab-scan" class="tab-content active"></div>
      <div id="tab-history" class="tab-content"></div>
      <div id="tab-pricing" class="tab-content"></div>
      <div id="tab-profile" class="tab-content"></div>
      <nav class="fixed bottom-0 left-0 right-0 bg-[#1a1a24]/95 backdrop-blur border-t border-[#2a2a35] z-50">
        <div class="flex justify-around items-center h-16 max-w-lg mx-auto">
          ${['scan','history','pricing','profile'].map((id, i) =>
            `<a href="#${id}" class="tab-link flex flex-col items-center gap-0.5 px-4 py-1 text-[10px] font-medium transition-all ${id === currentTab ? 'text-[#00ff88] scale-105' : 'text-gray-500'}" data-tab="${id}">
              ${[`<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"/></svg>`,
                 `<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"/></svg>`,
                 `<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"/></svg>`,
                 `<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/></svg>`][i]}
              <span class="text-[10px] font-medium">${['Проверка','История','Подписки','Профиль'][i]}</span>
            </a>`
          ).join('')}
        </div>
      </nav>
    `;
    document.querySelectorAll('.tab-link').forEach(el => {
      el.addEventListener('click', e => {
        e.preventDefault();
        switchTab(el.dataset.tab);
      });
    });
    renderTab(currentTab);
  }

  function haptic(style) {
    try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.(style); } catch(e) {}
  }
  function hapticOk() {
    try { window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred?.('success'); } catch(e) {}
  }
  window.haptic = haptic;
  function esc(s) {    return (s || '').replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  const ICONS = {
    scan: `<svg class="w-7 h-7" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 18a9.065 9.065 0 0 1-6.23-2.207L4.2 15.3m15.6 0 1.045.261a3 3 0 0 1 2.105 2.839V18a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3v-.6a3 3 0 0 1 2.105-2.839l1.045-.261"/></svg>`,
    history: `<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"/></svg>`,
    pricing: `<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 002.455 2.456zM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"/></svg>`,
    profile: `<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/></svg>`,
    check: `<svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>`,
    chevron: `<svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5"/></svg>`,
  };

  function spinnerHTML(label) {
    return `<div class="flex flex-col items-center justify-center py-16 text-gray-500 fade-in">
      <svg width="32" height="32" viewBox="0 0 40 40" class="animate-spin mb-3">
        <circle cx="20" cy="20" r="16" fill="none" stroke="#00ff88" stroke-width="3" stroke-dasharray="80" stroke-dashoffset="60" stroke-linecap="round"/>
      </svg>
      ${label ? `<span class="text-sm">${esc(label)}</span>` : ''}
    </div>`;
  }

  function switchTab(tab) {
    currentTab = tab;
    haptic('light');
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');
    document.querySelectorAll('.tab-link').forEach(el => {
      el.classList.toggle('text-[#00ff88]', el.dataset.tab === tab);
      el.classList.toggle('scale-105', el.dataset.tab === tab);
      el.classList.toggle('text-gray-500', el.dataset.tab !== tab);
    });
    renderTab(tab);
  }

  function renderTab(tab) {
    const el = document.getElementById('tab-' + tab);
    if (!el) return;
    switch(tab) {
      case 'scan': renderScan(el); break;
      case 'history': renderHistory(el); break;
      case 'pricing': renderPricing(el); break;
      case 'profile': renderProfile(el); break;
    }
  }

  function renderScan(el) {
    el.innerHTML = `
      <div class="flex items-center gap-2 mb-1">
        <span class="text-[#00ff88]">${ICONS.scan}</span>
        <h1 class="text-2xl font-bold"><span class="text-[#00ff88]">Cutanix</span></h1>
      </div>
      <p class="text-gray-400 text-sm mb-6">Проверьте безопасность вашего косметического средства</p>
      <div class="relative flex bg-[#1a1a24] rounded-xl p-1 mb-5">
        <div id="mode-slider" class="floating-pill" style="width: calc(50% - 4px); transform: translateX(0%);"></div>
        <button class="mode-btn flex-1 relative z-10 py-2.5 rounded-lg text-sm font-medium transition-colors duration-300 text-[#0a0a0f]" data-mode="photo">Фото</button>
        <button class="mode-btn flex-1 relative z-10 py-2.5 rounded-lg text-sm font-medium transition-colors duration-300 text-gray-400 hover:text-gray-300" data-mode="text">Текст</button>
      </div>
      <div id="photo-zone" class="relative overflow-hidden rounded-2xl border-2 border-dashed border-[#2a2a35] p-8 text-center cursor-pointer transition-all hover:border-[#00ff88]/30 hover:bg-[#1a1a24]/50 mb-4">
        <input type="file" id="photo-input" accept="image/*" class="hidden">
        <div id="photo-preview" class="hidden absolute inset-0 bg-cover bg-center"></div>
        <div id="photo-change" class="hidden absolute bottom-2 left-1/2 -translate-x-1/2 z-20 bg-[#0a0a0f]/80 text-[#00ff88] text-xs px-3 py-1.5 rounded-full border border-[#00ff88]/30">Изменить фото</div>
        <div id="photo-placeholder" class="relative z-10">
          <div class="w-14 h-14 mx-auto mb-3 rounded-full bg-[#2a2a35] flex items-center justify-center">
            <svg class="w-7 h-7 text-[#00ff88]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"/>
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z"/>
            </svg>
          </div>
          <p class="text-gray-200 text-sm font-medium">Нажмите, чтобы загрузить фото</p>
          <p class="text-gray-500 text-xs mt-1.5">${user?.subscription_tier ? 'JPG, PNG до 10 МБ' : 'Доступно в платных тарифах'}</p>
        </div>
      </div>
      <textarea id="inci-text" placeholder="Вставьте состав текстом (INCI)..." class="hidden w-full bg-[#1a1a24] border border-[#2a2a35] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-[#00ff88]/50 transition-all" rows="5"></textarea>
      <button id="btn-analyze" class="btn btn-primary mt-3" disabled>Анализировать фото</button>
      <div id="result-area" class="mt-6 space-y-4"></div>
    `;

    const textarea = document.getElementById('inci-text');
    const btn = document.getElementById('btn-analyze');
    const photoZone = document.getElementById('photo-zone');
    const photoInput = document.getElementById('photo-input');
    const photoPreview = document.getElementById('photo-preview');
    const photoPlaceholder = document.getElementById('photo-placeholder');
    const photoChange = document.getElementById('photo-change');
    const modeSlider = document.getElementById('mode-slider');
    const modeBtns = el.querySelectorAll('.mode-btn');
    const canAnalyze = user && (user.requests_used || 0) < (user.requests_limit || 3);
    let selectedPhoto = null;
    let mode = 'photo';
    let analyzing = false;

    function setLocked(lock) {
      analyzing = lock;
      textarea.disabled = lock;
      modeBtns.forEach(b => b.disabled = lock);
      photoInput.disabled = lock;
      photoZone.style.pointerEvents = lock ? 'none' : '';
      photoChange.classList.toggle('opacity-40', lock);
    }

    function updateBtn() {
      const ready = mode === 'photo' ? !!selectedPhoto : !!textarea.value.trim();
      btn.disabled = !ready;
      btn.textContent = mode === 'photo' ? 'Анализировать фото' : 'Анализировать';
    }

    function updateMode() {
      modeSlider.style.transform = mode === 'photo' ? 'translateX(0%)' : 'translateX(100%)';
      modeBtns.forEach(b => {
        if (b.dataset.mode === mode) {
          b.classList.remove('text-gray-400', 'hover:text-gray-300');
          b.classList.add('text-[#0a0a0f]');
        } else {
          b.classList.add('text-gray-400', 'hover:text-gray-300');
          b.classList.remove('text-[#0a0a0f]');
        }
      });
      photoZone.classList.toggle('hidden', mode !== 'photo');
      textarea.classList.toggle('hidden', mode !== 'text');
      resultArea().innerHTML = '';
      updateBtn();
    }

    function resultArea() {
      return document.getElementById('result-area');
    }

    modeBtns.forEach(b => {
      b.addEventListener('click', () => {
        if (analyzing) return;
        haptic('light');
        mode = b.dataset.mode;
        updateMode();
      });
    });

    textarea.addEventListener('input', updateBtn);

    btn.addEventListener('click', async () => {
      if (analyzing) return;
      if (mode === 'photo' && !selectedPhoto) return;
      if (mode === 'text' && !textarea.value.trim()) return;
      haptic('medium');
      btn.disabled = true;
      setLocked(true);
      const prevText = btn.textContent;
      btn.textContent = 'Анализируем...';
      const resultEl = resultArea();
      resultEl.innerHTML = progressCardHTML('Анализируем состав…');
      try {
        let data;
        if (mode === 'photo' && selectedPhoto) {
          const fd = new FormData();
          fd.append('image', selectedPhoto);
          data = await postAnalysis(fd);
        } else {
          data = await postAnalysis({ text: textarea.value.trim() });
        }
        if (data?.task_id) await pollAnalysis(data.task_id, resultEl);
      } catch(e) {
        resultEl.innerHTML = `<div class="bg-card p-4 text-center text-red-400 text-sm">${e.message || 'Ошибка анализа'}</div>`;
      } finally {
        setLocked(false);
        btn.textContent = prevText;
        updateBtn();
      }
    });

    photoZone.addEventListener('click', () => {
      if (analyzing) return;
      haptic('light');
      if (!user?.subscription_tier) {
        showPaywall();
        return;
      }
      photoInput.click();
    });

    photoInput.addEventListener('change', (e) => {
      if (analyzing) return;
      const file = e.target.files?.[0];
      if (!file) return;
      selectedPhoto = file;
      const reader = new FileReader();
      reader.onload = (ev) => {
        photoPreview.style.backgroundImage = `url(${ev.target.result})`;
        photoPreview.classList.remove('hidden');
        photoChange.classList.remove('hidden');
        photoPlaceholder.classList.add('hidden');
      };
      reader.readAsDataURL(file);
      resultArea().innerHTML = '';
      updateBtn();
      photoInput.value = '';
    });

    if (!canAnalyze && user) {
      const p = document.createElement('p');
      p.className = 'text-xs text-red-400 text-center mt-2';
      p.textContent = 'Достигнут лимит запросов. Обновите тариф.';
      btn.parentNode.appendChild(p);
    }

    updateMode();
  }

  function resultCardHTML(r) {
    const statusOrder = { red: 0, yellow: 1, green: 2 };
    const comps = [...(r.components || [])].sort(
      (a, b) => (statusOrder[a.status] ?? 3) - (statusOrder[b.status] ?? 3)
    );
    const safetyColor = r.safety_index >= 7 ? 'text-green-400' : r.safety_index >= 4 ? 'text-yellow-400' : 'text-red-400';
    const verdictBg = r.verdict_en === 'safe' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400';
    return `
      <div class="bg-card p-5 neon-border fade-in">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-semibold text-lg">Индекс безопасности</h3>
          <span class="text-3xl font-bold ${safetyColor}">${r.safety_index}/10</span>
        </div>
        <div class="progress-bar mb-4">
          <div class="progress-fill ${r.safety_index >= 7 ? 'bg-green-400' : r.safety_index >= 4 ? 'bg-yellow-400' : 'bg-red-400'}" style="width:${r.safety_index * 10}%"></div>
        </div>
        <div class="flex items-center justify-between text-sm">
          <span class="text-gray-400">Комедогенность</span>
          <span class="font-medium">${r.comedogenicity}/10</span>
        </div>
        <div class="mt-3 text-center">
          <span class="inline-block px-4 py-1.5 rounded-full text-sm font-medium ${verdictBg}">${r.verdict}</span>
        </div>
        ${r.summary ? `<p class="text-gray-400 text-xs mt-3 text-center">${r.summary}</p>` : ''}
      </div>
      ${comps.length ? `
      <div class="bg-card p-4">
        <h3 class="font-semibold mb-3 text-sm">Компоненты</h3>
        <div class="space-y-2" id="components-list">${comps.map((c, i) => `
          <div class="bg-card-inner p-3 cursor-pointer" onclick="try{window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.('light')}catch(e){};this.querySelector('.comp-detail').classList.toggle('hidden')">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <span class="w-2.5 h-2.5 rounded-full ${c.status === 'green' ? 'bg-green-400' : c.status === 'yellow' ? 'bg-yellow-400' : 'bg-red-400'}"></span>
                <span class="text-sm font-medium">${c.name}</span>
              </div>
              ${ICONS.chevron}
            </div>
            <div class="comp-detail mt-2 text-xs text-gray-400 space-y-1 pl-5 hidden">
              <p>${c.function}</p>
              <p class="text-gray-500">${c.safety_note}</p>
            </div>
          </div>
        `).join('')}</div>
      </div>` : ''}
    `;
  }

  function showResult(el, data) {
    if (data.status !== 'ready' || !data.result) {
      el.innerHTML = '<div class="bg-card p-4 text-center text-gray-400 text-sm">Анализ ещё не готов</div>';
      return;
    }
    el.innerHTML = resultCardHTML(data.result);
  }

  function showHistoryDetail(item) {
    const overlay = document.createElement('div');
    overlay.className = 'fixed inset-0 z-50 flex items-start justify-center bg-black/70 backdrop-blur px-4 pt-10 pb-10 overflow-y-auto';
    const st = item.status;
    const statusText = st === 'ready' ? 'Готово' : st === 'failed' ? 'Ошибка' : 'В обработке';
    const statusColor = st === 'ready' ? 'text-green-400' : st === 'failed' ? 'text-red-400' : 'text-yellow-400';
    const reqText = item.input_text || (item.image ? 'Состав распознан с фото' : 'Без текста');
    const reqTextHtml = esc(reqText);
    const reqLabel = item.image ? 'Состав (распознано с фото)' : 'Состав (INCI)';
    const resultHTML = (st === 'ready' && item.result)
      ? resultCardHTML(item.result)
      : '<div class="bg-card p-4 text-center text-gray-400 text-sm">Анализ ещё не готов</div>';
    overlay.innerHTML = `
      <div class="bg-card p-6 max-w-md w-full border border-[#00ff88]/20 modal-in fade-in">
        <div class="flex items-start justify-between mb-4">
          <div>
            <h3 class="font-bold text-lg">Запрос</h3>
            <p class="text-xs text-gray-500 mt-0.5">${new Date(item.created_at).toLocaleString('ru-RU')}</p>
          </div>
          <button class="text-gray-400 hover:text-white text-2xl leading-none -mt-1" onclick="try{window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.('light')}catch(e){}; this.closest('.fixed').remove()">×</button>
        </div>
        <div class="mb-4">
          <span class="text-xs ${statusColor}">${statusText}</span>
        </div>
        <div class="bg-[#1a1a24] border border-[#2a2a35] rounded-xl p-3 mb-4">
          <p class="text-xs text-gray-500 mb-1.5">${reqLabel}</p>
          <p class="text-sm text-gray-200 whitespace-pre-wrap break-words">${reqTextHtml}</p>
        </div>
        <div class="space-y-4">${resultHTML}</div>
      </div>
    `;
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.remove();
    });
    document.body.appendChild(overlay);
  }
  window.showHistoryDetail = showHistoryDetail;

  function showPaywall() {
    const overlay = document.createElement('div');
    overlay.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur px-4';
    overlay.innerHTML = `
      <div class="bg-card p-6 max-w-sm w-full border border-[#00ff88]/30 fade-in">
        <div class="text-center">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-[#00ff88]/10 flex items-center justify-center">
            <svg class="w-8 h-8 text-[#00ff88]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"/>
            </svg>
          </div>
          <h3 class="text-lg font-bold mb-2">Pro-версия</h3>
          <p class="text-gray-400 text-sm mb-6">Сканирование по фото доступно в Pro-версии</p>
          <div class="space-y-2.5">
            <button class="btn btn-primary" onclick="switchTab('pricing'); this.closest('.fixed').remove()">Посмотреть тарифы</button>
            <button class="btn btn-secondary" onclick="try{window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.('light')}catch(e){}; this.closest('.fixed').remove()">Отмена</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
  }

  function renderHistory(el) {
    el.innerHTML = `<h1 class="text-2xl font-bold mb-6"><span class="inline-flex items-center">${ICONS.history}</span> <span class="text-[#00ff88]">История</span></h1>` + spinnerHTML('Загрузка...');
    apiGet('/history/').then(data => {
      if (!data || !data.results?.length) {
        el.innerHTML = `<h1 class="text-2xl font-bold mb-6"><span class="inline-flex items-center">${ICONS.history}</span> <span class="text-[#00ff88]">История</span></h1><div class="text-center text-gray-400 py-8 fade-in"><p class="text-lg mb-2">История пуста</p><p class="text-sm text-gray-500">Проверьте состав, чтобы появилась запись</p></div>`;
        return;
      }
      el.innerHTML = `<h1 class="text-2xl font-bold mb-6"><span class="inline-flex items-center">${ICONS.history}</span> <span class="text-[#00ff88]">История</span></h1><div class="space-y-3">${data.results.map(item => {
        const st = item.status;
        const statusText = st === 'ready' ? 'Готово' : st === 'failed' ? 'Ошибка' : 'В обработке';
        const statusColor = st === 'ready' ? 'text-green-400' : st === 'failed' ? 'text-red-400' : 'text-yellow-400';
        const preview = item.input_text || (item.image ? 'Состав распознан с фото' : 'Без текста');
        const short = preview.length > 110 ? preview.slice(0, 110) + '…' : preview;
        return `
        <div class="bg-card p-4 min-h-[128px] fade-in cursor-pointer flex flex-col" onclick="haptic('light'); showHistoryDetail(${JSON.stringify(item).replace(/"/g, '&quot;')})">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-gray-400">${new Date(item.created_at).toLocaleDateString('ru-RU')}</span>
            <span class="text-xs ${statusColor}">${statusText}</span>
          </div>
          <p class="text-sm text-gray-300 line-clamp-2 flex-1">${esc(short)}</p>
          ${item.result ? `<div class="flex items-center gap-2 mt-2 text-xs"><span class="${item.result.safety_index >= 7 ? 'text-green-400' : item.result.safety_index >= 4 ? 'text-yellow-400' : 'text-red-400'}">Безопасность: ${item.result.safety_index}/10</span></div>` : ''}
        </div>`;
      }).join('')}</div>`;
    }).catch(() => {
      el.innerHTML = `<h1 class="text-2xl font-bold mb-6"><span class="inline-flex items-center">${ICONS.history}</span> <span class="text-[#00ff88]">История</span></h1><div class="text-center text-red-400 py-8 fade-in">Ошибка загрузки истории</div>`;
    });
  }

  function renderPricing(el) {
    el.innerHTML = `<h1 class="text-2xl font-bold mb-6"><span class="inline-flex items-center">${ICONS.pricing}</span> <span class="text-[#00ff88]">Подписки</span></h1>` + spinnerHTML('Загрузка...');
    apiGet('/pricing/').then(plans => {
      if (!plans?.length) { el.innerHTML = `<h1 class="text-2xl font-bold mb-6"><span class="inline-flex items-center">${ICONS.pricing}</span> <span class="text-[#00ff88]">Подписки</span></h1><div class="text-center text-gray-400 py-8 fade-in">Нет доступных тарифов</div>`; return; }

      el.innerHTML = `
        <h1 class="text-2xl font-bold mb-6"><span class="inline-flex items-center">${ICONS.pricing}</span> <span class="text-[#00ff88]">Подписки</span></h1>
        <div class="space-y-4">
          ${plans.map(plan => `
            <div class="bg-card p-5 ${plan.is_featured ? 'neon-border neon-glow relative' : ''} ${pulseTier === plan.name ? 'just-activated' : ''}">
              ${plan.is_featured ? '<div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#00ff88] text-[#0a0a0f] text-xs font-bold px-3 py-0.5 rounded-full">ЛУЧШИЙ ВЫБОР</div>' : ''}
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold">${plan.name}</h3>
                ${user?.subscription_tier === plan.name ? `<span class="text-xs bg-[#00ff88]/20 text-[#00ff88] px-2 py-0.5 rounded-full ${pulseTier === plan.name ? 'badge-in' : ''}">Текущий</span>` : ''}
              </div>
              <div class="mb-4"><span class="text-3xl font-bold ${plan.is_featured ? 'text-[#00ff88]' : ''}">${plan.price_rub}</span><span class="text-gray-500 text-sm"> ₽ / ${plan.period_days} дн.</span></div>
              <div class="text-xs text-gray-500 mb-3">Лимит: ${plan.requests_limit} запросов</div>
              <ul class="space-y-2 mb-5">${(plan.features || []).map(f => `<li class="flex items-start gap-2 text-sm text-gray-300"><span class="text-[#00ff88] mt-0.5">${ICONS.check}</span>${f}</li>`).join('')}</ul>
              <button class="btn ${user?.subscription_tier === plan.name ? 'btn-secondary opacity-50 cursor-not-allowed' : 'btn-primary'}" ${user?.subscription_tier === plan.name ? 'disabled' : ''} onclick="activatePlan(${plan.id}, this)">${user?.subscription_tier === plan.name ? 'Активен' : 'Выбрать'}</button>
            </div>
          `).join('')}
        </div>
      `;

      refreshPricingCards = () => renderPricing(el);

    }).catch(() => {
      el.innerHTML = `<h1 class="text-2xl font-bold mb-6"><span class="inline-flex items-center">${ICONS.pricing}</span> <span class="text-[#00ff88]">Подписки</span></h1><div class="text-center text-red-400 py-8 fade-in">Ошибка загрузки</div>`;
    });
  }

  window.activatePlan = async function(planId, btn) {
    const plan = null;
    btn.disabled = true;
    btn.textContent = 'Оплата...';
    try {
      const data = await apiPost('/payment/create/', { plan_id: planId });
      if (data?.invoice) {
        haptic('heavy');
        window.Telegram?.WebApp?.openInvoice(data.invoice.invoice_link, async (status) => {
          if (status === 'paid' || status === 'cancelled') {
            await loadProfile();
            if (refreshPricingCards) refreshPricingCards();
            if (refreshProfileView) refreshProfileView();
          }
          btn.disabled = false;
          btn.textContent = 'Выбрать';
        });
      } else {
        btn.textContent = 'Ошибка';
        btn.disabled = false;
      }
    } catch(e) {
      btn.textContent = 'Ошибка';
      btn.disabled = false;
    }
  };

  window.switchTab = function(tab) {
    switchTab(tab);
  };

  window.openLink = function(url) {
    openLink(url);
  };

  function renderProfile(el) {
    if (!user) { el.innerHTML = '<div class="text-center text-gray-500 py-8">Загрузка...</div>'; return; }
    const progress = user.requests_limit > 0 ? (user.requests_used / user.requests_limit) * 100 : 0;
    const hasTier = !!user.subscription_tier;
    const tierColor = hasTier ? 'text-[#00ff88]' : 'text-gray-400';
    const tierBg = hasTier ? 'bg-[#00ff88]/10' : 'bg-gray-500/10';
    const progressColor = progress > 80 ? '#ef4444' : progress > 50 ? '#f59e0b' : '#00ff88';

    el.innerHTML = `
      <h1 class="text-2xl font-bold mb-6 fade-in flex items-center gap-2">${ICONS.profile} Профиль</h1>
      <div class="bg-card p-5 relative overflow-hidden fade-in">
        <div class="flex items-center gap-4 mb-5">
          ${user.photo_url
            ? `<img src="${user.photo_url}" alt="avatar" class="w-16 h-16 rounded-full object-cover border-2 border-[#2a2a35]" onerror="this.style.display='none';this.nextSibling.style.display='flex'">`
            : ''}
          <div class="w-16 h-16 rounded-full bg-[#2a2a35] flex items-center justify-center text-2xl font-bold text-[#00ff88] ${user.photo_url ? 'hidden' : ''}">${user.first_name?.[0] || 'U'}</div>
          <div class="flex-1 min-w-0">
            <h2 class="font-semibold text-lg truncate">${user.first_name || 'Пользователь'}${user.last_name ? ' ' + user.last_name : ''}</h2>
            ${user.username ? `<p class="text-gray-400 text-sm truncate">@${user.username}</p>` : ''}
          </div>
        </div>
        <div class="bg-card-inner p-4 mb-3">
          <div class="flex items-center justify-between mb-3">
            <span class="text-gray-400 text-sm">Тариф</span>
            <span class="font-bold px-3 py-1 rounded-full text-sm ${tierColor} ${tierBg}">${user.subscription_tier || 'Free'}</span>
          </div>
          ${user.subscription_expires && user.subscription_tier ? `<div class="flex items-center justify-between mb-3"><span class="text-gray-400 text-sm">Действует до</span><span class="text-sm">${new Date(user.subscription_expires).toLocaleDateString('ru-RU')}</span></div>` : ''}
          <div>
            <div class="flex items-center justify-between text-xs text-gray-400 mb-1">
              <span>Запросов</span>
              <span>${user.requests_used || 0}/${user.requests_limit || 0}</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" style="width:${Math.min(progress, 100)}%;background:${progressColor}"></div>
            </div>
          </div>
        </div>
        <div class="bg-card-inner p-4">
          <div class="flex items-center justify-between">
            <span class="text-gray-400 text-sm">Telegram ID</span>
            <span class="text-sm font-mono text-gray-300">${user.telegram_id || '—'}</span>
          </div>
        </div>
      </div>
      <div class="mt-6 space-y-2.5">
        <button class="btn btn-secondary" onclick="openLink('https://t.me/S112OS')">
          <svg class="w-5 h-5 text-[#00ff88] shrink-0" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/></svg>
          Помощь и Поддержка
        </button>
        <button class="btn btn-secondary" onclick="openLink('https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19')">
          <svg class="w-5 h-5 text-blue-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          Пользовательское соглашение
        </button>
        <button class="btn btn-secondary" onclick="openLink('https://telegra.ph/Politika-konfidencialnosti-06-21-31')">
          <svg class="w-5 h-5 text-purple-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
          Политика конфиденциальности
        </button>
        ${user.is_admin ? `
        <a href="${user.admin_url}" class="btn mt-2" style="background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.35);color:#fbbf24;">
          <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><circle cx="12" cy="12" r="3"/></svg>
          Панель администратора
        </a>` : ''}
      </div>
    `;
    refreshProfileView = () => renderProfile(el);
  }

  function openLink(url) {
    try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.('light'); } catch(e) {}
    const tg = window.Telegram?.WebApp;
    if (!tg) {
      window.open(url, '_blank');
      return;
    }
    if (url.includes('t.me/') && tg.openTelegramLink) {
      tg.openTelegramLink(url);
      return;
    }
    if (tg.openLink) {
      tg.openLink(url, { try_instant_view: true });
    }
  }

  async function init() {
    if (window.__CUTANIX_BLOCKED) return;
    var tg = window.Telegram && window.Telegram.WebApp;
    if (!tg || !tg.initData) return;
    try { tg.ready(); tg.expand(); } catch(e) {}
    await loadProfile();
    hideLoading();
    currentTab = 'scan';
    render();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
