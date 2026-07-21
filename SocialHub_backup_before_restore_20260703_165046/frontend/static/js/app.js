// @ts-nocheck
// ========================================================================
// SocialHub - Modern Social Media UI v4.0
// ========================================================================

const API = '/api';
let currentUser = null;
let token = localStorage.getItem('token');
let refreshToken = localStorage.getItem('refreshToken');
let activeProfileUserId = null;

const AUTH_FREE_PATHS = ['/login', '/register', '/forgot-password', '/reset-password'];
const FEATURE_REGISTRY = [
    { key: 'home', label: 'Home', href: '/', icon: 'fa-house', public: true },
    { key: 'posts', label: 'Posts', href: '/posts', icon: 'fa-newspaper', public: true },
    { key: 'reels', label: 'Reels', href: '/reels', icon: 'fa-clapperboard', public: true },
    { key: 'stories', label: 'Stories', href: '/stories', icon: 'fa-circle-play' },
    { key: 'creator', label: 'Creator Dashboard', href: '/creator-dashboard', icon: 'fa-chart-pie' },
    { key: 'scheduled', label: 'Scheduled', href: '/scheduled', icon: 'fa-calendar-days' },
    { key: 'marketplace', label: 'Marketplace', href: '/marketplace', icon: 'fa-store', public: true },
    { key: 'collabs', label: 'Collabs', href: '/collabs', icon: 'fa-handshake', public: true },
    { key: 'notifications', label: 'Notifications', href: '/notifications', icon: 'fa-bell', badge: 'notif-badge' },
    { key: 'chat', label: 'Chat', href: '/chat', icon: 'fa-envelope' },
    { key: 'search', label: 'Search', href: '/search', icon: 'fa-magnifying-glass', public: true },
    { key: 'instagram', label: 'Instagram Studio', href: '/instagram-studio', icon: 'fa-chart-line' },
    { key: 'connect-instagram', label: 'Connect Instagram', href: '/connect-instagram', icon: 'fa-brands fa-instagram' },
    { key: 'data', label: 'Data Studio', href: '/data-studio', icon: 'fa-database' },
    { key: 'bookmarks', label: 'Bookmarks', href: '/bookmarks', icon: 'fa-bookmark' },
    { key: 'settings', label: 'Settings', href: '/settings', icon: 'fa-gear' },
    { key: 'admin', label: 'Admin', href: '/admin', icon: 'fa-shield-halved', adminOnly: true },
];

function toast(message, type = 'info') {
    let el = document.getElementById('global-toast');
    if (!el) {
        el = document.createElement('div');
        el.id = 'global-toast';
        document.body.appendChild(el);
    }
    el.textContent = message;
    el.className = `global-toast show ${type}`;
    setTimeout(() => el.classList.remove('show'), 3500);
}

// ========================================================================
// MODAL FUNCTIONS FOR NEW UI
// ========================================================================
function showCreatePost() {
    const modal = document.getElementById('create-post-modal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeCreatePostModal() {
    const modal = document.getElementById('create-post-modal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
        // Clear form
        const textarea = document.getElementById('post-content');
        const fileInput = document.getElementById('post-files');
        if (textarea) textarea.value = '';
        if (fileInput) fileInput.value = '';
    }
}

async function handleCreatePost(event) {
    event.preventDefault();
    const content = document.getElementById('post-content').value;
    const fileInput = document.getElementById('post-files');
    const files = fileInput?.files || [];
    const submitBtn = event.target.querySelector('button[type="submit"]');
    
    if (!content.trim() && files.length === 0) {
        toast('Please write something or upload a file!', 'error');
        return;
    }
    
    setButtonLoading(submitBtn, true);
    
    try {
        const formData = new FormData();
        formData.append('content', content);
        
        // Add any files
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        
        const response = await fetch(`${API}/posts/upload`, {
            method: 'POST',
            headers: getMultipartHeaders(),
            body: formData,
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Failed to create post' }));
            throw new Error(error.detail || 'Failed to create post');
        }
        
        toast('Post created successfully!', 'success');
        closeCreatePostModal();
        
        // Refresh feed if on posts page
        if (window.location.pathname === '/posts' || window.location.pathname === '/') {
            setTimeout(() => window.location.reload(), 500);
        }
    } catch (error) {
        console.error('Error creating post:', error);
        toast(error.message || 'Failed to create post', 'error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
}

function isLoggedIn() {
    return !!token;
}

function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// Close modal on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('create-post-modal');
        if (modal && modal.classList.contains('active')) {
            closeCreatePostModal();
        }
    }
});

// Close modal on overlay click
document.addEventListener('click', (e) => {
    const modal = document.getElementById('create-post-modal');
    if (modal && e.target === modal.querySelector('.modal-overlay')) {
        closeCreatePostModal();
    }
});

// ========================================================================
// 1. AUTH UTILITIES
// ========================================================================
function setTokens(access, refresh) {
    token = access;
    refreshToken = refresh;
    localStorage.setItem('token', access);
    localStorage.setItem('refreshToken', refresh);
}

function clearTokens() {
    token = null;
    refreshToken = null;
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
}

function isLoggedIn() {
    return !!token;
}

function getHeaders() {
    return token
        ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        : { 'Content-Type': 'application/json' };
}

function getMultipartHeaders() {
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function api(path, opts = {}) {
    const url = API + path;
    const headers = opts.multipart ? getMultipartHeaders() : getHeaders();
    try {
        const res = await fetch(url, { headers, ...opts });
        if (res.status === 401 && refreshToken) {
            const refreshed = await refreshAccessToken();
            if (refreshed) return api(path, opts);
            clearTokens();
            window.location.href = '/login';
            return null;
        }
        if (!res.ok) {
            const e = await res.json().catch(() => ({}));
            throw new Error(e.detail || 'Request failed');
        }
        return res.json();
    } catch (e) {
        console.error('API Error:', e);
        if (!opts.silent) toast(e.message || 'Something went wrong. Please try again.', 'error');
        throw e;
    }
}

async function refreshAccessToken() {
    try {
        const res = await fetch(`${API}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (res.ok) {
            const data = await res.json();
            setTokens(data.access_token, data.refresh_token);
            return true;
        }
    } catch (e) {}
    return false;
}

// ========================================================================
// 2. MEDIA URL HELPER - Fixes double uploads issue and broken images
// ========================================================================
function getMediaUrl(path) {
    if (!path || path === 'undefined' || path === 'null') return '/static/images/default-avatar.png';
    if (path.startsWith('http') || path.startsWith('/static/')) return path;
    let clean = String(path).replace(/\\/g, '/').replace(/^\/+/, '');
    clean = clean.replace(/^(\.\.\/)+/, '').replace(/\/{2,}/g, '/').replace(/^uploads\//, '');
    clean = clean
        .replace(/^(post_images|videos)\//, 'posts/')
        .replace(/^profile_pics\//, 'profiles/')
        .replace(/^cover_photos\//, 'covers/')
        .replace(/^(frontend\/)?uploads\//, '')
        .replace(/^(backend\/)?frontend\/uploads\//, '')
        .replace(/\/post_images\/post_images\//g, '/posts/')
        .replace(/\/profile_pics\/profile_pics\//g, '/profiles/')
        .replace(/\/cover_photos\/cover_photos\//g, '/covers/')
        .replace(/\/posts\/posts\//g, '/posts/')
        .replace(/\/profiles\/profiles\//g, '/profiles/')
        .replace(/\/covers\/covers\//g, '/covers/')
        .replace(/^(posts|profiles|covers|reels|stories|chat_files|marketplace|original_media)\/\1\//, '$1/');
    while (clean.startsWith('uploads/')) clean = clean.slice('uploads/'.length);
    return '/uploads/' + clean;
}

function getCoverUrl(path) {
    if (!path || path === 'undefined' || path === 'null' || String(path).startsWith('default')) return '/static/images/default-cover.png';
    return getMediaUrl(path);
}

// ========================================================================
// 3. PAGE LOAD ANIMATIONS
// ========================================================================
function animatePageLoad() {
    document.body.classList.add('fade-in');
    const containers = document.querySelectorAll('.container, .container-wide');
    containers.forEach((el, i) => {
        el.style.animationDelay = `${i * 0.1}s`;
    });
}

function ensureGlobalShell() {
    if (!document.getElementById('global-toast')) {
        const toastEl = document.createElement('div');
        toastEl.id = 'global-toast';
        toastEl.className = 'global-toast';
        document.body.appendChild(toastEl);
    }

    if (!document.getElementById('create-post-modal')) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = 'create-post-modal';
        modal.innerHTML = `<div class="modal-content">
            <div class="modal-header">
                <h2><i class="fas fa-plus-circle"></i> Create Post</h2>
                <button class="modal-close" type="button" onclick="closeModal('create-post-modal')">&times;</button>
            </div>
            <form class="post-form" onsubmit="handleCreatePost(event)">
                <textarea id="post-content" placeholder="What's happening? Share a moment..." rows="5"></textarea>
                <input type="file" id="post-files" multiple accept="image/*,video/*" onchange="previewFiles(this)">
                <div id="upload-preview" class="upload-preview"></div>
                <button type="submit" class="btn btn-primary btn-block"><i class="fas fa-paper-plane"></i> Publish</button>
            </form>
        </div>`;
        document.body.appendChild(modal);
    } else {
        const fileInput = document.getElementById('post-files');
        if (fileInput && !fileInput.getAttribute('onchange')) fileInput.setAttribute('onchange', 'previewFiles(this)');
        const form = document.querySelector('#create-post-modal form');
        if (form && !document.getElementById('upload-preview')) {
            const preview = document.createElement('div');
            preview.id = 'upload-preview';
            preview.className = 'upload-preview';
            fileInput?.insertAdjacentElement('afterend', preview);
        }
    }

    if (!document.getElementById('edit-post-modal')) {
        const editModal = document.createElement('div');
        editModal.className = 'modal';
        editModal.id = 'edit-post-modal';
        editModal.innerHTML = `<div class="modal-content">
            <div class="modal-header">
                <h2><i class="fas fa-pen-to-square"></i> Edit Post</h2>
                <button class="modal-close" type="button" onclick="closeModal('edit-post-modal')">&times;</button>
            </div>
            <form class="post-form" onsubmit="savePostEdit(event)">
                <input type="hidden" id="edit-post-id">
                <textarea id="edit-post-content" placeholder="Update your caption..." rows="5"></textarea>
                <input id="edit-post-hashtags" placeholder="hashtags, comma, separated">
                <button type="submit" class="btn btn-primary btn-block"><i class="fas fa-save"></i> Save Changes</button>
            </form>
        </div>`;
        document.body.appendChild(editModal);
    }

    if (!document.getElementById('reel-comments-modal')) {
        const reelModal = document.createElement('div');
        reelModal.className = 'modal reel-comments-modal';
        reelModal.id = 'reel-comments-modal';
        reelModal.innerHTML = `<div class="modal-content reel-comments-sheet">
            <div class="modal-header">
                <h2><i class="fas fa-comments"></i> Reel comments</h2>
                <button class="modal-close" type="button" onclick="closeModal('reel-comments-modal')">&times;</button>
            </div>
            <div id="reel-comments-content" class="reel-comments-content"></div>
        </div>`;
        document.body.appendChild(reelModal);
    }

    if (!document.getElementById('comments-modal')) {
        const commentsModal = document.createElement('div');
        commentsModal.className = 'modal comments-drawer-modal';
        commentsModal.id = 'comments-modal';
        commentsModal.innerHTML = `<div class="modal-content comments-drawer">
            <div class="modal-header"><h2><i class="fas fa-comments"></i> Comments</h2><button class="modal-close" type="button" onclick="closeModal('comments-modal')">&times;</button></div>
            <div id="comments-content"></div>
        </div>`;
        document.body.appendChild(commentsModal);
    }

    document.querySelectorAll('.modal').forEach((modal) => {
        if (modal.dataset.shellReady) return;
        modal.dataset.shellReady = 'true';
        modal.addEventListener('click', (event) => {
            if (event.target === modal) modal.classList.remove('active');
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') document.querySelectorAll('.modal.active, #story-viewer.active').forEach((el) => el.classList.remove('active'));
    });
}

function closeModal(id) {
    document.getElementById(id)?.classList.remove('active');
}

function setActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('#nav-links a, .nav-links a, #mobile-bottom-nav a').forEach((link) => {
        const href = link.getAttribute('href');
        if (!href || href === '#') return;
        const isActive = href === path || (href !== '/' && path.startsWith(href));
        link.classList.toggle('active', isActive);
    });
}

function buildTopSearchBar() {
    if (document.getElementById('global-action-bar') || AUTH_FREE_PATHS.includes(window.location.pathname)) return;
    const bar = document.createElement('div');
    bar.id = 'global-action-bar';
    bar.className = 'global-action-bar';
    bar.innerHTML = `<form onsubmit="event.preventDefault(); const q=this.querySelector('input').value.trim(); if(q){ window.location.href='/search?q=' + encodeURIComponent(q); }">
        <i class="fas fa-search"></i><input aria-label="Search SocialHub" placeholder="Search creators, posts, #tags...">
    </form><div class="global-actions"><button class="btn btn-outline btn-sm" onclick="toggleTheme()"><i class="fas fa-circle-half-stroke"></i> Theme</button><button class="btn btn-primary btn-sm" onclick="showCreatePost()"><i class="fas fa-plus"></i> Create</button></div>`;
    document.body.insertBefore(bar, document.body.firstChild?.nextSibling || document.body.firstChild);
}

function ensureMobileBottomNav() {
    if (document.getElementById('mobile-bottom-nav') || AUTH_FREE_PATHS.includes(window.location.pathname)) return;
    const nav = document.createElement('nav');
    nav.id = 'mobile-bottom-nav';
    nav.className = 'mobile-bottom-nav';
    nav.innerHTML = renderFeatureLinks({ mobile: true, includePublicOnly: !isLoggedIn() });
    document.body.appendChild(nav);
}

async function hydrateCurrentUser() {
    if (!isLoggedIn() || currentUser) return currentUser;
    try {
        currentUser = await api('/auth/me');
    } catch (e) {}
    return currentUser;
}

// ========================================================================
// 4. NAVIGATION
// ========================================================================
function getVisibleFeatures({ includePublicOnly = false } = {}) {
    const isAdmin = currentUser && ['admin', 'moderator'].includes(String(currentUser.role || '').toLowerCase());
    return FEATURE_REGISTRY.filter((feature) => {
        if (feature.adminOnly && !isAdmin) return false;
        if (!isLoggedIn()) return !!feature.public;
        if (includePublicOnly) return !!feature.public;
        return true;
    });
}

function renderFeatureLinks({ mobile = false, includePublicOnly = false } = {}) {
    const features = getVisibleFeatures({ includePublicOnly });
    const createButton = isLoggedIn() ? `<button type="button" class="${mobile ? 'mobile-create' : 'btn btn-primary btn-sm'}" onclick="showCreatePost()" title="Create Post"><i class="fas fa-plus"></i>${mobile ? '' : ' Create'}</button>` : '';
    const links = features.map((feature) => `<a href="${feature.href}" class="${mobile ? '' : 'nav-icon'}" title="${feature.label}">
        <i class="fas ${feature.icon}"></i><span>${mobile ? feature.label : ''}</span>${feature.badge ? `<span id="${feature.badge}" class="badge hidden">0</span>` : ''}
    </a>`).join('');
    return mobile ? links + createButton : links + createButton;
}

function updateNav() {
    const nav = document.getElementById('nav-links');
    if (!nav) return;
    if (isLoggedIn()) {
        nav.innerHTML = `${renderFeatureLinks()}<div class="nav-avatar" id="nav-avatar"></div>`;
        loadUnreadCount();
        loadNavAvatar();
    } else {
        nav.innerHTML = `${renderFeatureLinks({ includePublicOnly: true })}<a href="/login" class="btn btn-primary btn-sm">Login</a><a href="/register" class="btn btn-outline btn-sm">Register</a>`;
    }
    const mobileNav = document.getElementById('mobile-bottom-nav');
    if (mobileNav) mobileNav.innerHTML = renderFeatureLinks({ mobile: true, includePublicOnly: !isLoggedIn() });
    setActiveNav();
}

async function loadNavAvatar() {
    try {
        const user = await api('/auth/me');
        currentUser = user;
        const av = document.getElementById('nav-avatar');
        if (av) {
            const src = getProfilePic(user);
            av.innerHTML = `<a href="/profile/${user.username}">
                <img src="${src}" alt="${user.username}" class="avatar-sm" onerror="this.onerror=null;this.src='/static/images/default-avatar.png'">
            </a>`;
        }
    } catch (e) {}
}

async function loadUnreadCount() {
    try {
        const data = await api('/notifications/unread-count');
        const badge = document.getElementById('notif-badge');
        if (badge && data.unread_count > 0) {
            badge.textContent = data.unread_count;
            badge.classList.remove('hidden');
            badge.classList.add('pulse');
        }
    } catch (e) {}
}

// ========================================================================
// 5. PROFILE PICTURE HELPER
// ========================================================================
function getProfilePic(user) {
    if (!user) return '/static/images/default-avatar.png';
    const raw = user.profile_picture || '';
    if (!raw || raw === 'undefined' || raw === 'null' || raw.includes('default')) {
        return '/static/images/default-avatar.png';
    }
    const url = getMediaUrl(raw);
    if (url.includes('undefined') || url.includes('null')) return '/static/images/default-avatar.png';
    return url;
}

// ========================================================================
// 6. TIME FORMATTER
// ========================================================================
function formatTime(dt) {
    if (!dt) return '';
    const d = new Date(dt);
    const now = new Date();
    const diff = (now - d) / 1000;
    
    // Always show exact time for posts
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const month = months[d.getMonth()];
    const day = d.getDate();
    const hours = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    
    // Show date only (no year) if it's this year, otherwise include year
    if (d.getFullYear() === now.getFullYear()) {
        return `${month} ${day} at ${hours}:${minutes}`;
    } else {
        return `${month} ${day}, ${d.getFullYear()} at ${hours}:${minutes}`;
    }
}

// ========================================================================
// 7. ESCAPE HTML - Security
// ========================================================================
function escapeHtml(t) {
    if (!t) return '';
    return String(t)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;')
        .replace(/\n/g, '<br>');
}

function renderContentWithHashtags(text) {
    const safe = escapeHtml(text || '');
    return safe.replace(/(^|\s)(#[\w]{2,50})/g, (match, space, tag) => `${space}<a class="hashtag" href="/search?q=${encodeURIComponent(tag.slice(1))}">${tag}</a>`);
}

// ========================================================================
// 8. BUTTON LOADING STATE
// ========================================================================
function setButtonLoading(btn, loading) {
    if (!btn) return;
    if (loading) {
        btn.classList.add('loading');
        btn.disabled = true;
    } else {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

// ========================================================================
// 9. AUTH PAGES
// ========================================================================
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errEl = document.getElementById('error');
    const successEl = document.getElementById('success');
    const btn = e.target.querySelector('button[type="submit"]');
    try {
        setButtonLoading(btn, true);
        const data = await api('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
        if (data.requires_2fa) {
            toast('2FA verification required', 'info');
            setButtonLoading(btn, false);
            return;
        }
        setTokens(data.access_token, data.refresh_token);
        if (successEl) {
            successEl.textContent = 'Login successful! Redirecting...';
            successEl.classList.remove('hidden');
        }
        toast('Logged in successfully', 'success');
        setTimeout(() => { window.location.href = '/'; }, 500);
    } catch (e) {
        if (errEl) {
            errEl.textContent = e.message;
            errEl.classList.remove('hidden');
            errEl.classList.add('shake');
        }
        setButtonLoading(btn, false);
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const fullName = document.getElementById('full_name')?.value || '';
    const errEl = document.getElementById('error');
    const btn = e.target.querySelector('button[type="submit"]');
    try {
        setButtonLoading(btn, true);
        const data = await api('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, username, password, full_name: fullName }),
        });
        setTokens(data.access_token, data.refresh_token);
        toast('Account created successfully', 'success');
        setTimeout(() => { window.location.href = '/'; }, 500);
    } catch (e) {
        if (errEl) {
            errEl.textContent = e.message;
            errEl.classList.remove('hidden');
        }
        setButtonLoading(btn, false);
    }
}

function logout() {
    if (token) api('/auth/logout', { method: 'POST' }).catch(() => {});
    clearTokens();
    toast('Logged out', 'success');
    window.location.href = '/login';
}

async function handleForgotPassword(e) {
    e.preventDefault();
    const email = document.getElementById('email')?.value || '';
    const errEl = document.getElementById('error');
    const successEl = document.getElementById('success');
    const btn = e.target.querySelector('button[type="submit"]');
    try {
        setButtonLoading(btn, true);
        const data = await api('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) });
        if (successEl) {
            successEl.textContent = data.message || 'If the email exists, a reset link has been sent.';
            successEl.classList.remove('hidden');
        }
        if (errEl) errEl.classList.add('hidden');
        toast('Reset instructions sent if the email exists', 'success');
    } catch (e) {
        if (errEl) { errEl.textContent = e.message; errEl.classList.remove('hidden'); }
        if (successEl) successEl.classList.add('hidden');
        toast(e.message, 'error');
    } finally {
        setButtonLoading(btn, false);
    }
}

async function resetPassword(e) {
    if (e) e.preventDefault();
    const params = new URLSearchParams(window.location.search);
    const tokenValue = document.getElementById('token')?.value;
    const resetToken = params.get('token') || (tokenValue && !tokenValue.includes('{{') ? tokenValue : '');
    const password = document.getElementById('password')?.value || '';
    const form = document.getElementById('reset-form');
    const btn = form?.querySelector('button[type="submit"]');
    if (!resetToken) return toast('Reset token missing. Open the reset link from your email/log.', 'error');
    try {
        setButtonLoading(btn, true);
        await api('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token: resetToken, password }) });
        if (form) form.innerHTML = '<p style="color:var(--success);text-align:center;">Password reset successfully! <a href="/login">Login</a></p>';
        toast('Password reset successfully', 'success');
    } catch (e) {
        toast(e.message || 'Reset failed', 'error');
    } finally {
        setButtonLoading(btn, false);
    }
}

// ========================================================================
// 10. PASSWORD SHOW/HIDE TOGGLE
// ========================================================================
function togglePassword(inputId, toggleBtn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === 'password') {
        input.type = 'text';
        toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i>';
    } else {
        input.type = 'password';
        toggleBtn.innerHTML = '<i class="fas fa-eye"></i>';
    }
}

// ========================================================================
// 11. HOME / FEED
// ========================================================================
async function loadFeed(page = 1) {
    const feed = document.getElementById('feed-posts') || document.getElementById('feed');
    if (!feed || !isLoggedIn()) {
        if (feed) {
            feed.innerHTML = `<div class="empty-state fade-in">
                <i class="fas fa-camera fa-3x"></i>
                <h3>Welcome to SocialHub</h3>
                <p>Login to see your feed</p>
                <a href="/login" class="btn btn-primary" style="margin-top:16px">Login</a>
            </div>`;
        }
        return;
    }
    try {
        feed.innerHTML = Array(3).fill(0).map(() => `<div class="skeleton-post">
            <div class="skeleton-header"><div class="skeleton-avatar"></div><div class="skeleton-line medium"></div></div>
            <div class="skeleton-media"></div>
            <div class="skeleton-actions"><div class="skeleton-action"></div><div class="skeleton-action"></div><div class="skeleton-action"></div></div>
        </div>`).join('');

        const data = await api(`/posts/premium/feed?page=${page}`).catch(() => api(`/posts?page=${page}`));
        if (!data.posts || data.posts.length === 0) {
            feed.innerHTML = `<div class="empty-state fade-in">
                <i class="fas fa-newspaper fa-3x"></i>
                <h3>No posts yet</h3>
                <p>Follow people to see their posts here!</p>
            </div>`;
            return;
        }
        const premiumHeader = page === 1 ? `<div class="premium-feed-card slide-up">
            <div><span class="card-kicker"><i class="fas fa-crown"></i> Premium Home Feed</span><h3>Ranked for you</h3><p>Trending local posts, people you follow, polls, reels, stories and fresh content are connected in one feed.</p></div>
            <a href="/search" class="btn btn-outline btn-sm"><i class="fas fa-compass"></i> Explore</a>
        </div>` : '';
        feed.innerHTML = premiumHeader + data.posts.map((p, i) => {
            return renderPost(p).replace('class="post-card"', `class="post-card" style="animation-delay: ${i * 0.05}s"`);
        }).join('');

        if (data.has_next) {
            const loadMoreBtn = document.createElement('button');
            loadMoreBtn.className = 'btn btn-outline center';
            loadMoreBtn.textContent = 'Load More';
            loadMoreBtn.onclick = () => loadFeed(page + 1);
            feed.appendChild(loadMoreBtn);
        }
    } catch (e) {
        feed.innerHTML = `<div class="empty-state fade-in">
            <i class="fas fa-exclamation-circle fa-3x"></i>
            <h3>Error loading feed</h3>
            <p>Please try again later</p>
        </div>`;
    }
}

function renderPost(post) {
    const author = post.author || {};
    const images = (post.images || []).map((img) => {
        const rawUrl = img.is_video ? img.video_url : img.image_url;
        if (!rawUrl || rawUrl === 'undefined' || rawUrl === 'null') return '';
        const src = getMediaUrl(rawUrl);
        if (img.is_video) {
            return `<video src="${src}" controls class="post-media" loading="lazy"></video>`;
        }
        return `<img src="${src}" class="post-media" loading="lazy" onerror="this.onerror=null;this.src='/static/images/default-avatar.png'">`;
    }).join('');

    let pollHtml = '';
    if (post.poll) {
        const opts = post.poll.options.map((o) => {
            const pct = post.poll.total_votes > 0 ? Math.round((o.votes_count / post.poll.total_votes) * 100) : 0;
            return `<div class="poll-option" onclick="votePoll('${post.id}','${o.id}')">
                <div class="poll-bar" style="width:${pct}%"></div>
                <span class="poll-text"><span>${escapeHtml(o.text)}</span><span>${pct}% (${o.votes_count})</span></span>
            </div>`;
        }).join('');
        pollHtml = `<div class="poll">${opts}<div class="poll-total">${post.poll.total_votes} votes</div></div>`;
    }

    let repostHtml = '';
    if (post.repost) repostHtml = `<div class="repost-ref">${renderPost(post.repost)}</div>`;

    const likedClass = post.is_liked ? 'active' : '';
    const heartIcon = post.is_liked ? 'fas' : 'far';
    const ownPostMenu = currentUser && currentUser.id === post.user_id
        ? `<div class="post-menu"><button class="post-menu-btn" onclick="showEditPost('${post.id}')" title="Edit post"><i class="fas fa-pen"></i></button><button class="post-menu-btn" onclick="deletePost('${post.id}')" title="Delete post"><i class="fas fa-trash"></i></button></div>`
        : `<button class="post-menu-btn" onclick="toast('Only post owners can delete posts', 'info')" title="Post options"><i class="fas fa-ellipsis-h"></i></button>`;

    return `<div class="post-card" id="post-${post.id}">
        <div class="post-header">
            <a href="/profile/${author.username || ''}" class="post-author">
                <img src="${getProfilePic(author)}" class="avatar" alt="" onerror="this.src='/static/images/default-avatar.png'">
                <div>
                    <span class="username">${escapeHtml(author.username || '')}</span>
                    ${author.is_verified ? '<i class="fas fa-check-circle verified"></i>' : ''}
                    <div class="post-time">${formatTime(post.created_at)}</div>
                </div>
            </a>
            ${ownPostMenu}
        </div>
        ${post.content ? `<div class="post-content">${renderContentWithHashtags(post.content)}</div>` : ''}
        ${(post.hashtags || []).length ? `<div class="tag-row post-tags">${post.hashtags.map((h) => `<a href="/search?q=${encodeURIComponent(String(h).replace(/^#/, ''))}">#${escapeHtml(String(h).replace(/^#/, ''))}</a>`).join('')}</div>` : ''}
        ${images ? `<div class="post-images">${images}</div>` : ''}
        ${pollHtml}
        ${repostHtml}
        <div class="post-actions">
            <button class="action-btn ${likedClass}" onclick="toggleLike('${post.id}', this)">
                <i class="${heartIcon} fa-heart"></i><span>${post.likes_count || 0}</span>
            </button>
            <button class="action-btn" onclick="showComments('${post.id}')">
                <i class="far fa-comment"></i><span>${post.comments_count || 0}</span>
            </button>
            <button class="action-btn" onclick="sharePost('${post.id}')">
                <i class="far fa-share-square"></i><span>${post.shares_count || 0}</span>
            </button>
            <button class="action-btn ${post.is_saved ? 'active' : ''}" onclick="toggleBookmark('${post.id}')">
                <i class="${post.is_saved ? 'fas' : 'far'} fa-bookmark"></i>
            </button>
        </div>
    </div>`;
}

async function showEditPost(postId) {
    try {
        const post = await api(`/posts/${postId}`);
        document.getElementById('edit-post-id').value = post.id;
        document.getElementById('edit-post-content').value = post.content || '';
        document.getElementById('edit-post-hashtags').value = (post.hashtags || []).join(', ');
        document.getElementById('edit-post-modal')?.classList.add('active');
    } catch (e) { toast(e.message || 'Could not load post', 'error'); }
}

async function savePostEdit(e) {
    e.preventDefault();
    const id = document.getElementById('edit-post-id')?.value;
    const content = document.getElementById('edit-post-content')?.value || '';
    const hashtags = String(document.getElementById('edit-post-hashtags')?.value || '').split(',').map((h) => h.trim().replace(/^#/, '')).filter(Boolean);
    const btn = e.target.querySelector('button[type="submit"]');
    try {
        setButtonLoading(btn, true);
        await api(`/posts/${id}`, { method: 'PUT', body: JSON.stringify({ content, hashtags }) });
        closeModal('edit-post-modal');
        toast('Post updated', 'success');
        if (window.location.pathname.startsWith('/profile/')) loadUserPosts(activeProfileUserId || currentUser?.id); else loadFeed();
    } catch (err) { toast(err.message || 'Update failed', 'error'); }
    finally { setButtonLoading(btn, false); }
}

// ========================================================================
// 12. LIKE BUTTON WITH POP ANIMATION
// ========================================================================
async function toggleLike(postId, btnElement) {
    try {
        const isLiked = btnElement.classList.contains('active');
        if (isLiked) {
            btnElement.classList.remove('active');
            btnElement.innerHTML = '<i class="far fa-heart"></i>';
            await api(`/likes/${postId}`, { method: 'DELETE' });
        } else {
            btnElement.classList.add('active');
            btnElement.innerHTML = '<i class="fas fa-heart"></i>';
            const icon = btnElement.querySelector('i');
            if (icon) { icon.classList.add('heartbeat'); setTimeout(() => icon.classList.remove('heartbeat'), 600); }
            await api(`/likes/${postId}`, { method: 'POST', body: JSON.stringify({ reaction: 'like' }) });
        }
        loadFeed();
    } catch (e) { loadFeed(); }
}

async function toggleBookmark(postId) {
    try { await api(`/posts/${postId}/bookmark`, { method: 'POST' }); loadFeed(); } catch (e) {}
}

async function sharePost(postId) {
    try { await api(`/posts/${postId}/repost`, { method: 'POST', body: JSON.stringify({}) }); toast('Post reposted', 'success'); loadFeed(); } catch (e) { toast('Error sharing post', 'error'); }
}

async function votePoll(postId, optionId) {
    try { await api(`/posts/${postId}/vote`, { method: 'POST', body: JSON.stringify({ option_id: optionId }) }); loadFeed(); } catch (e) { toast(e.message || 'Could not vote on poll', 'error'); }
}

async function deletePost(postId) {
    if (!confirm('Delete this post?')) return;
    try {
        await api(`/posts/${postId}`, { method: 'DELETE' });
        toast('Post deleted', 'success');
        const card = document.getElementById(`post-${postId}`);
        if (card) card.remove();
        else loadFeed();
    } catch (e) {
        toast(e.message || 'Could not delete post', 'error');
    }
}

// ========================================================================
// 13. CREATE POST WITH IMAGE/VIDEO UPLOAD
// ========================================================================
function showCreatePost() {
    const modal = document.getElementById('create-post-modal');
    if (modal) {
        modal.classList.add('active');
        setTimeout(() => { const t = document.getElementById('post-content'); if (t) t.focus(); }, 300);
    }
}

function previewFiles(input) {
    const preview = document.getElementById('upload-preview');
    if (!preview) return;
    preview.innerHTML = '';
    const files = Array.from(input.files || []);
    files.forEach((f) => {
        const url = URL.createObjectURL(f);
        const el = document.createElement('div');
        el.className = 'preview-item';
        if (f.type.startsWith('image/')) {
            el.innerHTML = `<img src="${url}" alt="preview"><button type="button" class="preview-remove" onclick="this.parentElement.remove()">&times;</button>`;
        } else if (f.type.startsWith('video/')) {
            el.innerHTML = `<video src="${url}" controls></video><button type="button" class="preview-remove" onclick="this.parentElement.remove()">&times;</button>`;
        }
        preview.appendChild(el);
    });
}

// ========================================================================
// 14. COMMENTS WITH SMOOTH ANIMATIONS
// ========================================================================
async function showComments(postId) {
    const modal = document.getElementById('comments-modal');
    const content = document.getElementById('comments-content');
    if (!modal || !content) return;
    modal.classList.add('active');
    content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    try {
        const comments = await api(`/comments/${postId}`);
        let html = `<div class="comment-form">
                <img src="${currentUser ? getProfilePic(currentUser) : '/static/images/default-avatar.png'}" class="avatar-xs" alt="">
                <input id="comment-input" placeholder="Write a comment..." onkeypress="if(event.key==='Enter')addComment('${postId}')">
                <button onclick="addComment('${postId}')" class="btn btn-primary btn-sm">Post</button>
            </div>`;
        comments.forEach((c) => { html += renderComment(c, postId); });
        content.innerHTML = html;
        content.scrollTop = 0;
    } catch (e) { content.innerHTML = '<p style="text-align:center;padding:20px">Error loading comments</p>'; }
}

function renderComment(c, postId) {
    const a = c.author || {};
    let replies = '';
    if (c.replies && c.replies.length > 0) {
        replies = '<div class="replies">' + c.replies.map((r) => renderComment(r, postId)).join('') + '</div>';
    }
    return `<div class="comment">
        <img src="${getProfilePic(a)}" class="avatar-xs" alt="" onerror="this.src='/static/images/default-avatar.png'">
        <div class="comment-body">
            <span class="username">${escapeHtml(a.username || '')}</span>
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
    try {
        await api(`/comments/${postId}`, { method: 'POST', body: JSON.stringify({ content: input.value.trim() }) });
        input.value = '';
        showComments(postId);
    } catch (e) { toast(e.message || 'Error posting comment', 'error'); }
}

function showReplyInput(commentId, postId) {
    const el = document.getElementById(`reply-form-${commentId}`);
    if (el) {
        el.innerHTML = `<div class="comment-form" style="padding:8px 0">
            <input id="reply-${commentId}" placeholder="Write a reply..." onkeypress="if(event.key==='Enter')addReply('${postId}','${commentId}')">
        </div>`;
    }
}

async function addReply(postId, parentId) {
    const input = document.getElementById(`reply-${parentId}`);
    if (!input || !input.value.trim()) return;
    try {
        await api(`/comments/${postId}`, { method: 'POST', body: JSON.stringify({ content: input.value.trim(), parent_id: parentId }) });
        showComments(postId);
    } catch (e) { toast(e.message || 'Error posting reply', 'error'); }
}

// ========================================================================
// 15. PROFILE PAGE
// ========================================================================
async function loadProfile() {
    const path = window.location.pathname;
    const username = path.split('/profile/')[1];
    if (!username) return;
    const container = document.getElementById('profile-content');
    if (!container) return;
    try {
        await hydrateCurrentUser();
        const profile = await api(`/users/profile/${username}`);
        activeProfileUserId = profile.id;
        document.title = `${profile.full_name || profile.username} - SocialHub`;
        let isOwn = currentUser && currentUser.id === profile.id;
        container.innerHTML = `<div class="profile-header slide-up">
                <div class="profile-cover">
                    <img src="${getCoverUrl(profile.cover_photo)}" alt="Cover" onerror="this.onerror=null;this.src='/static/images/default-cover.png'">
                </div>
                <div class="profile-info">
                    <img src="${getProfilePic(profile)}" class="avatar-xl" alt="" onerror="this.src='/static/images/default-avatar.png'">
                    <div class="profile-details">
                        <h2>${escapeHtml(profile.full_name || profile.username)} ${profile.is_verified ? '<i class="fas fa-check-circle verified"></i>' : ''} ${profile.badge ? '<span class="badge-' + profile.badge + '">' + profile.badge + '</span>' : ''}</h2>
                        <p class="bio">${escapeHtml(profile.bio || '')}</p>
                        <div class="profile-stats">
                            <span><strong>${profile.posts_count || 0}</strong> posts</span>
                            <span><strong>${profile.followers_count || 0}</strong> followers</span>
                            <span><strong>${profile.following_count || 0}</strong> following</span>
                        </div>
                        <div class="profile-actions">
                            ${!isOwn && isLoggedIn() ? '<button class="btn btn-primary" onclick="toggleFollow(\'' + profile.id + '\', this)">Follow</button>' : ''}
                            ${isOwn ? '<a href="/settings" class="btn btn-outline">Edit Profile</a>' : ''}
                            ${!isOwn && isLoggedIn() ? '<a href="/chat" class="btn btn-outline"><i class="fas fa-envelope"></i> Message</a>' : ''}
                        </div>
                    </div>
                </div>
            </div>
            <div class="profile-tabs">
                <button class="profile-tab active" onclick="switchProfileTab(this, 'posts')"><i class="fas fa-th"></i> Posts</button>
                <button class="profile-tab" onclick="switchProfileTab(this, 'saved')"><i class="fas fa-bookmark"></i> Saved</button>
                <button class="profile-tab" onclick="switchProfileTab(this, 'reels')"><i class="fas fa-video"></i> Reels</button>
                <button class="profile-tab" onclick="switchProfileTab(this, 'tagged')"><i class="fas fa-user-tag"></i> Tagged</button>
            </div>
            <div id="user-posts" class="posts-grid"></div>`;
        loadUserPosts(profile.id);
    } catch (e) {
        container.innerHTML = `<div class="empty-state fade-in"><i class="fas fa-user-slash fa-3x"></i><h3>User not found</h3></div>`;
    }
}

function switchProfileTab(btn, tab) {
    document.querySelectorAll('.profile-tab').forEach((t) => t.classList.remove('active'));
    btn.classList.add('active');
    if (tab === 'posts') loadUserPosts(activeProfileUserId || currentUser?.id);
    else if (tab === 'saved') loadSavedPosts();
    else if (tab === 'reels') loadUserReels();
    else {
        const el = document.getElementById('user-posts');
        if (el) el.innerHTML = '<div class="empty-state" style="grid-column: 1/-1"><i class="fas fa-user-tag fa-3x"></i><h3>No tagged posts</h3></div>';
    }
}

async function loadSavedPosts() {
    const el = document.getElementById('user-posts');
    if (!el) return;
    try {
        const data = await api('/posts/bookmarks');
        if (data.posts && data.posts.length > 0) {
            el.innerHTML = data.posts.map((p, i) => renderPost(p).replace('class="post-card"', `class="post-card" style="animation-delay: ${i * 0.05}s"`)).join('');
        } else {
            el.innerHTML = '<div class="empty-state" style="grid-column: 1/-1"><i class="fas fa-bookmark fa-3x"></i><h3>No saved posts</h3><p>Posts you save will appear here</p></div>';
        }
    } catch (e) { el.innerHTML = '<div class="empty-state" style="grid-column: 1/-1"><i class="fas fa-exclamation-circle fa-3x"></i><h3>Error loading saved posts</h3></div>'; }
}

async function loadSavedCenter(filter = 'all') {
    const feed = document.getElementById('feed') || document.getElementById('feed-posts');
    if (!feed) return;
    feed.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    try {
        await hydrateCurrentUser();
        const [postsData, reelsData] = await Promise.all([
            filter !== 'reels' ? api('/posts/saved-center', { silent: true }).catch((e) => ({ error: e.message, posts: [] })) : Promise.resolve({ posts: [] }),
            filter !== 'posts' ? api('/reels/saved', { silent: true }).catch(() => ({ reels: [] })) : Promise.resolve({ reels: [] }),
        ]);
        const savedPostsHtml = postsData.posts?.length ? `<section data-saved-section="posts"><h3 style="margin:18px 0">Saved Posts</h3>${postsData.posts.map((p) => renderPost(p)).join('')}</section>` : '';
        const savedReelsHtml = reelsData.reels?.length ? `<section data-saved-section="reels"><h3 style="margin:18px 0">Saved Reels</h3><div class="reels-container">${reelsData.reels.map((r) => renderReel(r)).join('')}</div></section>` : '';
        feed.innerHTML = `<div class="premium-feed-card"><div><span class="card-kicker"><i class="fas fa-bookmark"></i> Saved Center</span><h3>Saved posts & reels</h3><p>Everything you save appears here.</p></div></div>
            <div class="saved-filter-bar">
                <button class="btn btn-outline btn-sm ${filter === 'all' ? 'active' : ''}" onclick="loadSavedCenter('all')">All</button>
                <button class="btn btn-outline btn-sm ${filter === 'posts' ? 'active' : ''}" onclick="loadSavedCenter('posts')">Posts</button>
                <button class="btn btn-outline btn-sm ${filter === 'reels' ? 'active' : ''}" onclick="loadSavedCenter('reels')">Reels</button>
            </div>` + (savedPostsHtml + savedReelsHtml || `<div class="empty-state"><i class="fas fa-bookmark fa-3x"></i><h3>No saved items</h3><p>Posts and reels you save will appear here.</p></div>`);
    } catch (e) {
        feed.innerHTML = `<div class="empty-state"><i class="fas fa-triangle-exclamation fa-3x"></i><h3>Could not load saved center</h3><p>${escapeHtml(e.message)}</p></div>`;
    }
}

async function loadUserReels() {
    const el = document.getElementById('user-posts');
    if (!el) return;
    try {
        const data = await api('/reels');
        if (data.reels && data.reels.length > 0) {
            el.innerHTML = data.reels.map((r, i) => renderReel(r).replace('class="reel-card"', `class="reel-card" style="animation-delay: ${i * 0.05}s"`)).join('');
        } else {
            el.innerHTML = '<div class="empty-state" style="grid-column: 1/-1"><i class="fas fa-video fa-3x"></i><h3>No reels yet</h3></div>';
        }
    } catch (e) { el.innerHTML = '<div class="empty-state" style="grid-column: 1/-1"><i class="fas fa-exclamation-circle fa-3x"></i><h3>Error loading reels</h3></div>'; }
}

async function loadUserPosts(userId) {
    const el = document.getElementById('user-posts');
    if (!el) return;
    try {
        const data = await api(`/posts/user/${userId}`);
        if (data.posts && data.posts.length > 0) {
            el.innerHTML = data.posts.map((p, i) => renderPost(p).replace('class="post-card"', `class="post-card" style="animation-delay: ${i * 0.05}s"`)).join('');
        } else {
            el.innerHTML = '<div class="empty-state" style="grid-column: 1/-1"><i class="fas fa-newspaper fa-3x"></i><h3>No posts yet</h3></div>';
        }
    } catch (e) { el.innerHTML = '<div class="empty-state" style="grid-column: 1/-1"><i class="fas fa-exclamation-circle fa-3x"></i><h3>Error loading posts</h3></div>'; }
}

async function toggleFollow(userId, btnElement) {
    try {
        const status = await api(`/follow/check/${userId}`);
        if (status.is_following) {
            await api(`/follow/${userId}`, { method: 'DELETE' });
            if (btnElement) { btnElement.textContent = 'Follow'; btnElement.className = 'btn btn-primary'; }
            toast('Unfollowed user', 'success');
        } else {
            await api(`/follow/${userId}`, { method: 'POST' });
            if (btnElement) { btnElement.textContent = 'Following'; btnElement.className = 'btn btn-outline'; }
            toast('Following user', 'success');
        }
    } catch (e) { toast(e.message || 'Could not update follow status', 'error'); }
}

// ========================================================================
// 16. STORIES
// ========================================================================
async function loadStories() {
    const container = document.getElementById('stories-container');
    if (!container || !isLoggedIn()) return;
    try {
        const stories = await api('/stories');
        if (stories.length === 0) {
            container.innerHTML = '<div class="empty-state" style="padding:30px"><i class="fas fa-bookmark fa-2x"></i><h3>No stories yet</h3></div>';
            return;
        }
        const grouped = {};
        stories.forEach((s) => {
            if (!grouped[s.user_id]) grouped[s.user_id] = [];
            grouped[s.user_id].push(s);
        });
        let html = '<div class="stories-row slide-up">';
        for (const [userId, userStories] of Object.entries(grouped)) {
            const u = userStories[0].user || {};
            html += `<div class="story-circle" onclick="viewStory('${userStories[0].id}', '${userId}')">
                <img src="${getProfilePic(u)}" class="story-avatar" alt="" onerror="this.src='/static/images/default-avatar.png'">
                <span>${escapeHtml(u.username || '')}</span>
            </div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="empty-state" style="padding:30px"><i class="fas fa-exclamation-circle fa-2x"></i><h3>Error loading stories</h3></div>';
    }
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
        const progressBars = stories.map((_, i) => { return `<div class="story-progress-bar ${i <= idx ? 'active' : ''}"></div>`; }).join('');
        const pollsHtml = (s.polls || []).map((poll) => `<div class="story-poll-card">
            <h4>${escapeHtml(poll.question)}</h4>
            ${(poll.options || []).map((opt) => {
                const votes = poll.results?.[opt] || 0;
                const pct = poll.total_votes ? Math.round((votes / poll.total_votes) * 100) : 0;
                return `<button onclick="voteStoryPoll('${s.id}','${poll.id}','${escapeHtml(opt)}')"><span>${escapeHtml(opt)}</span><b>${pct}%</b></button>`;
            }).join('')}
        </div>`).join('');
        viewer.innerHTML = `<div class="story-slide">
            <div class="story-progress">${progressBars}</div>
            <div class="story-header">
                <img src="${getProfilePic(u)}" alt="" onerror="this.src='/static/images/default-avatar.png'">
                <span style="font-weight:700">${escapeHtml(u.username || '')}</span>
                <span style="opacity:0.7;font-size:12px">${formatTime(s.created_at)}</span>
                ${currentUser && currentUser.id === s.user_id ? `<button onclick="deleteStory('${s.id}')" title="Delete story"><i class="fas fa-trash"></i></button>` : ''}
                <button onclick="document.getElementById('story-viewer').classList.remove('active')">&times;</button>
            </div>
            <div class="story-media">
                ${s.media_type === 'video' ? '<video src="' + getMediaUrl(s.media_url) + '" autoplay controls></video>' : '<img src="' + getMediaUrl(s.media_url) + '" alt="" onerror="this.src=\'/static/images/default-avatar.png\'">'}
            </div>
            <div class="story-controls"><button class="btn btn-outline btn-sm" onclick="window._prevStory()"><i class="fas fa-chevron-left"></i> Prev</button><button class="btn btn-primary btn-sm" onclick="window._nextStory()">Next <i class="fas fa-chevron-right"></i></button></div>
            ${s.caption ? '<p class="story-caption">' + escapeHtml(s.caption) + '</p>' : ''}
             ${pollsHtml}
             <div class="story-extra-actions">
                <button class="btn btn-outline btn-sm" onclick="reactStory('${s.id}','love')"><i class="fas fa-heart"></i> React</button>
                ${currentUser && currentUser.id === s.user_id ? `<button class="btn btn-outline btn-sm" onclick="addStoryPollPrompt('${s.id}')"><i class="fas fa-square-poll-vertical"></i> Poll</button><button class="btn btn-outline btn-sm" onclick="highlightStoryPrompt('${s.id}')"><i class="fas fa-star"></i> Highlight</button>` : ''}
             </div>
        </div>`;
    }
    window._showStory = show;
    window._nextStory = () => { idx += 1; show(); };
    window._prevStory = () => { idx = Math.max(0, idx - 1); show(); };
    show();
}

async function reactStory(storyId, reaction = 'love') {
    try { await api(`/stories/${storyId}/react`, { method: 'POST', body: JSON.stringify({ reaction }) }); toast('Story reaction sent', 'success'); }
    catch (e) { toast(e.message || 'Could not react', 'error'); }
}

async function voteStoryPoll(storyId, pollId, answer) {
    try { await api(`/stories/${storyId}/vote`, { method: 'POST', body: JSON.stringify({ poll_id: pollId, answer }) }); toast('Vote saved', 'success'); }
    catch (e) { toast(e.message || 'Could not vote', 'error'); }
}

async function addStoryPollPrompt(storyId) {
    const question = prompt('Poll question:');
    if (!question) return;
    const options = (prompt('Options separated by commas:', 'Yes,No') || '').split(',').map((x) => x.trim()).filter(Boolean);
    if (options.length < 2) return toast('Add at least two options', 'error');
    try { await api(`/stories/${storyId}/poll`, { method: 'POST', body: JSON.stringify({ question, options, poll_type: 'poll' }) }); toast('Story poll added', 'success'); }
    catch (e) { toast(e.message || 'Could not add poll', 'error'); }
}

async function highlightStoryPrompt(storyId) {
    const title = prompt('Highlight title:', 'Highlights');
    if (!title) return;
    try { await api(`/stories/${storyId}/highlight`, { method: 'POST', body: JSON.stringify({ title }) }); toast('Story added to highlights', 'success'); }
    catch (e) { toast(e.message || 'Could not highlight story', 'error'); }
}

// ========================================================================
// 17. REELS
// ========================================================================
async function loadReels(page = 1) {
    const container = document.getElementById('reels-container');
    if (!container) return;
    try {
        const data = await api(`/reels/viewer?page=${page}`).catch(() => api(`/reels?page=${page}`));
        if (!data.reels || data.reels.length === 0) {
            container.innerHTML = '<div class="empty-state fade-in"><i class="fas fa-film fa-3x"></i><h3>No reels yet</h3><p>Be the first to create a reel!</p></div>';
            return;
        }
        container.innerHTML = data.reels.map((r, i) => {
            return renderReel(r).replace('class="reel-card"', `class="reel-card" style="animation-delay: ${i * 0.05}s"`);
        }).join('');
    } catch (e) {
        container.innerHTML = '<div class="empty-state fade-in"><i class="fas fa-exclamation-circle fa-3x"></i><h3>Error loading reels</h3></div>';
    }
}

function renderReel(reel) {
    const u = reel.user || {};
    return `<div class="reel-card full-reel-card">
        <video src="${getMediaUrl(reel.video_url)}" controls class="reel-video" onerror="this.src='/static/images/default-avatar.png'"></video>
        <div class="reel-play-overlay"><i class="fas fa-play"></i></div>
        <div class="reel-actions">
            <button onclick="likeReel('${reel.id}')"><i class="fas fa-heart"></i> ${reel.likes_count || 0}</button>
            <button onclick="showReelComments('${reel.id}')"><i class="fas fa-comment"></i> ${reel.comments_count || 0}</button>
            <button onclick="navigator.share ? navigator.share({title:'SocialHub Reel', url:location.origin + '/reels'}) : toast('Link copied', 'success')"><i class="fas fa-share"></i></button>
            <button class="${reel.is_saved ? 'active' : ''}" onclick="saveReel('${reel.id}')"><i class="${reel.is_saved ? 'fas' : 'far'} fa-bookmark"></i></button>
            ${currentUser && currentUser.id === reel.user_id ? `<button onclick="deleteReel('${reel.id}')"><i class="fas fa-trash"></i></button>` : ''}
        </div>
        <div class="reel-overlay">
            <div class="reel-info">
                <div class="username">@${escapeHtml(u.username || '')}</div>
                <p>${escapeHtml(reel.caption || '')}</p>
                <div class="audio"><i class="fas fa-music"></i> Original Audio</div>
            </div>
        </div>
    </div>`;
}

async function likeReel(id) {
    try { await api(`/reels/${id}/like`, { method: 'POST' }); loadReels(); } catch (e) { try { await api(`/reels/${id}/like`, { method: 'DELETE' }); loadReels(); } catch (e2) {} }
}

async function saveReel(id) {
    try { await api(`/reels/${id}/save`, { method: 'POST' }); toast('Reel saved!', 'success'); } catch (e) { toast(e.message, 'error'); }
}

async function createReelFromUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById('reel-file');
    const caption = document.getElementById('reel-caption')?.value || '';
    const btn = e.target.querySelector('button[type="submit"]');
    if (!fileInput?.files?.[0]) return toast('Choose a video file first', 'error');
    const form = new FormData();
    form.append('file', fileInput.files[0]);
    form.append('caption', caption);
    try {
        setButtonLoading(btn, true);
        const res = await fetch(`${API}/reels`, { method: 'POST', headers: getMultipartHeaders(), body: form });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Could not upload reel');
        e.target.reset();
        toast('Reel uploaded', 'success');
        loadReels();
    } catch (err) {
        toast(err.message, 'error');
    } finally {
        setButtonLoading(btn, false);
    }
}

async function deleteReel(id) {
    if (!confirm('Delete this reel?')) return;
    try {
        await api(`/reels/${id}`, { method: 'DELETE' });
        toast('Reel deleted', 'success');
        loadReels();
    } catch (e) {
        toast(e.message, 'error');
    }
}

async function commentReel(id) {
    const content = prompt('Write a comment:');
    if (!content) return;
    try {
        await api(`/reels/${id}/comments`, { method: 'POST', body: JSON.stringify({ content }) });
        toast('Comment added', 'success');
        loadReels();
    } catch (e) {
        toast(e.message, 'error');
    }
}

async function showReelComments(id) {
    const modal = document.getElementById('reel-comments-modal');
    const content = document.getElementById('reel-comments-content');
    if (!modal || !content) return;
    modal.classList.add('active');
    content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    try {
        const comments = await api(`/reels/${id}/comments`);
        content.innerHTML = `<div class="comment-form"><input id="reel-comment-input" placeholder="Add a comment..." onkeypress="if(event.key==='Enter')addReelComment('${id}')"><button class="btn btn-primary btn-sm" onclick="addReelComment('${id}')">Post</button></div>` +
            ((comments || []).length ? comments.map((c) => `<div class="comment"><img class="avatar-xs" src="/static/images/default-avatar.png" alt=""><div class="comment-body"><span class="username">${escapeHtml(c.author?.username || 'User')}</span><span class="comment-text">${escapeHtml(c.content || '')}</span><div class="comment-meta"><span>${formatTime(c.created_at)}</span></div></div></div>`).join('') : '<div class="empty-state"><i class="fas fa-comment-slash fa-3x"></i><h3>No comments yet</h3></div>');
    } catch (e) { content.innerHTML = `<div class="empty-state"><h3>Error loading comments</h3><p>${escapeHtml(e.message)}</p></div>`; }
}

async function addReelComment(id) {
    const input = document.getElementById('reel-comment-input');
    const content = input?.value.trim();
    if (!content) return;
    try { await api(`/reels/${id}/comments`, { method: 'POST', body: JSON.stringify({ content }) }); input.value = ''; toast('Comment added', 'success'); showReelComments(id); loadReels(); }
    catch (e) { toast(e.message || 'Could not comment', 'error'); }
}

// ========================================================================
// 18. CHAT / MESSENGER
// ========================================================================
let currentChatId = null;
let chatMessagesCache = [];
let aiChatHistory = [];
let isAIChatOpen = false;

function getChatDisplay(chat) {
    const other = chat.participants?.find((p) => currentUser && p.id !== currentUser.id) || chat.participants?.[0] || {};
    return {
        title: chat.is_group ? (chat.name || 'Group chat') : (other.full_name || other.username || chat.name || 'Chat'),
        subtitle: chat.is_group ? `${chat.participants?.length || 0} members` : (other.username ? `@${other.username}` : 'Direct message'),
        avatar: chat.is_group ? '/static/images/default-avatar.png' : getProfilePic(other),
    };
}

function renderChatHeader(title, subtitle, icon = 'comments') {
    const header = document.getElementById('chat-header');
    if (!header) return;
    header.innerHTML = `<div style="display:flex;align-items:center;gap:12px;width:100%">
        <div class="avatar-sm" style="display:flex;align-items:center;justify-content:center;background:var(--bg-glass);border-radius:50%"><i class="fas fa-${icon}"></i></div>
        <div style="flex:1"><h3 style="margin:0;font-size:16px">${escapeHtml(title)}</h3><p style="margin:2px 0 0;color:var(--text-secondary);font-size:12px">${escapeHtml(subtitle || '')}</p></div>
        ${!isAIChatOpen ? '<button class="btn btn-outline btn-sm" onclick="openAIChat()"><i class="fas fa-robot"></i> AI</button>' : '<button class="btn btn-outline btn-sm" onclick="window.location.href=\'/chat\'"><i class="fas fa-inbox"></i> Messages</button>'}
    </div>`;
}

function renderMessages(messages) {
    const container = document.getElementById('messages-container');
    if (!container) return;
    container.style.display = 'block';
    container.style.padding = '20px';
    container.style.overflowY = 'auto';
    if (!messages.length) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-comment-dots fa-3x"></i><h3>No messages yet</h3><p>Send the first message.</p></div>';
        return;
    }
    container.innerHTML = messages.map((m) => {
        const isMine = m.local_role ? m.local_role === 'user' : (currentUser && m.sender_id === currentUser.id);
        const reactions = (m.reactions || []).map((r) => r.reaction).join(' ');
        return `<div class="message ${isMine ? 'sent' : 'received'}">
            <div class="message-bubble">
                ${m.is_deleted ? '<em>This message has been deleted</em>' : escapeHtml(m.content || '')}
                ${m.file_url ? '<a href="' + getMediaUrl(m.file_url) + '" target="_blank" style="display:block;margin-top:8px;color:inherit;text-decoration:underline">📎 File</a>' : ''}
                ${reactions ? `<div class="message-reactions">${escapeHtml(reactions)}</div>` : ''}
            </div>
            ${!m.local_role ? `<div class="message-tools"><button onclick="reactMessage('${m.id}','❤️')">❤️</button><button onclick="reactMessage('${m.id}','😂')">😂</button><button onclick="reactMessage('${m.id}','👍')">👍</button></div>` : ''}
            <span class="message-time">
                ${m.created_at ? formatTime(m.created_at) : 'now'}
                ${isMine && !m.local_role ? '<i class="fas fa-check-double" style="color:' + (m.is_read ? 'var(--blue)' : 'var(--text-secondary)') + '"></i>' : ''}
            </span>
        </div>`;
    }).join('');
    setTimeout(() => { container.scrollTop = container.scrollHeight; }, 50);
}

async function reactMessage(messageId, reaction) {
    try { await api(`/chats/messages/${messageId}/react`, { method: 'POST', body: JSON.stringify({ reaction }) }); if (currentChatId) loadChatMessages(currentChatId); }
    catch (e) { toast(e.message || 'Could not react', 'error'); }
}

function showChatInput(placeholder = 'Type a message...') {
    const inputBar = document.getElementById('chat-input-bar');
    const input = document.getElementById('message-input');
    if (inputBar) inputBar.style.display = 'flex';
    if (input) input.placeholder = placeholder;
}

async function loadChats() {
    const list = document.getElementById('chat-list');
    if (!list) return;
    try {
        await hydrateCurrentUser();
        const chats = await api('/chats');
        if (chats.length === 0) {
            list.innerHTML = `<div class="chat-item" onclick="openAIChat()">
                <div class="avatar-sm" style="display:flex;align-items:center;justify-content:center;background:var(--bg-glass);border-radius:50%"><i class="fas fa-robot"></i></div>
                <div class="chat-info"><span class="username">SocialHub AI</span><p class="last-msg">Ask AI anything</p></div>
            </div><div class="empty-state" style="padding:40px"><i class="fas fa-comments fa-3x"></i><h3>No conversations yet</h3><p>Start chatting!</p></div>`;
            return;
        }
        list.innerHTML = `<div class="chat-item ${isAIChatOpen ? 'active' : ''}" onclick="openAIChat()">
            <div class="avatar-sm" style="display:flex;align-items:center;justify-content:center;background:var(--bg-glass);border-radius:50%"><i class="fas fa-robot"></i></div>
            <div class="chat-info"><span class="username">SocialHub AI</span><p class="last-msg">OpenAI assistant</p></div>
        </div>` + chats.map((c, i) => {
            const display = getChatDisplay(c);
            const lastMsg = c.last_message;
            const isActive = currentChatId && currentChatId === c.id;
            return `<div class="chat-item ${isActive ? 'active' : ''}" onclick="window.location.href='/chat/${c.id}'" style="animation: slideLeft 0.3s ease ${i * 0.05}s backwards">
                <img src="${display.avatar}" class="avatar-sm" alt="" onerror="this.src='/static/images/default-avatar.png'">
                <div class="chat-info">
                    <span class="username">${escapeHtml(display.title)}</span>
                    <p class="last-msg">${lastMsg ? escapeHtml(lastMsg.content || '').substring(0, 50) : 'Start chatting'}</p>
                </div>
                ${c.unread_count > 0 ? '<span class="unread-badge pulse">' + c.unread_count + '</span>' : ''}
            </div>`;
        }).join('');
    } catch (e) {
        list.innerHTML = '<div class="empty-state" style="padding:40px"><i class="fas fa-exclamation-circle fa-3x"></i><h3>Error loading chats</h3></div>';
    }
}

async function loadChatMessages(chatId) {
    const container = document.getElementById('messages-container');
    if (!container) return;
    isAIChatOpen = false;
    currentChatId = chatId;
    showChatInput();
    try {
        await hydrateCurrentUser();
        loadChats();
        api(`/chats/${chatId}`).then((chat) => {
            const display = getChatDisplay(chat);
            renderChatHeader(display.title, display.subtitle, chat.is_group ? 'users' : 'user');
        }).catch(() => {});
        const messages = await api(`/chats/${chatId}/messages`);
        chatMessagesCache = messages.reverse();
        renderMessages(chatMessagesCache);
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-circle fa-3x"></i><h3>Error loading messages</h3></div>';
    }
}

async function sendMessage(chatId) {
    const input = document.getElementById('message-input');
    if (!input || !input.value.trim()) return;
    if (isAIChatOpen) return sendAIMessage();
    if (!chatId) return toast('Open a chat first', 'error');
    const sendBtn = document.querySelector('.send-btn');
    const content = input.value.trim();
    try {
        setButtonLoading(sendBtn, true);
        const saved = await api(`/chats/${chatId}/messages`, { method: 'POST', body: JSON.stringify({ content }) });
        input.value = '';
        chatMessagesCache.push(saved);
        renderMessages(chatMessagesCache);
        loadChats();
        loadChatMessages(chatId);
    } catch (e) { toast(e.message || 'Error sending message', 'error'); } finally { setButtonLoading(sendBtn, false); }
}

let typingTimer = null;
function notifyTyping() {
    if (!currentChatId || typingTimer) return;
    typingTimer = setTimeout(() => { typingTimer = null; }, 2000);
    api(`/chats/${currentChatId}/typing`, { method: 'POST' }).catch(() => {});
    const header = document.getElementById('chat-header');
    if (header && !document.getElementById('typing-chip')) header.insertAdjacentHTML('beforeend', '<span id="typing-chip" class="typing-chip">typing…</span>');
    setTimeout(() => document.getElementById('typing-chip')?.remove(), 1800);
}

async function sendChatFile(chatId, input) {
    if (!chatId) return toast('Open a chat first', 'error');
    const file = input?.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    try {
        const res = await fetch(`${API}/chats/${chatId}/files`, { method: 'POST', headers: getMultipartHeaders(), body: form });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'File upload failed');
        input.value = '';
        toast(file.type.startsWith('audio') ? 'Voice message sent' : 'File sent', 'success');
        loadChatMessages(chatId);
        loadChats();
    } catch (e) {
        toast(e.message || 'Could not send file', 'error');
    }
}

async function createGroupChat() {
    const name = prompt('Group name:');
    if (!name) return;
    const members = prompt('Member usernames or user IDs comma separated:') || '';
    const rawMembers = members.split(',').map((x) => x.trim()).filter(Boolean);
    if (rawMembers.length === 0) return toast('Add at least one member', 'error');
    try {
        const participant_ids = [];
        for (const member of rawMembers) {
            if (member.length > 20 && member.includes('-')) {
                participant_ids.push(member);
            } else {
                const results = await api(`/search/users?q=${encodeURIComponent(member)}`);
                const user = (results || []).find((u) => u.username.toLowerCase() === member.toLowerCase()) || (results || [])[0];
                if (user) participant_ids.push(user.id);
            }
        }
        if (participant_ids.length === 0) return toast('No valid members found', 'error');
        const data = await api('/chats', { method: 'POST', body: JSON.stringify({ name, participant_ids, is_group: true }) });
        toast('Group created', 'success');
        if (data?.id) window.location.href = `/chat/${data.id}`;
        else loadChats();
    } catch (e) {
        toast(e.message || 'Could not create group', 'error');
    }
}

function openAIChat() {
    isAIChatOpen = true;
    currentChatId = null;
    renderChatHeader('SocialHub AI', 'OpenAI assistant', 'robot');
    showChatInput('Ask SocialHub AI...');
    renderMessages(aiChatHistory.length ? aiChatHistory : [{ local_role: 'assistant', content: 'Hi! I am SocialHub AI. Ask me anything.', created_at: new Date().toISOString() }]);
    loadChats();
}

async function sendAIMessage() {
    const input = document.getElementById('message-input');
    const sendBtn = document.querySelector('.send-btn');
    const content = input?.value.trim();
    if (!content) return;
    const userMsg = { local_role: 'user', content, created_at: new Date().toISOString() };
    aiChatHistory.push(userMsg);
    input.value = '';
    renderMessages([...aiChatHistory, { local_role: 'assistant', content: 'Thinking...', created_at: new Date().toISOString() }]);
    try {
        setButtonLoading(sendBtn, true);
        const history = aiChatHistory.slice(-10).map((m) => ({ role: m.local_role === 'assistant' ? 'assistant' : 'user', content: m.content }));
        const data = await api('/ai-chat', { method: 'POST', body: JSON.stringify({ message: content, history }) });
        aiChatHistory.push({ local_role: 'assistant', content: data.reply, created_at: new Date().toISOString() });
        renderMessages(aiChatHistory);
        if (data.using_fallback) toast('AI fallback active: add OPENAI_API_KEY for OpenAI replies', 'info');
    } catch (e) {
        aiChatHistory.push({ local_role: 'assistant', content: e.message || 'AI chat failed', created_at: new Date().toISOString() });
        renderMessages(aiChatHistory);
        toast(e.message || 'AI chat failed', 'error');
    } finally {
        setButtonLoading(sendBtn, false);
    }
}

function filterChats(query) {
    const q = (query || '').toLowerCase();
    document.querySelectorAll('.chat-item').forEach((item) => {
        item.style.display = item.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
}

function insertEmoji(emoji = '😊') {
    const input = document.getElementById('message-input');
    if (!input) return toast('Open a chat first', 'info');
    input.value += emoji;
    input.focus();
}

async function startNewChat() {
    const username = prompt('Enter a username to message:');
    if (!username) return;
    try {
        const results = await api(`/search/users?q=${encodeURIComponent(username)}`);
        const user = (results || []).find((u) => u.username.toLowerCase() === username.toLowerCase()) || (results || [])[0];
        if (!user) return toast('No matching user found', 'error');
        const chat = await api('/chats', { method: 'POST', body: JSON.stringify({ participant_ids: [user.id], is_group: false }) });
        toast('Chat created', 'success');
        window.location.href = `/chat/${chat.id}`;
    } catch (e) {
        toast(e.message || 'Could not start chat', 'error');
    }
}

// ========================================================================
// 19. NOTIFICATIONS
// ========================================================================
function getNotificationMessage(notification) {
    const rawMessage = String(notification?.message || '').trim();
    const actor = notification?.actor || {};
    const actorName = actor.username || actor.full_name || 'Someone';

    // Some old/stale notifications can contain a generic API error such as
    // "Not found" as their saved message. Do not surface that raw backend
    // error in the UI; rebuild a user-friendly message from notification data.
    const isGenericErrorMessage = /^(not found|404|request failed)$/i.test(rawMessage);
    if (rawMessage && !isGenericErrorMessage) return rawMessage;

    switch (notification?.type) {
        case 'like':
            return `${actorName} liked your post`;
        case 'comment':
            return `${actorName} commented on your post`;
        case 'share':
            return `${actorName} shared your post`;
        case 'tag':
        case 'mention':
            return `${actorName} tagged you in a post`;
        case 'follow':
            return `${actorName} started following you`;
        case 'follow_request':
            return `${actorName} requested to follow you`;
        default:
            return 'You have a new notification';
    }
}

async function loadNotifications() {
    const container = document.getElementById('notifications-container');
    if (!container) return;
    try {
        const filter = document.querySelector('.notif-filter.active')?.dataset.filter || 'all';
        const unreadOnly = filter === 'unread';
        const typeFilter = ['like', 'comment', 'follow', 'message', 'mention'].includes(filter) ? `&type=${filter}` : '';
        const notifs = await api(`/notifications?unread_only=${unreadOnly}${typeFilter}`);
        if (notifs.length === 0) {
            container.innerHTML = '<div class="empty-state fade-in"><i class="fas fa-bell-slash fa-3x"></i><h3>No notifications yet</h3><p>When someone interacts with you, you will see it here</p></div>';
            return;
        }
        container.innerHTML = notifs.map((n, i) => {
            const actor = n.actor || {};
            const notifType = n.type || '';
            const message = getNotificationMessage(n);
            let iconClass = 'follow', icon = 'fa-user-plus';
            if (notifType === 'like') { iconClass = 'like'; icon = 'fa-heart'; }
            else if (notifType === 'comment') { iconClass = 'comment'; icon = 'fa-comment'; }
            else if (notifType === 'follow' || notifType === 'follow_request') { iconClass = 'follow'; icon = 'fa-user-plus'; }
            else if (notifType === 'tag' || notifType === 'mention') { iconClass = 'tag'; icon = 'fa-tag'; }
            return `<div class="notif-item ${n.is_read ? '' : 'unread'}" onclick="markNotifRead('${n.id}')" style="animation-delay: ${i * 0.05}s">
                <div class="notif-icon ${iconClass}"><i class="fas ${icon}"></i></div>
                <img src="${getProfilePic(actor)}" class="avatar-sm" alt="" onerror="this.src='/static/images/default-avatar.png'">
                <div class="notif-content"><p>${escapeHtml(message)}</p><span class="notif-time">${formatTime(n.created_at)}</span></div>
            </div>`;
        }).join('');
    } catch (e) {
        container.innerHTML = '<div class="empty-state fade-in"><i class="fas fa-exclamation-circle fa-3x"></i><h3>Error loading notifications</h3></div>';
    }
}

function setNotificationFilter(btn, filter) {
    document.querySelectorAll('.notif-filter').forEach((b) => b.classList.remove('active'));
    btn?.classList.add('active');
    loadNotifications();
}

async function markNotifRead(id) {
    try { await api(`/notifications/${id}/read`, { method: 'PUT' }); loadNotifications(); loadUnreadCount(); } catch (e) {}
}

async function markAllRead() {
    try { await api('/notifications/read-all', { method: 'PUT' }); loadNotifications(); loadUnreadCount(); } catch (e) {}
}

// ========================================================================
// 20. SEARCH
// ========================================================================
async function handleSearch(e) {
    if (e) e.preventDefault();
    const q = document.getElementById('search-input')?.value;
    if (!q) return;
    const container = document.getElementById('search-results');
    if (!container) return;
    try {
        container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        const results = await api(`/search?q=${encodeURIComponent(q)}`);
        let html = '';
        if (results.users && results.users.length > 0) {
            html += '<h3 style="font-weight:700;margin-bottom:12px">Users</h3>';
            html += results.users.map((u) => `<a href="/profile/${u.username}" class="search-user">
                <img src="${getProfilePic(u)}" class="avatar-sm" alt="" onerror="this.src='/static/images/default-avatar.png'">
                <span>${escapeHtml(u.username)}</span>
                ${u.is_verified ? '<i class="fas fa-check-circle verified"></i>' : ''}
            </a>`).join('');
        }
        if (results.posts && results.posts.length > 0) {
            html += '<h3 style="margin-top:20px;font-weight:700;margin-bottom:12px">Posts</h3>';
            html += results.posts.map((p) => renderPost(p)).join('');
        }
        if (!html) { html = '<div class="empty-state fade-in"><i class="fas fa-search fa-3x"></i><h3>No results found</h3></div>'; }
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="empty-state fade-in"><i class="fas fa-exclamation-circle fa-3x"></i><h3>Error searching</h3></div>';
    }
}

async function switchSearchTab(btn, tab) {
    document.querySelectorAll('.search-tab').forEach((t) => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    const input = document.getElementById('search-input');
    const container = document.getElementById('search-results');
    if (!container) return;
    const q = input?.value || '';
    try {
        container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        if (tab === 'top') {
            const data = await api(`/search?q=${encodeURIComponent(q)}`);
            container.innerHTML = [
                ...(data.users || []).slice(0, 5).map((u) => `<a href="/profile/${u.username}" class="search-user"><img src="${getProfilePic(u)}" class="avatar-sm"><span>${escapeHtml(u.username)}</span></a>`),
                ...(data.posts || []).map((p) => renderPost(p)),
                ...((data.hashtags || []).map((h) => `<button class="btn btn-outline btn-sm" onclick="document.getElementById('search-input').value='${String(h).replace('#', '')}';handleSearch(event)">${escapeHtml(h)}</button>`))
            ].join('') || '<div class="empty-state"><h3>No trending data yet</h3></div>';
        } else if (tab === 'users') {
            const data = await api(`/search?q=${encodeURIComponent(q)}&type=users`);
            container.innerHTML = (data.users || []).map((u) => `<a href="/profile/${u.username}" class="search-user"><img src="${getProfilePic(u)}" class="avatar-sm"><span>${escapeHtml(u.username)}</span></a>`).join('') || '<div class="empty-state"><h3>No users found</h3></div>';
        } else if (tab === 'tags') {
            const data = await api(`/search?q=${encodeURIComponent(q)}&type=hashtags`);
            container.innerHTML = (data.hashtags || []).map((h) => `<button class="btn btn-outline" onclick="document.getElementById('search-input').value='${String(h).replace('#', '')}';handleSearch(event)">${escapeHtml(h)}</button>`).join('') || '<div class="empty-state"><h3>No tags found</h3></div>';
        } else {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-map-marker-alt fa-3x"></i><h3>Places are local demo only</h3><p>No external location scraping is used.</p></div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><h3>Error loading tab</h3></div>';
    }
}

async function loadExplorePage() {
    const grid = document.getElementById('explore-grid');
    if (!grid) return;
    try {
        grid.innerHTML = Array(6).fill(0).map(() => '<div class="skeleton-card"><div class="skeleton" style="height:180px"></div></div>').join('');
        const data = await api('/posts/explore');
        const tags = (data.hashtags || []).map((h) => `<button class="btn btn-outline btn-sm" onclick="document.getElementById('search-input').value='${escapeHtml(h.tag)}';handleSearch(event)">#${escapeHtml(h.tag)} <small>${h.count}</small></button>`).join('');
        grid.innerHTML = `<div class="explore-tags">${tags || '<span class="card-kicker">No tags yet</span>'}</div>` + ((data.posts || []).length ? data.posts.map((p) => renderPost(p)).join('') : '<div class="empty-state"><i class="fas fa-compass fa-3x"></i><h3>No explore posts yet</h3></div>');
    } catch (e) { grid.innerHTML = `<div class="empty-state"><h3>Explore unavailable</h3><p>${escapeHtml(e.message)}</p></div>`; }
}

// ========================================================================
// 21. ADMIN DASHBOARD
// ========================================================================
async function generateCaptionForForm() {
    const active = document.activeElement && document.activeElement.tagName === 'TEXTAREA' ? document.activeElement : null;
    const form = active?.closest('form') || document.querySelector('form[data-advanced-form], form.post-form, #reel-upload-form') || document;
    const title = form.querySelector('[name="title"], #post-title, #caption-title')?.value || '';
    const description = form.querySelector('[name="description"], [name="content"], #caption-description, #reel-caption, #post-content')?.value || '';
    const category = form.querySelector('[name="category"], #caption-category, #product-category')?.value || '';
    const target = document.getElementById('caption-description') || document.getElementById('reel-caption') || active || form.querySelector('textarea');
    try {
        const data = await api('/ai/caption', { method: 'POST', body: JSON.stringify({ title, description, category }) });
        const text = [data.caption || '', (data.hashtags || []).join(' ')].filter(Boolean).join('\n\n');
        if (target) target.value = text;
        toast('Caption generated', 'success');
    } catch (e) { toast(e.message || 'Could not generate caption', 'error'); }
}

async function loadCreatorDashboard() {
    const root = document.getElementById('creator-dashboard-root');
    if (!root) return;
    root.innerHTML = `<div class="skeleton-card"><div class="skeleton" style="height:180px"></div></div>`;
    try {
        const data = await api('/creator/dashboard');
        const stats = [
            ['Posts', data.total_posts, 'fa-newspaper'], ['Reels', data.total_reels, 'fa-clapperboard'],
            ['Followers', data.followers, 'fa-users'], ['Following', data.following, 'fa-user-plus'],
            ['Likes', data.likes, 'fa-heart'], ['Comments', data.comments, 'fa-comments'],
            ['Views', data.views, 'fa-eye'], ['Engagement', `${data.engagement_rate || 0}%`, 'fa-chart-line']
        ];
        const chart = data.chart || [];
        const maxChart = Math.max(...chart, 1);
        root.innerHTML = `<div class="stats-grid advanced-stats-grid">
            ${stats.map(([label, value, icon], i) => `<div class="stat-card slide-up" style="animation-delay:${i * 0.04}s"><div class="stat-icon"><i class="fas ${icon}"></i></div><h3>${typeof value === 'number' ? value.toLocaleString() : escapeHtml(value)}</h3><div class="stat-label">${label}</div></div>`).join('')}
        </div><div class="card slide-up advanced-chart-card"><h3><i class="fas fa-chart-column"></i> Performance Overview</h3><div class="chart-bars modern-chart">${chart.map((value) => `<span title="${value}" style="height:${Math.max(10, (value / maxChart) * 180)}px"><b>${Number(value || 0).toLocaleString()}</b></span>`).join('')}</div><div class="chart-labels"><span>Posts</span><span>Reels</span><span>Likes</span><span>Comments</span><span>Views</span></div></div>`;
    } catch (e) { root.innerHTML = `<div class="empty-state fade-in"><i class="fas fa-chart-pie fa-3x"></i><h3>Could not load dashboard</h3><p>${escapeHtml(e.message)}</p></div>`; }
}

async function loadScheduledItems() {
    const list = document.getElementById('scheduled-list');
    if (!list) return;
    list.innerHTML = `<div class="skeleton-card"><div class="skeleton" style="height:120px"></div></div>`;
    try {
        const data = await api('/schedule/me');
        const items = data.items || [];
        list.innerHTML = items.length ? items.map((item) => `<div class="feature-card advanced-card slide-up" id="schedule-${item.id}"><div class="card-kicker"><i class="fas fa-clock"></i> ${escapeHtml(item.content_type || 'post')} · ${escapeHtml(item.status || 'pending')}</div><p>${escapeHtml(item.content || 'No caption')}</p>${(item.hashtags || []).length ? `<div class="tag-row">${item.hashtags.map((h) => `<span>#${escapeHtml(h)}</span>`).join('')}</div>` : ''}<small>${new Date(item.scheduled_at).toLocaleString()}</small><button class="btn btn-outline btn-sm" onclick="deleteScheduledItem('${item.id}')"><i class="fas fa-trash"></i> Delete</button></div>`).join('') : `<div class="empty-state"><i class="fas fa-calendar-xmark fa-3x"></i><h3>No scheduled posts</h3><p>Create one above to plan future content.</p></div>`;
    } catch (e) { list.innerHTML = `<div class="empty-state"><i class="fas fa-triangle-exclamation fa-3x"></i><h3>Error loading scheduled posts</h3><p>${escapeHtml(e.message)}</p></div>`; }
}

async function deleteScheduledItem(id) {
    if (!confirm('Delete this scheduled item?')) return;
    try { await api(`/schedule/${id}`, { method: 'DELETE' }); toast('Scheduled item deleted', 'success'); loadScheduledItems(); }
    catch (e) { toast(e.message || 'Delete failed', 'error'); }
}

function initScheduledPage() {
    const form = document.querySelector('[data-advanced-form="schedule"]');
    if (form && !form.dataset.bound) {
        form.dataset.bound = 'true';
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = form.querySelector('button[type="submit"]');
            const fd = new FormData(form);
            const payload = { content: fd.get('content') || '', content_type: fd.get('content_type') || 'post', hashtags: String(fd.get('hashtags') || '').split(',').map((h) => h.trim().replace(/^#/, '')).filter(Boolean), scheduled_at: fd.get('scheduled_at') };
            try { setButtonLoading(btn, true); await api('/schedule/post', { method: 'POST', body: JSON.stringify(payload) }); form.reset(); toast('Content scheduled', 'success'); loadScheduledItems(); }
            catch (err) { toast(err.message || 'Schedule failed', 'error'); }
            finally { setButtonLoading(btn, false); }
        });
    }
    loadScheduledItems();
}

async function loadMarketplaceProducts() {
    const list = document.getElementById('marketplace-list');
    if (!list) return;
    list.innerHTML = `<div class="skeleton-card"><div class="skeleton" style="height:220px"></div></div>`;
    try {
        const data = await api('/marketplace/products');
        const products = data.products || [];
        list.innerHTML = products.length ? products.map((p) => {
            const canDelete = currentUser && (currentUser.id === p.seller_id || currentUser.role === 'admin');
            return `<div class="product-card advanced-card slide-up" id="product-${p.id}"><img src="${p.image_url ? getMediaUrl(p.image_url) : '/static/images/default-cover.png'}" alt="${escapeHtml(p.title)}" onerror="this.onerror=null;this.src='/static/images/default-cover.png'"><div class="card-kicker">${escapeHtml(p.category || 'General')}</div><h3>${escapeHtml(p.title)}</h3><strong>₹${Number(p.price || 0).toLocaleString()}</strong><p>${escapeHtml(p.description || '')}</p><small>Seller: ${escapeHtml(p.seller?.username || 'SocialHub user')}</small><div class="card-actions"><button class="btn btn-primary btn-sm" onclick="window.location.href='/chat'"><i class="fas fa-message"></i> Message</button>${canDelete ? `<button class="btn btn-outline btn-sm" onclick="deleteMarketplaceProduct('${p.id}')"><i class="fas fa-trash"></i> Delete</button>` : ''}</div></div>`;
        }).join('') : `<div class="empty-state"><i class="fas fa-store-slash fa-3x"></i><h3>No products yet</h3><p>Add the first marketplace product.</p></div>`;
    } catch (e) { list.innerHTML = `<div class="empty-state"><i class="fas fa-triangle-exclamation fa-3x"></i><h3>Error loading marketplace</h3><p>${escapeHtml(e.message)}</p></div>`; }
}

async function deleteMarketplaceProduct(id) {
    if (!confirm('Delete this product?')) return;
    try { await api(`/marketplace/products/${id}`, { method: 'DELETE' }); toast('Product deleted', 'success'); loadMarketplaceProducts(); }
    catch (e) { toast(e.message || 'Delete failed', 'error'); }
}

function initMarketplacePage() {
    const form = document.querySelector('[data-advanced-form="marketplace"]');
    if (form && !form.dataset.bound) {
        form.dataset.bound = 'true';
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = form.querySelector('button[type="submit"]');
            try { setButtonLoading(btn, true); const res = await fetch(`${API}/marketplace/products`, { method: 'POST', headers: getMultipartHeaders(), body: new FormData(form) }); if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Product upload failed'); form.reset(); toast('Product added', 'success'); loadMarketplaceProducts(); }
            catch (err) { toast(err.message || 'Product upload failed', 'error'); }
            finally { setButtonLoading(btn, false); }
        });
    }
    loadMarketplaceProducts();
}

async function loadCollabOffers() {
    const list = document.getElementById('collabs-list');
    if (!list) return;
    list.innerHTML = `<div class="skeleton-card"><div class="skeleton" style="height:180px"></div></div>`;
    try {
        const data = await api('/collabs');
        const offers = data.offers || [];
        list.innerHTML = offers.length ? offers.map((o) => `<div class="collab-card advanced-card slide-up" id="collab-${o.id}"><div class="card-kicker"><i class="fas fa-handshake"></i> ${escapeHtml(o.category || 'General')}</div><h3>${escapeHtml(o.title)}</h3><p>${escapeHtml(o.description)}</p><strong>${escapeHtml(o.budget || 'Open budget')}</strong><small>Posted by ${escapeHtml(o.user?.username || 'SocialHub user')} · ${o.applications_count || 0} applications</small><button class="btn btn-primary btn-sm" onclick="applyToCollab('${o.id}')"><i class="fas fa-paper-plane"></i> Apply</button></div>`).join('') : `<div class="empty-state"><i class="fas fa-handshake-slash fa-3x"></i><h3>No collaboration offers</h3><p>Publish an offer above.</p></div>`;
    } catch (e) { list.innerHTML = `<div class="empty-state"><i class="fas fa-triangle-exclamation fa-3x"></i><h3>Error loading collaborations</h3><p>${escapeHtml(e.message)}</p></div>`; }
}

async function applyToCollab(id) {
    const message = prompt('Application message:');
    if (message === null) return;
    try { await api(`/collabs/${id}/apply`, { method: 'POST', body: JSON.stringify({ message }) }); toast('Application sent', 'success'); loadCollabOffers(); }
    catch (e) { toast(e.message || 'Could not apply', 'error'); }
}

function initCollabsPage() {
    const form = document.querySelector('[data-advanced-form="collab"]');
    if (form && !form.dataset.bound) {
        form.dataset.bound = 'true';
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = form.querySelector('button[type="submit"]');
            const payload = Object.fromEntries(new FormData(form).entries());
            try { setButtonLoading(btn, true); await api('/collabs', { method: 'POST', body: JSON.stringify(payload) }); form.reset(); toast('Collaboration offer published', 'success'); loadCollabOffers(); }
            catch (err) { toast(err.message || 'Could not publish offer', 'error'); }
            finally { setButtonLoading(btn, false); }
        });
    }
    loadCollabOffers();
}

async function loadAdminDashboard() {
    const dash = document.getElementById('admin-dashboard');
    if (!dash) return;
    try {
        const [d, creator] = await Promise.all([
            api('/admin/dashboard'),
            api('/admin/creator-dashboard')
        ]);
        const creatorCards = [
            ['Posts', creator.total_posts],
            ['Reels', creator.total_reels],
            ['Followers', creator.followers],
            ['Following', creator.following],
            ['Likes', creator.likes],
            ['Comments', creator.comments],
            ['Views', creator.views],
            ['Engagement', creator.engagement_rate]
        ];
        const chart = creator.chart || [];
        const maxChart = Math.max(...chart, 1);
        dash.innerHTML = `<div class="stats-grid">
            <div class="stat-card users slide-up"><div class="stat-icon"><i class="fas fa-users"></i></div><h3>${d.total_users || 0}</h3><div class="stat-label">Total Users</div></div>
            <div class="stat-card posts slide-up"><div class="stat-icon"><i class="fas fa-newspaper"></i></div><h3>${d.total_posts || 0}</h3><div class="stat-label">Total Posts</div></div>
            <div class="stat-card reports slide-up"><div class="stat-icon"><i class="fas fa-flag"></i></div><h3>${d.total_reports || 0}</h3><div class="stat-label">Total Reports</div></div>
            <div class="stat-card active slide-up"><div class="stat-icon"><i class="fas fa-circle"></i></div><h3>${d.active_users_today || 0}</h3><div class="stat-label">Active Today</div></div>
        </div>
        <div class="card slide-up" style="margin-top:24px;margin-bottom:18px">
            <h2 style="font-size:24px;font-weight:800;margin-bottom:8px"><i class="fas fa-chart-pie"></i> All Creator Dashboard</h2>
            <p style="color:var(--text-secondary)">Admin overview of all posts, reels, engagement, comments, likes, followers, and views.</p>
        </div>
        <div class="stats-grid">
            ${creatorCards.map(([label, value]) => `<div class="stat-card slide-up"><h3>${Number(value || 0).toLocaleString()}</h3><div class="stat-label">${label}</div></div>`).join('')}
        </div>
        <div class="card slide-up" style="margin-top:18px;min-height:220px">
            <h3 style="margin-bottom:20px">Performance Chart</h3>
            <div style="display:flex;align-items:flex-end;gap:12px;height:130px">
                ${chart.map((value, index) => `<div title="${value}" style="flex:1;height:${Math.max(10, (value / maxChart) * 100)}%;border-radius:8px;background:linear-gradient(90deg,#fd8d32,#e1306c,#c13584)"></div>`).join('')}
            </div>
            <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:10px;color:var(--text-secondary);font-size:12px;text-align:center">
                <span>Posts</span><span>Reels</span><span>Likes</span><span>Comments</span><span>Views</span>
            </div>
        </div>`;
    } catch (e) { dash.innerHTML = '<div class="empty-state fade-in"><i class="fas fa-lock fa-3x"></i><h3>Admin access required</h3></div>'; }
}

function initAdminTabs() {
    document.querySelectorAll('[data-admin-tab]').forEach((link) => {
        if (link.dataset.bound) return;
        link.dataset.bound = 'true';
        link.addEventListener('click', (event) => {
            event.preventDefault();
            document.querySelectorAll('[data-admin-tab]').forEach((l) => l.classList.remove('active'));
            link.classList.add('active');
            loadAdminTab(link.dataset.adminTab);
        });
    });
}

async function loadAdminTab(tab = 'dashboard') {
    const dash = document.getElementById('admin-dashboard');
    if (!dash) return;
    if (tab === 'dashboard') return loadAdminDashboard();
    dash.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading admin data...</p></div>';
    try {
        if (tab === 'users') {
            const data = await api('/admin/users?page_size=50');
            const users = data.users || [];
            dash.innerHTML = `<div class="card"><h2><i class="fas fa-users"></i> Users</h2></div>${users.length ? `<div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>User</th><th>Name</th><th>Followers</th><th>Verified</th><th>Actions</th></tr></thead><tbody>${users.map((u) => `<tr><td><a href="/profile/${u.username}">@${escapeHtml(u.username)}</a></td><td>${escapeHtml(u.full_name || '')}</td><td>${u.followers_count || 0}</td><td>${u.is_verified ? 'Yes' : 'No'}</td><td><button class="btn btn-outline btn-sm" onclick="adminVerifyUser('${u.id}')">Verify</button><button class="btn btn-outline btn-sm" onclick="adminBanUser('${u.id}', true)">Ban</button></td></tr>`).join('')}</tbody></table></div>` : '<div class="empty-state"><i class="fas fa-user-slash fa-3x"></i><h3>No users found</h3></div>'}`;
        } else if (tab === 'posts') {
            const data = await api('/admin/posts?page_size=50');
            const posts = data.posts || [];
            dash.innerHTML = `<div class="card"><h2><i class="fas fa-newspaper"></i> Posts</h2></div>${posts.length ? posts.map((p) => `<div class="post-card"><div class="post-header"><strong>@${escapeHtml(p.author?.username || 'user')}</strong><button class="btn btn-outline btn-sm" onclick="adminRemoveContent('post','${p.id}')"><i class="fas fa-trash"></i> Remove</button></div><p>${escapeHtml(p.content || '')}</p><small>${formatTime(p.created_at)}</small></div>`).join('') : '<div class="empty-state"><i class="fas fa-newspaper fa-3x"></i><h3>No posts found</h3></div>'}`;
        } else if (tab === 'reports') {
            const data = await api('/admin/reports?page_size=50');
            const reports = data.reports || [];
            dash.innerHTML = `<div class="card"><h2><i class="fas fa-flag"></i> Reports</h2></div>${reports.length ? reports.map((r) => `<div class="feature-card"><div class="card-kicker">${escapeHtml(r.status || 'pending')}</div><h3>${escapeHtml(r.reason || 'Report')}</h3><p>${escapeHtml(r.description || '')}</p><small>${formatTime(r.created_at)}</small><div class="card-actions"><button class="btn btn-primary btn-sm" onclick="adminUpdateReport('${r.id}','reviewed')">Mark reviewed</button><button class="btn btn-outline btn-sm" onclick="adminUpdateReport('${r.id}','resolved')">Resolve</button></div></div>`).join('') : '<div class="empty-state"><i class="fas fa-flag fa-3x"></i><h3>No reports</h3></div>'}`;
        } else {
            dash.innerHTML = `<div class="card"><h2><i class="fas fa-cog"></i> Admin Settings</h2><p style="color:var(--text-secondary)">Use the sidebar to manage users, posts, reports, backups, marketplace and collaborations.</p><button class="btn btn-primary" onclick="adminBackup()"><i class="fas fa-database"></i> Create Backup</button></div>`;
        }
    } catch (e) {
        dash.innerHTML = `<div class="empty-state fade-in"><i class="fas fa-triangle-exclamation fa-3x"></i><h3>Error loading ${escapeHtml(tab)}</h3><p>${escapeHtml(e.message)}</p></div>`;
    }
}

async function adminVerifyUser(userId) {
    try { await api(`/admin/users/${userId}/verify`, { method: 'POST' }); toast('User verified', 'success'); loadAdminTab('users'); }
    catch (e) { toast(e.message || 'Could not verify user', 'error'); }
}

async function adminBanUser(userId, isBanned) {
    if (!confirm(isBanned ? 'Ban this user?' : 'Unban this user?')) return;
    try { await api(`/admin/users/${userId}/ban?is_banned=${isBanned}`, { method: 'POST' }); toast(isBanned ? 'User banned' : 'User unbanned', 'success'); loadAdminTab('users'); }
    catch (e) { toast(e.message || 'Could not update user', 'error'); }
}

async function adminRemoveContent(type, id) {
    if (!confirm(`Remove this ${type}?`)) return;
    try { await api(`/admin/remove/${type}/${id}`, { method: 'POST' }); toast(`${type} removed`, 'success'); loadAdminTab('posts'); }
    catch (e) { toast(e.message || 'Could not remove content', 'error'); }
}

async function adminUpdateReport(reportId, status) {
    try { await api(`/admin/reports/${reportId}`, { method: 'PUT', body: JSON.stringify({ status }) }); toast('Report updated', 'success'); loadAdminTab('reports'); }
    catch (e) { toast(e.message || 'Could not update report', 'error'); }
}

async function adminBackup() {
    if (!confirm('Create a backup zip of the SQLite database and uploads folder?')) return;
    try {
        const data = await api('/admin/backup', { method: 'POST' });
        toast(data.message || 'Backup created', 'success');
    } catch (e) {
        toast(e.message || 'Backup failed', 'error');
    }
}

// ========================================================================
// 22. SETTINGS
// ========================================================================
function handleUpdateProfile(e) {
    e.preventDefault();
    const fullName = document.getElementById('settings-fullname').value;
    const bio = document.getElementById('settings-bio').value;
    const website = document.getElementById('settings-website')?.value || '';
    const location = document.getElementById('settings-location')?.value || '';
    const phone = document.getElementById('settings-phone')?.value || '';
    const btn = e.target.querySelector('button[type="submit"]');
    setButtonLoading(btn, true);
    const socialLinks = ['instagram', 'youtube', 'website', 'linkedin', 'twitter'].map((platform) => {
        const url = document.getElementById(`settings-social-${platform}`)?.value || '';
        return url ? { platform, url } : null;
    }).filter(Boolean);
    api('/users/profile', { method: 'PUT', body: JSON.stringify({ full_name: fullName, bio, website, location, phone_number: phone }) })
        .then(() => socialLinks.length ? api('/users/profile/social-links', { method: 'PUT', body: JSON.stringify(socialLinks) }) : null)
        .then(() => { toast('Profile updated!', 'success'); if (typeof loadNavAvatar === 'function') loadNavAvatar(); })
        .catch((e) => toast(e.message, 'error'))
        .finally(() => setButtonLoading(btn, false));
}

async function changePasswordPrompt() {
    const current_password = prompt('Current password:');
    if (!current_password) return;
    const new_password = prompt('New password (min 6 chars, uppercase, lowercase, number):');
    if (!new_password) return;
    try {
        await api('/auth/change-password', { method: 'POST', body: JSON.stringify({ current_password, new_password }) });
        toast('Password changed successfully', 'success');
    } catch (e) {
        toast(e.message || 'Could not change password', 'error');
    }
}

async function loadNotificationSettingsPrompt() {
    try {
        const s = await api('/notifications/settings');
        toast(`Notifications: likes ${s.likes ? 'on' : 'off'}, comments ${s.comments ? 'on' : 'off'}, follows ${s.follows ? 'on' : 'off'}`, 'info');
    } catch (e) {
        toast(e.message || 'Could not load notification settings', 'error');
    }
}

function showPrivacyInfo() {
    toast('Privacy controls are enforced by public/private account type in Edit Profile.', 'info');
}

function uploadProfilePic(e) {
    const file = e.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    fetch(API + '/users/profile/picture', { method: 'POST', headers: { 'Authorization': `Bearer ${token}` }, body: form })
        .then((res) => res.json())
        .then((data) => {
            const raw = data.profile_picture || data.file_path || data.filename || data.path || '';
            if (!raw || raw === 'undefined' || raw === 'null') { toast('Upload succeeded but path not returned. Please refresh.', 'error'); return; }
            const src = getMediaUrl(raw);
            const avatar = document.getElementById('settings-avatar');
            if (avatar) avatar.src = src;
            toast('Profile picture updated!', 'success');
            if (typeof loadNavAvatar === 'function') loadNavAvatar();
        })
        .catch(() => toast('Error uploading', 'error'));
}

function uploadCoverPhoto(e) {
    const file = e.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    fetch(API + '/users/profile/cover', { method: 'POST', headers: getMultipartHeaders(), body: form })
        .then((res) => { if (!res.ok) throw new Error('Upload failed'); return res.json(); })
        .then((data) => {
            const cover = document.getElementById('settings-cover');
            if (cover) cover.src = getMediaUrl(data.cover_photo);
            toast('Cover photo updated!', 'success');
        })
        .catch((e) => toast(e.message || 'Error uploading cover', 'error'));
}

async function createStoryFromUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById('story-file');
    const caption = document.getElementById('story-caption')?.value || '';
    const btn = e.target.querySelector('button[type="submit"]');
    if (!fileInput?.files?.[0]) return toast('Choose an image or video first', 'error');
    const form = new FormData();
    form.append('file', fileInput.files[0]);
    form.append('caption', caption);
    try {
        setButtonLoading(btn, true);
        const res = await fetch(`${API}/stories`, { method: 'POST', headers: getMultipartHeaders(), body: form });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Could not upload story');
        e.target.reset();
        toast('Story uploaded', 'success');
        loadStories();
    } catch (err) { toast(err.message, 'error'); } finally { setButtonLoading(btn, false); }
}

function ensureSettingsSocialFields() {
    const emailField = document.getElementById('settings-email');
    if (!emailField || document.getElementById('settings-social-instagram')) return;
    emailField.closest('.form-group')?.insertAdjacentHTML('afterend', `
        <div class="form-group"><label>Website</label><input id="settings-website" placeholder="https://your-site.com"></div>
        <div class="form-group"><label>Location</label><input id="settings-location" placeholder="City, Country"></div>
        <div class="form-group"><label>Social Links</label><div class="social-link-grid">
            <input id="settings-social-instagram" placeholder="Instagram URL (official profile link only)">
            <input id="settings-social-youtube" placeholder="YouTube URL">
            <input id="settings-social-linkedin" placeholder="LinkedIn URL">
            <input id="settings-social-twitter" placeholder="X / Twitter URL">
        </div></div>`);
}

async function deleteStory(id) {
    if (!confirm('Delete this story?')) return;
    try { await api(`/stories/${id}`, { method: 'DELETE' }); toast('Story deleted', 'success'); document.getElementById('story-viewer')?.classList.remove('active'); loadStories(); }
    catch (e) { toast(e.message, 'error'); }
}

// ========================================================================
// 23. LOAD SUGGESTIONS
// ========================================================================
async function loadSuggestions() {
    const el = document.getElementById('suggestions-sidebar');
    if (!el) return;
    try {
        const results = await api('/users/suggestions');
        if (results && results.length > 0) {
            el.innerHTML = results.slice(0, 5).map((u) => `<div class="suggestion-item">
                <img src="${getProfilePic(u)}" class="avatar-sm" alt="" onerror="this.src='/static/images/default-avatar.png'">
                <div class="info"><div class="name">${escapeHtml(u.username)}</div><div class="sub">${escapeHtml(u.full_name || '')}</div></div>
                <button class="follow-btn" onclick="toggleFollow('${u.id}', this)">Follow</button>
            </div>`).join('');
        } else {
            el.innerHTML = '<div style="color:var(--text-secondary);font-size:12px;padding:8px 0">No suggestions yet</div>';
        }
    } catch (e) { el.innerHTML = ''; }
}

// ========================================================================
// 24. GLOBAL IMAGE ERROR HANDLER
// ========================================================================
function setupGlobalImageFallback() {
    document.addEventListener('error', function(e) {
        if (e.target.tagName === 'IMG') { e.target.onerror = null; e.target.src = '/static/images/default-avatar.png'; }
    }, true);
}

// ========================================================================
// 25. DARK / LIGHT MODE TOGGLE
// ========================================================================
function toggleTheme() {
    document.body.classList.toggle('light-mode');
    localStorage.setItem('theme', document.body.classList.contains('light-mode') ? 'light' : 'dark');
}

function loadTheme() {
    const theme = localStorage.getItem('theme');
    if (theme === 'light') document.body.classList.add('light-mode');
}

// ========================================================================
// 26. DATA STUDIO FUNCTIONS
// ========================================================================
function showDataStudioToast(message, type = 'info') {
    const toast = document.getElementById('studioToast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = 'studio-toast show ' + type;
    toast.style.display = 'block';
    setTimeout(() => { toast.className = 'studio-toast'; toast.style.display = 'none'; }, 4000);
}

function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function loadDataStudioStats() {
    try {
        const stats = await api('/data-studio/stats');
        document.getElementById('stat-users').textContent = (stats.total_users || 0).toLocaleString();
        document.getElementById('stat-posts').textContent = (stats.total_posts || 0).toLocaleString();
        document.getElementById('stat-photos').textContent = (stats.total_photos || 0).toLocaleString();
        document.getElementById('stat-videos').textContent = (stats.total_videos || 0).toLocaleString();
        document.getElementById('stat-reels').textContent = (stats.total_reels || 0).toLocaleString();
        document.getElementById('stat-follows').textContent = (stats.total_follow_relations || 0).toLocaleString();
    } catch (e) {
        console.error('Error loading stats:', e);
    }
}

async function seed10kData() {
    const usersCount = parseInt(document.getElementById('usersCount').value) || 10000;
    const postsPerUser = parseInt(document.getElementById('postsPerUser').value) || 3;
    const reelsCount = parseInt(document.getElementById('reelsCount').value) || 2000;
    const followEdges = parseInt(document.getElementById('followEdges').value) || 15000;
    
    const btn = document.getElementById('generateBtn');
    const btnText = btn.querySelector('.btn-text');
    const btnLoading = btn.querySelector('.btn-loading');
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    setButtonLoading(btn, true);
    btnText.style.display = 'none';
    btnLoading.style.display = 'inline';
    progressContainer.style.display = 'block';
    
    try {
        const formData = new FormData();
        formData.append('users_count', usersCount);
        formData.append('posts_per_user', postsPerUser);
        formData.append('reels_count', reelsCount);
        formData.append('follow_edges_count', followEdges);
        
        progressFill.style.width = '10%';
        progressText.textContent = 'Creating users...';
        
        const res = await fetch(`${API}/data-studio/seed-10k`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData,
        });
        
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Failed to generate data');
        }
        
        const data = await res.json();
        progressFill.style.width = '100%';
        progressText.textContent = data.message || 'Complete!';
        
        showDataStudioToast(`Success! ${data.users_created} users, ${data.posts_created} posts, ${data.reels_created} reels created`, 'success');
        loadDataStudioStats();
        loadDataStudioUsers(1);
        
        setTimeout(() => {
            progressContainer.style.display = 'none';
            progressFill.style.width = '0%';
        }, 3000);
    } catch (e) {
        progressText.textContent = 'Error: ' + e.message;
        showDataStudioToast('Error: ' + e.message, 'error');
    } finally {
        setButtonLoading(btn, false);
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
    }
}

async function deleteDemoBatch(batchId) {
    if (!confirm('Delete this demo batch? This will mark it as deleted.')) return;
    try {
        await api(`/data-studio/demo-batch/${batchId}`, { method: 'DELETE' });
        showDataStudioToast('Batch deleted successfully', 'success');
        loadDataStudioStats();
    } catch (e) {
        showDataStudioToast('Error deleting batch: ' + e.message, 'error');
    }
}

async function loadDataStudioUsers(page = 1) {
    const tbody = document.getElementById('userTableBody');
    if (!tbody) return;
    const search = document.getElementById('userSearch')?.value || '';
    
    try {
        const data = await api(`/data-studio/users?page=${page}&limit=20&search=${encodeURIComponent(search)}`);
        if (!data.users || data.users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:20px">No users found</td></tr>';
            return;
        }
        tbody.innerHTML = data.users.map((u) => `<tr>
            <td>${escapeHtml(u.username)}</td>
            <td>${escapeHtml(u.full_name || '')}</td>
            <td>${escapeHtml(u.email)}</td>
            <td>${u.is_verified ? '✅' : '❌'}</td>
            <td>${(u.followers_count || 0).toLocaleString()}</td>
            <td>${(u.following_count || 0).toLocaleString()}</td>
            <td>${(u.posts_count || 0).toLocaleString()}</td>
        </tr>`).join('');
        
        renderPagination('userPagination', data.page, data.total_pages, (p) => loadDataStudioUsers(p));
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:20px">Error loading users</td></tr>';
    }
}

function renderPagination(containerId, currentPage, totalPages, onPageClick) {
    const container = document.getElementById(containerId);
    if (!container || totalPages <= 1) return;
    let html = '';
    html += `<button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="(${onPageClick})(${currentPage - 1})">Prev</button>`;
    for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
        html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="(${onPageClick})(${i})">${i}</button>`;
    }
    html += `<button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="(${onPageClick})(${currentPage + 1})">Next</button>`;
    container.innerHTML = html;
}

async function loadFollowGraph() {
    try {
        const graph = await api('/data-studio/follow-graph?limit=200');
        document.getElementById('graphNodes').textContent = (graph.nodes || []).length;
        document.getElementById('graphEdges').textContent = (graph.edges || []).length;
        document.getElementById('graphContainer').style.display = 'block';
        showDataStudioToast(`Loaded ${graph.nodes.length} nodes and ${graph.edges.length} edges`, 'info');
    } catch (e) {
        showDataStudioToast('Error loading graph: ' + e.message, 'error');
    }
}

async function uploadOriginalMedia() {
    const fileInput = document.getElementById('mediaFile');
    const ownershipConfirmed = document.getElementById('ownershipConfirm').checked;
    
    if (!fileInput.files[0]) {
        showDataStudioToast('Please select a file', 'error');
        return;
    }
    if (!ownershipConfirmed) {
        showDataStudioToast('You must confirm ownership', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('ownership_confirmed', 'true');
    
    try {
        const res = await fetch(`${API}/data-studio/media/original/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData,
        });
        
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Upload failed');
        }
        
        const data = await res.json();
        showDataStudioToast('Media uploaded successfully!', 'success');
        fileInput.value = '';
        document.getElementById('ownershipConfirm').checked = false;
        loadOriginalMedia();
    } catch (e) {
        showDataStudioToast('Upload error: ' + e.message, 'error');
    }
}

async function loadOriginalMedia() {
    const grid = document.getElementById('mediaGrid');
    if (!grid) return;
    
    try {
        const data = await api('/data-studio/media/original?page=1&limit=20');
        if (!data.assets || data.assets.length === 0) {
            grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><i class="fas fa-folder-open fa-3x"></i><h3>No media uploaded yet</h3></div>';
            return;
        }
        grid.innerHTML = data.assets.map((a) => `<div class="original-media-item">
            <div class="media-preview">
                ${a.media_type === 'image' 
                    ? `<img src="${getMediaUrl(a.url || ('original_media/' + (currentUser?.id || '') + '/' + a.filename))}" alt="${escapeHtml(a.original_filename)}" onerror="this.src='/static/images/default-avatar.png'">`
                    : `<video src="${getMediaUrl(a.url || ('original_media/' + (currentUser?.id || '') + '/' + a.filename))}" controls></video>`
                }
            </div>
            <div class="media-info">
                <p class="media-name">${escapeHtml(a.original_filename)}</p>
                <p class="media-meta">${formatFileSize(a.file_size)} • ${a.media_type}</p>
                <div class="media-actions">
                    <button class="btn btn-sm btn-primary" onclick="createPostFromAsset('${a.id}')">Create Post</button>
                    ${a.media_type === 'video' ? '<button class="btn btn-sm btn-secondary" onclick="createReelFromAsset(\'' + a.id + '\')">Create Reel</button>' : ''}
                </div>
            </div>
        </div>`).join('');
    } catch (e) {
        grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><i class="fas fa-exclamation-circle fa-3x"></i><h3>Error loading media</h3></div>';
    }
}

async function createPostFromAsset(assetId) {
    const caption = prompt('Enter caption for this post:');
    if (!caption) return;
    try {
        const formData = new FormData();
        formData.append('caption', caption);
        await api(`/data-studio/media/original/${assetId}/create-post`, { method: 'POST', body: formData, multipart: true });
        showDataStudioToast('Post created successfully!', 'success');
    } catch (e) {
        showDataStudioToast('Error creating post: ' + e.message, 'error');
    }
}

async function createReelFromAsset(assetId) {
    const caption = prompt('Enter caption for this reel:');
    if (!caption) return;
    try {
        const formData = new FormData();
        formData.append('caption', caption);
        await api(`/data-studio/media/original/${assetId}/create-reel`, { method: 'POST', body: formData, multipart: true });
        showDataStudioToast('Reel created successfully!', 'success');
    } catch (e) {
        showDataStudioToast('Error creating reel: ' + e.message, 'error');
    }
}

function updateDataStudioProfileLink() {
    const link = document.getElementById('data-studio-profile-link');
    if (link && currentUser?.username) link.href = `/profile/${currentUser.username}`;
}

// ========================================================================
// 27. ROUTER & INITIALIZATION
// ========================================================================
async function initApp() {
    const path = window.location.pathname;
    loadTheme();
    animatePageLoad();
    ensureGlobalShell();
    buildTopSearchBar();
    ensureMobileBottomNav();

    if (path === '/login' || path === '/register') clearTokens();
    await hydrateCurrentUser();
    updateNav();

    if (path === '/' || path === '/posts') {
        loadFeed();
        if (isLoggedIn()) { loadSuggestions(); loadStories(); }
    } else if (path === '/login') {
        const f = document.getElementById('login-form');
        if (f) f.addEventListener('submit', handleLogin);
        const toggleBtn = document.getElementById('password-toggle');
        if (toggleBtn) toggleBtn.addEventListener('click', () => togglePassword('password', toggleBtn));
    } else if (path === '/register') {
        const f = document.getElementById('register-form');
        if (f) f.addEventListener('submit', handleRegister);
        const toggleBtn = document.getElementById('password-toggle');
        if (toggleBtn) toggleBtn.addEventListener('click', () => togglePassword('password', toggleBtn));
    } else if (path.startsWith('/profile/')) {
        loadProfile();
    } else if (path === '/stories') {
        loadStories();
        const storyForm = document.getElementById('story-upload-form');
        if (storyForm) storyForm.addEventListener('submit', createStoryFromUpload);
    } else if (path === '/reels') {
        loadReels();
        const reelForm = document.getElementById('reel-upload-form');
        if (reelForm) reelForm.addEventListener('submit', createReelFromUpload);
    } else if (path === '/creator-dashboard') {
        loadCreatorDashboard();
    } else if (path === '/scheduled') {
        initScheduledPage();
    } else if (path === '/marketplace') {
        initMarketplacePage();
    } else if (path === '/collabs') {
        initCollabsPage();
    } else if (path === '/data-studio') {
        if (isLoggedIn()) {
            updateDataStudioProfileLink();
            loadDataStudioStats();
            loadDataStudioUsers(1);
            loadOriginalMedia();
        }
        const seedForm = document.getElementById('seedForm');
        if (seedForm) seedForm.addEventListener('submit', (e) => { e.preventDefault(); seed10kData(); });
        const uploadForm = document.getElementById('uploadForm');
        if (uploadForm) uploadForm.addEventListener('submit', (e) => { e.preventDefault(); uploadOriginalMedia(); });
        const searchBtn = document.getElementById('searchBtn');
        if (searchBtn) searchBtn.addEventListener('click', () => loadDataStudioUsers(1));
        const userSearch = document.getElementById('userSearch');
        if (userSearch) userSearch.addEventListener('keypress', (e) => { if (e.key === 'Enter') loadDataStudioUsers(1); });
        const loadGraphBtn = document.getElementById('loadGraphBtn');
        if (loadGraphBtn) loadGraphBtn.addEventListener('click', loadFollowGraph);
        const loadLogsBtn = document.getElementById('loadLogsBtn');
        if (loadLogsBtn) loadLogsBtn.addEventListener('click', () => loadOriginalMedia());
    } else if (path === '/chat') {
        loadChats();
        document.getElementById('message-input')?.addEventListener('input', notifyTyping);
    } else if (path.startsWith('/chat/')) {
        const chatId = path.split('/chat/')[1];
        currentChatId = chatId;
        loadChatMessages(chatId);
        document.getElementById('message-input')?.addEventListener('input', notifyTyping);
    } else if (path === '/notifications') {
        loadNotifications();
    } else if (path === '/search' || path === '/explore') {
        const f = document.getElementById('search-form');
        if (f) f.addEventListener('submit', handleSearch);
        const params = new URLSearchParams(window.location.search);
        const initialQ = params.get('q');
        if (initialQ) { const input = document.getElementById('search-input'); if (input) input.value = initialQ; handleSearch(); }
        if (path === '/explore' || !initialQ) loadExplorePage();
    } else if (path === '/bookmarks') {
        loadSavedCenter('all');
    } else if (path === '/admin') {
        initAdminTabs();
        loadAdminDashboard();
    } else if (path === '/settings') {
        ensureSettingsSocialFields();
        if (isLoggedIn()) {
            api('/auth/me').then((user) => {
                currentUser = user;
                const avatar = document.getElementById('settings-avatar');
                if (avatar) avatar.src = getProfilePic(user);
                const fn = document.getElementById('settings-fullname');
                if (fn) fn.value = user.full_name || '';
                const e = document.getElementById('settings-email');
                if (e) e.value = user.email || '';
                return api(`/users/profile/${user.username}`);
            }).then((profile) => {
                if (!profile) return;
                const b = document.getElementById('settings-bio');
                if (b) b.value = (profile.bio || '');
                const cover = document.getElementById('settings-cover');
                if (cover && profile.cover_photo) cover.src = getMediaUrl(profile.cover_photo);
                document.getElementById('settings-website') && (document.getElementById('settings-website').value = profile.website || '');
                document.getElementById('settings-location') && (document.getElementById('settings-location').value = profile.location || '');
                (profile.social_links || []).forEach((link) => { const field = document.getElementById(`settings-social-${link.platform}`); if (field) field.value = link.url || ''; });
            }).catch(() => {});
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    setupGlobalImageFallback();
    initApp();
});