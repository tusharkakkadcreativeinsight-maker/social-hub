// ==================== SocialHub Frontend v2.0 ====================
const API = '/api';
let currentUser = null;
let token = localStorage.getItem('access_token') || localStorage.getItem('token') || sessionStorage.getItem('access_token') || sessionStorage.getItem('token');
let refreshToken = localStorage.getItem('refresh_token') || localStorage.getItem('refreshToken') || sessionStorage.getItem('refresh_token') || sessionStorage.getItem('refreshToken');
const MAX_STORY_SIZE = 100 * 1024 * 1024;
const MAX_REEL_SIZE = 100 * 1024 * 1024;
const STORY_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo'];
const REEL_TYPES = ['video/mp4', 'video/webm', 'video/quicktime', 'application/octet-stream', 'binary/octet-stream'];
const COVER_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MUSIC_TYPES = ['audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/ogg', 'audio/mp4', 'audio/x-m4a', 'application/octet-stream'];
let reelsSoundEnabled = localStorage.getItem('reels_sound_enabled') === 'true';
let reelsPlaybackObserver = null;
let activeProfile = null;
let selectedMusic = null;
let currentPreviewAudio = null;

// ==================== AUTH UTILITIES ====================
function setTokens(access, refresh) {
    token = access; refreshToken = refresh;
    localStorage.setItem('token', access);
    localStorage.setItem('refreshToken', refresh);
    localStorage.setItem('access_token', access);
    if (refresh) localStorage.setItem('refresh_token', refresh);
}
function clearTokens() { token = null; refreshToken = null; ['token','refreshToken','access_token','refresh_token'].forEach(k => { localStorage.removeItem(k); sessionStorage.removeItem(k); }); }
function isLoggedIn() { return !!token; }
function getHeaders() { return token ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }; }
function getMultipartHeaders() { return token ? { 'Authorization': `Bearer ${token}` } : {}; }

async function api(path, opts = {}) {
    const url = API + path;
    const headers = opts.multipart ? getMultipartHeaders() : getHeaders();
    try {
        const res = await fetch(url, { headers, ...opts });
        if (res.status === 401 && refreshToken) {
            const refreshed = await refreshAccessToken();
            if (refreshed) return api(path, opts);
            clearTokens(); window.location.href = '/login'; return null;
        }
        if (!res.ok) {
            const e = await res.json().catch(() => ({}));
            // FastAPI 422 returns validation errors as arrays; convert to readable string
            if (Array.isArray(e.detail)) {
                const msgs = e.detail.map(err => err.msg || String(err)).join('; ');
                throw new Error(msgs);
            }
            throw new Error(e.detail || 'Request failed');
        }
        return res.json();
    } catch (e) { console.error('API Error:', e); throw e; }
}

async function refreshAccessToken() {
    try {
        const res = await fetch(`${API}/auth/refresh`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: refreshToken }) });
        if (res.ok) { const data = await res.json(); setTokens(data.access_token, data.refresh_token); return true; }
    } catch (e) {}
    return false;
}

// ==================== NAVIGATION ====================
function updateNav() {
    const nav = document.getElementById('nav-links');
    if (!nav) return;
    if (isLoggedIn()) {
        nav.innerHTML = `
            <button class="theme-toggle" type="button" title="Theme"><i class="fas fa-moon"></i></button>
            <a href="/notifications" class="nav-icon" title="Notifications"><i class="fas fa-bell"></i><span id="notif-badge" class="badge hidden">0</span></a>
            <a href="/chat" class="nav-icon" title="Messages"><i class="fas fa-envelope"></i></a>
            <button class="btn btn-outline btn-sm" onclick="showGoLiveModal()"><i class="fas fa-video"></i> Go Live</button>
            <button class="btn btn-primary btn-sm" onclick="showCreatePost()"><i class="fas fa-plus"></i> Create</button>
            <div class="nav-avatar" id="nav-avatar"></div>`;
        initTheme();
        loadUnreadCount();
        loadNavAvatar();
    } else {
        nav.innerHTML = `<a href="/login" class="btn btn-primary btn-sm">Login</a><a href="/register" class="btn btn-outline btn-sm">Register</a>`;
    }
}

async function loadNavAvatar() {
    try {
        const user = await api('/auth/me');
        currentUser = user;
        const av = document.getElementById('nav-avatar');
        if (av) av.innerHTML = `<a href="/profile/${user.username}"><img src="${getProfilePic(user)}" alt="${user.username}" class="avatar-sm"></a>`;
    } catch (e) {}
}

async function loadUnreadCount() {
    try {
        const data = await api('/notifications/unread-count');
        const badge = document.getElementById('notif-badge');
        if (badge && data.unread_count > 0) { badge.textContent = data.unread_count; badge.classList.remove('hidden'); }
        const sbadge = document.getElementById('sidebar-notif-badge');
        if (sbadge && data.unread_count > 0) { sbadge.textContent = data.unread_count; sbadge.classList.remove('hidden'); }
    } catch (e) {}
}

function getProfilePic(user) {
    if (!user) return '/static/images/default_avatar.svg';
    if (user.profile_picture && !user.profile_picture.includes('default')) return mediaUrl(user.profile_picture);
    return '/static/images/default_avatar.svg';
}

const INDIA_TIME_ZONE = 'Asia/Kolkata';

function parseApiDate(dt) {
    if (!dt) return null;
    if (dt instanceof Date) return dt;
    let value = String(dt).trim();
    // Backend stores naive UTC and now serializes with Z. This fallback keeps
    // older cached/API values stable by treating timezone-less ISO strings as UTC.
    if (/^\d{4}-\d{2}-\d{2}T/.test(value) && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(value)) value += 'Z';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

function formatTime(dt) {
    const d = parseApiDate(dt);
    if (!d) return '';
    const diff = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
    if (diff < 60) return 'Just now';
    if (diff < 3600) {
        const mins = Math.floor(diff / 60);
        return mins === 1 ? '1 min ago' : `${mins} mins ago`;
    }
    if (diff < 86400) {
        const hours = Math.floor(diff / 3600);
        return hours === 1 ? '1 hour ago' : `${hours} hours ago`;
    }
    if (diff < 172800) return 'Yesterday';
    if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`;
    return new Intl.DateTimeFormat('en-IN', {
        timeZone: INDIA_TIME_ZONE,
        day: '2-digit', month: 'short', year: 'numeric'
    }).format(d);
}

function formatIndiaDateTime(dt) {
    const d = parseApiDate(dt);
    if (!d) return '';
    return new Intl.DateTimeFormat('en-IN', {
        timeZone: INDIA_TIME_ZONE,
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit', hour12: true
    }).format(d);
}

function formatChatTime(dt) {
    const d = parseApiDate(dt);
    if (!d) return '';
    const diff = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
    const nowParts = new Intl.DateTimeFormat('en-CA', { timeZone: INDIA_TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
    const msgParts = new Intl.DateTimeFormat('en-CA', { timeZone: INDIA_TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit' }).format(d);
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yParts = new Intl.DateTimeFormat('en-CA', { timeZone: INDIA_TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit' }).format(yesterday);
    if (msgParts === yParts) return 'Yesterday';
    return new Intl.DateTimeFormat('en-IN', { timeZone: INDIA_TIME_ZONE, hour: '2-digit', minute: '2-digit', hour12: true }).format(d).toUpperCase();
}

// ==================== AUTH PAGES ====================
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errEl = document.getElementById('error');
    try {
        const data = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
        if (data.requires_2fa) { showToast('2FA verification required', 'warning'); return; }
        setTokens(data.access_token, data.refresh_token);
        window.location.href = '/';
    } catch (e) { if (errEl) { errEl.textContent = e.message; errEl.classList.remove('hidden'); } }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const fullName = document.getElementById('full_name')?.value || '';
    const errEl = document.getElementById('error');
    try {
        const data = await api('/auth/register', { method: 'POST', body: JSON.stringify({ email, username, password, full_name: fullName }) });
        setTokens(data.access_token, data.refresh_token);
        window.location.href = '/';
    } catch (e) { if (errEl) { errEl.textContent = e.message; errEl.classList.remove('hidden'); } }
}

function logout() { clearTokens(); window.location.href = '/login'; }

// ==================== HOME / FEED ====================
let feedPage = 1;
let feedHasNext = false;
let feedLoading = false;
let feedObserver = null;

async function loadFeed(page = 1, append = false) {
    const feed = document.getElementById('feed-posts') || document.getElementById('feed');
    if (!feed || !isLoggedIn()) { if (feed) feed.innerHTML = '<div class="empty-state insta-empty"><h2>Welcome to SocialHub</h2><p>Login to see your Instagram-style feed</p><a href="/login" class="btn btn-primary">Login</a></div>'; return; }
    if (feedLoading) return;
    feedLoading = true;
    try {
        if (!append) feed.innerHTML = renderPostSkeletons();
        const data = await api(`/posts/premium/feed?page=${page}&page_size=6`);
        const posts = data.posts || [];
        if (!posts.length && !append) { feed.innerHTML = '<div class="empty-state"><i class="fas fa-newspaper fa-3x"></i><h3>No posts yet</h3><p>Follow people or create your first post to start your feed.</p></div>'; return; }
        const html = posts.map((post, index) => renderPost(post, { sponsored: page > 1 && index === 2 })).join('');
        feed.innerHTML = append ? feed.innerHTML.replace(/<div class="feed-loading-more"[\s\S]*?<\/div>$/, '') + html : html;
        feedPage = page;
        feedHasNext = !!data.has_next;
        if (feedHasNext) feed.insertAdjacentHTML('beforeend', '<div class="feed-loading-more"><div class="spinner"></div><span>Scroll for more posts</span></div>');
        initFeedInfiniteScroll();
    } catch (e) {
        if (!append) feed.innerHTML = '<div class="empty-state">Error loading feed. Please try again.</div>';
        showToast(e.message || 'Error loading feed', 'error');
    } finally { feedLoading = false; }
}

function initFeedInfiniteScroll() {
    const sentinel = document.getElementById('feed-sentinel');
    if (!sentinel || feedObserver) return;
    feedObserver = new IntersectionObserver(entries => {
        if (entries.some(e => e.isIntersecting) && feedHasNext && !feedLoading) loadFeed(feedPage + 1, true);
    }, { rootMargin: '500px 0px' });
    feedObserver.observe(sentinel);
}

function renderPostSkeletons() {
    return Array.from({ length: 3 }).map(() => `
        <div class="post-card skeleton-post" aria-label="Loading post">
            <div class="post-header">
                <div class="post-author"><span class="skeleton skeleton-avatar"></span><div><span class="skeleton skeleton-line short"></span><span class="skeleton skeleton-line tiny"></span></div></div>
                <span class="skeleton skeleton-dot"></span>
            </div>
            <div class="post-content"><span class="skeleton skeleton-line"></span><span class="skeleton skeleton-line medium"></span></div>
            <div class="skeleton skeleton-media"></div>
            <div class="post-actions"><span class="skeleton skeleton-pill"></span><span class="skeleton skeleton-pill"></span><span class="skeleton skeleton-pill"></span></div>
        </div>`).join('');
}

function renderPost(post, options = {}) {
    const author = post.author || {};
    const canDelete = currentUser && (post.user_id === currentUser.id || currentUser.role === 'admin');
    const mediaItems = post.images || [];
    const images = mediaItems.map((img, index) =>
        img.is_video ? `<video src="${mediaUrl(img.video_url || img.image_url)}" controls playsinline preload="metadata" class="post-media"></video>` :
        `<img src="${mediaUrl(img.image_url)}" class="post-media" loading="lazy" alt="Post media ${index + 1}">`
    ).join('');
    const mediaClass = mediaItems.length > 1 ? 'post-images carousel-post' : 'post-images';

    let pollHtml = '';
    if (post.poll) {
        const opts = post.poll.options.map(o => {
            const pct = post.poll.total_votes > 0 ? Math.round((o.votes_count / post.poll.total_votes) * 100) : 0;
            return `<div class="poll-option" onclick="votePoll('${post.id}','${o.id}')" style="position:relative"><div class="poll-bar" style="width:${pct}%"></div><span class="poll-text">${o.text} ${pct}% (${o.votes_count})</span></div>`;
        }).join('');
        pollHtml = `<div class="poll">${opts}<div class="poll-total">${post.poll.total_votes} votes</div></div>`;
    }

    let repostHtml = '';
    if (post.repost) repostHtml = `<div class="repost-ref">${renderPost(post.repost)}</div>`;

    return `<div class="post-card insta-post ${options.sponsored ? 'sponsored-post' : ''}" id="post-${post.id}" ondblclick="doubleTapLike('${post.id}', this)">
        ${options.sponsored ? '<div class="sponsored-strip"><i class="fas fa-bullhorn"></i> Sponsored creator recommendation</div>' : ''}
        <div class="post-header">
            <a href="/profile/${author.username}" class="post-author">
                <img src="${getProfilePic(author)}" class="avatar-sm" alt="">
                <div>
                    <span class="username">${author.username || ''}</span>${author.is_verified ? '<i class="fas fa-check-circle verified"></i>' : ''}
                    <div class="post-time">${formatTime(post.created_at)}</div>
                </div>
            </a>
            <div class="content-menu"><button class="post-menu-btn" onclick="toggleContentMenu(this)"><i class="fas fa-ellipsis-h"></i></button>
                <div class="content-menu-dropdown hidden">
                    <button onclick="copyPostLink('${post.id}')"><i class="fas fa-link"></i> Copy link</button>
                    <button onclick="hidePost('${post.id}')"><i class="fas fa-eye-slash"></i> Hide post</button>
                    <button onclick="markPostPreference('${post.id}','interested')"><i class="fas fa-thumbs-up"></i> Interested</button>
                    <button onclick="markPostPreference('${post.id}','not_interested')"><i class="fas fa-thumbs-down"></i> Not interested</button>
                    <button onclick="reportPost('${post.id}')"><i class="fas fa-flag"></i> Report</button>
                    <button onclick="muteUser('${post.user_id}')"><i class="fas fa-volume-xmark"></i> Mute user</button>
                    <button onclick="blockUser('${post.user_id}')"><i class="fas fa-ban"></i> Block user</button>
                    <button onclick="showPostInsights('${post.id}')"><i class="fas fa-chart-line"></i> Insights</button>
                    ${canDelete ? `<button onclick="deleteContent('post','${post.id}')"><i class="fas fa-trash"></i> Delete</button>` : ''}
                </div>
            </div>
        </div>
        ${post.content ? `<div class="post-content"><p>${escapeHtml(post.content)}</p></div>` : ''}
        ${images ? `<div class="${mediaClass}">${images}<div class="double-like-heart"><i class="fas fa-heart"></i></div></div>` : ''}
        ${pollHtml}
        ${repostHtml}
        <div class="post-caption-preview"><strong>${author.username || 'Creator'}</strong> ${post.content ? escapeHtml(post.content).replace(/<br>/g, ' ').substring(0, 90) : 'shared a new moment.'}</div>
        <button class="comments-preview" onclick="showComments('${post.id}')">View ${post.comments_count || 0} comments</button>
        <div class="post-actions">
            <button class="action-btn ${post.is_liked ? 'active' : ''}" onclick="toggleLike('${post.id}', this)" aria-label="Like post">
                <i class="fas fa-heart"></i> <span>${post.likes_count}</span>
            </button>
            <button class="action-btn" onclick="showComments('${post.id}')">
                <i class="fas fa-comment"></i> <span>${post.comments_count}</span>
            </button>
            <button class="action-btn" onclick="sharePost('${post.id}')">
                <i class="fas fa-share"></i> <span>${post.shares_count || 0}</span>
            </button>
            <button class="action-btn" onclick="copyPostLink('${post.id}')" aria-label="Copy link"><i class="fas fa-link"></i></button>
            <button class="action-btn ${post.is_saved ? 'active' : ''}" onclick="toggleBookmark('${post.id}')">
                <i class="fas fa-bookmark"></i>
            </button>
        </div>
    </div>`;
}

function escapeHtml(t) {
    if (t === null || t === undefined) return '';
    return String(t)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;')
        .replace(/\n/g, '<br>');
}

function showToast(message, type = 'info') {
    let wrap = document.getElementById('toast-container');
    if (!wrap) {
        wrap = document.createElement('div');
        wrap.id = 'toast-container';
        wrap.className = 'toast-container';
        document.body.appendChild(wrap);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message || 'Done';
    wrap.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 20);
    setTimeout(() => { toast.classList.remove('show'); setTimeout(() => toast.remove(), 250); }, 3200);
}

function mediaUrl(path) {
    if (!path) return '';
    if (/^https?:\/\//i.test(path)) return path;
    const normalized = String(path).replace(/\\/g, '/');
    const uploadsIndex = normalized.toLowerCase().lastIndexOf('/uploads/');
    let clean = uploadsIndex >= 0 ? normalized.slice(uploadsIndex + '/uploads/'.length) : normalized.replace(/^\/+/, '');
    while (/^uploads\//i.test(clean)) clean = clean.replace(/^uploads\//i, '');
    clean = clean
        .replace(/^post_images\//i, 'posts/')
        .replace(/^videos\//i, 'posts/')
        .replace(/^profile_pics\//i, 'profiles/')
        .replace(/^cover_photos\//i, 'covers/')
        .replace(/^chat_files\//i, 'chat/');
    return `/uploads/${clean}`;
}

async function parseResponseError(res, fallback = 'Request failed') {
    const payload = await res.json().catch(() => ({}));
    if (Array.isArray(payload.detail)) return payload.detail.map(d => d.msg || d.detail || String(d)).join(', ');
    return payload.detail || payload.message || fallback;
}

async function fetchChecked(url, opts = {}, retryOnAuth = true) {
    const res = await fetch(url, opts);
    if (res.status === 401 && refreshToken && retryOnAuth) {
        const refreshed = await refreshAccessToken();
        if (refreshed) return fetchChecked(url, { ...opts, headers: opts.multipart ? getMultipartHeaders() : (opts.headers || getHeaders()) }, false);
        clearTokens();
        window.location.href = '/login';
        throw new Error('Session expired. Please login again.');
    }
    if (!res.ok) throw new Error(await parseResponseError(res, `Request failed (${res.status})`));
    return res.status === 204 ? {} : res.json().catch(() => ({}));
}

function formatBytes(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    return `${(bytes / Math.pow(1024, index)).toFixed(index ? 1 : 0)} ${units[index]}`;
}

function validateUploadFile(file, allowedTypes, maxSize, label) {
    if (!file) return `${label} file is required`;
    const ext = (file.name.split('.').pop() || '').toLowerCase();
    const fallbackTypeOk = label === 'Reel'
        ? ['mp4', 'webm', 'mov'].includes(ext)
        : label === 'Music'
            ? ['mp3', 'wav', 'm4a', 'ogg'].includes(ext)
            : ['jpg', 'jpeg', 'png', 'webp', 'mp4', 'webm', 'mov'].includes(ext);
    if (!allowedTypes.includes(file.type) && !fallbackTypeOk) return `${label} file type is not supported`;
    if (file.size > maxSize) return `${label} is too large. Max size is ${formatBytes(maxSize)}`;
    return '';
}

function renderUploadPreview(inputId, previewId, allowedTypes, maxSize, label) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    if (!input || !preview) return;
    const file = input.files?.[0];
    preview.innerHTML = '';
    if (!file) return;
    const error = validateUploadFile(file, allowedTypes, maxSize, label);
    if (error) {
        preview.innerHTML = `<div class="upload-error"><i class="fas fa-triangle-exclamation"></i> ${escapeHtml(error)}</div>`;
        input.value = '';
        return;
    }
    const url = URL.createObjectURL(file);
    const isVideo = file.type.startsWith('video/') || /\.(mp4|webm|mov)$/i.test(file.name);
    preview.innerHTML = `<div class="upload-preview-card">
        ${isVideo ? `<video src="${url}" controls muted playsinline></video>` : `<img src="${url}" alt="Preview">`}
        <div><strong>${escapeHtml(file.name)}</strong><small>${formatBytes(file.size)}</small></div>
    </div>`;
}

function uploadWithProgress(url, form, onProgress, retryOnAuth = true) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', url);
        Object.entries(getMultipartHeaders()).forEach(([key, value]) => xhr.setRequestHeader(key, value));
        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable && onProgress) onProgress(Math.round((event.loaded / event.total) * 100));
        };
        xhr.onload = () => {
            const payload = (() => { try { return JSON.parse(xhr.responseText || '{}'); } catch { return {}; } })();
            if (xhr.status >= 200 && xhr.status < 300) resolve(payload);
            else if (xhr.status === 401 && refreshToken && retryOnAuth) {
                refreshAccessToken()
                    .then(refreshed => refreshed ? uploadWithProgress(url, form, onProgress, false).then(resolve).catch(reject) : (clearTokens(), window.location.href = '/login'))
                    .catch(reject);
            }
            else reject(new Error(payload.detail || payload.message || `Upload failed (${xhr.status})`));
        };
        xhr.onerror = () => reject(new Error('Network error during upload'));
        xhr.send(form);
    });
}

function setUploadProgress(kind, percent, active = true) {
    const bar = document.getElementById(`${kind}-upload-progress`);
    const fill = document.getElementById(`${kind}-upload-progress-fill`);
    const text = document.getElementById(`${kind}-upload-progress-text`);
    if (!bar || !fill || !text) return;
    bar.classList.toggle('hidden', !active);
    fill.style.width = `${percent}%`;
    text.textContent = active ? `Uploading ${percent}%` : '';
}

function resetUploadPreview(kind) {
    const preview = document.getElementById(`${kind}-preview`);
    if (preview) preview.innerHTML = '';
    setUploadProgress(kind, 0, false);
}

function showSkeleton(target, count = 3) {
    const el = typeof target === 'string' ? document.querySelector(target) : target;
    if (el) el.innerHTML = Array.from({ length: count }).map(() => '<div class="skeleton skeleton-media"></div>').join('');
}

function openModal(id) { const el = document.getElementById(id); if (el) el.classList.add('active'); }
function closeModal(id) { const el = document.getElementById(id); if (el) el.classList.remove('active'); }

function getThemePreference() {
    const legacy = localStorage.getItem('theme');
    const saved = localStorage.getItem('socialhub-theme') || legacy || 'system';
    return ['light', 'dark', 'system'].includes(saved) ? saved : 'system';
}
function resolveTheme(pref = getThemePreference()) {
    if (pref === 'system') return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    return pref;
}
function initTheme() {
    const pref = getThemePreference();
    const resolved = resolveTheme(pref);
    localStorage.setItem('socialhub-theme', pref);
    localStorage.removeItem('theme');
    document.documentElement.dataset.theme = resolved;
    document.documentElement.dataset.themePreference = pref;
    document.documentElement.style.colorScheme = resolved;
    document.querySelectorAll('.theme-toggle').forEach(btn => {
        btn.dataset.theme = resolved;
        btn.setAttribute('aria-label', `Theme: ${pref}. Activate to cycle light, dark, and system.`);
        btn.setAttribute('title', `Theme: ${pref}`);
    });
    document.querySelectorAll('.theme-toggle i').forEach(i => i.className = resolved === 'dark' ? 'fas fa-sun' : 'fas fa-moon');
}
function toggleTheme() {
    const order = ['light', 'dark', 'system'];
    const pref = getThemePreference();
    const next = order[(order.indexOf(pref) + 1) % order.length];
    localStorage.setItem('socialhub-theme', next);
    initTheme();
    showToast(`${next[0].toUpperCase() + next.slice(1)} theme enabled`);
}
if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', () => {
        if (getThemePreference() === 'system') initTheme();
    });
}

function requireLoginForUpload() {
    if (isLoggedIn()) return true;
    showToast('Please login first to upload media', 'warning');
    setTimeout(() => { window.location.href = '/login'; }, 900);
    return false;
}

function showCreateStory() {
    if (!requireLoginForUpload()) return;
    openModal('create-story-modal');
}

function showCreateReel() {
    if (!requireLoginForUpload()) return;
    resetUploadPreview('reel');
    selectedMusic = null;
    const selectedId = document.getElementById('selected-music-id');
    const selectedLabel = document.getElementById('selected-music-label');
    if (selectedId) selectedId.value = '';
    if (selectedLabel) selectedLabel.textContent = 'No music selected';
    openModal('create-reel-modal');
}
function setActiveNav(slug) {
    const path = slug || window.location.pathname.replace(/^\//, '') || 'home';
    document.querySelectorAll('.menu-list a').forEach(a => {
        const href = a.getAttribute('href') || '';
        a.classList.toggle('active', href === window.location.pathname || href.includes(path));
    });
}
function renderSocialHubMenu(active = '') {
    const menus = document.querySelectorAll('.socialhub-auto-menu');
    if (!menus.length) return;
    const items = [
        ['/', 'fa-home', 'Home', 'home'], ['/reels', 'fa-video', 'Reels', 'reels'], ['/stories', 'fa-clock', 'Stories', 'stories'],
        ['/search', 'fa-compass', 'Explore', 'search'], ['/notifications', 'fa-bell', 'Notifications', 'notifications'], ['/chat', 'fa-envelope', 'Messages', 'chat'],
        [currentUser ? `/profile/${currentUser.username}` : '/settings', 'fa-user', 'Profile', 'profile'], ['/creator-dashboard', 'fa-chart-line', 'Analytics', 'creator-dashboard'],
        ['/data-studio', 'fa-database', 'Data Studio', 'data-studio'], ['/ai-creator-studio', 'fa-wand-magic-sparkles', 'AI Studio', 'ai-creator-studio'], ['/music-library', 'fa-music', 'Music', 'music-library'], ['/live', 'fa-tower-broadcast', 'Live', 'live'], ['/marketplace', 'fa-store', 'Marketplace', 'marketplace'],
        ['/collabs', 'fa-handshake', 'Collabs', 'collabs'], ['/settings', 'fa-cog', 'Settings', 'settings'], ['/admin', 'fa-shield', 'Admin', 'admin']
    ];
    menus.forEach(menu => { menu.innerHTML = items.map(([href, icon, label, key]) => `<a href="${href}" class="${active === key ? 'active' : ''}"><i class="fas ${icon}"></i> ${label}</a>`).join(''); });
    setActiveNav(active);
}
async function hydrateMiniUser() {
    if (!isLoggedIn()) return;
    try {
        const user = currentUser || await api('/auth/me');
        document.querySelectorAll('.socialhub-user-mini').forEach(card => {
            card.querySelector('img').src = getProfilePic(user);
            card.querySelector('.name').textContent = user.full_name || user.username;
            card.querySelector('.handle').textContent = '@' + user.username;
        });
        document.querySelectorAll('a[href="/profile/testuser"]').forEach(a => a.href = `/profile/${user.username}`);
    } catch (e) {}
}

// ==================== POST ACTIONS ====================
async function toggleLike(postId, button = null) {
    try {
        await api(`/likes/${postId}`, { method: 'POST', body: JSON.stringify({ reaction: 'like' }) });
        if (button) button.classList.add('active', 'pulse-like');
        setTimeout(() => button?.classList.remove('pulse-like'), 500);
    } catch (e) {
        try { await api(`/likes/${postId}`, { method: 'DELETE' }); if (button) button.classList.remove('active'); } catch (e2) {}
    }
}

async function doubleTapLike(postId, card) {
    const heart = card?.querySelector('.double-like-heart');
    heart?.classList.remove('animate');
    void heart?.offsetWidth;
    heart?.classList.add('animate');
    await toggleLike(postId, card?.querySelector('.action-btn'));
}

async function toggleBookmark(postId) {
    try { await api(`/posts/${postId}/bookmark`, { method: 'POST' }); showToast('Saved updated', 'success'); } catch (e) { showToast(e.message || 'Could not save post', 'error'); }
}

async function sharePost(postId) {
    try { await api(`/posts/${postId}/share`, { method: 'POST', body: JSON.stringify({ channel: 'socialhub' }) }); await copyPostLink(postId, false); showToast('Share link ready!', 'success'); } catch (e) { showToast(e.message || 'Error sharing post', 'error'); }
}

async function copyPostLink(postId, notify = true) {
    const url = `${location.origin}/posts?post=${encodeURIComponent(postId)}`;
    try { await navigator.clipboard.writeText(url); if (notify) showToast('Post link copied', 'success'); }
    catch { prompt('Copy post link', url); }
}

async function hidePost(postId) { document.getElementById(`post-${postId}`)?.remove(); await api(`/posts/${postId}/hide`, { method: 'POST' }).catch(()=>{}); showToast('Post hidden', 'success'); }
async function markPostPreference(postId, preference) { await api(`/posts/${postId}/preference`, { method: 'POST', body: JSON.stringify({ preference }) }).catch(()=>{}); showToast(preference === 'interested' ? 'We will show more like this' : 'We will show fewer like this', 'success'); }
async function reportPost(postId) { const reason = prompt('Why are you reporting this post?', 'spam'); if (!reason) return; try { await api(`/posts/${postId}/report`, { method: 'POST', body: JSON.stringify({ reason }) }); showToast('Report submitted', 'success'); } catch(e) { showToast(e.message || 'Report failed', 'error'); } }
async function muteUser(userId) { await api(`/users/${userId}/mute`, { method: 'POST' }).catch(()=>{}); showToast('User muted for this session', 'success'); }
async function blockUser(userId) { if (!confirm('Block this user?')) return; await api(`/users/${userId}/block`, { method: 'POST' }).catch(()=>{}); showToast('User blocked for this session', 'success'); }
async function showPostInsights(postId) { try { const d = await api(`/posts/${postId}/insights`); showToast(`Insights: ${d.likes_count||0} likes, ${d.comments_count||0} comments, ${d.shares_count||0} shares`, 'info'); } catch(e) { showToast('Insights unavailable', 'warning'); } }

async function votePoll(postId, optionId) {
    try { await api(`/posts/${postId}/vote`, { method: 'POST', body: JSON.stringify({ option_id: optionId }) }); loadFeed(); } catch (e) { showToast(e.message, 'error'); }
}

// ==================== CREATE POST ====================
function showCreatePost() {
    const modal = document.getElementById('create-post-modal');
    if (modal) modal.classList.add('active');
    else window.location.href = '/';
}

async function handleCreatePost(e) {
    e.preventDefault();
    if (!requireLoginForUpload()) return;
    const content = document.getElementById('post-content')?.value || '';
    const form = new FormData();
    if (content) form.append('content', content);
    const fileInput = document.getElementById('post-files');
    if (fileInput) {
        for (const f of fileInput.files) {
            const err = validateUploadFile(f, STORY_TYPES, MAX_STORY_SIZE, 'Post media');
            if (err) return showToast(err, 'warning');
            form.append('files', f);
        }
    }
    if (!content.trim() && (!fileInput || fileInput.files.length === 0)) return showToast('Write something or choose media first', 'warning');
    try {
        const submit = e.target.querySelector('button[type="submit"]');
        if (submit) submit.disabled = true;
        setUploadProgress('post', 0, true);
        await uploadWithProgress(`${API}/posts`, form, (p) => setUploadProgress('post', p, true));
        e.target.reset();
        resetUploadPreview('post');
        const modal = document.getElementById('create-post-modal');
        if (modal) modal.classList.remove('active');
        showToast('Post created successfully', 'success');
        if (typeof loadFeed === 'function') loadFeed();
    } catch (e) { showToast(e.message || 'Error creating post', 'error'); }
    finally {
        const submit = e.target.querySelector('button[type="submit"]');
        if (submit) submit.disabled = false;
        setUploadProgress('post', 0, false);
    }
}

async function handleCreateStory(e) {
    e.preventDefault();
    if (!requireLoginForUpload()) return;
    const caption = document.getElementById('story-caption')?.value || '';
    const file = document.getElementById('story-file')?.files?.[0];
    if (!file) return showToast('Choose an image or video for your story', 'warning');
    const validationError = validateUploadFile(file, STORY_TYPES, MAX_STORY_SIZE, 'Story');
    if (validationError) return showToast(validationError, 'warning');

    const form = new FormData();
    form.append('file', file);
    if (caption) form.append('caption', caption);

    try {
        const submit = e.target.querySelector('button[type="submit"]');
        if (submit) submit.disabled = true;
        setUploadProgress('story', 0, true);
        await uploadWithProgress(`${API}/stories`, form, (p) => setUploadProgress('story', p, true));
        e.target.reset();
        resetUploadPreview('story');
        closeModal('create-story-modal');
        showToast('Story uploaded successfully', 'success');
        if (typeof loadStories === 'function') loadStories();
    } catch (err) {
        showToast(err.message || 'Error uploading story', 'error');
    } finally {
        const submit = e.target.querySelector('button[type="submit"]');
        if (submit) submit.disabled = false;
        setUploadProgress('story', 0, false);
    }
}

async function handleCreateReel(e) {
    e.preventDefault();
    if (!requireLoginForUpload()) return;
    const caption = document.getElementById('reel-caption')?.value || '';
    const title = document.getElementById('reel-title')?.value || '';
    const hashtags = document.getElementById('reel-hashtags')?.value || '';
    const thumbnail = document.getElementById('reel-thumbnail')?.files?.[0];
    const file = document.getElementById('reel-file')?.files?.[0];
    if (!file) return showToast('Choose a video file for your reel', 'warning');
    const validationError = validateUploadFile(file, REEL_TYPES, MAX_REEL_SIZE, 'Reel');
    if (validationError) return showToast(validationError, 'warning');
    if (thumbnail) {
        const coverError = validateUploadFile(thumbnail, COVER_TYPES, 10 * 1024 * 1024, 'Cover');
        if (coverError) return showToast(coverError, 'warning');
    }

    const form = new FormData();
    form.append('file', file);
    form.append('caption', caption.trim());
    if (title.trim()) form.append('title', title.trim());
    const musicId = document.getElementById('selected-music-id')?.value || '';
    if (musicId) form.append('music_id', musicId);
    if (selectedMusic) form.append('music_name', `${selectedMusic.title}${selectedMusic.artist ? ' - ' + selectedMusic.artist : ''}`);
    else if (title.trim()) form.append('music_name', title.trim());
    form.append('hashtags', hashtags.trim());
    form.append('visibility', document.getElementById('reel-visibility')?.value || 'public');
    ['location','text-overlay','filter-name','trim-start','trim-end'].forEach(id => { const value = document.getElementById(`reel-${id}`)?.value; if (value) form.append(id.replace(/-/g, '_'), value); });
    if (thumbnail) form.append('cover', thumbnail);

    try {
        const submit = e.target.querySelector('button[type="submit"]');
        if (submit) {
            submit.disabled = true;
            submit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
        }
        setUploadProgress('reel', 0, true);
        await uploadWithProgress(`${API}/reels/upload`, form, (p) => setUploadProgress('reel', p, true));
        e.target.reset();
        resetUploadPreview('reel');
        closeModal('create-reel-modal');
        showToast('Reel uploaded successfully', 'success');
        if (typeof loadReels === 'function') loadReels();
    } catch (err) {
        showToast(err.message || 'Error uploading reel', 'error');
    } finally {
        const submit = e.target.querySelector('button[type="submit"]');
        if (submit) {
            submit.disabled = false;
            submit.innerHTML = '<i class="fas fa-cloud-upload-alt"></i> Upload Reel';
        }
        setUploadProgress('reel', 0, false);
    }
}

// ==================== COMMENTS ====================
async function showComments(postId) {
    const modal = document.getElementById('comments-modal');
    const content = document.getElementById('comments-content');
    if (!modal || !content) return;
    modal.classList.add('active');
    content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    try {
        const comments = await api(`/comments/${postId}`);
        let html = `<div class="comment-form"><input id="comment-input" placeholder="Write a comment..." onkeypress="if(event.key==='Enter')addComment('${postId}')"><button onclick="addComment('${postId}')" class="btn btn-primary btn-sm">Post</button></div>`;
        comments.forEach(c => { html += renderComment(c, postId); });
        content.innerHTML = html;
    } catch (e) { content.innerHTML = '<p>Error loading comments</p>'; }
}

function renderComment(c, postId) {
    const a = c.author || {};
    let replies = '';
    if (c.replies && c.replies.length > 0) {
        replies = '<div class="replies">' + c.replies.map(r => renderComment(r, postId)).join('') + '</div>';
    }
    return `<div class="comment">
        <img src="${getProfilePic(a)}" class="avatar-xs" alt="">
        <div class="comment-body">
            <span class="username">${a.username || ''}</span>
            <span class="comment-text">${escapeHtml(c.content)}</span>
            <div class="comment-meta">
                <span>${formatTime(c.created_at)}</span>
                <button onclick="showReplyInput('${c.id}','${postId}')">Reply</button>
            </div>
            <div id="reply-form-${c.id}"></div>
        </div>
    </div>${replies}`;
}

async function addComment(postId) {
    const input = document.getElementById('comment-input');
    if (!input || !input.value.trim()) return;
    try { await api(`/comments/${postId}`, { method: 'POST', body: JSON.stringify({ content: input.value.trim() }) }); input.value = ''; showComments(postId); } catch (e) { showToast(e.message || 'Error posting comment', 'error'); }
}

function showReplyInput(commentId, postId) {
    const el = document.getElementById(`reply-form-${commentId}`);
    if (el) el.innerHTML = `<input id="reply-${commentId}" placeholder="Write a reply..." onkeypress="if(event.key==='Enter')addReply('${postId}','${commentId}')">`;
}

async function addReply(postId, parentId) {
    const input = document.getElementById(`reply-${parentId}`);
    if (!input || !input.value.trim()) return;
    try { await api(`/comments/${postId}`, { method: 'POST', body: JSON.stringify({ content: input.value.trim(), parent_id: parentId }) }); showComments(postId); } catch (e) { showToast(e.message || 'Error posting reply', 'error'); }
}

// ==================== INSTAGRAM-LIKE PROFILE (Complete Overhaul) ====================

/**
 * Render the profile skeleton/loading UI
 */
function renderProfileSkeleton() {
    return `<div class="profile-skeleton">
        <div class="profile-skeleton-cover"></div>
        <div class="profile-skeleton-body">
            <div class="profile-skeleton-avatar"></div>
            <div class="profile-skeleton-line short" style="margin-top:16px;"></div>
            <div class="profile-skeleton-line medium"></div>
            <div class="profile-skeleton-line long"></div>
            <div class="profile-skeleton-stats">
                <div class="profile-skeleton-stat"></div>
                <div class="profile-skeleton-stat"></div>
                <div class="profile-skeleton-stat"></div>
                <div class="profile-skeleton-stat"></div>
            </div>
        </div>
        <div class="profile-skeleton-tabs">
            <div class="profile-skeleton-tab"></div>
            <div class="profile-skeleton-tab"></div>
            <div class="profile-skeleton-tab"></div>
            <div class="profile-skeleton-tab"></div>
        </div>
    </div>`;
}

/**
 * Render an Instagram-like profile image editor card (only for own profile)
 */
function renderProfileImageEditor(profile) {
    return `<div class="profile-edit-card">
        <div class="profile-edit-preview">
            <img id="profile-image-preview" src="${getProfilePic(profile)}" class="avatar-xl" alt="Profile preview">
            <div><h3>Profile photo</h3><p>Upload JPG, PNG, or WEBP. This updates navbar, posts, reels, comments, chat, and lists.</p></div>
        </div>
        <input id="profile-image-input" type="file" accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp" class="hidden" onchange="loadProfileImage()">
        <div class="profile-edit-actions">
            <button class="btn btn-outline" type="button" onclick="document.getElementById('profile-image-input').click()"><i class="fas fa-camera"></i> Upload/change photo</button>
            <button class="btn btn-primary" type="button" onclick="uploadProfileImage()"><i class="fas fa-save"></i> Save</button>
            <button class="btn btn-danger" type="button" onclick="removeProfileImage()"><i class="fas fa-trash"></i> Remove photo</button>
        </div>
    </div>`;
}

function loadProfileImage() {
    const input = document.getElementById('profile-image-input');
    const preview = document.getElementById('profile-image-preview');
    const file = input?.files?.[0];
    if (!file || !preview) return;
    const error = validateUploadFile(file, COVER_TYPES, 10 * 1024 * 1024, 'Profile image');
    if (error) { input.value = ''; return showToast(error, 'warning'); }
    preview.src = URL.createObjectURL(file);
}

async function uploadProfileImage() {
    const input = document.getElementById('profile-image-input');
    const file = input?.files?.[0];
    if (!file) return showToast('Choose a profile image first', 'warning');
    const error = validateUploadFile(file, COVER_TYPES, 10 * 1024 * 1024, 'Profile image');
    if (error) return showToast(error, 'warning');
    try {
        const form = new FormData();
        form.append('file', file);
        await fetchChecked(`${API}/users/me/profile-image`, { method: 'POST', headers: getMultipartHeaders(), body: form, multipart: true });
        showToast('Profile image updated', 'success');
        await loadNavAvatar();
        if (activeProfile?.username) loadProfile();
    } catch (e) { showToast(e.message || 'Could not upload profile image', 'error'); }
}

async function removeProfileImage() {
    if (!(await confirmDelete('Remove your profile photo?'))) return;
    try {
        await api('/users/me/profile-image', { method: 'DELETE' });
        showToast('Profile image removed', 'success');
        await loadNavAvatar();
        if (activeProfile?.username) loadProfile();
    } catch (e) { showToast(e.message || 'Could not remove profile image', 'error'); }
}

/**
 * Format joined date in a friendly way
 */
function formatJoinedDate(dt) {
    const d = parseApiDate(dt);
    if (!d) return '';
    const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
    return `${months[d.getMonth()]} ${d.getFullYear()}`;
}

/**
 * Render the profile header (Instagram-like)
 */
function renderProfileHeader(profile, isOwn, followStatus) {
    const coverSrc = profile.cover_photo && !profile.cover_photo.startsWith('default') ? mediaUrl(profile.cover_photo) : null;
    const avatarSrc = getProfilePic(profile);
    const joinedDate = formatJoinedDate(profile.created_at);

    // Build action buttons
    let actionsHtml = '';
    if (isOwn) {
        actionsHtml = `<button class="profile-action-btn outline" onclick="window.location.href='/settings'"><i class="fas fa-cog"></i> Edit Profile</button>`;
    } else if (isLoggedIn()) {
        const isFollowing = followStatus && followStatus.is_following;
        const isPending = followStatus && followStatus.is_pending;
        if (isPending) {
            actionsHtml = `<button class="profile-action-btn outline" disabled><i class="fas fa-clock"></i> Requested</button>`;
        } else {
            actionsHtml = `<button class="profile-action-btn ${isFollowing ? 'outline following' : 'primary'}" id="profile-follow-btn" onclick="handleProfileFollow('${profile.id}')">${isFollowing ? '<i class="fas fa-check"></i> Following' : '<i class="fas fa-plus"></i> Follow'}</button>`;
        }
        actionsHtml += `<button class="profile-action-btn icon-btn" onclick="handleProfileMessage('${profile.id}')" title="Message"><i class="fas fa-envelope"></i></button>`;
    } else {
        actionsHtml = `<button class="profile-action-btn primary" onclick="window.location.href='/login?next=/profile/${profile.username}'"><i class="fas fa-plus"></i> Follow</button>`;
    }

    // Badge HTML
    let badgeHtml = '';
    if (profile.is_verified) badgeHtml += `<i class="fas fa-check-circle verified-badge"></i>`;
    if (profile.badge) badgeHtml += `<span class="badge-tag">${escapeHtml(profile.badge)}</span>`;
    if (profile.account_type && profile.account_type !== 'public') badgeHtml += `<span class="badge-tag" style="background:rgba(255,255,255,0.1);color:var(--text-secondary);font-size:10px;">${escapeHtml(profile.account_type)}</span>`;

    // Details row
    let detailsHtml = '';
    if (profile.website) detailsHtml += `<span><i class="fas fa-link"></i> <a href="${escapeHtml(profile.website)}" target="_blank" rel="noopener">${escapeHtml(profile.website.replace(/^https?:\/\//, ''))}</a></span>`;
    if (profile.location) detailsHtml += `<span><i class="fas fa-map-marker-alt"></i> ${escapeHtml(profile.location)}</span>`;
    if (profile.account_type && profile.account_type !== 'public') detailsHtml += `<span><i class="fas fa-lock"></i> ${escapeHtml(profile.account_type)}</span>`;

    return `<div class="profile-header-card">
        <div class="profile-cover-wrap">
            ${coverSrc ? `<img src="${coverSrc}" alt="Cover photo" onerror="this.parentElement.style.background='linear-gradient(135deg, #1d1a2b, #101018)'">` : ''}
            <div class="profile-cover-gradient"></div>
        </div>
        <div class="profile-avatar-section">
            <div class="profile-avatar-wrap">
                <img src="${avatarSrc}" class="profile-avatar" alt="${escapeHtml(profile.username)}" onerror="this.src='/static/images/default_avatar.svg'">
                ${profile.is_verified ? '<div class="profile-avatar-badge"><i class="fas fa-check"></i></div>' : ''}
            </div>
            <div class="profile-meta-section">
                <div class="profile-name-row">
                    <h1>${escapeHtml(profile.full_name || profile.username)}</h1>
                    ${badgeHtml}
                </div>
                <div class="profile-username-display">@${escapeHtml(profile.username)}</div>
                ${profile.bio ? `<div class="profile-bio-text">${escapeHtml(profile.bio).replace(/\n/g, '<br>')}</div>` : ''}
                ${detailsHtml ? `<div class="profile-details-row">${detailsHtml}</div>` : ''}
                ${joinedDate ? `<div class="profile-joined-date"><i class="fas fa-calendar-alt"></i> Joined ${joinedDate}</div>` : ''}
            </div>
        </div>
        <div class="profile-stats-bar">
            <div class="profile-stat-item"><span class="stat-number" id="profile-posts-count">${profile.posts_count || 0}</span><span class="stat-label">Posts</span></div>
            <div class="profile-stat-item"><span class="stat-number" id="profile-reels-count">${profile.reels_count || 0}</span><span class="stat-label">Reels</span></div>
            <div class="profile-stat-item"><span class="stat-number" id="profile-followers-count">${profile.followers_count || 0}</span><span class="stat-label">Followers</span></div>
            <div class="profile-stat-item"><span class="stat-number" id="profile-following-count">${profile.following_count || 0}</span><span class="stat-label">Following</span></div>
        </div>
        <div class="profile-actions-row">${actionsHtml}</div>
    </div>`;
}

/**
 * Build the profile tabs HTML
 */
function renderProfileTabs(profile, isOwn) {
    let tabs = `
        <button class="profile-tab-btn active" data-tab="posts" onclick="switchProfileTab('posts')"><i class="fas fa-th"></i> <span>Posts</span></button>
        <button class="profile-tab-btn" data-tab="reels" onclick="switchProfileTab('reels')"><i class="fas fa-video"></i> <span>Reels</span></button>`;
    if (isOwn) {
        tabs += `<button class="profile-tab-btn" data-tab="saved" onclick="switchProfileTab('saved')"><i class="fas fa-bookmark"></i> <span>Saved</span></button>
        <button class="profile-tab-btn" data-tab="tagged" onclick="switchProfileTab('tagged')"><i class="fas fa-user-tag"></i> <span>Tagged</span></button>`;
    }
    tabs += `<button class="profile-tab-btn" data-tab="about" onclick="switchProfileTab('about')"><i class="fas fa-info-circle"></i> <span>About</span></button>`;
    return `<div class="profile-tabs-container">${tabs}</div>`;
}

/**
 * Main profile loader - Instagram-like
 */
async function loadProfile() {
    const path = window.location.pathname;
    const username = path.split('/profile/')[1];
    if (!username) return;
    const container = document.getElementById('profile-content');
    if (!container) return;
    
    // Ensure container shows skeleton
    container.innerHTML = renderProfileSkeleton();
    
    try {
        if (!currentUser && isLoggedIn()) {
            try { currentUser = await api('/auth/me'); } catch (e) {}
        }
        const profile = await api(`/users/profile/${username}`);
        activeProfile = profile;
        document.title = `${profile.full_name || profile.username} - SocialHub`;
        const isOwn = currentUser && currentUser.id === profile.id;

        // Get follow status
        let followStatus = null;
        if (!isOwn && isLoggedIn()) {
            try { followStatus = await api(`/follow/check/${profile.id}`); } catch (e) {}
        }

        // Render header and tabs
        container.innerHTML = renderProfileHeader(profile, isOwn, followStatus);
        if (isOwn) container.innerHTML += renderProfileImageEditor(profile);

        // Render tabs below profile
        const tabContent = document.getElementById('profile-tab-content');
        if (tabContent) {
            tabContent.innerHTML = renderProfileTabs(profile, isOwn);
        }

        // Load posts by default
        loadProfilePosts(profile.id);
    } catch (e) {
        container.innerHTML = '<div class="profile-empty-state"><i class="fas fa-user-slash"></i><h3>User not found</h3><p>The profile you are looking for does not exist.</p></div>';
        const tabContent = document.getElementById('profile-tab-content');
        if (tabContent) tabContent.innerHTML = '';
    }
}

/**
 * Switch between profile tabs
 */
function switchProfileTab(tab) {
    document.querySelectorAll('.profile-tab-btn').forEach(t => t.classList.remove('active'));
    const btn = document.querySelector(`.profile-tab-btn[data-tab="${tab}"]`);
    if (btn) btn.classList.add('active');
    
    const userId = activeProfile?.id || currentUser?.id;
    const tabContent = document.getElementById('profile-tab-content');
    if (!tabContent) return;

    // Clear any existing content after tabs
    const existingContent = tabContent.nextElementSibling;
    if (existingContent && existingContent.id !== 'profile-tab-content') {
        existingContent.remove();
    }

    if (tab === 'posts') loadProfilePosts(userId);
    else if (tab === 'reels') loadProfileReels(userId);
    else if (tab === 'saved') loadProfileSaved();
    else if (tab === 'tagged') loadProfileTagged();
    else if (tab === 'about') loadProfileAbout();
}

/**
 * Load profile posts - 3-column Instagram grid
 */
async function loadProfilePosts(userId) {
    const tabContent = document.getElementById('profile-tab-content');
    if (!tabContent) return;
    // Ensure next element is the content area
    removeProfileContentAfter(tabContent);
    
    const contentDiv = document.createElement('div');
    contentDiv.id = 'profile-posts-content';
    tabContent.after(contentDiv);
    
    contentDiv.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    try {
        const data = await api(`/posts/user/${userId}`);
        const posts = data.posts || data || [];
        if (posts.length > 0) {
            let html = '<div class="profile-posts-grid">';
            posts.forEach(p => {
                const firstImage = (p.images && p.images.length > 0) ? p.images[0] : null;
                const imgUrl = firstImage ? mediaUrl(firstImage.image_url) : null;
                const isVideo = firstImage && firstImage.is_video;
                const mediaHtml = imgUrl ? (isVideo ? `<video src="${mediaUrl(firstImage.video_url || firstImage.image_url)}" muted preload="metadata"></video>` : `<img src="${imgUrl}" alt="" loading="lazy">`) : '<div style="background:var(--bg);height:100%;display:flex;align-items:center;justify-content:center;color:var(--text-secondary)"><i class="fas fa-file-image" style="font-size:32px"></i></div>';
                html += `<div class="profile-post-grid-item" onclick="showComments('${p.id}')">
                    ${mediaHtml}
                    <div class="profile-post-grid-overlay">
                        <span><i class="fas fa-heart"></i> ${p.likes_count || 0}</span>
                        <span><i class="fas fa-comment"></i> ${p.comments_count || 0}</span>
                    </div>
                </div>`;
            });
            html += '</div>';
            contentDiv.innerHTML = html;
        } else {
            contentDiv.innerHTML = '<div class="profile-empty-state"><i class="fas fa-camera"></i><h3>No posts yet</h3><p>When this user shares a post, it will appear here.</p></div>';
        }
    } catch (e) {
        contentDiv.innerHTML = '<div class="profile-empty-state"><i class="fas fa-exclamation-circle"></i><h3>Error loading posts</h3></div>';
    }
}

/**
 * Load profile reels - 3-column grid
 */
async function loadProfileReels(userId) {
    const tabContent = document.getElementById('profile-tab-content');
    if (!tabContent) return;
    removeProfileContentAfter(tabContent);
    
    const contentDiv = document.createElement('div');
    contentDiv.id = 'profile-posts-content';
    tabContent.after(contentDiv);
    
    contentDiv.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    try {
        const data = await api(`/reels/user/${userId}`);
        const reels = data.reels || data || [];
        if (reels.length > 0) {
            let html = '<div class="profile-reels-grid">';
            reels.forEach(r => {
                const cover = r.cover_image || r.thumbnail_url;
                const mediaHtml = cover ? `<img src="${mediaUrl(cover)}" alt="" loading="lazy">` : `<video src="${mediaUrl(r.video_url)}" muted preload="metadata"></video>`;
                html += `<div class="profile-reel-grid-item" onclick="window.location.href='/reels#reel-${r.id}'">
                    ${mediaHtml}
                    <div class="profile-reel-grid-play"><i class="fas fa-play"></i></div>
                    <div class="profile-reel-grid-stats"><span><i class="fas fa-play"></i> ${r.views_count || 0}</span><span><i class="fas fa-heart"></i> ${r.likes_count || 0}</span></div>
                </div>`;
            });
            html += '</div>';
            contentDiv.innerHTML = html;
        } else {
            contentDiv.innerHTML = '<div class="profile-empty-state"><i class="fas fa-video"></i><h3>No reels yet</h3><p>When this user uploads a reel, it will appear here.</p></div>';
        }
    } catch (e) {
        contentDiv.innerHTML = '<div class="profile-empty-state"><i class="fas fa-exclamation-circle"></i><h3>Error loading reels</h3></div>';
    }
}

/**
 * Load saved posts (own profile only)
 */
async function loadProfileSaved() {
    const tabContent = document.getElementById('profile-tab-content');
    if (!tabContent) return;
    removeProfileContentAfter(tabContent);
    
    const contentDiv = document.createElement('div');
    contentDiv.id = 'profile-posts-content';
    tabContent.after(contentDiv);
    
    contentDiv.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    try {
        const data = await api('/posts/bookmarks');
        if (data.posts && data.posts.length > 0) {
            const posts = data.posts;
            let html = '<div class="profile-posts-grid">';
            posts.forEach(p => {
                const firstImage = (p.images && p.images.length > 0) ? p.images[0] : null;
                const imgUrl = firstImage ? mediaUrl(firstImage.image_url) : null;
                const mediaHtml = imgUrl ? `<img src="${imgUrl}" alt="" loading="lazy">` : '<div style="background:var(--bg);height:100%;display:flex;align-items:center;justify-content:center;color:var(--text-secondary)"><i class="fas fa-file-image" style="font-size:32px"></i></div>';
                html += `<div class="profile-post-grid-item" onclick="showComments('${p.id}')">
                    ${mediaHtml}
                    <div class="profile-post-grid-overlay">
                        <span><i class="fas fa-heart"></i> ${p.likes_count || 0}</span>
                        <span><i class="fas fa-comment"></i> ${p.comments_count || 0}</span>
                    </div>
                </div>`;
            });
            html += '</div>';
            contentDiv.innerHTML = html;
        } else {
            contentDiv.innerHTML = '<div class="profile-empty-state"><i class="fas fa-bookmark"></i><h3>No saved posts</h3><p>Posts you save will appear here.</p></div>';
        }
    } catch (e) {
        contentDiv.innerHTML = '<div class="profile-empty-state"><i class="fas fa-exclamation-circle"></i><h3>Error loading saved posts</h3></div>';
    }
}

/**
 * Tagged tab (placeholder)
 */
function loadProfileTagged() {
    const tabContent = document.getElementById('profile-tab-content');
    if (!tabContent) return;
    removeProfileContentAfter(tabContent);
    
    const contentDiv = document.createElement('div');
    contentDiv.id = 'profile-posts-content';
    tabContent.after(contentDiv);
    contentDiv.innerHTML = '<div class="profile-empty-state"><i class="fas fa-user-tag"></i><h3>No tagged posts</h3><p>Posts where this user is tagged will appear here.</p></div>';
}

/**
 * About tab - shows full profile info
 */
function loadProfileAbout() {
    const tabContent = document.getElementById('profile-tab-content');
    if (!tabContent) return;
    removeProfileContentAfter(tabContent);
    
    const profile = activeProfile;
    if (!profile) return;

    const contentDiv = document.createElement('div');
    contentDiv.id = 'profile-posts-content';
    tabContent.after(contentDiv);

    const isOwn = currentUser && currentUser.id === profile.id;
    const joinedDate = formatJoinedDate(profile.created_at);

    let itemsHtml = '';
    if (profile.bio) itemsHtml += `<div class="profile-about-item"><i class="fas fa-quote-left"></i><div><div class="about-label">Bio</div><div class="about-value">${escapeHtml(profile.bio).replace(/\n/g, '<br>')}</div></div></div>`;
    if (profile.website) itemsHtml += `<div class="profile-about-item"><i class="fas fa-link"></i><div><div class="about-label">Website</div><div class="about-value"><a href="${escapeHtml(profile.website)}" target="_blank" rel="noopener">${escapeHtml(profile.website)}</a></div></div></div>`;
    if (profile.location) itemsHtml += `<div class="profile-about-item"><i class="fas fa-map-marker-alt"></i><div><div class="about-label">Location</div><div class="about-value">${escapeHtml(profile.location)}</div></div></div>`;
    itemsHtml += `<div class="profile-about-item"><i class="fas fa-user-tag"></i><div><div class="about-label">Account Type</div><div class="about-value" style="text-transform:capitalize">${escapeHtml(profile.account_type || 'Public')}</div></div></div>`;
    if (joinedDate) itemsHtml += `<div class="profile-about-item"><i class="fas fa-calendar-alt"></i><div><div class="about-label">Joined</div><div class="about-value">${joinedDate}</div></div></div>`;
    if (isOwn && profile.email) itemsHtml += `<div class="profile-about-item"><i class="fas fa-envelope"></i><div><div class="about-label">Email</div><div class="about-value">${escapeHtml(profile.email)}</div></div></div>`;

    // Social links
    let socialsHtml = '';
    if (profile.social_links && profile.social_links.length > 0) {
        socialsHtml = '<div class="profile-about-socials">';
        profile.social_links.forEach(link => {
            const iconMap = { 'twitter': 'fa-twitter', 'instagram': 'fa-instagram', 'youtube': 'fa-youtube', 'github': 'fa-github', 'linkedin': 'fa-linkedin', 'facebook': 'fa-facebook', 'tiktok': 'fa-tiktok', 'snapchat': 'fa-snapchat' };
            const icon = iconMap[link.platform.toLowerCase()] || 'fa-globe';
            socialsHtml += `<a href="${escapeHtml(link.url)}" target="_blank" rel="noopener"><i class="fab ${icon}"></i> ${escapeHtml(link.platform)}</a>`;
        });
        socialsHtml += '</div>';
    }

    contentDiv.innerHTML = `<div class="profile-about-section">
        <h3>About</h3>
        <div class="profile-about-grid">${itemsHtml}</div>
        ${socialsHtml}
    </div>`;
}

/**
 * Helper to remove content after tab container
 */
function removeProfileContentAfter(tabContent) {
    const next = tabContent.nextElementSibling;
    if (next && next.id === 'profile-posts-content') {
        next.remove();
    }
}

/**
 * Handle follow/unfollow with instant UI update
 */
async function handleProfileFollow(userId) {
    const btn = document.getElementById('profile-follow-btn');
    if (!btn) return;
    try {
        const oldText = btn.textContent.trim();
        const wasFollowing = oldText === 'Following' || oldText.includes('✓');
        if (wasFollowing) {
            await api(`/follow/${userId}`, { method: 'DELETE' });
            btn.className = 'profile-action-btn primary';
            btn.innerHTML = '<i class="fas fa-plus"></i> Follow';
            const followersEl = document.getElementById('profile-followers-count');
            if (followersEl) {
                const count = parseInt(followersEl.textContent) || 0;
                followersEl.textContent = Math.max(0, count - 1);
            }
            showToast('Unfollowed', 'info');
        } else {
            await api(`/follow/${userId}`, { method: 'POST' });
            btn.className = 'profile-action-btn outline following';
            btn.innerHTML = '<i class="fas fa-check"></i> Following';
            const followersEl = document.getElementById('profile-followers-count');
            if (followersEl) {
                const count = parseInt(followersEl.textContent) || 0;
                followersEl.textContent = count + 1;
            }
            showToast('Followed', 'success');
        }
    } catch (e) {
        showToast(e.message || 'Could not update follow status', 'error');
        // Revert button state on error
        try {
            const check = await api(`/follow/check/${userId}`);
            if (check.is_following) {
                btn.className = 'profile-action-btn outline following';
                btn.innerHTML = '<i class="fas fa-check"></i> Following';
            } else {
                btn.className = 'profile-action-btn primary';
                btn.innerHTML = '<i class="fas fa-plus"></i> Follow';
            }
        } catch (e2) {}
    }
}

/**
 * Handle message button click - opens chat with user
 */
async function handleProfileMessage(userId) {
    if (!isLoggedIn()) {
        window.location.href = '/login';
        return;
    }
    try {
        const chat = await api(`/chats/direct/${userId}`, { method: 'POST' });
        window.location.href = `/chat/${chat.id}`;
    } catch (e) {
        // Fallback to chat page
        window.location.href = '/chat';
    }
}

// Keep old function names as aliases for backward compatibility
const loadUserPosts = loadProfilePosts;
const loadUserReels = loadProfileReels;
const loadSavedPosts = loadProfileSaved;
const toggleFollow = handleProfileFollow;

// ==================== STORIES ====================
async function loadStories() {
    const container = document.getElementById('stories-container');
    if (!container || !isLoggedIn()) return;
    try {
        const stories = await api('/stories');
        if (stories.length === 0) { container.innerHTML = '<div class="empty-state"><p>No stories yet</p></div>'; return; }
        const grouped = {};
        stories.forEach(s => { if (!grouped[s.user_id]) grouped[s.user_id] = []; grouped[s.user_id].push(s); });
        let html = '<div class="stories-row">';
        for (const [userId, userStories] of Object.entries(grouped)) {
            const u = userStories[0].user || {};
            html += `<div class="story-circle" onclick="viewStory('${userStories[0].id}', '${userId}')"><img src="${getProfilePic(u)}" class="story-avatar" alt=""><span>${u.username}</span></div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    } catch (e) { container.innerHTML = '<div class="empty-state">Error loading stories</div>'; }
}

async function viewStory(storyId, userId) {
    try {
        await api(`/stories/${storyId}/view`, { method: 'POST' });
        const stories = await api(`/stories/user/${userId}`);
        if (stories.length > 0) showStoryViewer(stories);
    } catch (e) {}
}

function showStoryViewer(stories) {
    let idx = 0;
    const viewer = document.getElementById('story-viewer');
    if (!viewer) return;
    viewer.classList.add('active');
    function show() {
        if (idx >= stories.length) { viewer.classList.remove('active'); return; }
        const s = stories[idx];
        const u = s.user || {};
        const isOwner = currentUser && s.user_id === currentUser.id;
        const progressBars = stories.map((_, i) => `<div class="story-progress-bar ${i <= idx ? 'active' : ''}"></div>`).join('');
        viewer.innerHTML = `<div class="story-slide">
            <div class="story-progress">${progressBars}</div>
            <div class="story-header">
                <img src="${getProfilePic(u)}">
                <span style="font-weight:600">${u.username}</span>
                <span style="opacity:0.7;font-size:12px">${formatTime(s.created_at)}</span>
                ${isOwner ? `<button class="story-delete-btn" title="Delete story" onclick="deleteStory('${s.id}')"><i class="fas fa-trash"></i></button>` : ''}
                <button onclick="document.getElementById('story-viewer').classList.remove('active')">&times;</button>
            </div>
            <div class="story-media">${s.media_type === 'video' ? `<video src="${mediaUrl(s.media_url)}" autoplay controls playsinline></video>` : `<img src="${mediaUrl(s.media_url)}" alt="">`}</div>
            ${s.caption ? `<p class="story-caption">${escapeHtml(s.caption)}</p>` : ''}
            <div class="story-reactions">
                ${['❤️','🔥','👏','😂','😮'].map(r => `<button type="button" onclick="reactToStory('${s.id}','${r}')">${r}</button>`).join('')}
            </div>
            <div style="display:flex;justify-content:center;gap:16px;padding:16px">
                ${idx > 0 ? `<button class="btn btn-ghost" onclick="window.changeStory(-1)"><i class="fas fa-chevron-left"></i></button>` : ''}
                <button class="btn btn-ghost" onclick="window.changeStory(1)"><i class="fas fa-chevron-right"></i></button>
            </div>
        </div>`;
    }
    window.changeStory = (delta) => { idx += delta; show(); };
    show();
}

async function reactToStory(storyId, reaction) {
    try {
        await api(`/stories/${storyId}/react`, { method: 'POST', body: JSON.stringify({ reaction }) });
        showToast('Reaction sent', 'success');
    } catch (e) { showToast(e.message || 'Could not react to story', 'error'); }
}

async function deleteStory(storyId) {
    if (!(await confirmDelete('Are you sure you want to delete this?'))) return;
    try {
        await api(`/stories/${storyId}`, { method: 'DELETE' });
        showToast('Story deleted', 'success');
        document.getElementById('story-viewer')?.classList.remove('active');
        if (typeof loadStories === 'function') loadStories();
        if (typeof loadFeedStories === 'function') loadFeedStories();
    } catch (e) { showToast(e.message || 'Could not delete story', 'error'); }
}

// ==================== REELS ====================
async function loadReels(page = 1) {
    const container = document.getElementById('reels-container');
    if (!container) return;
    try {
        if (!currentUser && isLoggedIn()) {
            try { currentUser = await api('/auth/me'); } catch (e) {}
        }
        const data = await api(`/reels?page=${page}`);
        if (!data.reels || data.reels.length === 0) { container.innerHTML = '<div class="empty-state"><i class="fas fa-film fa-3x"></i><h3>No reels yet</h3><p>Be the first to create a reel!</p></div>'; return; }
        container.innerHTML = data.reels.map(r => renderReel(r)).join('');
        initReelAudioState();
        initReelPlaybackObserver();
    } catch (e) { container.innerHTML = `<div class="empty-state">${escapeHtml(e.message || 'Error loading reels')}</div>`; }
}

function renderReel(reel) {
    const u = reel.user || {};
    const canDelete = currentUser && (String(reel.user_id) === String(currentUser.id) || currentUser.role === 'admin');
    const src = mediaUrl(reel.video_url);
    if (!src) return `<div class="reel-card video-error" id="reel-${reel.id}"><div class="reel-video-error"><i class="fas fa-triangle-exclamation"></i><span>Video unavailable.</span>${canDelete ? `<button class="btn btn-danger btn-sm" type="button" onclick="deleteContent('reel','${reel.id}')"><i class="fas fa-trash"></i> Delete this reel</button>` : ''}</div></div>`;
    const audioTitle = reel.music_name || reel.title || 'Original Audio';
    const artistName = reel.music_artist || (audioTitle.includes(' - ') ? audioTitle.split(' - ').slice(1).join(' - ') : 'Original audio');
    const musicTitle = audioTitle.includes(' - ') ? audioTitle.split(' - ')[0] : audioTitle;
    return `<div class="reel-card" id="reel-${reel.id}">
        <video src="${src}" playsinline loop preload="metadata" class="reel-video" data-reel-video onerror="this.closest('.reel-card').classList.add('video-error')"></video>
        <div class="reel-video-error"><i class="fas fa-triangle-exclamation"></i><span>Video could not load.</span><small>${escapeHtml(src)}</small>${canDelete ? `<button class="btn btn-danger btn-sm" type="button" onclick="deleteContent('reel','${reel.id}')"><i class="fas fa-trash"></i> Delete this reel</button>` : ''}</div>
        <div class="reel-voice-status" data-reel-voice-status><i class="fas fa-volume-xmark"></i><span>Voice muted</span></div>
        <button class="reel-sound-toggle" type="button" onclick="toggleReelSound(this)" aria-label="Toggle reel sound" title="Toggle sound">
            <i class="fas fa-volume-xmark"></i><span>Muted</span>
        </button>
        <div class="reel-actions">
            <button class="${reel.is_liked ? 'liked' : ''}" onclick="likeReel('${reel.id}')"><i class="fas fa-heart"></i><span>${reel.likes_count || 0}</span></button>
            <button onclick="showReelComments('${reel.id}')"><i class="fas fa-comment"></i><span>${reel.comments_count || 0}</span></button>
            <button onclick="shareReel('${reel.id}')"><i class="fas fa-share"></i><span>${reel.shares_count || 0}</span></button>
            <button onclick="saveReel('${reel.id}')"><i class="fas fa-bookmark"></i><span>Save</span></button>
            ${canDelete ? `<button onclick="deleteContent('reel','${reel.id}')"><i class="fas fa-trash"></i><span>Delete</span></button>` : ''}
        </div>
        <div class="reel-overlay">
            <div class="reel-info">
                <div class="reel-author"><img src="${getProfilePic(u)}" class="avatar-sm" alt=""><span>@${u.username || ''}</span></div>
                <p>${escapeHtml(reel.caption || '')}</p>
                ${(reel.hashtags || []).length ? `<div class="hashtags">${reel.hashtags.map(tag => `<span>#${escapeHtml(tag)}</span>`).join(' ')}</div>` : ''}
                ${reel.location ? `<div class="reel-location"><i class="fas fa-location-dot"></i> ${escapeHtml(reel.location)}</div>` : ''}
                <button class="audio music-link" type="button" onclick="viewReelsByMusic('${reel.music_id || ''}')"><i class="fas fa-music"></i><span><strong>${escapeHtml(musicTitle)}</strong><small>${escapeHtml(artistName)}</small></span></button>
                ${reel.music_id ? `<button class="use-audio-btn" type="button" onclick="loadMusicLibrary(); setTimeout(() => selectMusic({id:'${reel.music_id}', title:${JSON.stringify(musicTitle)}, artist:${JSON.stringify(artistName)}}), 300)"><i class="fas fa-plus"></i> Use this audio</button>` : ''}
            </div>
        </div>
    </div>`;
}

function renderReelGridCard(reel) {
    const cover = reel.cover_image || reel.thumbnail_url;
    const media = cover ? `<img src="${mediaUrl(cover)}" alt="Reel cover">` : `<video src="${mediaUrl(reel.video_url)}" muted preload="metadata"></video>`;
    const canDelete = currentUser && (reel.user_id === currentUser.id || currentUser.role === 'admin');
    return `<div class="reel-grid-card" onclick="window.location.href='/reels#reel-${reel.id}'">
        ${media}<div class="reel-grid-overlay"><i class="fas fa-play"></i><span>${reel.views_count || 0}</span>${canDelete ? `<button class="grid-delete" onclick="event.stopPropagation();deleteContent('reel','${reel.id}')"><i class="fas fa-trash"></i></button>` : ''}</div>
    </div>`;
}

async function loadMusicLibrary(q = '') {
    const picker = document.getElementById('music-picker');
    const list = document.getElementById('music-list');
    if (!picker || !list) return;
    picker.classList.remove('hidden');
    list.innerHTML = '<div class="loading"><div class="spinner"></div><span>Loading music...</span></div>';
    try {
        const endpoint = q && q.trim() ? `/music/search?q=${encodeURIComponent(q.trim())}` : '/music/trending';
        let tracks = await api(endpoint);
        if ((!tracks || !tracks.length) && !(q && q.trim())) tracks = await api('/music');
        list.innerHTML = (tracks || []).map(track => `<div class="music-row" data-music-id="${track.id}">
            <button type="button" class="music-play" onclick="previewMusic('${mediaUrl(track.audio_path)}', this)"><i class="fas fa-play"></i></button>
            <div class="music-meta"><strong>${escapeHtml(track.title)}</strong><span>${escapeHtml(track.artist || 'Unknown artist')} ${track.is_trending ? ' • Trending' : ''}</span></div>
            <button type="button" class="btn btn-primary btn-sm" onclick='selectMusic(${JSON.stringify(track).replace(/'/g, '&#039;')})'>Select</button>
        </div>`).join('') || '<div class="empty-state"><p>No music found. Upload music from the API or try another search.</p></div>';
    } catch (e) {
        list.innerHTML = `<div class="empty-state"><p>${escapeHtml(e.message || 'Could not load music')}</p></div>`;
    }
}

function searchMusic(q = '') { return loadMusicLibrary(q); }

function playMusicPreview(src, button) {
    if (currentPreviewAudio) {
        currentPreviewAudio.pause();
        document.querySelectorAll('.music-play i').forEach(i => i.className = 'fas fa-play');
    }
    if (currentPreviewAudio && currentPreviewAudio.src.includes(src)) {
        currentPreviewAudio = null;
        return;
    }
    currentPreviewAudio = new Audio(src);
    currentPreviewAudio.play().catch(() => showToast('Could not play preview', 'warning'));
    const icon = button?.querySelector('i');
    if (icon) icon.className = 'fas fa-pause';
    currentPreviewAudio.onended = () => { if (icon) icon.className = 'fas fa-play'; currentPreviewAudio = null; };
}

const previewMusic = playMusicPreview;

function selectMusic(track) {
    selectedMusic = track;
    const selectedId = document.getElementById('selected-music-id');
    const selectedLabel = document.getElementById('selected-music-label');
    if (selectedId) selectedId.value = track.id;
    if (selectedLabel) selectedLabel.textContent = `${track.title}${track.artist ? ' - ' + track.artist : ''}`;
    document.getElementById('music-picker')?.classList.add('hidden');
    showToast('Music selected', 'success');
}

async function uploadMusic() {
    if (!requireLoginForUpload()) return;
    const title = document.getElementById('music-upload-title')?.value?.trim();
    const artist = document.getElementById('music-upload-artist')?.value?.trim() || '';
    const category = document.getElementById('music-upload-category')?.value?.trim() || '';
    const file = document.getElementById('music-upload-file')?.files?.[0];
    if (!title || !file) return showToast('Music title and audio file are required', 'warning');
    const err = validateUploadFile(file, MUSIC_TYPES, 10 * 1024 * 1024, 'Music');
    if (err) return showToast(err, 'warning');
    const form = new FormData();
    form.append('title', title); form.append('artist', artist); form.append('category', category); form.append('audio_file', file);
    try {
        const track = await uploadWithProgress(`${API}/music/upload`, form, null);
        selectMusic(track);
        await loadMusicLibrary();
        showToast('Music uploaded', 'success');
    } catch (e) { showToast(e.message || 'Could not upload music', 'error'); }
}

async function attachMusicToReel(reelId, musicId = null) {
    const selectedId = musicId || selectedMusic?.id || document.getElementById('selected-music-id')?.value;
    if (!selectedId) return showToast('Select music first', 'warning');
    try {
        await api(`/reels/${reelId}/music`, { method: 'POST', body: JSON.stringify({ music_id: selectedId }) });
        showToast('Music attached to reel', 'success');
        if (document.getElementById('reels-container')) loadReels();
    } catch (e) { showToast(e.message || 'Could not attach music', 'error'); }
}

function viewReelsByMusic(musicId) {
    if (!musicId) return;
    const container = document.getElementById('reels-container');
    if (container) {
        api(`/reels?music_id=${encodeURIComponent(musicId)}`).then(data => {
            container.innerHTML = data.reels?.length ? data.reels.map(r => renderReel(r)).join('') : '<div class="empty-state"><p>No reels found for this audio.</p></div>';
            initReelAudioState(); initReelPlaybackObserver();
        }).catch(e => showToast(e.message || 'Could not load audio reels', 'error'));
    } else {
        window.location.href = `/reels?music_id=${encodeURIComponent(musicId)}`;
    }
}

function setReelSoundState(enabled) {
    reelsSoundEnabled = !!enabled;
    localStorage.setItem('reels_sound_enabled', reelsSoundEnabled ? 'true' : 'false');
    document.querySelectorAll('[data-reel-video]').forEach(video => {
        video.muted = !reelsSoundEnabled;
        video.volume = reelsSoundEnabled ? 1 : 0;
        updateReelVoiceStatus(video, reelsSoundEnabled ? 'ready' : 'muted');
    });
    document.querySelectorAll('.reel-sound-toggle').forEach(btn => {
        btn.classList.remove('sound-blocked');
        btn.classList.toggle('sound-on', reelsSoundEnabled);
        btn.setAttribute('aria-pressed', reelsSoundEnabled ? 'true' : 'false');
        btn.setAttribute('aria-label', reelsSoundEnabled ? 'Mute reel sound' : 'Unmute reel sound');
        btn.setAttribute('title', reelsSoundEnabled ? 'Mute sound' : 'Unmute sound');
        btn.innerHTML = reelsSoundEnabled
            ? '<i class="fas fa-volume-high"></i><span>Sound on</span>'
            : '<i class="fas fa-volume-xmark"></i><span>Muted</span>';
    });
}

function updateReelVoiceStatus(video, state = null) {
    const card = video?.closest?.('.reel-card');
    const badge = card?.querySelector?.('[data-reel-voice-status]');
    if (!badge) return;
    const nextState = state || (video.muted || video.volume === 0 ? 'muted' : 'ready');
    const config = {
        ready: ['fa-volume-high', 'Voice on'],
        muted: ['fa-volume-xmark', 'Voice muted'],
        blocked: ['fa-circle-exclamation', 'Tap to enable voice']
    }[nextState] || ['fa-volume-xmark', 'Voice muted'];
    badge.classList.toggle('ready', nextState === 'ready');
    badge.classList.toggle('blocked', nextState === 'blocked');
    badge.innerHTML = `<i class="fas ${config[0]}"></i><span>${config[1]}</span>`;
}

async function toggleReelSound(button) {
    setReelSoundState(!reelsSoundEnabled);
    const video = button?.closest('.reel-card')?.querySelector('[data-reel-video]');
    if (video && reelsSoundEnabled) {
        try {
            await video.play();
            updateReelVoiceStatus(video, 'ready');
        } catch (e) {
            button?.classList.add('sound-blocked');
            updateReelVoiceStatus(video, 'blocked');
            showToast('Tap the reel once to allow voice playback', 'warning');
        }
    }
}

function initReelAudioState() {
    setReelSoundState(reelsSoundEnabled);
    document.querySelectorAll('[data-reel-video]').forEach(video => {
        video.addEventListener('click', () => {
            if (video.paused) video.play().then(() => updateReelVoiceStatus(video)).catch(() => updateReelVoiceStatus(video, 'blocked'));
            else video.pause();
        });
        video.addEventListener('volumechange', () => {
            const userMuted = video.muted || video.volume === 0;
            if (userMuted !== !reelsSoundEnabled) setReelSoundState(!userMuted);
            updateReelVoiceStatus(video);
        });
        video.addEventListener('loadedmetadata', () => updateReelVoiceStatus(video));
        updateReelVoiceStatus(video);
    });
}

function initReelPlaybackObserver() {
    const videos = document.querySelectorAll('[data-reel-video]');
    if (reelsPlaybackObserver) reelsPlaybackObserver.disconnect();
    if (!('IntersectionObserver' in window)) return;
    reelsPlaybackObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const video = entry.target;
            if (entry.isIntersecting && entry.intersectionRatio >= 0.65) {
                video.muted = !reelsSoundEnabled;
                updateReelVoiceStatus(video, reelsSoundEnabled ? 'ready' : 'muted');
                video.play().catch(() => updateReelVoiceStatus(video, reelsSoundEnabled ? 'blocked' : 'muted'));
            } else {
                video.pause();
            }
        });
    }, { threshold: [0, 0.35, 0.65, 1] });
    videos.forEach(video => reelsPlaybackObserver.observe(video));
}

async function likeReel(id) { try { await api(`/reels/${id}/like`, { method: 'POST' }); loadReels(); } catch (e) { try { await api(`/reels/${id}/like`, { method: 'DELETE' }); loadReels(); } catch (e2) {} } }
async function saveReel(id) { try { await api(`/reels/${id}/save`, { method: 'POST' }); showToast('Reel saved!', 'success'); } catch (e) { showToast(e.message || 'Could not save reel', 'error'); } }
async function shareReel(id) {
    const url = `${window.location.origin}/reels#reel-${id}`;
    try { await api(`/reels/${id}/share`, { method: 'POST' }); } catch (e) {}
    navigator.clipboard?.writeText(url);
    showToast('Reel link copied', 'success');
    if (document.getElementById('reels-container')) loadReels();
}

async function showReelComments(reelId) {
    const modal = document.getElementById('comments-modal');
    const content = document.getElementById('comments-content');
    if (!modal || !content) return;
    modal.classList.add('active');
    content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    try {
        const comments = await api(`/reels/${reelId}/comments`);
        const rows = comments.map(c => renderComment({ ...c, author: c.author || {} }, reelId)).join('');
        content.innerHTML = `<div class="comment-form"><input id="reel-comment-input" placeholder="Add a reel comment..." onkeypress="if(event.key==='Enter')addReelComment('${reelId}')"><button onclick="addReelComment('${reelId}')" class="btn btn-primary btn-sm">Post</button></div>${rows || '<div class="empty-state"><p>No comments yet</p></div>'}`;
    } catch (e) { content.innerHTML = '<p>Error loading reel comments</p>'; }
}

async function addReelComment(reelId) {
    const input = document.getElementById('reel-comment-input');
    if (!input || !input.value.trim()) return;
    try {
        await api(`/reels/${reelId}/comments`, { method: 'POST', body: JSON.stringify({ content: input.value.trim() }) });
        input.value = '';
        showReelComments(reelId);
    } catch (e) { showToast(e.message || 'Error posting reel comment', 'error'); }
}

// ==================== CHAT ====================
let currentChatId = null;
let chatSocket = null;
let chatMessagesById = new Map();
let chatSearchTimer = null;
let chatUsersCache = [];

async function loadChats() {
    const list = document.getElementById('chat-list');
    if (!list) return;
    try {
        list.innerHTML = '<div class="loading"><div class="spinner"></div><span>Loading chats...</span></div>';
        const chats = await api('/chats');
        if (!Array.isArray(chats) || chats.length === 0) {
            list.innerHTML = '<div class="empty-state chat-empty"><i class="fas fa-comments fa-3x"></i><h3>No conversations yet</h3><p>Search a user above to start chatting.</p></div>';
            await loadChatUsers('');
            return;
        }
        list.innerHTML = chats.map(c => {
            const other = c.participants.find(p => currentUser && p.id !== currentUser.id) || c.participants[0] || {};
            const lastMsg = c.last_message;
            const isActive = currentChatId && currentChatId === c.id;
            return `<div class="chat-item ${isActive ? 'active' : ''}" data-chat-name="${escapeHtml((other.username || c.name || '').toLowerCase())}" onclick="openChat('${c.id}')">
                <img src="${getProfilePic(other)}" class="avatar-sm">
                <div class="chat-info">
                    <span class="username">${escapeHtml(other.full_name || other.username || c.name || 'Chat')}</span>
                    <p class="last-msg">${lastMsg ? escapeHtml(lastMsg.content || lastMsg.message_text || '').substring(0, 54) : 'Start chatting'}</p>
                </div>
                <div class="chat-meta"><span>${lastMsg ? formatChatTime(lastMsg.created_at) : ''}</span>${c.unread_count > 0 ? `<span class="unread-badge">${c.unread_count}</span>` : ''}</div>
            </div>`;
        }).join('');
        if (currentChatId) updateChatHeaderFromList(chats.find(c => c.id === currentChatId));
        initChatSocket();
    } catch (e) { list.innerHTML = `<div class="empty-state chat-empty"><i class="fas fa-triangle-exclamation"></i><p>${escapeHtml(e.message || 'Error loading chats')}</p></div>`; }
}

async function loadChatUsers(q = '') {
    const results = document.getElementById('chat-user-results');
    if (!results) return;
    try {
        const users = await api(`/chats/users?q=${encodeURIComponent(q)}`);
        chatUsersCache = users || [];
        if (!q.trim()) { results.innerHTML = ''; return; }
        results.innerHTML = chatUsersCache.length ? chatUsersCache.map(u => `<button class="chat-user-result" onclick="startDirectChat('${u.id}')"><img src="${getProfilePic(u)}" class="avatar-sm"><span><strong>${escapeHtml(u.full_name || u.username)}</strong><small>@${escapeHtml(u.username)}</small></span></button>`).join('') : '<div class="chat-search-empty">No users found</div>';
    } catch (e) { results.innerHTML = '<div class="chat-search-empty">Unable to search users</div>'; }
}

function handleChatSearch(q) {
    document.querySelectorAll('.chat-item').forEach(item => {
        const name = item.getAttribute('data-chat-name') || item.textContent.toLowerCase();
        item.style.display = name.includes(q.toLowerCase()) ? 'flex' : 'none';
    });
    clearTimeout(chatSearchTimer);
    chatSearchTimer = setTimeout(() => loadChatUsers(q), 250);
}

async function startDirectChat(userId) {
    try {
        const chat = await api(`/chats/direct/${userId}`, { method: 'POST' });
        document.getElementById('chat-user-results').innerHTML = '';
        document.getElementById('chat-search-input').value = '';
        openChat(chat.id, false);
    } catch (e) { showToast(e.message || 'Could not start chat', 'error'); }
}

function openChat(chatId, push = true) {
    currentChatId = chatId;
    if (push) history.pushState({}, '', `/chat/${chatId}`);
    document.getElementById('message-bar')?.style.setProperty('display', 'flex');
    document.querySelectorAll('.chat-item').forEach(i => i.classList.toggle('active', i.getAttribute('onclick')?.includes(chatId)));
    loadChatMessages(chatId);
}

function updateChatHeaderFromList(chat) {
    const header = document.getElementById('chat-main-header');
    if (!header || !chat) return;
    const other = chat.participants?.find(p => currentUser && p.id !== currentUser.id) || chat.participants?.[0] || {};
    header.classList.remove('hidden');
    header.innerHTML = `<button class="chat-back-btn" onclick="history.pushState({},'', '/chat'); currentChatId=null; document.getElementById('chat-main-header').classList.add('hidden'); document.getElementById('message-bar').style.display='none'; loadChats();"><i class="fas fa-arrow-left"></i></button><img src="${getProfilePic(other)}" class="avatar-sm"><div><div class="username">${escapeHtml(other.full_name || other.username || chat.name || 'Chat')}</div><div class="status"><span class="online-dot"></span> Messages</div></div><div class="chat-main-actions"><button onclick="loadChatMessages(currentChatId)" title="Refresh"><i class="fas fa-rotate"></i></button></div>`;
}

async function loadChatMessages(chatId) {
    const container = document.getElementById('messages-container');
    if (!container) return;
    try {
        container.innerHTML = '<div class="loading"><div class="spinner"></div><span>Loading messages...</span></div>';
        const chat = await api(`/chats/${chatId}`);
        updateChatHeaderFromList(chat);
        const messages = await api(`/chats/${chatId}/messages`);
        chatMessagesById.clear();
        container.innerHTML = (messages || []).map(m => {
            chatMessagesById.set(m.id, m);
            const isMine = currentUser && m.sender_id === currentUser.id;
            return `<div class="message ${isMine ? 'sent' : 'received'}">
                <div class="message-bubble">${m.is_deleted ? '<em>This message has been deleted</em>' : escapeHtml(m.content || m.message_text || '')}${m.file_url ? `<a href="${mediaUrl(m.file_url)}" target="_blank" style="display:block;margin-top:8px;color:inherit;text-decoration:underline">📎 File</a>` : ''}</div>
                <span class="message-time">${formatChatTime(m.created_at)} ${isMine ? `<i class="fas fa-check-double ${m.is_read ? 'read' : ''}"></i>` : ''}</span>
            </div>`;
        }).join('') || '<div class="empty-state chat-empty"><i class="fas fa-paper-plane fa-3x"></i><h3>No messages yet</h3><p>Say hello 👋</p></div>';
        container.scrollTop = container.scrollHeight;
        await api(`/chats/${chatId}/read`, { method: 'PUT' }).catch(() => null);
        loadChats();
        initChatSocket();
    } catch (e) { container.innerHTML = `<div class="empty-state chat-empty"><i class="fas fa-triangle-exclamation fa-2x"></i><p>${escapeHtml(e.message || 'Error loading messages')}</p></div>`; }
}

async function sendMessage(chatId) {
    const input = document.getElementById('message-input');
    const sendBtn = document.getElementById('chat-send-btn');
    if (!input || !input.value.trim()) return;
    if (!chatId) { showToast('Select a chat first', 'warning'); return; }
    const text = input.value.trim();
    const tempId = `tmp-${Date.now()}`;
    appendChatMessage({ id: tempId, sender_id: currentUser?.id, content: text, created_at: new Date().toISOString(), is_read: false }, true);
    input.value = '';
    if (sendBtn) sendBtn.disabled = true;
    try {
        const saved = await api(`/chats/${chatId}/messages`, { method: 'POST', body: JSON.stringify({ content: text, message_text: text }) });
        const tempEl = document.getElementById(`msg-${tempId}`);
        if (tempEl) tempEl.outerHTML = renderChatMessage(saved, saved.sender_id === currentUser?.id);
        loadChats();
    } catch (e) { showToast(e.message || 'Error sending message', 'error'); }
    finally { if (sendBtn) sendBtn.disabled = false; input.focus(); }
}

function renderChatMessage(m, isMine) {
    return `<div class="message ${isMine ? 'sent' : 'received'}" id="msg-${m.id}"><div class="message-bubble">${m.is_deleted ? '<em>This message has been deleted</em>' : escapeHtml(m.content || m.message_text || '')}</div><span class="message-time">${formatChatTime(m.created_at)} ${isMine ? `<i class="fas fa-check-double ${m.is_read ? 'read' : ''}"></i>` : ''}</span></div>`;
}

function appendChatMessage(m, isMine = false) {
    const container = document.getElementById('messages-container');
    if (!container || chatMessagesById.has(m.id)) return;
    chatMessagesById.set(m.id, m);
    if (container.querySelector('.empty-state')) container.innerHTML = '';
    container.insertAdjacentHTML('beforeend', renderChatMessage(m, isMine));
    container.scrollTop = container.scrollHeight;
}

function initChatSocket() {
    if (!token || chatSocket || !location.pathname.startsWith('/chat')) return;
    try {
        const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
        chatSocket = new WebSocket(`${protocol}://${location.host}/ws/chat?token=${encodeURIComponent(token)}`);
        chatSocket.onopen = () => { if (currentChatId) chatSocket.send(JSON.stringify({ type: 'join', chat_id: currentChatId })); };
        chatSocket.onmessage = (evt) => {
            const data = JSON.parse(evt.data || '{}');
            if (data.type === 'new_message' && data.message) {
                if (data.message.chat_id === currentChatId) appendChatMessage(data.message, data.message.sender_id === currentUser?.id);
                loadChats();
            }
            if (data.type === 'messages_read' && data.chat_id === currentChatId) loadChatMessages(currentChatId);
        };
        chatSocket.onclose = () => { chatSocket = null; };
    } catch (e) { chatSocket = null; }
}

// ==================== NOTIFICATIONS ====================
let allNotifications = [];
let currentNotificationFilter = 'all';

async function loadNotifications() {
    const container = document.getElementById('notifications-container');
    if (!container) return;
    try {
        const notifs = await api('/notifications');
        allNotifications = notifs;
        renderFilteredNotifications('all');
    } catch (e) { container.innerHTML = '<div class="notif-empty-state"><i class="fas fa-exclamation-circle"></i><h3>Error loading notifications</h3></div>'; }
}

function filterNotifications(filter) {
    currentNotificationFilter = filter;
    document.querySelectorAll('.notif-filter-btn').forEach(b => {
        const isActive = b.dataset.filter === filter;
        b.classList.toggle('active', isActive);
        b.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    renderFilteredNotifications(filter);
}

function renderFilteredNotifications(filter) {
    const container = document.getElementById('notifications-container');
    if (!container) return;

    let filtered = allNotifications;
    if (filter !== 'all') {
        filtered = allNotifications.filter(n => {
            const t = (n.type || '').toLowerCase();
            if (filter === 'like') return t === 'like';
            if (filter === 'comment') return t === 'comment';
            if (filter === 'follow') return t === 'follow' || t === 'follow_request';
            if (filter === 'mention') return t === 'mention' || t === 'tag';
            return true;
        });
    }

    if (filtered.length === 0) {
        container.innerHTML = '<div class="notif-empty-state"><i class="fas fa-bell-slash fa-3x"></i><h3>No notifications yet</h3><p>When someone interacts with you, you\'ll see it here</p></div>';
        return;
    }

    // Group by date
    const groups = { today: [], thisWeek: [], earlier: [] };
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startOfWeek = new Date(startOfToday);
    startOfWeek.setDate(startOfWeek.getDate() - startOfWeek.getDay());

    filtered.forEach(n => {
        const d = parseApiDate(n.created_at);
        if (!d) { groups.earlier.push(n); return; }
        if (d >= startOfToday) groups.today.push(n);
        else if (d >= startOfWeek) groups.thisWeek.push(n);
        else groups.earlier.push(n);
    });

    const groupLabels = {
        today: 'Today',
        thisWeek: 'This Week',
        earlier: 'Earlier'
    };

    let html = '';
    ['today', 'thisWeek', 'earlier'].forEach(key => {
        if (groups[key].length === 0) return;
        html += `<div class="notif-date-group">${groupLabels[key]}</div>`;
        html += groups[key].map(n => renderNotificationItem(n)).join('');
    });

    container.innerHTML = html;
}

function renderNotificationItem(n) {
    const actor = n.actor || {};
    const notifType = n.type || '';
    const isUnread = !n.is_read;
    let overlayClass = 'follow';
    let icon = 'fa-user-plus';
    if (notifType === 'like') { overlayClass = 'like'; icon = 'fa-heart'; }
    else if (notifType === 'comment') { overlayClass = 'comment'; icon = 'fa-comment'; }
    else if (notifType === 'follow') { overlayClass = 'follow'; icon = 'fa-user-plus'; }
    else if (notifType === 'follow_request') { overlayClass = 'follow'; icon = 'fa-user-check'; }
    else if (notifType === 'tag' || notifType === 'mention') { overlayClass = 'mention'; icon = 'fa-tag'; }

    const avatarSrc = getProfilePic(actor);
    const avatarHtml = avatarSrc && !avatarSrc.includes('default')
        ? `<img src="${avatarSrc}" class="notif-user-avatar" alt="${escapeHtml(actor.username || '')}" loading="lazy">`
        : `<div class="notif-user-avatar-placeholder" aria-hidden="true">${(actor.username || '?')[0].toUpperCase()}</div>`;

    // Post thumbnail for like/comment/tag notifications
    let thumbHtml = '';
    if ((notifType === 'like' || notifType === 'comment' || notifType === 'tag' || notifType === 'mention') && n.post && n.post.images && n.post.images.length > 0) {
        const imgUrl = mediaUrl(n.post.images[0].image_url);
        thumbHtml = `<img src="${imgUrl}" class="notif-post-thumb" alt="" loading="lazy">`;
    } else if ((notifType === 'like' || notifType === 'comment') && n.post && n.post.image_url) {
        thumbHtml = `<img src="${mediaUrl(n.post.image_url)}" class="notif-post-thumb" alt="" loading="lazy">`;
    }

    return `<div class="notification-item ${isUnread ? 'unread' : ''}" onclick="markNotifRead('${n.id}')" role="button" tabindex="0" aria-label="${escapeHtml(n.message || '')}">
        ${isUnread ? '<span class="unread-dot" aria-hidden="true"></span>' : ''}
        <div class="notif-icon-badge">
            ${avatarHtml}
            <div class="notif-icon-overlay ${overlayClass}" aria-hidden="true"><i class="fas ${icon}"></i></div>
        </div>
        <div class="notif-content">
            <p class="notif-text">${escapeHtml(n.message || '')}</p>
            <span class="notif-time">${formatTime(n.created_at)}</span>
        </div>
        ${thumbHtml}
    </div>`;
}

async function markNotifRead(id) {
    try { await api(`/notifications/${id}/read`, { method: 'PUT' }); loadUnreadCount(); } catch (e) {}
    // Mark the item as read in the UI
    const item = document.querySelector(`.notification-item[onclick*="'${id}'"]`);
    if (item) {
        item.classList.remove('unread');
        const dot = item.querySelector('.unread-dot');
        if (dot) dot.remove();
    }
}

async function markAllRead() {
    try {
        await api('/notifications/read-all', { method: 'PUT' });
        document.querySelectorAll('.notification-item.unread').forEach(el => {
            el.classList.remove('unread');
            const dot = el.querySelector('.unread-dot');
            if (dot) dot.remove();
        });
        loadUnreadCount();
    } catch (e) {}
}

// ==================== SEARCH ====================
async function handleSearch(e) {
    if (e) e.preventDefault();
    const q = document.getElementById('search-input')?.value;
    if (!q) return;
    const container = document.getElementById('search-results');
    if (!container) return;
    try {
        const results = await api(`/search?q=${encodeURIComponent(q)}`);
        let html = '';
        if (results.users && results.users.length > 0) { html += '<h3>Users</h3>' + results.users.map(u => `<a href="/profile/${u.username}" class="search-user"><img src="${getProfilePic(u)}" class="avatar-sm"><span>${u.username}</span>${u.is_verified ? '<i class="fas fa-check-circle verified"></i>' : ''}</a>`).join(''); }
        if (results.posts && results.posts.length > 0) { html += '<h3 style="margin-top:20px">Posts</h3>' + results.posts.map(p => renderPost(p)).join(''); }
        if (results.reels && results.reels.length > 0) { html += '<h3 style="margin-top:20px">Reels</h3><div class="search-reels-grid">' + results.reels.map(r => renderReel(r)).join('') + '</div>'; }
        if (results.hashtags && results.hashtags.length > 0) { html += '<h3 style="margin-top:20px">Hashtags</h3><div class="hashtag-results">' + results.hashtags.map(t => `<button class="hashtag-chip" onclick="document.getElementById('search-input').value='${escapeHtml(t)}';handleSearch()">${escapeHtml(t)}</button>`).join('') + '</div>'; }
        if (!html) html = '<div class="empty-state"><p>No results found</p></div>';
        container.innerHTML = html;
    } catch (e) { container.innerHTML = '<div class="empty-state">Error searching</div>'; }
}

// ==================== ADMIN ====================
async function loadAdminDashboard() {
    const dash = document.getElementById('admin-dashboard');
    if (!dash) return;
    try {
        const d = await api('/admin/dashboard');
        dash.innerHTML = `<div class="stats-grid">
            <div class="stat-card users"><div class="stat-icon"><i class="fas fa-users"></i></div><h3>${d.total_users || 0}</h3><div class="stat-label">Total Users</div><div class="stat-change up"><i class="fas fa-arrow-up"></i> +12.8%</div></div>
            <div class="stat-card posts"><div class="stat-icon"><i class="fas fa-newspaper"></i></div><h3>${d.total_posts || 0}</h3><div class="stat-label">Total Posts</div><div class="stat-change up"><i class="fas fa-arrow-up"></i> +8.2%</div></div>
            <div class="stat-card reports"><div class="stat-icon"><i class="fas fa-flag"></i></div><h3>${d.total_reports || 0}</h3><div class="stat-label">Total Reports</div><div class="stat-change down"><i class="fas fa-arrow-down"></i> -3.4%</div></div>
            <div class="stat-card active"><div class="stat-icon"><i class="fas fa-circle"></i></div><h3>${d.active_users_today || 0}</h3><div class="stat-label">Active Now</div><div class="stat-change up"><i class="fas fa-arrow-up"></i> +6.7%</div></div>
        </div>`;
    } catch (e) { dash.innerHTML = '<div class="empty-state"><i class="fas fa-lock fa-3x"></i><h3>Admin access required</h3></div>'; }
}



// ==================== GLOBAL PAGE ANIMATIONS ====================
function initPageAnimations() {
    document.body.classList.add('page-animate-ready');

    const animatedSelectors = [
        '.auth-card', '.page-header', '.create-post-card', '.post-card', '.stories-card',
        '.trending-card', '.suggestions-card', '.profile-header', '.notifications-card',
        '.notif-item', '.search-bar', '.search-tabs', '.search-user', '.explore-item',
        '.reel-card', '.story-circle', '.chat-layout', '.chat-item', '.message',
        '.admin-sidebar', '.admin-content', '.stat-card', '.chart-card',
        '.settings-sidebar', '.settings-content', '.setting-item', '.form-group', '.hero-card', '.quick-actions-card'
    ].join(',');

    const markAnimated = (root = document) => {
        root.querySelectorAll(animatedSelectors).forEach((el, index) => {
            if (!el.classList.contains('animate-in')) {
                el.classList.add('animate-in');
                el.style.animationDelay = `${Math.min(index * 0.035, 0.35)}s`;
            }
        });
    };

    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -20px 0px' });

        markAnimated();
        document.querySelectorAll('.animate-in').forEach((el) => observer.observe(el));

        const mutationObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType !== 1) return;
                    if (node.matches && node.matches(animatedSelectors)) {
                        node.classList.add('animate-in');
                        observer.observe(node);
                    }
                    if (node.querySelectorAll) {
                        markAnimated(node);
                        node.querySelectorAll('.animate-in').forEach((el) => observer.observe(el));
                    }
                });
            });
        });
        mutationObserver.observe(document.body, { childList: true, subtree: true });
    } else {
        markAnimated();
        document.querySelectorAll('.animate-in').forEach((el) => el.classList.add('is-visible'));
    }

    // Smooth page transition for normal internal links
    document.addEventListener('click', (event) => {
        const link = event.target.closest('a[href]');
        if (!link) return;
        const href = link.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('javascript:') || link.target === '_blank') return;
        const url = new URL(href, window.location.origin);
        if (url.origin !== window.location.origin) return;
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        document.body.classList.add('page-leaving');
        setTimeout(() => { window.location.href = url.href; }, 150);
    });

}

// ==================== ROUTER ====================
function initApp() {
    initTheme();
    initPageAnimations();
    const path = window.location.pathname;
    updateNav();
    document.addEventListener('click', (e) => { if (e.target.closest('.theme-toggle')) toggleTheme(); });
    renderSocialHubMenu((document.body.dataset && document.body.dataset.page) || '');
    hydrateMiniUser();
    if (path === '/' || path === '/posts') { loadFeed(); loadStories(); loadSuggestedUsers(); }
    else if (path === '/login') { const f = document.getElementById('login-form'); if (f) f.addEventListener('submit', handleLogin); }
    else if (path === '/register') { const f = document.getElementById('register-form'); if (f) f.addEventListener('submit', handleRegister); }
    else if (path.startsWith('/profile/')) { loadProfile(); }
    else if (path === '/stories') { loadStories(); }
    else if (path === '/reels') { loadReels(); }
    else if (path === '/chat') { loadChats(); }
    else if (path.startsWith('/chat/')) { const chatId = path.split('/chat/')[1]; currentChatId = chatId; loadChatMessages(chatId); }
    else if (path === '/notifications') { loadNotifications(); }
    else if (path === '/search') { const f = document.getElementById('search-form'); if (f) f.addEventListener('submit', handleSearch); }
    else if (path === '/admin') { loadAdminDashboard(); }
    const storyFile = document.getElementById('story-file');
    if (storyFile) storyFile.addEventListener('change', () => renderUploadPreview('story-file', 'story-preview', STORY_TYPES, MAX_STORY_SIZE, 'Story'));
    const reelFile = document.getElementById('reel-file');
    if (reelFile) reelFile.addEventListener('change', () => renderUploadPreview('reel-file', 'reel-preview', REEL_TYPES, MAX_REEL_SIZE, 'Reel'));
    const reelCover = document.getElementById('reel-thumbnail');
    if (reelCover) reelCover.addEventListener('change', () => renderUploadPreview('reel-thumbnail', 'reel-preview', COVER_TYPES, 10 * 1024 * 1024, 'Cover'));
    const uploadReelBtn = document.getElementById('uploadReelBtn') || document.querySelector('.upload-reel-btn, #openReelUpload, .openReelUpload');
    if (uploadReelBtn) uploadReelBtn.addEventListener('click', showCreateReel);
    const reelUploadForm = document.getElementById('reel-upload-form');
    if (reelUploadForm) reelUploadForm.addEventListener('submit', handleCreateReel);
    document.querySelectorAll('[data-close-modal]').forEach(btn => btn.addEventListener('click', (event) => {
        const id = btn.getAttribute('data-close-modal');
        if (btn.classList.contains('modal-overlay') && event.target !== btn) return;
        closeModal(id);
    }));
    const postFiles = document.getElementById('post-files');
    if (postFiles) postFiles.addEventListener('change', renderPostUploadPreview);
}

document.addEventListener('DOMContentLoaded', initApp);

function renderPostUploadPreview() {
    const input = document.getElementById('post-files');
    const preview = document.getElementById('post-preview');
    if (!input || !preview) return;
    preview.innerHTML = '';
    Array.from(input.files || []).forEach(file => {
        const error = validateUploadFile(file, STORY_TYPES, MAX_STORY_SIZE, 'Post media');
        if (error) {
            preview.innerHTML += `<div class="upload-error"><i class="fas fa-triangle-exclamation"></i> ${escapeHtml(error)}</div>`;
            return;
        }
        const url = URL.createObjectURL(file);
        const isVideo = file.type.startsWith('video/') || /\.(mp4|webm|mov|avi)$/i.test(file.name);
        preview.innerHTML += `<div class="upload-preview-card compact">
            ${isVideo ? `<video src="${url}" controls muted playsinline></video>` : `<img src="${url}" alt="Preview">`}
            <div><strong>${escapeHtml(file.name)}</strong><small>${formatBytes(file.size)}</small></div>
        </div>`;
    });
}

// ==================== PREMIUM FEATURE PAGES ====================
function money(v) { return '$' + Number(v || 0).toFixed(2); }
async function loadDataStudioPage() {
    try { const s = await api('/data-studio/stats'); const vals = [s.total_users, s.total_posts, s.total_reels, s.total_follow_relations]; ['Users','Posts','Reels','Followers'].forEach((label,i)=>{ const card=document.getElementById(`stat-${i+1}`)?.closest('.stat-card'); if(card){card.querySelector('h3').textContent=vals[i]||0; card.querySelector('.stat-label').textContent=label;} }); } catch(e){ showToast('Login required for Data Studio','warning'); }
    loadOriginalMedia();
}
async function seedDemoData() { try { const f=new FormData(); f.append('users_count','100'); f.append('posts_per_user','2'); f.append('reels_count','20'); f.append('follow_edges_count','250'); await fetchChecked(`${API}/data-studio/seed-10k`,{method:'POST',headers:getMultipartHeaders(),body:f,multipart:true}); showToast('Demo data seeded', 'success'); loadDataStudioPage(); } catch(e){ showToast(e.message,'error'); } }
async function uploadOriginalMedia(file) { if(!file) return; try { const f=new FormData(); f.append('file',file); f.append('ownership_confirmed','true'); await fetchChecked(`${API}/data-studio/media/original/upload`,{method:'POST',headers:getMultipartHeaders(),body:f,multipart:true}); showToast('Original media uploaded', 'success'); loadOriginalMedia(); } catch(e){ showToast(e.message,'error'); } }
async function loadOriginalMedia() { const grid=document.getElementById('original-media-grid'); if(!grid) return; showSkeleton(grid,2); try { const d=await api('/data-studio/media/original'); grid.innerHTML=(d.assets||[]).map(a=>`<div class="media-card">${a.media_type==='video'?`<video src="${mediaUrl(a.url)}" controls></video>`:`<img src="${mediaUrl(a.url)}" alt="">`}<strong>${escapeHtml(a.original_filename)}</strong><div class="btn-group"><button class="btn btn-sm btn-outline" onclick="createPostFromAsset('${a.id}')">Post</button><button class="btn btn-sm btn-outline" onclick="createReelFromAsset('${a.id}')">Reel</button></div></div>`).join('') || '<div class="empty-state">No media uploaded yet.</div>'; } catch(e){ grid.innerHTML='<div class="empty-state">Login to view original media.</div>'; } }
async function createPostFromAsset(id){ try { const f=new FormData(); f.append('caption','Created from original media'); await fetchChecked(`${API}/data-studio/media/original/${id}/create-post`,{method:'POST',headers:getMultipartHeaders(),body:f,multipart:true}); showToast('Post created', 'success'); } catch(e){ showToast(e.message,'error'); } }
async function createReelFromAsset(id){ try { const f=new FormData(); f.append('caption','Created from original media'); await fetchChecked(`${API}/data-studio/media/original/${id}/create-reel`,{method:'POST',headers:getMultipartHeaders(),body:f,multipart:true}); showToast('Reel created', 'success'); } catch(e){ showToast(e.message || 'Reels require video files','warning'); } }
async function loadCreatorDashboardPage(){ try { const d=await api('/creator/dashboard'); const vals=[d.views,d.likes,d.followers,(d.engagement_rate||0)+'%']; ['Views','Likes','Followers','Engagement'].forEach((label,i)=>{ const card=document.getElementById(`stat-${i+1}`)?.closest('.stat-card'); if(card){card.querySelector('h3').textContent=vals[i]||0; card.querySelector('.stat-label').textContent=label;} }); const top=document.getElementById('creator-top-content'); if(top) top.innerHTML=(d.best_content||[]).map(x=>`<div class="mini-row"><span>${escapeHtml(x.title)}</span><strong>${x.score}</strong></div>`).join('') || '<div class="empty-state">No content yet.</div>'; } catch(e){ showToast('Login required for creator dashboard','warning'); } }
async function runCreatorAI(){
    const topic=document.getElementById('ai-topic')?.value?.trim()||'creator growth';
    const tool=document.getElementById('ai-tool')?.value||'caption';
    const out=document.getElementById('ai-output');
    if(!out) return;
    const payloads={
        'caption':{title:topic,description:topic,category:'creator'},
        'hashtags':{keywords:topic,count:12},
        'bio':{name:currentUser?.full_name||currentUser?.username||'Creator',niche:topic,vibe:'professional'},
        'reel-title':{topic,keywords:topic},
        'post-ideas':{niche:topic,count:6},
        'content-calendar':{niche:topic,goal:'growth',days:7},
        'viral-hooks':{topic,audience:'creators'},
        'comment-reply':{comment:topic,tone:'friendly',context:'SocialHub creator content'}
    };
    try{
        out.innerHTML='<div class="loading"><div class="spinner"></div><span>Generating...</span></div>';
        const data=await api(`/ai/${tool}`,{method:'POST',body:JSON.stringify(payloads[tool])});
        const cards=[];
        const add=(title,value)=>{ if(value!==undefined&&value!==null&&String(value).trim()) cards.push(`<div class="ai-card"><div class="card-title-row"><h4>${escapeHtml(title)}</h4><button class="btn btn-sm btn-outline" onclick="navigator.clipboard.writeText(this.closest('.ai-card').querySelector('.ai-value').innerText);showToast('Copied','success')">Copy</button></div><div class="ai-value">${Array.isArray(value)?value.map(v=>typeof v==='object'?JSON.stringify(v,null,2):v).join('\n'):typeof value==='object'?JSON.stringify(value,null,2):escapeHtml(value)}</div></div>`); };
        Object.entries(data||{}).forEach(([k,v])=>{ if(!['source','ai_text'].includes(k)) add(k.replace(/_/g,' '),v); });
        if(data.ai_text) add('OpenAI draft',data.ai_text);
        out.innerHTML=(cards.join('')||'<div class="empty-state">No AI output returned.</div>')+`<small class="ai-source">Source: ${escapeHtml(data.source||'openai')}</small>`;
    }catch(e){ out.innerHTML=`<div class="empty-state">${escapeHtml(e.message||'AI generation failed')}</div>`; }
}

function previewImagePromptFile(){
    renderUploadPreview('image-prompt-file','image-prompt-preview',COVER_TYPES,10*1024*1024,'Image prompt');
}

async function runImagePromptEditor(){
    if(!requireLoginForUpload()) return;
    const file=document.getElementById('image-prompt-file')?.files?.[0];
    const prompt=document.getElementById('image-prompt-text')?.value?.trim()||'';
    const style=document.getElementById('image-prompt-style')?.value||'natural';
    const out=document.getElementById('image-prompt-output');
    if(!out) return;
    if(!file) return showToast('Choose an image first','warning');
    const validationError=validateUploadFile(file,COVER_TYPES,10*1024*1024,'Image prompt');
    if(validationError) return showToast(validationError,'warning');
    if(!prompt) return showToast('Describe the image change you want','warning');

    const form=new FormData();
    form.append('image',file);
    form.append('prompt',prompt);
    form.append('style',style);
    try{
        out.innerHTML='<div class="loading"><div class="spinner"></div><span>Reading image and improving prompt...</span></div>';
        const data=await fetchChecked(`${API}/ai/image-prompt`,{method:'POST',headers:getMultipartHeaders(),body:form,multipart:true});
        const info=data.image_info||{};
        out.innerHTML=`
            <div class="ai-card">
                <div class="card-title-row"><h4>Improved image edit prompt</h4><button class="btn btn-sm btn-outline" onclick="navigator.clipboard.writeText(document.getElementById('image-prompt-result').innerText);showToast('Copied','success')">Copy</button></div>
                <div class="ai-value" id="image-prompt-result">${escapeHtml(data.revised_prompt||'')}</div>
            </div>
            <div class="ai-card"><h4>Backend image read</h4><div class="ai-value">${escapeHtml(`${info.filename||file.name}\n${info.width||'?'} x ${info.height||'?'} ${info.format||''}\n${formatBytes(info.size_bytes||file.size)}`)}</div></div>
            <div class="ai-card"><h4>Edit steps</h4><div class="ai-value">${(data.edit_steps||[]).map((s,i)=>`${i+1}. ${escapeHtml(s)}`).join('<br>')}</div></div>
            <small class="ai-source">Source: ${escapeHtml(data.source||'local_fallback')}</small>`;
    }catch(e){
        out.innerHTML=`<div class="empty-state">${escapeHtml(e.message||'Image prompt failed')}</div>`;
    }
}
async function loadScheduledPage(){ const el=document.getElementById('scheduled-list'); if(!el) return; try{ const d=await api('/schedule/me'); el.innerHTML=(d.items||[]).map(i=>`<div class="mini-row"><span>${escapeHtml(i.content||'Scheduled item')}</span><strong class="status-badge">${i.status}</strong></div>`).join('') || '<div class="empty-state">No scheduled posts.</div>'; }catch(e){ el.innerHTML='<div class="empty-state">Login to manage schedules.</div>'; } }
async function schedulePostFromPage(e){ e.preventDefault(); try{ await api('/schedule/post',{method:'POST',body:JSON.stringify({content:document.getElementById('schedule-content').value,scheduled_at:new Date(document.getElementById('schedule-time').value).toISOString(),media_urls:[],hashtags:[],content_type:'post'})}); showToast('Post scheduled'); loadScheduledPage(); }catch(err){ showToast(err.message,'error'); } }
async function loadMarketplacePage(){ const grid=document.getElementById('marketplace-grid'); if(!grid) return; try{ const d=await api('/marketplace/products'); grid.innerHTML=(d.products||[]).map(p=>`<article class="product-card"><div class="product-media">${p.image_url?`<img src="${mediaUrl(p.image_url)}">`:'<i class="fas fa-box-open"></i>'}</div><h3>${escapeHtml(p.title)}</h3><p>${escapeHtml(p.category||'General')}</p><strong>${money(p.price)}</strong></article>`).join('') || '<div class="empty-state">No products yet.</div>'; }catch(e){ grid.innerHTML='<div class="empty-state">Unable to load products.</div>'; } }
async function loadMusicLibraryPage(){ const grid=document.getElementById('music-library-grid'); if(!grid) return; grid.innerHTML='<div class="loading"><div class="spinner"></div><span>Loading music...</span></div>'; try{ const tracks=await api('/music'); grid.innerHTML=(tracks||[]).map(t=>`<article class="music-page-card"><button class="music-play" onclick="previewMusic('${mediaUrl(t.audio_path)}', this)"><i class="fas fa-play"></i></button><div><h3>${escapeHtml(t.title)}</h3><p>${escapeHtml(t.artist||'Unknown artist')} ${t.is_trending?' • Trending':''}</p><small>${escapeHtml(t.category||'Music')} • ${t.use_count||0} uses</small></div></article>`).join('') || '<div class="empty-state">No music tracks yet. Upload one from the reel music picker.</div>'; }catch(e){ grid.innerHTML='<div class="empty-state">Unable to load music library.</div>'; } }
async function loadLivePage(){ const grid=document.getElementById('live-grid'); if(!grid) return; grid.innerHTML='<div class="loading"><div class="spinner"></div><span>Loading live streams...</span></div>'; try{ const d=await api('/live/active'); grid.innerHTML=(d.lives||[]).map(l=>`<article class="live-card"><div class="live-badge">LIVE</div><h3>${escapeHtml(l.title)}</h3><p>${escapeHtml(l.description||'SocialHub Live')}</p><div class="mini-row"><span>@${escapeHtml(l.host?.username||'creator')}</span><strong>${l.viewer_count||0} viewers</strong></div><button class="btn btn-primary" onclick="showGoLiveModal()">Open Live Studio</button></article>`).join('') || '<div class="empty-state"><i class="fas fa-video fa-3x"></i><h3>No one is live right now</h3><p>Start a live stream with camera preview, chat, likes, and gifts.</p><button class="btn btn-primary" onclick="showGoLiveModal()">Go Live</button></div>'; }catch(e){ grid.innerHTML='<div class="empty-state">Login to view live streams.</div>'; } }
async function loadCollectionsPage(){ const grid=document.getElementById('collections-grid'); if(!grid) return; try{ const d=await api('/collections'); const items=d.collections||d||[]; grid.innerHTML=(Array.isArray(items)?items:[]).map(c=>`<article class="collection-card"><i class="fas fa-bookmark"></i><h3>${escapeHtml(c.name||'Collection')}</h3><p>${escapeHtml(c.description||'Saved posts and reels')}</p></article>`).join('') || '<div class="empty-state">No collections yet. Save posts and create collections from Saved.</div>'; }catch(e){ grid.innerHTML='<div class="empty-state">Login to manage collections.</div>'; } }
async function createProductFromPage(e){ e.preventDefault(); try { const f=new FormData(); ['title','price','category','description'].forEach(k=>f.append(k,document.getElementById('product-'+k).value)); const img=document.getElementById('product-image').files[0]; if(img) f.append('image',img); await fetchChecked(`${API}/marketplace/products`,{method:'POST',headers:getMultipartHeaders(),body:f,multipart:true}); closeModal('product-modal'); showToast('Product added', 'success'); loadMarketplacePage(); } catch(err){ showToast(err.message,'error'); } }
async function loadCollabsPage(){ const grid=document.getElementById('collabs-grid'); if(!grid) return; try{ const d=await api('/collabs'); grid.innerHTML=(d.offers||[]).map(o=>`<article class="collab-card"><span class="status-badge">${escapeHtml(o.status)}</span><h3>${escapeHtml(o.title)}</h3><p>${escapeHtml(o.description)}</p><div>${escapeHtml(o.budget||'Open budget')}</div><button class="btn btn-primary btn-sm" onclick="applyCollab('${o.id}')">Apply</button></article>`).join('') || '<div class="empty-state">No collabs yet.</div>'; }catch(e){ grid.innerHTML='<div class="empty-state">Unable to load collabs.</div>'; } }
async function createCollabFromPage(e){ e.preventDefault(); await api('/collabs',{method:'POST',body:JSON.stringify({title:document.getElementById('collab-title').value,description:document.getElementById('collab-description').value,budget:document.getElementById('collab-budget').value,category:document.getElementById('collab-category').value})}); closeModal('collab-modal'); showToast('Collab posted'); loadCollabsPage(); }
async function applyCollab(id){ try{ await api(`/collabs/${id}/apply`,{method:'POST',body:JSON.stringify({message:'I am interested in this collaboration.'})}); showToast('Application submitted'); }catch(e){ showToast(e.message,'error'); } }
function instagramAccountLabel(account){
    if (!account) return 'Instagram account';
    const username = account.username || account.handle || account.name;
    return username ? `@${escapeHtml(String(username).replace(/^@/, ''))}` : 'Instagram account';
}
async function loadInstagramStatus(){
    const el=document.getElementById('instagram-status');
    try{
        const d=await api('/instagram/account');
        const account=d.account||{};
        if(el) el.innerHTML=d.connected
            ? `<div class="mini-row"><span>Status</span><strong>Connected</strong></div><div class="mini-row"><span>Account</span><strong>${instagramAccountLabel(account)}</strong></div><div class="mini-row"><span>SocialHub</span><small>Imported data will show this username, not the private Instagram ID.</small></div>`
            : '<div class="mini-row"><span>Status</span><strong>Not connected</strong></div>';
    }catch(e){
        if(el) el.innerHTML='<div class="mini-row"><span>Status</span><strong>Login required</strong></div>';
    }
}
async function loadInstagramStudioPage(){ await loadInstagramStatus(); const grid=document.getElementById('instagram-media-grid'); if(!grid) return; try{ const d=await api('/instagram/media'); const accountLabel=instagramAccountLabel(d.account); grid.innerHTML=(d.media||[]).map(m=>`<div class="media-card"><img src="${m.thumbnail_url||m.media_url||'/static/images/default_cover.svg'}"><strong>${accountLabel}</strong><small>${escapeHtml(m.media_type||'Instagram media')}</small><div class="btn-group"><button class="btn btn-sm btn-outline" onclick="api('/instagram/import/${m.id}/post',{method:'POST'}).then(()=>showToast('Imported as post'))">Post</button><button class="btn btn-sm btn-outline" onclick="api('/instagram/import/${m.id}/reel',{method:'POST'}).then(()=>showToast('Imported as reel'))">Reel</button></div></div>`).join('') || '<div class="empty-state">No Instagram media imported yet.</div>'; }catch(e){ grid.innerHTML='<div class="empty-state">Connect Instagram to import media.</div>'; } }

async function loadSuggestedUsers() {
    const el = document.getElementById('suggested-users-list');
    if (!el || !isLoggedIn()) return;
    try {
        const users = await api('/users/suggestions');
        el.innerHTML = (users || []).slice(0, 5).map(u => `<div class="suggested-user"><a href="/profile/${u.username}"><img src="${getProfilePic(u)}" class="avatar-sm" alt=""><span><strong>${escapeHtml(u.username)}</strong><small>${escapeHtml(u.full_name || 'Suggested for you')}</small></span></a><button class="btn btn-sm btn-primary" onclick="api('/follow/${u.id}',{method:'POST'}).then(()=>showToast('Followed','success')).catch(e=>showToast(e.message,'error'))">Follow</button></div>`).join('') || '<div class="empty-mini">No suggestions yet.</div>';
    } catch(e) { el.innerHTML = '<div class="empty-mini">Login to see suggestions.</div>'; }
}

// ==================== DELETE CONFIRMATION + LIVE CAMERA ====================
function toggleContentMenu(btn) { document.querySelectorAll('.content-menu-dropdown').forEach(m => { if (m !== btn.nextElementSibling) m.classList.add('hidden'); }); btn.nextElementSibling?.classList.toggle('hidden'); }
function confirmDelete(text = 'Are you sure you want to delete this?') { return new Promise(resolve => { const wrap=document.createElement('div'); wrap.className='confirm-backdrop active'; wrap.innerHTML=`<div class="confirm-modal"><h3>${escapeHtml(text)}</h3><div class="modal-actions"><button class="btn btn-outline" data-cancel>Cancel</button><button class="btn btn-danger" data-delete>Delete</button></div></div>`; document.body.appendChild(wrap); wrap.querySelector('[data-cancel]').onclick=()=>{wrap.remove();resolve(false);}; wrap.querySelector('[data-delete]').onclick=()=>{wrap.remove();resolve(true);}; }); }
async function deleteContent(type, id) { if (!(await confirmDelete())) return; const endpoints={post:`/posts/${id}`,reel:`/reels/${id}`,story:`/stories/${id}`,comment:`/comments/${id}`,message:`/chats/messages/${id}`,live:`/live/${id}`,marketplace:`/marketplace/${id}`}; try{ await api(endpoints[type],{method:'DELETE'}); document.getElementById(`${type}-${id}`)?.remove(); showToast('Deleted successfully','success'); if(type==='post'&&document.getElementById('feed')) loadFeed(); if(type==='reel'&&document.getElementById('reels-container')) loadReels(); }catch(e){ showToast(e.message||'Delete failed','error'); } }

let liveStream = null, liveSession = null, liveSocket = null, liveFacingMode = 'user', liveMuted = false;
function showGoLiveModal(){ if(!requireLoginForUpload()) return; let modal=document.getElementById('go-live-modal'); if(!modal){ modal=document.createElement('div'); modal.id='go-live-modal'; modal.className='modal-overlay active'; modal.innerHTML=`<div class="modal live-modal"><button class="modal-close" onclick="endLive(true)">&times;</button><h2><i class="fas fa-video"></i> Go Live</h2><div class="live-preview-wrap"><video id="live-preview" autoplay muted playsinline></video><div id="live-placeholder" class="live-placeholder"><i class="fas fa-camera"></i><p>Camera is off</p></div><div class="hearts-layer" id="live-hearts"></div></div><input id="live-title" class="form-control" placeholder="Live title" value="Live from SocialHub"><textarea id="live-description" class="form-control" placeholder="Description"></textarea><div class="live-toolbar"><button class="btn btn-outline" onclick="turnCameraOn()">Start camera</button><button class="btn btn-outline" onclick="stopLiveCamera()">Stop camera</button><button class="btn btn-outline" onclick="toggleLiveMute()">Mute/unmute mic</button><button class="btn btn-outline" onclick="switchLiveCamera()">Switch camera</button></div><div class="live-status"><span id="live-error"></span><span><i class="fas fa-eye"></i> <b id="live-viewers">0</b></span></div><div class="modal-actions"><button class="btn btn-primary" onclick="startLiveSession()">Start Live</button><button class="btn btn-danger" onclick="endLive()">End Live</button></div><div id="live-chat" class="live-chat-panel"></div><div class="comment-form"><input id="live-chat-input" placeholder="Say something..." onkeypress="if(event.key==='Enter')sendLiveChat()"><button class="btn btn-primary btn-sm" onclick="sendLiveChat()">Send</button><button class="btn btn-outline btn-sm" onclick="sendLiveLike()">❤️</button><button class="btn btn-outline btn-sm" onclick="sendLiveGift()">🎁</button></div></div>`; document.body.appendChild(modal);} modal.classList.add('active'); }
async function turnCameraOn(){ const err=document.getElementById('live-error'); try{ stopLiveCamera(); liveStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:liveFacingMode},audio:true}); const video=document.getElementById('live-preview'); if(video){ video.srcObject=liveStream; video.classList.add('active'); } document.getElementById('live-placeholder')?.classList.add('hidden'); err.textContent=''; broadcastCameraStatus(true); }catch(e){ if(err) err.textContent=e.name==='NotFoundError'?'Camera not found. Showing placeholder.':'Camera/microphone permission denied or unavailable.'; showToast(err?.textContent||'Camera unavailable','error'); } }
function stopLiveCamera(){ if(liveStream){ liveStream.getTracks().forEach(t=>t.stop()); liveStream=null; } const video=document.getElementById('live-preview'); if(video){ video.srcObject=null; video.classList.remove('active'); } document.getElementById('live-placeholder')?.classList.remove('hidden'); broadcastCameraStatus(false); }
function toggleLiveMute(){ liveMuted=!liveMuted; liveStream?.getAudioTracks().forEach(t=>t.enabled=!liveMuted); showToast(liveMuted?'Microphone muted':'Microphone unmuted'); broadcastCameraStatus(!!liveStream); }
async function switchLiveCamera(){ liveFacingMode=liveFacingMode==='user'?'environment':'user'; await turnCameraOn(); }
async function startLiveSession(){ try{ const title=document.getElementById('live-title')?.value||'Live from SocialHub'; const description=document.getElementById('live-description')?.value||''; const data=await api('/live/start',{method:'POST',body:JSON.stringify({title,description,camera_enabled:!!liveStream,microphone_enabled:!liveMuted})}); liveSession=data.live; await api(`/live/${liveSession.id}/join`,{method:'POST'}); connectLiveSocket(); showToast('Live started','success'); }catch(e){ showToast(e.message||'Could not start live','error'); } }
function connectLiveSocket(){ if(!liveSession||liveSocket) return; const protocol=location.protocol==='https:'?'wss':'ws'; liveSocket=new WebSocket(`${protocol}://${location.host}/ws/live/${liveSession.id}?token=${encodeURIComponent(token)}`); liveSocket.onmessage=e=>{ const d=JSON.parse(e.data||'{}'); if(d.type==='chat_message') appendLiveChat(`@${d.username}: ${d.message}`); if(d.type==='viewer_count') document.getElementById('live-viewers').textContent=d.viewer_count; if(d.type==='live_like') animateHeart(); if(d.type==='live_gift') appendLiveChat('🎁 Gift received!'); if(d.type==='live_ended') endLive(true); }; liveSocket.onclose=()=>liveSocket=null; }
function appendLiveChat(text){ const panel=document.getElementById('live-chat'); if(panel){ panel.insertAdjacentHTML('beforeend',`<div>${escapeHtml(text)}</div>`); panel.scrollTop=panel.scrollHeight; } }
function sendLiveChat(){ const input=document.getElementById('live-chat-input'); if(!input?.value.trim()||!liveSocket) return; liveSocket.send(JSON.stringify({type:'chat_message',message:input.value.trim()})); input.value=''; }
async function sendLiveLike(){ if(liveSession) await api(`/live/${liveSession.id}/like`,{method:'POST'}).catch(()=>{}); animateHeart(); }
async function sendLiveGift(){ if(liveSession) await api(`/live/${liveSession.id}/gift`,{method:'POST',body:JSON.stringify({gift:'star'})}).catch(()=>{}); appendLiveChat('🎁 Gift sent!'); }
function animateHeart(){ const layer=document.getElementById('live-hearts'); if(!layer) return; const h=document.createElement('span'); h.textContent='❤️'; h.className='floating-heart'; h.style.left=Math.random()*80+10+'%'; layer.appendChild(h); setTimeout(()=>h.remove(),1200); }
function broadcastCameraStatus(on){ if(liveSocket?.readyState===1) liveSocket.send(JSON.stringify({type:'camera_status',camera_enabled:on,microphone_enabled:!liveMuted})); }
async function endLive(closeOnly=false){ if(liveSession&&!closeOnly) await api(`/live/end/${liveSession.id}`,{method:'POST'}).catch(()=>{}); stopLiveCamera(); liveSocket?.close(); liveSocket=null; liveSession=null; document.getElementById('go-live-modal')?.classList.remove('active'); }
window.addEventListener('beforeunload', stopLiveCamera);

// ==================== VOICE & GUJARATI TRANSLATION ====================
// Voice recognition state
let voiceRecognition = null;
let isVoiceRecording = false;
let voiceRecognitionLang = 'gu-IN'; // Default: Gujarati

// Available language codes for speech recognition
const VOICE_LANGS = {
    'gu-IN': 'Gujarati (ગુજરાતી)',
    'hi-IN': 'Hindi (हिन्दी)',
    'en-IN': 'English (India)',
    'en-US': 'English (US)'
};

// Available TTS languages
const TTS_LANGS = {
    'gu': { name: 'Gujarati (ગુજરાતી)', regex: /\u0A80-\u0AFF/ },
    'hi': { name: 'Hindi (हिन्दी)', regex: /\u0900-\u097F/ },
    'en': { name: 'English', regex: /a-zA-Z/ }
};

/**
 * Open the Translate & Voice modal
 */
/**
 * Copy translation to clipboard
 */
function copyTranslation() {
    const output = document.getElementById('translate-output');
    if (!output || !output.value.trim()) {
        showToast('Nothing to copy', 'warning');
        return;
    }
    navigator.clipboard.writeText(output.value).then(() => {
        showToast('Translation copied to clipboard', 'success');
    }).catch(() => {
        // Fallback for older browsers
        output.select();
        document.execCommand('copy');
        showToast('Translation copied', 'success');
    });
}

/**
 * Open the Translate & Voice modal
 */
function openTranslateModal() {
    const modal = document.getElementById('translate-modal');
    if (modal) {
        modal.classList.add('active');
        // Reset fields
        document.getElementById('translate-input').value = '';
        document.getElementById('translate-output').value = '';
        document.getElementById('translate-source-lang').value = 'auto';
        document.getElementById('translate-target-lang').value = 'gu';
        document.getElementById('translate-status').textContent = '';
    } else {
        showToast('Translation feature not available on this page', 'warning');
    }
}

/**
 * Translate text between English and Gujarati using the backend API
 */
async function handleTranslate() {
    const input = document.getElementById('translate-input');
    const output = document.getElementById('translate-output');
    const status = document.getElementById('translate-status');
    const sourceLang = document.getElementById('translate-source-lang').value;
    const targetLang = document.getElementById('translate-target-lang').value;
    
    const text = input.value.trim();
    if (!text) {
        showToast('Please enter text to translate', 'warning');
        return;
    }
    
    status.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Translating...';
    output.value = '';
    
    try {
        const data = await api('/translate', {
            method: 'POST',
            body: JSON.stringify({
                text: text,
                source_lang: sourceLang,
                target_lang: targetLang
            })
        });
        
        output.value = data.translated_text;
        status.innerHTML = data.using_fallback 
            ? '<span style="color:var(--warning)"><i class="fas fa-info-circle"></i> Dictionary translation (AI not configured)</span>'
            : '<span style="color:var(--success)"><i class="fas fa-check-circle"></i> Translation complete</span>';
    } catch (e) {
        status.innerHTML = `<span style="color:var(--danger)"><i class="fas fa-exclamation-circle"></i> ${escapeHtml(e.message)}</span>`;
    }
}

/**
 * Swap source and target languages
 */
function swapTranslateLanguages() {
    const source = document.getElementById('translate-source-lang');
    const target = document.getElementById('translate-target-lang');
    
    // Don't swap if source is 'auto'
    if (source.value === 'auto') {
        source.value = target.value;
        target.value = 'en';
        return;
    }
    
    const temp = source.value;
    source.value = target.value;
    target.value = temp;
}

/**
 * Speak the translated or input text using Web Speech API (Text-to-Speech)
 */
function speakText(elementId) {
    const text = document.getElementById(elementId).value.trim();
    if (!text) {
        showToast('No text to speak', 'warning');
        return;
    }
    
    // Stop any ongoing speech
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Detect language for proper pronunciation
    const hasGujarati = /[\u0A80-\u0AFF]/.test(text);
    const hasHindi = /[\u0900-\u097F]/.test(text);
    
    if (hasGujarati) {
        utterance.lang = 'gu-IN';
    } else if (hasHindi) {
        utterance.lang = 'hi-IN';
    } else {
        utterance.lang = 'en-IN';
    }
    
    utterance.rate = 0.9; // Slightly slower for clarity
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    
    window.speechSynthesis.speak(utterance);
    
    showToast('🔊 Speaking...', 'info');
}

/**
 * Start/Stop voice recording using Web Speech API (Speech-to-Text)
 */
function toggleVoiceRecording(targetElementId) {
    const btn = document.getElementById('voice-record-btn');
    const statusEl = document.getElementById('voice-status');
    
    // Check if browser supports SpeechRecognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showToast('Voice recognition is not supported in your browser. Try Chrome.', 'error');
        return;
    }
    
    if (isVoiceRecording) {
        // Stop recording
        if (voiceRecognition) {
            voiceRecognition.stop();
        }
        isVoiceRecording = false;
        if (btn) {
            btn.innerHTML = '<i class="fas fa-microphone"></i> Record';
            btn.classList.remove('recording');
        }
        if (statusEl) statusEl.textContent = '';
        return;
    }
    
    // Start recording
    voiceRecognition = new SpeechRecognition();
    voiceRecognition.continuous = false;
    voiceRecognition.interimResults = true;
    voiceRecognition.lang = document.getElementById('voice-lang-select')?.value || 'gu-IN';
    
    voiceRecognition.onstart = () => {
        isVoiceRecording = true;
        if (btn) {
            btn.innerHTML = '<i class="fas fa-stop"></i> Stop';
            btn.classList.add('recording');
        }
        if (statusEl) {
            statusEl.innerHTML = '<i class="fas fa-circle pulse"></i> Listening... Speak now';
            statusEl.className = 'voice-status listening';
        }
    };
    
    voiceRecognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        
        const inputEl = document.getElementById(targetElementId);
        if (inputEl) {
            if (finalTranscript) {
                inputEl.value += finalTranscript;
            }
            // Show interim results as placeholder
            if (interimTranscript) {
                inputEl.placeholder = interimTranscript + '...';
            }
        }
        
        if (statusEl && finalTranscript) {
            statusEl.innerHTML = `<i class="fas fa-check-circle"></i> Recognized: "${finalTranscript}"`;
            statusEl.className = 'voice-status recognized';
        }
    };
    
    voiceRecognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        isVoiceRecording = false;
        if (btn) {
            btn.innerHTML = '<i class="fas fa-microphone"></i> Record';
            btn.classList.remove('recording');
        }
        if (statusEl) {
            let errorMsg = 'Voice recognition error';
            if (event.error === 'no-speech') errorMsg = 'No speech detected. Please try again.';
            else if (event.error === 'audio-capture') errorMsg = 'No microphone found. Check your device.';
            else if (event.error === 'not-allowed') errorMsg = 'Microphone access denied. Allow microphone in browser settings.';
            else if (event.error === 'language-not-supported') errorMsg = 'Language not supported for voice recognition.';
            statusEl.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${errorMsg}`;
            statusEl.className = 'voice-status error';
        }
    };
    
    voiceRecognition.onend = () => {
        isVoiceRecording = false;
        if (btn) {
            btn.innerHTML = '<i class="fas fa-microphone"></i> Record';
            btn.classList.remove('recording');
        }
        const statusEl2 = document.getElementById('voice-status');
        if (statusEl2 && !statusEl2.classList.contains('error')) {
            setTimeout(() => {
                statusEl2.textContent = '';
                statusEl2.className = 'voice-status';
            }, 3000);
        }
    };
    
    try {
        voiceRecognition.start();
    } catch (e) {
        showToast('Failed to start voice recognition: ' + e.message, 'error');
        isVoiceRecording = false;
        if (btn) {
            btn.innerHTML = '<i class="fas fa-microphone"></i> Record';
            btn.classList.remove('recording');
        }
    }
}

/**
 * Change voice recognition language
 */
function changeVoiceLang() {
    const select = document.getElementById('voice-lang-select');
    if (select) {
        voiceRecognitionLang = select.value;
        showToast(`Voice language set to ${VOICE_LANGS[voiceRecognitionLang] || voiceRecognitionLang}`, 'info');
    }
}

/**
 * Initialize voice features on page load
 */
function initVoiceFeatures() {
    // Check for SpeechRecognition support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        const recordBtns = document.querySelectorAll('.voice-record-btn');
        recordBtns.forEach(btn => {
            btn.disabled = true;
            btn.title = 'Voice recognition not supported in this browser';
        });
    }
    
    // Check for SpeechSynthesis support
    if (!window.speechSynthesis) {
        const speakBtns = document.querySelectorAll('.speak-btn');
        speakBtns.forEach(btn => {
            btn.disabled = true;
            btn.title = 'Text-to-speech not supported in this browser';
        });
    }
}

// Auto-init voice features when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initVoiceFeatures);
} else {
    initVoiceFeatures();
}
