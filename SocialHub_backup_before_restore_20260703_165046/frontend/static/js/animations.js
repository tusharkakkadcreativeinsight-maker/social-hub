// SocialHub advanced UI, animation, toast, theme, PWA, and feature helpers
(function () {
    const API_BASE = window.API || '/api';
    let deferredInstallPrompt = null;

    function authHeaders(json = true) {
        const t = localStorage.getItem('token');
        const headers = {};
        if (t) headers.Authorization = `Bearer ${t}`;
        if (json) headers['Content-Type'] = 'application/json';
        return headers;
    }

    window.showToast = function showToast(type = 'info', message = '') {
        if (typeof type !== 'string') type = 'info';
        if (!message && ['success', 'error', 'warning', 'info'].indexOf(type) === -1) {
            message = type;
            type = 'info';
        }
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        const safeType = String(type).replace(/[^a-z0-9_-]/gi, '').toLowerCase() || 'info';
        const toast = document.createElement('div');
        toast.className = `toast ${safeType}`;
        toast.setAttribute('role', 'status');
        const title = document.createElement('strong');
        title.textContent = safeType.toUpperCase();
        const body = document.createElement('div');
        body.textContent = String(message || '');
        toast.append(title, body);
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(12px) scale(.98)';
            setTimeout(() => toast.remove(), 240);
        }, 3000);
    };

    window.initPageAnimations = function initPageAnimations() {
        document.body.classList.add('fade-in');
        document.querySelectorAll('main, .container, .container-wide, .card, .post-card, .reel-card').forEach((el, index) => {
            el.classList.add('slide-up');
            el.style.animationDelay = `${Math.min(index * 35, 240)}ms`;
        });
    };

    window.initRippleEffect = function initRippleEffect() {
        document.addEventListener('click', (event) => {
            const btn = event.target.closest('button, .btn, a.nav-icon');
            if (!btn || btn.classList.contains('no-ripple')) return;
            btn.classList.add('ripple');
            const rect = btn.getBoundingClientRect();
            const span = document.createElement('span');
            const size = Math.max(rect.width, rect.height);
            span.className = 'ripple-span';
            span.style.width = span.style.height = `${size}px`;
            span.style.left = `${event.clientX - rect.left - size / 2}px`;
            span.style.top = `${event.clientY - rect.top - size / 2}px`;
            btn.appendChild(span);
            setTimeout(() => span.remove(), 620);
        }, { passive: true });
    };

    window.initButtonLoading = function initButtonLoading() {
        document.addEventListener('submit', (event) => {
            const form = event.target;
            if (!form || form.dataset.noLoading === 'true') return;
            const btn = form.querySelector('button[type="submit"], .btn-submit');
            if (!btn) return;
            btn.classList.add('btn-loading');
            btn.disabled = true;
            setTimeout(() => {
                btn.classList.remove('btn-loading');
                btn.disabled = false;
            }, 6000);
        }, true);
    };

    window.initThemeToggle = function initThemeToggle() {
        const saved = localStorage.getItem('theme') || 'dark';
        document.documentElement.dataset.theme = saved;
        document.body.classList.toggle('light-mode', saved === 'light');
        document.body.classList.toggle('dark-mode', saved === 'dark');
        window.toggleTheme = function toggleTheme() {
            const next = (document.documentElement.dataset.theme || 'dark') === 'dark' ? 'light' : 'dark';
            document.documentElement.dataset.theme = next;
            document.body.classList.toggle('light-mode', next === 'light');
            document.body.classList.toggle('dark-mode', next === 'dark');
            localStorage.setItem('theme', next);
            window.showToast('info', `${next === 'dark' ? 'Dark' : 'Light'} mode enabled`);
        };
    };

    window.initLikeAnimation = function initLikeAnimation() {
        document.addEventListener('click', (event) => {
            const target = event.target.closest('[onclick*="like"], .like-btn, .reel-action');
            if (!target) return;
            const icon = target.querySelector('i, svg') || target;
            icon.classList.remove('heart-pop');
            void icon.offsetWidth;
            icon.classList.add('heart-pop');
        }, true);
    };

    window.initSkeletonLoader = function initSkeletonLoader() {
        document.querySelectorAll('#feed-posts:empty, #reels-container:empty, #messages-container.loading').forEach((el) => {
            el.innerHTML = Array.from({ length: 3 }).map(() => `
                <div class="skeleton-card">
                    <div style="display:flex;gap:12px;align-items:center;margin-bottom:14px">
                        <div class="skeleton skeleton-avatar"></div><div style="flex:1"><div class="skeleton"></div><div class="skeleton" style="width:55%;margin-top:8px"></div></div>
                    </div>
                    <div class="skeleton" style="height:180px"></div>
                </div>`).join('');
        });
    };

    window.initStoryViewer = function initStoryViewer() {
        document.addEventListener('click', (event) => {
            const story = event.target.closest('.story-item, [data-story-url]');
            if (!story || story.dataset.viewerBound === 'true') return;
            const url = story.dataset.storyUrl || story.querySelector('img,video')?.src;
            if (!url) return;
            event.preventDefault();
            let viewer = document.getElementById('story-viewer');
            if (!viewer) {
                viewer = document.createElement('div');
                viewer.id = 'story-viewer';
                viewer.className = 'modal story-viewer';
                document.body.appendChild(viewer);
            }
            viewer.innerHTML = `<div class="modal-content modal-show" style="max-width:420px;background:#050505;color:white;padding:12px">
                <div class="story-progress"><span></span></div>
                <button class="modal-close" style="float:right;color:white" onclick="document.getElementById('story-viewer').classList.remove('active')">&times;</button>
                ${url.match(/\.(mp4|webm|mov)(\?|$)/i) ? `<video src="${url}" controls autoplay style="width:100%;border-radius:18px;margin-top:12px"></video>` : `<img src="${url}" style="width:100%;border-radius:18px;margin-top:12px">`}
            </div>`;
            viewer.classList.add('active');
        });
    };

    window.initMobileNav = function initMobileNav() {
        if (document.querySelector('.mobile-bottom-nav')) return;
        const nav = document.createElement('nav');
        nav.className = 'mobile-bottom-nav';
        nav.innerHTML = `
            <a href="/" title="Home"><i class="fas fa-home"></i></a>
            <a href="/search" title="Explore"><i class="fas fa-compass"></i></a>
            <a href="/reels" title="Reels"><i class="fas fa-clapperboard"></i></a>
            <a href="/chat" title="Chat"><i class="fas fa-comment"></i></a>
            <a href="/creator-dashboard" title="Dashboard"><i class="fas fa-chart-pie"></i></a>
            <button type="button" title="Theme" onclick="toggleTheme()"><i class="fas fa-circle-half-stroke"></i></button>`;
        document.body.appendChild(nav);
        nav.querySelectorAll('a').forEach((a) => a.classList.toggle('active', a.getAttribute('href') === location.pathname));
    };

    function setSubmitReady(form) {
        const btn = form?.querySelector('button[type="submit"]');
        if (btn) { btn.disabled = false; btn.classList.remove('btn-loading'); }
    }

    window.generateCaptionForForm = async function generateCaptionForForm() {
        const title = document.querySelector('#post-title,#reel-caption,#caption-title')?.value || '';
        const description = document.querySelector('#post-content,#caption-description,#reel-caption')?.value || '';
        const category = document.querySelector('#caption-category,#product-category')?.value || 'social';
        try {
            const res = await fetch(`${API_BASE}/ai/caption`, { method: 'POST', headers: authHeaders(), body: JSON.stringify({ title, description, category }) });
            if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Caption failed');
            const data = await res.json();
            const target = document.querySelector('#post-content,#reel-caption,#caption-output');
            if (target) target.value = `${data.caption}\n\n${(data.hashtags || []).join(' ')}`;
            window.showToast('success', 'Caption generated');
        } catch (error) { window.showToast('error', error.message); }
    };

    window.initAdvancedPages = function initAdvancedPages() {
        const path = location.pathname;
        if (path === '/creator-dashboard') loadCreatorDashboard();
        if (path === '/scheduled') loadScheduledPosts();
        if (path === '/marketplace') loadMarketplace();
        if (path === '/collabs') loadCollabs();
        document.querySelectorAll('form[data-advanced-form]').forEach((form) => {
            form.addEventListener('submit', handleAdvancedForm);
        });
    };

    async function handleAdvancedForm(event) {
        event.preventDefault();
        const form = event.currentTarget;
        const type = form.dataset.advancedForm;
        try {
            if (type === 'schedule') {
                const raw = Object.fromEntries(new FormData(form));
                const payload = {
                    content: raw.content || '',
                    scheduled_at: raw.scheduled_at,
                    content_type: raw.content_type || 'post',
                    hashtags: String(raw.hashtags || '').split(',').map((x) => x.trim().replace(/^#/, '')).filter(Boolean),
                    media_urls: [],
                };
                await fetch(`${API_BASE}/schedule/post`, { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) }).then(checkJson);
                await loadScheduledPosts();
            } else if (type === 'marketplace') {
                await fetch(`${API_BASE}/marketplace/products`, { method: 'POST', headers: authHeaders(false), body: new FormData(form) }).then(checkJson);
                await loadMarketplace();
            } else if (type === 'collab') {
                await fetch(`${API_BASE}/collabs`, { method: 'POST', headers: authHeaders(), body: JSON.stringify(Object.fromEntries(new FormData(form))) }).then(checkJson);
                await loadCollabs();
            }
            form.reset();
            window.showToast('success', 'Saved successfully');
        } catch (error) { window.showToast('error', error.message); }
        finally { setSubmitReady(form); }
    }

    async function checkJson(res) {
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Request failed');
        return res.json();
    }

    async function loadCreatorDashboard() {
        const root = document.getElementById('creator-dashboard-root');
        if (!root) return;
        root.innerHTML = '<div class="skeleton-card"><div class="skeleton" style="height:160px"></div></div>';
        try {
            const data = await fetch(`${API_BASE}/creator/dashboard`, { headers: authHeaders(false) }).then(checkJson);
            const cards = [
                ['Posts', data.total_posts], ['Reels', data.total_reels], ['Followers', data.followers], ['Following', data.following],
                ['Likes', data.likes], ['Comments', data.comments], ['Views', data.views], ['Engagement', `${data.engagement_rate}%`]
            ];
            root.innerHTML = `<div class="advanced-grid">${cards.map(([k,v]) => `<div class="feature-card"><p>${k}</p><h2 data-count="${parseFloat(v) || 0}">${v}</h2></div>`).join('')}</div>
                <div class="card" style="margin-top:18px"><h3>Performance Chart</h3><div class="chart-bars">${(data.chart || []).map(n => `<span style="height:${Math.max(8, Math.min(180, n + 8))}px" title="${n}"></span>`).join('')}</div></div>`;
            countUp(root);
        } catch (e) { root.innerHTML = `<div class="empty-state">${e.message}</div>`; }
    }

    function countUp(root = document) {
        root.querySelectorAll('[data-count]').forEach((el) => {
            const target = Number(el.dataset.count || 0);
            let current = 0;
            const step = Math.max(1, target / 30);
            const timer = setInterval(() => {
                current += step;
                if (current >= target) { current = target; clearInterval(timer); }
                el.textContent = Number.isInteger(target) ? Math.round(current).toLocaleString() : current.toFixed(2);
            }, 24);
        });
    }

    async function loadScheduledPosts() {
        const root = document.getElementById('scheduled-list');
        if (!root) return;
        try {
            const data = await fetch(`${API_BASE}/schedule/me`, { headers: authHeaders(false) }).then(checkJson);
            root.innerHTML = (data.items || []).map(item => `<div class="feature-card">
                <strong>${item.content_type || 'post'} · ${item.status}</strong><p>${item.content || ''}</p><small>${new Date(item.scheduled_at).toLocaleString()}</small>
                <button class="btn btn-sm btn-outline" onclick="deleteScheduled('${item.id}')">Delete</button></div>`).join('') || '<div class="empty-state">No scheduled posts</div>';
        } catch (e) { root.innerHTML = `<div class="empty-state">${e.message}</div>`; }
    }
    window.deleteScheduled = async function (id) {
        if (!confirm('Delete scheduled item?')) return;
        await fetch(`${API_BASE}/schedule/${id}`, { method: 'DELETE', headers: authHeaders(false) }).then(checkJson);
        window.showToast('success', 'Scheduled item deleted');
        loadScheduledPosts();
    };

    async function loadMarketplace() {
        const root = document.getElementById('marketplace-list');
        if (!root) return;
        const data = await fetch(`${API_BASE}/marketplace/products`).then(checkJson).catch(() => ({ products: [] }));
        root.innerHTML = (data.products || []).map(p => `<div class="product-card">
            ${p.image_url ? `<img src="/uploads/${p.image_url}" style="height:180px;width:100%;object-fit:cover;border-radius:16px">` : ''}
            <h3>${escapeHtmlLocal(p.title)}</h3><p>${escapeHtmlLocal(p.description || '')}</p><strong>₹${Number(p.price || 0).toLocaleString()}</strong>
            <button class="btn btn-primary btn-sm" onclick="location.href='/chat'">Message Seller</button></div>`).join('') || '<div class="empty-state">No products yet</div>';
    }

    async function loadCollabs() {
        const root = document.getElementById('collabs-list');
        if (!root) return;
        const data = await fetch(`${API_BASE}/collabs`).then(checkJson).catch(() => ({ offers: [] }));
        root.innerHTML = (data.offers || []).map(o => `<div class="collab-card"><h3>${escapeHtmlLocal(o.title)}</h3><p>${escapeHtmlLocal(o.description)}</p><small>${escapeHtmlLocal(o.category || 'General')} · ${escapeHtmlLocal(o.budget || 'Open budget')}</small><br><button class="btn btn-primary btn-sm" onclick="applyCollab('${o.id}')">Apply</button></div>`).join('') || '<div class="empty-state">No collaboration offers yet</div>';
    }
    window.applyCollab = async function (id) {
        const message = prompt('Application message') || '';
        await fetch(`${API_BASE}/collabs/${id}/apply`, { method: 'POST', headers: authHeaders(), body: JSON.stringify({ message }) }).then(checkJson);
        window.showToast('success', 'Application sent');
    };

    function escapeHtmlLocal(value) {
        return String(value || '').replace(/[&<>'"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
    }

    window.initPWAInstall = function initPWAInstall() {
        if ('serviceWorker' in navigator) navigator.serviceWorker.register('/service-worker.js').catch(() => {});
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredInstallPrompt = e;
            let btn = document.querySelector('.install-app-btn');
            if (!btn) {
                btn = document.createElement('button');
                btn.className = 'btn btn-primary install-app-btn';
                btn.innerHTML = '<i class="fas fa-download"></i> Install App';
                document.body.appendChild(btn);
            }
            btn.style.display = 'inline-flex';
            btn.onclick = async () => { deferredInstallPrompt.prompt(); await deferredInstallPrompt.userChoice; btn.style.display = 'none'; };
        });
    };

    function bootAnimations() {
        initThemeToggle();
        initPageAnimations();
        initRippleEffect();
        initButtonLoading();
        initStoryViewer();
        initLikeAnimation();
        initSkeletonLoader();
        initMobileNav();
        // Advanced page data/forms are initialized by app.js to avoid duplicate
        // submit handlers and stale renderers.
        // initAdvancedPages();
        initPWAInstall();
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bootAnimations);
    else bootAnimations();
})();
