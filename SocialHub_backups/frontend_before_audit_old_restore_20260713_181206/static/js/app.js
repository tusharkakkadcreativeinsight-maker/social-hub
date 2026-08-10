import { api, clearTokens, getToken, hydrateCurrentUser, setTokens } from './core/api.js';
import { escapeHTML, qs, qsa, text, create, debounce } from './core/dom.js';
import { mediaUrl, avatarUrl, coverUrl, bindImageFallbacks } from './core/media.js';
import { initTheme, setTheme, toggleTheme } from './core/theme.js';
import { openModal, closeModal, closeAllModals, trapFocus } from './core/modal.js';
import { toast } from './core/toast.js';
import { createSocket } from './core/websocket.js';
import { renderPostCard } from './components/post-card.js';
import { renderReelCard, observeReelVideos } from './components/reel-card.js';
import { bindUploadPreview } from './components/upload-preview.js';

let currentUser = null;
let activePostId = null;
let activeChatId = null;
let chatSocket = null;
let liveSocket = null;
let liveStream = null;

function endpointData(value, fallback = []) { return Array.isArray(value) ? value : (value?.items || value?.results || value?.posts || value?.reels || value?.notifications || fallback); }
function setHTML(el, html) { if (el) el.innerHTML = html; }
function empty(icon, title, body='') { return `<div class="empty-state"><i class="fas fa-${icon}"></i><h3>${escapeHTML(title)}</h3><p class="muted">${escapeHTML(body)}</p></div>`; }
function skeleton(el) { setHTML(el, '<div class="skeleton-list"></div>'); }
function isLoggedIn(){ return Boolean(getToken()); }

async function initShell(){
  currentUser = await hydrateCurrentUser().catch(()=>null);
  qsa('[data-admin-only]').forEach(el => { if (!currentUser?.is_admin) el.hidden = true; });
  qsa('#topbar-avatar,.user-avatar').forEach(img => { img.src = avatarUrl(currentUser?.profile_picture || currentUser?.avatar_url); });
  qsa('a[data-nav="profile"]').forEach(a => { a.href = currentUser?.username ? `/profile/${encodeURIComponent(currentUser.username)}` : '/profile/me'; });
  const page = document.body.dataset.page || 'home';
  qsa('[data-nav]').forEach(a => a.classList.toggle('active', a.dataset.nav === page || (page === 'home' && a.dataset.nav === 'home')));
  await Promise.allSettled([loadUnreadCount(), loadRightRail()]);
}

async function loadUnreadCount(){
  if(!isLoggedIn()) return;
  const d = await api.get('/notifications/unread-count', { silent:true }).catch(()=>null);
  const count = d?.count || d?.unread_count || 0;
  const badge = qs('#notif-badge');
  if (badge) { badge.textContent = count; badge.classList.toggle('hidden', !count); }
  qsa('[data-unread-badge]').forEach(b => b.classList.toggle('hidden', !count));
}

async function loadRightRail(){
  const tags = await api.get('/hashtags/trending', { silent:true }).catch(()=>null);
  const list = endpointData(tags, tags?.hashtags || []).slice(0,8);
  setHTML(qs('#right-trending-tags'), list.length ? list.map(t => `<a href="/hashtag/${encodeURIComponent((t.tag||t.name||t.hashtag||'').replace(/^#/,''))}">#${escapeHTML((t.tag||t.name||t.hashtag||'socialhub').replace(/^#/,''))}</a>`).join('') : '<span class="muted">No trends yet</span>');
  if (!isLoggedIn()) return;
  const sug = await api.get('/users/suggestions', { silent:true }).catch(()=>null);
  const users = endpointData(sug, sug?.users || []).slice(0,5);
  setHTML(qs('#suggestions-list'), users.length ? users.map(u => `<a class="list-item" href="/profile/${encodeURIComponent(u.username)}"><img class="avatar-sm" src="${avatarUrl(u.profile_picture)}" alt=""><span><b>${escapeHTML(u.username)}</b><small class="muted">${escapeHTML(u.full_name||'Creator')}</small></span></a>`).join('') : '<div class="empty-state compact">No suggestions yet.</div>');
}

async function initHomePage(){ await Promise.allSettled([loadStories(), loadFeed()]); }
async function initPostsPage(){ await loadFeed(); }
async function loadStories(){
  const box = qs('#stories-container,#story-tray'); if(!box) return; skeleton(box);
  const d = await api.get('/stories', { silent:true }).catch(()=>null);
  const stories = endpointData(d, d?.stories || []).slice(0,16);
  box.innerHTML = `<button class="story-bubble" data-action="open-modal" data-target="create-story-modal"><img src="${avatarUrl(currentUser?.profile_picture)}" alt="Your story"><span>Your story</span></button>` + (stories.length ? stories.map(s => `<button class="story-bubble" data-action="view-story" data-story-id="${escapeHTML(s.id)}"><img src="${avatarUrl(s.user?.profile_picture || s.author?.profile_picture)}" alt="${escapeHTML(s.user?.username || 'Story')}"><span>${escapeHTML(s.user?.username || s.author?.username || 'story')}</span></button>`).join('') : '');
}

let feedPage = 1, feedLoading = false, feedDone = false;
async function loadFeed(reset=false){
  const feed = qs('#feed-posts'); if(!feed || feedLoading || feedDone) return;
  if(reset){ feedPage=1; feedDone=false; feed.innerHTML=''; }
  feedLoading = true; if(feedPage===1) skeleton(feed);
  try{
    const d = await api.get(`/posts?page=${feedPage}&page_size=10`);
    const posts = d?.posts || endpointData(d, []);
    if(feedPage===1) feed.innerHTML='';
    if(!posts.length && feedPage===1) feed.innerHTML = empty('newspaper','No posts yet','Follow creators or publish your first post.');
    posts.forEach(p => feed.insertAdjacentHTML('beforeend', renderPostCard(p)));
    feedDone = posts.length < 10; feedPage += 1;
    bindImageFallbacks(feed);
    const sentinel = qs('#feed-sentinel');
    if(sentinel && !sentinel.dataset.bound){ sentinel.dataset.bound='1'; new IntersectionObserver(e=>{ if(e[0].isIntersecting) loadFeed(); },{rootMargin:'400px'}).observe(sentinel); }
  } catch(e){ feed.innerHTML = empty('triangle-exclamation','Could not load feed', e.message || 'Please retry.'); }
  finally{ feedLoading = false; }
}

async function initReelsPage(){
  const c = qs('#reels-container'); if(!c) return; skeleton(c);
  const d = await api.get('/reels?page=1&page_size=20').catch(e=>({error:e.message}));
  const reels = d?.reels || endpointData(d, []);
  c.innerHTML = reels.length ? reels.map(renderReelCard).join('') : empty('clapperboard','No reels yet','Upload the first reel.');
  observeReelVideos(c); bindImageFallbacks(c);
}

async function initProfilePage(){
  const root=qs('#profile-root'); if(!root) return;
  const username = root.dataset.username === 'me' && currentUser?.username ? currentUser.username : root.dataset.username;
  const d = await api.get(`/users/profile/${encodeURIComponent(username)}`).catch(()=>api.get(`/profile/${encodeURIComponent(username)}`).catch(()=>null));
  const p = d?.user || d?.profile || d;
  if(p){
    text('#profile-name', p.full_name || p.username || 'SocialHub Creator'); text('#profile-handle', '@' + (p.username || username)); text('#profile-bio', p.bio || 'No bio yet.');
    qs('#profile-avatar').src = avatarUrl(p.profile_picture || p.avatar_url); qs('#profile-cover').src = coverUrl(p.cover_photo || p.cover_url);
    text('#profile-post-count', `${p.posts_count ?? p.post_count ?? 0} Posts`); text('#profile-followers', `${p.followers_count ?? 0} Followers`); text('#profile-following', `${p.following_count ?? 0} Following`);
  }
  const userId = p?.id || username;
  const profilePosts = await api.get(`/posts/user/${encodeURIComponent(userId)}`, {silent:true}).catch(()=>null);
  const arr = profilePosts?.posts || endpointData(profilePosts, []);
  setHTML(qs('#profile-grid'), arr.length ? arr.map(x => `<a class="tile" href="/posts"><img src="${mediaUrl(x.image_url || x.media?.[0]?.url)}" alt="Post" loading="lazy"></a>`).join('') : empty('image','No profile posts yet'));
  bindImageFallbacks(root);
}

async function initStoriesPage(){ await loadStories(); setHTML(qs('#story-viewer-page'), empty('clock','Select a story','Use the tray above.')); }

async function initSearchPage(){
  const input = qs('#search-input'), results = qs('#search-results'); if(!input) return; let controller;
  const run = debounce(async()=>{ const q=input.value.trim(); if(!q){results.innerHTML=empty('search','Start typing to search'); return;} controller?.abort(); controller = new AbortController(); skeleton(results); try{ const d=await api.get(`/search?q=${encodeURIComponent(q)}`,{signal:controller.signal}); const items=[...(d.users||[]),...(d.posts||[]),...(d.reels||[]),...(d.hashtags||[])]; results.innerHTML = items.length ? items.map(x=>`<a class="result-card" href="${x.username?'/profile/'+encodeURIComponent(x.username):x.tag?'/hashtag/'+encodeURIComponent(String(x.tag).replace(/^#/,'')):'/posts'}"><img class="avatar-sm" src="${avatarUrl(x.profile_picture)}" alt=""><span><b>${escapeHTML(x.username||x.tag||x.caption||x.content||'Result')}</b><small class="muted">${escapeHTML(x.full_name||x.type||'SocialHub')}</small></span></a>`).join('') : empty('magnifying-glass','No results'); }catch(e){ if(e.name!=='AbortError') results.innerHTML=empty('triangle-exclamation','Search failed',e.message); } },300);
  input.addEventListener('input', run); const q = new URLSearchParams(location.search).get('q'); if(q){ input.value=q; run(); }
}

async function initExplorePage(){
  const grid=qs('#explore-grid'); if(!grid) return; skeleton(grid);
  const [posts,reels,tags]=await Promise.allSettled([api.get('/trending/posts'),api.get('/trending/reels'),api.get('/hashtags/trending')]);
  const items=[...(posts.value?.posts||endpointData(posts.value,[])),...(reels.value?.reels||endpointData(reels.value,[])),...(tags.value?.hashtags||endpointData(tags.value,[]))];
  grid.innerHTML = items.length ? items.slice(0,30).map((x,i)=>`<a class="explore-card" href="${x.tag?'/hashtag/'+encodeURIComponent(String(x.tag).replace(/^#/,'')):x.video_url?'/reels':'/posts'}"><div class="empty-state"><i class="fas fa-${x.tag?'hashtag':x.video_url?'clapperboard':'image'}"></i><strong>${escapeHTML(x.tag||x.caption||x.content||'Explore')}</strong></div></a>`).join('') : empty('compass','Nothing trending yet');
}

async function initNotificationsPage(){
  const c=qs('#notifications-container'); if(!c) return; skeleton(c);
  const d=await api.get('/notifications').catch(e=>({error:e.message})); const n=d.notifications||endpointData(d,[]);
  c.innerHTML = n.length ? n.map(x=>`<article class="notification-item ${x.is_read?'':'unread'}"><img class="avatar-sm" src="${avatarUrl(x.actor?.profile_picture)}" alt=""><div><strong>${escapeHTML(x.title||x.type||'Notification')}</strong><p>${escapeHTML(x.message||x.content||'')}</p><small class="muted">${escapeHTML(x.created_at||'')}</small></div><a class="btn btn-sm btn-secondary" href="${escapeHTML(x.target_url||'/notifications')}">Open</a></article>`).join('') : empty('bell','No notifications');
}

async function initChatPage(){
  const list=qs('#conversation-list'); if(!list) return; skeleton(list);
  const d=await api.get('/chats').catch(()=>null); const chats=d?.chats||endpointData(d,[]);
  list.innerHTML = chats.length ? chats.map(c=>`<button class="conversation-item" data-action="open-chat" data-chat-id="${escapeHTML(c.id)}"><img class="avatar-sm" src="${avatarUrl(c.avatar_url||c.other_user?.profile_picture)}" alt=""><span><b>${escapeHTML(c.name||c.other_user?.username||'Conversation')}</b><small class="muted">${escapeHTML(c.last_message?.content||'Open chat')}</small></span></button>`).join('') : empty('comments','No conversations yet');
  if(getToken()) chatSocket = createSocket('/ws/chat', getToken(), { onMessage: handleChatSocketMessage });
}
async function openChat(id){ activeChatId=id; qs('#chat-layout')?.classList.add('chat-open'); const d=await api.get(`/chats/${id}/messages`).catch(()=>null); const msgs=d?.messages||endpointData(d,[]); setHTML(qs('#message-list'), msgs.map(m=>`<div class="message ${m.sender_id===currentUser?.id?'mine':''}">${escapeHTML(m.content||m.message||'')}</div>`).join('') || empty('comment','No messages yet')); }
function handleChatSocketMessage(msg){ if(msg.chat_id===activeChatId) qs('#message-list')?.insertAdjacentHTML('beforeend',`<div class="message">${escapeHTML(msg.content||'')}</div>`); }

async function initFeaturePage(){
  const page=document.body.dataset.page;
  const root=qs('.content-grid[id$="root"],#ai-tools,#admin-root,#creator-root,#instagram-root,#data-studio-root,#scheduled-root,#marketplace-root,#collabs-root,#connect-instagram-root');
  if(!root) return;
  const loaders={
    'collections': async()=>renderCollections(root), 'saved': async()=>renderSaved(root), 'follow-requests': async()=>renderFollowRequests(root), 'hashtag': async()=>renderHashtag(root), 'wallet': async()=>renderWallet(root), 'verification': async()=>renderVerification(root), 'music-library': async()=>renderMusic(root), 'live': async()=>renderLive(root), 'ai-creator-studio': async()=>renderAI(root), 'admin': async()=>renderAdmin(root), 'creator-dashboard': async()=>renderCards(root,'/creator/dashboard'), 'marketplace': async()=>renderCards(root,'/marketplace/products'), 'collabs': async()=>renderCards(root,'/collabs'), 'scheduled': async()=>renderCards(root,'/schedule/me'), 'data-studio': async()=>renderCards(root,'/data-studio/stats'), 'instagram-studio': async()=>renderCards(root,'/instagram/account'), 'connect-instagram': async()=>renderInstagramConnect(root)
  };
  await (loaders[page]?.() || renderCards(root,'/health'));
}
function card(title, body, icon='circle-info', action=''){ return `<article class="feature-panel"><h3><i class="fas fa-${icon}"></i> ${escapeHTML(title)}</h3><p class="muted">${escapeHTML(body||'')}</p>${action}</article>`; }
async function renderCards(root,path){ const d=await api.get(path,{silent:true}).catch(e=>({error:e.message})); root.innerHTML=card(path, d.error||'Connected to existing backend API.', 'plug', '<button class="btn btn-secondary" data-action="refresh-page">Refresh</button>') + `<pre class="section-card">${escapeHTML(JSON.stringify(d,null,2)).slice(0,3000)}</pre>`; }
async function renderCollections(root){ const d=await api.get('/collections').catch(()=>null); const items=d?.collections||endpointData(d,[]); root.innerHTML=`<form class="section-card" data-action="create-collection"><h2>New collection</h2><input name="name" class="form-control" placeholder="Collection name" required><button class="btn btn-primary">Create</button></form>`+(items.length?items.map(c=>card(c.name||'Collection',`${c.items_count||0} items`,'layer-group',`<button class="btn btn-sm btn-secondary" data-action="delete-collection" data-id="${c.id}">Delete</button>`)).join(''):empty('layer-group','No collections yet')); }
async function renderSaved(root){ const d=await api.get('/posts/saved-center').catch(()=>null); const items=d?.items||d?.posts||d?.saved_posts||endpointData(d,[]); root.innerHTML=`<div class="tabs"><button class="tab active">Saved posts</button><a class="tab" href="/collections">Collections</a></div>`+(items.length?items.map(renderPostCard).join(''):empty('bookmark','No saved items yet')); }
async function renderFollowRequests(root){ const d=await api.get('/follow/requests').catch(()=>null); const users=d?.requests||endpointData(d,[]); root.innerHTML=users.length?users.map(u=>`<article class="list-item"><img class="avatar-sm" src="${avatarUrl(u.profile_picture)}"><b>${escapeHTML(u.username)}</b><button class="btn btn-sm btn-primary" data-action="accept-follow" data-user-id="${u.id}">Accept</button><button class="btn btn-sm btn-secondary" data-action="reject-follow" data-user-id="${u.id}">Reject</button></article>`).join(''):empty('user-check','No follow requests'); }
async function renderHashtag(root){ const tag=root.dataset.tag||location.pathname.split('/').pop(); const d=await api.get(`/hashtags/${encodeURIComponent(tag)}`).catch(()=>null); const posts=d?.posts||endpointData(d,[]); root.innerHTML=card('#'+tag,`${d?.posts_count||posts.length||0} posts`,'hashtag')+(posts.length?posts.map(renderPostCard).join(''):empty('hashtag','No hashtag posts yet')); }
async function renderWallet(root){ const [w,e,p]=await Promise.allSettled([api.get('/wallet'),api.get('/wallet/earnings'),api.get('/wallet/payouts')]); root.innerHTML=`<section class="metric-grid"><div class="metric-card"><h2>${escapeHTML(w.value?.balance??'--')}</h2><p>Available balance</p></div><div class="metric-card"><h2>${escapeHTML(e.value?.total??'--')}</h2><p>Earnings (real/demo separated by backend)</p></div><div class="metric-card"><h2>${(p.value?.payouts||[]).length}</h2><p>Payouts</p></div></section><form class="section-card" data-action="request-payout"><h2>Request payout</h2><input class="form-control" name="amount" type="number" min="1" step="0.01" required><button class="btn btn-primary">Request</button></form>`; }
async function renderVerification(root){ const d=await api.get('/verification/status').catch(()=>null); root.innerHTML=card('Current status',d?.status||'Not requested','certificate')+`<form class="section-card" data-action="verification-request"><h2>Apply for verification</h2><input class="form-control" name="full_name" placeholder="Legal name" required><textarea class="form-control" name="reason" placeholder="Why should this account be verified?" required></textarea><input class="form-control" name="document" type="file" accept="image/*,.pdf"><button class="btn btn-primary">Submit securely</button></form>`; }
async function renderMusic(root){ const [tr,cat,my]=await Promise.allSettled([api.get('/music/trending'),api.get('/music/categories'),api.get('/music/me')]); const tracks=[...(tr.value?.tracks||endpointData(tr.value,[])),...(my.value?.tracks||endpointData(my.value,[]))]; root.innerHTML=`<form class="section-card" data-action="music-search"><input class="form-control" name="q" placeholder="Search tracks"><button class="btn btn-primary">Search</button></form><form class="section-card" data-action="music-upload"><input class="form-control" name="file" type="file" accept="audio/*" required><input class="form-control" name="title" placeholder="Title"><button class="btn btn-secondary">Upload</button></form>`+(tracks.length?tracks.map(t=>`<article class="list-item"><i class="fas fa-music"></i><b>${escapeHTML(t.title||t.name||'Track')}</b><audio src="${mediaUrl(t.file_url||t.audio_url)}" preload="metadata" controls></audio></article>`).join(''):empty('music','No tracks yet')); }
async function renderLive(root){ const d=await api.get('/live/active').catch(()=>null); const lives=d?.lives||endpointData(d,[]); root.innerHTML=`<section class="section-card"><video id="live-preview" class="post-media" autoplay muted playsinline></video><div class="hero-actions"><button class="btn btn-primary" data-action="start-camera">Camera preview</button><button class="btn btn-primary" data-action="start-live">Start live</button><button class="btn btn-danger" data-action="end-live">End/leave</button></div></section>`+(lives.length?lives.map(l=>card(l.title||'Live room',`${l.viewer_count||0} viewers`,'tower-broadcast',`<button class="btn btn-sm btn-secondary" data-action="join-live" data-id="${l.id}">Join</button>`)).join(''):empty('tower-broadcast','No active lives')); }
function renderAI(root){ const tools=['caption','hashtags','bio','reel-title','post-ideas','content-calendar','viral-hooks','comment-reply']; root.innerHTML=tools.map(t=>`<form class="feature-panel" data-action="ai-generate" data-ai-tool="${t}"><h3><i class="fas fa-wand-magic-sparkles"></i> ${t.replaceAll('-',' ')}</h3><textarea class="form-control" name="prompt" rows="3" placeholder="Describe your goal, niche, topic or comment"></textarea><button class="btn btn-primary">Generate</button><pre class="section-card" data-ai-result></pre></form>`).join(''); }
async function renderAdmin(root){ if(!currentUser?.is_admin){ root.innerHTML=empty('lock','Admin access required','Backend authorization is still enforced.'); return; } await renderCards(root,'/admin/dashboard'); }
function renderInstagramConnect(root){ root.innerHTML=card('Official connection','Uses the backend Meta OAuth endpoint.','link','<a class="btn btn-primary" href="/api/instagram/connect">Connect Instagram</a>'); }

async function handleAction(action, trigger, event){
  const id=trigger.dataset.target; const ds=trigger.dataset;
  if(action==='open-modal'){ event.preventDefault(); openModal(id); if(id==='share-modal') qs('#share-link').value=location.href; }
  if(action==='close-modal'){ event.preventDefault(); closeModal(id); }
  if(action==='toggle-theme') toggleTheme();
  if(action==='toggle-user-menu') qs('#user-menu')?.classList.toggle('active');
  if(action==='toggle-notifications') qs('#notification-menu')?.classList.toggle('active');
  if(action==='logout'){ clearTokens(); location.href='/login'; }
  if(action==='refresh-page') location.reload();
  if(action==='copy-share-link'){ await navigator.clipboard?.writeText(qs('#share-link')?.value || location.href); toast('Link copied','success'); }
  if(action==='native-share' && navigator.share) navigator.share({title:document.title,url:location.href});
  if(action==='like-post'){ trigger.classList.toggle('active'); await api.post(`/likes/${ds.postId}`,{}).catch(e=>toast(e.message,'error')); }
  if(action==='save-post'){ trigger.classList.toggle('active'); await api.post(`/posts/${ds.postId}/bookmark`).catch(e=>toast(e.message,'error')); }
  if(action==='open-comments'){ activePostId=ds.postId; openModal('comments-drawer'); loadComments(activePostId); }
  if(action==='open-chat') openChat(ds.chatId);
  if(action==='chat-back') qs('#chat-layout')?.classList.remove('chat-open');
  if(action==='chat-file-pick') qs('#chat-file-input')?.click();
  if(action==='mark-all-notifications-read'){ await api.put('/notifications/read-all',{}); initNotificationsPage(); }
  if(action==='accept-follow'){ await api.post(`/follow/accept/${ds.userId}`); trigger.closest('.list-item')?.remove(); }
  if(action==='reject-follow'){ await api.delete(`/follow/reject/${ds.userId}`); trigger.closest('.list-item')?.remove(); }
  if(action==='delete-collection'){ await api.delete(`/collections/${ds.id}`); trigger.closest('.feature-panel')?.remove(); }
  if(action==='start-camera') startCamera();
  if(action==='start-live') startLive();
  if(action==='end-live') stopLive();
  if(action==='join-live') joinLive(ds.id);
}

async function handleForm(form, event){
  const action=form.dataset.action || form.id; if(action==='global-search-form'){ event.preventDefault(); const q=form.q.value.trim(); if(q) location.href=`/search?q=${encodeURIComponent(q)}`; return; }
  event.preventDefault();
  try{
    if(action==='login-form'){ const d=await api.post('/auth/login',{email:form.email.value,password:form.password.value}); setTokens(d.access_token,d.refresh_token); location.href='/'; }
    if(action==='register-form'){ const d=await api.post('/auth/register',{full_name:form.full_name.value,username:form.username.value,email:form.email.value,password:form.password.value}); setTokens(d.access_token,d.refresh_token); location.href='/'; }
    if(action==='forgot-form'){ await api.post('/auth/forgot-password',{email:form.email.value}).catch(()=>{}); toast('If the account exists, a reset link was sent.','success'); }
    if(action==='reset-form'){ await api.post('/auth/reset-password',{token:form.token.value,password:form.password.value}); toast('Password reset complete','success'); location.href='/login'; }
    if(action==='create-post-form'){ const fd=new FormData(form); [...(qs('#post-files')?.files||[])].forEach(f=>fd.append('files',f)); await api.upload('/posts',fd,{onProgress:p=>{qs('#post-upload-progress')?.classList.remove('hidden'); qs('#post-upload-progress-fill').style.width=p+'%';}}); toast('Post published','success'); closeModal('create-post-modal'); loadFeed(true); }
    if(action==='reel-upload-form'){ const fd=new FormData(form); await api.upload('/reels/upload',fd); toast('Reel uploaded','success'); closeModal('create-reel-modal'); }
    if(action==='story-upload-form'){ const fd=new FormData(form); await api.upload('/stories',fd); toast('Story shared','success'); closeModal('create-story-modal'); loadStories(); }
    if(action==='comment-form'){ await api.post(`/comments/${activePostId}`,{content:qs('#comment-input').value}); qs('#comment-input').value=''; loadComments(activePostId); }
    if(action==='message-form' && activeChatId){ const input=qs('#message-input'); await api.post(`/chats/${activeChatId}/messages`,{content:input.value}); input.value=''; openChat(activeChatId); }
    if(action==='create-collection'){ await api.post('/collections',{name:form.name.value}); toast('Collection created','success'); initFeaturePage(); }
    if(action==='request-payout'){ await api.post('/wallet/payouts',{amount:Number(form.amount.value)}); toast('Payout requested','success'); }
    if(action==='verification-request'){ await api.post('/verification/request',{full_name:form.full_name.value,reason:form.reason.value,document_url:''}); toast('Verification request submitted','success'); }
    if(action==='ai-generate'){ const tool=form.dataset.aiTool; const payload={prompt:form.prompt.value, title:form.prompt.value, description:form.prompt.value, keywords:form.prompt.value, topic:form.prompt.value, niche:form.prompt.value, comment:form.prompt.value}; const d=await api.post(`/ai/${tool}`,payload); form.querySelector('[data-ai-result]').textContent=JSON.stringify(d,null,2); }
  }catch(e){ toast(e.message||'Action failed','error'); }
}

async function loadComments(postId){ const c=qs('#comments-content'); skeleton(c); const d=await api.get(`/comments/${postId}`).catch(()=>null); const comments=d?.comments||endpointData(d,[]); c.innerHTML=comments.length?comments.map(x=>`<div class="list-item"><img class="avatar-sm" src="${avatarUrl(x.user?.profile_picture)}"><p><b>${escapeHTML(x.user?.username||'user')}</b> ${escapeHTML(x.content)}</p></div>`).join(''):empty('comment','No comments yet'); }
async function startCamera(){ try{ liveStream=await navigator.mediaDevices.getUserMedia({video:true,audio:true}); qs('#live-preview').srcObject=liveStream; }catch(e){ toast('Camera or microphone permission denied','error'); } }
async function startLive(){ const d=await api.post('/live/start',{title:'SocialHub Live'}); toast('Live started','success'); if(getToken()) liveSocket=createSocket(`/ws/live/${d.id||d.live_id}`, getToken(), {onMessage:()=>{}}); }
async function joinLive(id){ await api.post(`/live/${id}/join`); if(getToken()) liveSocket=createSocket(`/ws/live/${id}`, getToken(), {onMessage:()=>{}}); toast('Joined live','success'); }
function stopLive(){ liveStream?.getTracks().forEach(t=>t.stop()); liveStream=null; liveSocket?.close(); liveSocket=null; toast('Live media stopped','success'); }

function bindGlobal(){
  document.addEventListener('click', e=>{ const trigger=e.target.closest('[data-action]'); if(trigger) handleAction(trigger.dataset.action, trigger, e); if(e.target.matches('[data-modal].active')) closeModal(e.target.id); });
  document.addEventListener('submit', e=>{ const form=e.target.closest('form'); if(form) handleForm(form,e); });
  document.addEventListener('keydown', e=>{ if(e.key==='Escape') closeAllModals(); });
  qsa('[data-action="toggle-password"]').forEach(b=>b.addEventListener('click',()=>{ const i=b.parentElement.querySelector('input'); i.type=i.type==='password'?'text':'password'; }));
  qsa('.settings-nav button').forEach(b=>b.addEventListener('click',()=>{ qsa('.settings-nav button').forEach(x=>x.classList.remove('active')); b.classList.add('active'); qsa('[data-settings-panel]').forEach(p=>p.hidden=p.dataset.settingsPanel!==b.dataset.panel); }));
  bindUploadPreview('post-files','post-preview'); bindUploadPreview('reel-file','reel-preview'); bindUploadPreview('story-file','story-preview'); bindImageFallbacks(document); trapFocus();
}

const pageControllers={home:initHomePage,posts:initPostsPage,profile:initProfilePage,reels:initReelsPage,stories:initStoriesPage,chat:initChatPage,search:initSearchPage,explore:initExplorePage,notifications:initNotificationsPage,'ai-creator-studio':initFeaturePage,collections:initFeaturePage,'follow-requests':initFeaturePage,hashtag:initFeaturePage,live:initFeaturePage,'music-library':initFeaturePage,saved:initFeaturePage,verification:initFeaturePage,wallet:initFeaturePage,'creator-dashboard':initFeaturePage,'instagram-studio':initFeaturePage,'connect-instagram':initFeaturePage,'data-studio':initFeaturePage,scheduled:initFeaturePage,marketplace:initFeaturePage,collabs:initFeaturePage,admin:initFeaturePage,settings:async()=>{}};
async function boot(){ initTheme(); bindGlobal(); await initShell(); const page=document.body.dataset.page; await pageControllers[page]?.(); }
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true}); else boot();
window.addEventListener('beforeunload',()=>{ chatSocket?.close(); liveSocket?.close(); liveStream?.getTracks().forEach(t=>t.stop()); });
