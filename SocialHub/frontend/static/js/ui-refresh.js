(function(){
  function $(s,r=document){return r.querySelector(s)} function $$(s,r=document){return Array.from(r.querySelectorAll(s))}
  function pageKey(){return document.body?.dataset?.page || location.pathname.split('/').filter(Boolean)[0] || 'home'}
  function activeNav(){const key=pageKey();$$('[data-nav]').forEach(a=>{const nav=a.dataset.nav;const href=a.getAttribute('href')||'';a.classList.toggle('active',nav===key||href===location.pathname||(key==='home'&&href==='/'))})}
  function openCreate(type){ if(type==='reel'&&window.showCreateReel)return showCreateReel(); if(type==='story'&&window.showCreateStory)return showCreateStory(); if(window.showCreatePost)return showCreatePost(); }
  function bind(){
    activeNav();
    document.addEventListener('click',function(e){
      const action=e.target.closest('[data-action]'); if(!action)return;
      const a=action.dataset.action;
      if(a==='open-create'){e.preventDefault();openCreate(action.dataset.createType||'post')}
      if(a==='toggle-popover'){e.preventDefault();const t=$('#'+action.dataset.target);$$('.popover-menu').forEach(p=>p!==t&&p.classList.remove('active'));t&&t.classList.toggle('active')}
      if(a==='toggle-sidebar'){document.body.classList.toggle('sidebar-collapsed')}
      if(a==='toggle-password'){const input=action.closest('.password-field')?.querySelector('input'); if(input){input.type=input.type==='password'?'text':'password'}}
      if(a==='copy-current-url'){navigator.clipboard?.writeText(location.href); window.showToast&&showToast('Link copied','success')}
    });
    document.addEventListener('keydown',e=>{if(e.key==='Escape'){$$('.modal-overlay.active,.popover-menu.active,.story-viewer.active').forEach(x=>x.classList.remove('active'))}});
    const q=new URLSearchParams(location.search).get('q'); if(q&&$('#search-input')){$('#search-input').value=q; setTimeout(()=>window.handleSearch&&handleSearch(),100)}
    if(location.pathname==='/explore' && window.loadFeed) window.loadFeed();
    if(location.pathname==='/marketplace' && window.loadMarketplacePage) window.loadMarketplacePage();
    if(location.pathname==='/collabs' && window.loadCollabsPage) window.loadCollabsPage();
    if(location.pathname==='/creator-dashboard' && window.loadCreatorDashboardPage) window.loadCreatorDashboardPage();
    if(location.pathname==='/ai-creator-studio' && window.hydrateMiniUser) window.hydrateMiniUser();
    if(location.pathname==='/data-studio' && window.loadDataStudioPage) window.loadDataStudioPage();
    if(location.pathname==='/scheduled' && window.loadScheduledPage) window.loadScheduledPage();
    if(location.pathname==='/connect-instagram' && window.loadInstagramStatus) window.loadInstagramStatus();
    if(location.pathname==='/instagram-studio' && window.loadInstagramStudioPage) window.loadInstagramStudioPage();
    if(location.pathname==='/music-library' && window.loadMusicLibraryPage) window.loadMusicLibraryPage();
    if(location.pathname==='/live' && window.loadLivePage) window.loadLivePage();
    if(location.pathname==='/collections' && window.loadCollectionsPage) window.loadCollectionsPage();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind);else bind();
})();


(function(){
  async function safeApi(path, opts){ if(window.api) return api(path, opts); throw new Error('API client unavailable'); }
  function byId(id){return document.getElementById(id)}
  function err(form,msg){let e=form?.querySelector('#error,.form-error'); if(e){e.textContent=msg;e.classList.remove('hidden')} else if(window.showToast) showToast(msg,'error')}
  async function bindForms(){
    const forgot=byId('forgot-password-form'); if(forgot&&!forgot.dataset.bound){forgot.dataset.bound='1';forgot.addEventListener('submit',async e=>{e.preventDefault();const btn=forgot.querySelector('button[type=submit]');btn&&(btn.disabled=true);try{await safeApi('/auth/forgot-password',{method:'POST',body:JSON.stringify({email:byId('email').value})});showToast('If the email exists, an OTP was sent.','success');setTimeout(()=>location.href='/reset-password',700)}catch(x){err(forgot,x.message||'Could not send OTP')}finally{btn&&(btn.disabled=false)}})}
    const reset=byId('reset-password-form'); if(reset&&!reset.dataset.bound){reset.dataset.bound='1';reset.addEventListener('submit',async e=>{e.preventDefault();const token=(byId('reset-token')?.value||new URLSearchParams(location.search).get('token')||'').trim();const password=byId('new-password')?.value||'';try{await safeApi('/auth/reset-password',{method:'POST',body:JSON.stringify({token,new_password:password,password})});showToast('Password reset successfully','success');setTimeout(()=>location.href='/login',800)}catch(x){err(reset,x.message||'Could not reset password')}})}
    const two=byId('two-factor-form'); if(two&&!two.dataset.bound){two.dataset.bound='1';two.addEventListener('submit',async e=>{e.preventDefault();try{const data=await safeApi('/auth/verify-2fa',{method:'POST',body:JSON.stringify({code:byId('two-factor-code')?.value})}); if(data.access_token&&window.setTokens) setTokens(data.access_token,data.refresh_token); location.href='/'}catch(x){err(two,x.message||'Invalid code')}})}
    const verify=byId('verification-form'); if(verify&&!verify.dataset.bound){verify.dataset.bound='1';verify.addEventListener('submit',async e=>{e.preventDefault();try{await safeApi('/verification/request',{method:'POST',body:JSON.stringify({full_name:byId('full-name')?.value,category:byId('category')?.value,reason:byId('reason')?.value})});showToast('Verification request submitted','success');verify.reset()}catch(x){showToast(x.message||'Could not submit verification','error')}})}
    const pwd=byId('change-password-form'); if(pwd&&!pwd.dataset.bound){pwd.dataset.bound='1';pwd.addEventListener('submit',async e=>{e.preventDefault();try{await safeApi('/auth/change-password',{method:'POST',body:JSON.stringify({current_password:byId('current-password')?.value,new_password:byId('new-password')?.value})});showToast('Password changed','success');pwd.reset()}catch(x){showToast(x.message||'Could not change password','error')}})}
  }
  async function loadWallet(){ if(!byId('balance')) return; try{const w=await safeApi('/wallet'); byId('balance').textContent=Number(w.balance||0).toFixed(2); byId('total-earned').textContent=Number(w.total_earned||0).toFixed(2); byId('total-withdrawn').textContent=Number(w.total_withdrawn||0).toFixed(2); const e=await safeApi('/wallet/earnings').catch(()=>({earnings:[]})); const list=byId('earnings-list'); if(list) list.innerHTML=(e.earnings||[]).map(x=>`<div class="mini-row"><span>${escapeHtml(x.source||'Earning')}</span><strong>$${Number(x.amount||0).toFixed(2)}</strong></div>`).join('')||'<div class="empty-state">No earnings yet.</div>' }catch(x){showToast('Login required for wallet','warning')} }
  function bindWalletButtons(){const gen=byId('generate-demo-btn'); if(gen&&!gen.dataset.bound){gen.dataset.bound='1';gen.onclick=async()=>{try{await safeApi('/wallet/demo/generate-earnings',{method:'POST'});showToast('Demo earnings generated','success');loadWallet()}catch(x){showToast(x.message||'Could not generate earnings','error')}}} const pay=byId('request-payout-btn'); if(pay&&!pay.dataset.bound){pay.dataset.bound='1';pay.onclick=async()=>{try{await safeApi('/wallet/payouts',{method:'POST',body:JSON.stringify({amount:10,method:'manual'})});showToast('Payout requested','success')}catch(x){showToast(x.message||'Could not request payout','error')}}}}
  async function emailVerifyStatus(){const el=byId('verification-status'); if(!el||location.pathname!=='/verify-email') return; const token=new URLSearchParams(location.search).get('token')||''; if(!token){el.textContent='Missing verification token.';return} try{await fetch('/api/auth/verify-email?token='+encodeURIComponent(token)); el.textContent='Email verified. You can login now.'}catch(e){el.textContent='Verification link could not be validated.'}}
  function init(){bindForms();loadWallet();bindWalletButtons();emailVerifyStatus(); if('serviceWorker' in navigator) navigator.serviceWorker.register('/service-worker.js').catch(()=>{});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
