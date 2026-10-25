(function () {
  'use strict';
  function createWorkspace(doc, win, request) {
    const el=id=>doc.getElementById(id),frame=el('workspace-frame');
    const routes={dashboard:'/dashboard',discovery:'/discovery',analysis:'/analysis',strategies:'/strategies',backtesting:'/backtesting',paper:'/paper',portfolio:'/holdings',history:'/activity',risk:'/console',broker:'/setup',settings:'/settings',learn:'/learn'};
    const titles={dashboard:'Dashboard',discovery:'Stock Discovery',analysis:'Stock Analysis',strategies:'Strategies',backtesting:'Backtesting',paper:'Paper Trading',portfolio:'Portfolio',history:'Trade History',risk:'Risk Management',broker:'Broker & Data',settings:'Settings',learn:'Learning Center'};
    const aliases={desk:'dashboard',activity:'history',console:'risk',setup:'broker',overview:'learn'};
    const purchaseAnchors=new Set(['purchases','purchase','holdings-heading','buy-heading','preview-heading','plans-heading','purchase-orders-heading','lots-heading']);
    const cleanAnchor=value=>typeof value==='string'&&/^[A-Za-z][A-Za-z0-9_-]{0,99}$/.test(value)?value:'';
    let token='',generation=0,busy=false,controller=null,current='',currentAnchor='',loaded='',surface='',dialogOpen=false;
    const baseTitle=doc.title||'Paper trading workspace';
    let alertBusy=false,alertController=null,alertRows=new Map(),alertExpired=false,desktopAlerts=false,alertFresh=false,alertChecked=false,alertAt=0,alertClock=0;
    const notifications=new Set();
    let healthBusy=false,healthController=null,healthChecked=0;
    function closeNotifications(){for(const notice of notifications)notice.close?.();notifications.clear();}
    function renderAlerts(){
      if(!token)return;
      const now=alertAt+Math.max(0,Date.now()-alertClock),pending=[...alertRows.values()].filter(row=>row.state==='awaiting_approval'&&Date.parse(row.expires_at)>=now);
      for(const row of alertRows.values())if(row.state==='awaiting_approval'&&Date.parse(row.expires_at)<now)alertExpired=true;
      doc.title=pending.length?'('+pending.length+') Proposals · '+baseTitle:baseTitle;
      el('workspace-proposals').hidden=false;
      const status=!alertFresh?(alertChecked?'Proposal checks unavailable or stale. Open Paper Trading and refresh before acting.':'Checking for paper proposals…'):pending.length?pending.length+' paper proposal'+(pending.length===1?'':'s')+' awaiting review.':alertExpired?'A proposal’s review deadline passed. Open Trade History to inspect its recorded outcome; no approval was sent by this alert.':'No pending proposal in the latest 100 decision records.';
      if(el('workspace-proposal-status').textContent!==status)el('workspace-proposal-status').textContent=status;
      el('workspace-proposal-deadline').textContent=alertFresh&&pending.length?'Earliest deadline in '+Math.max(0,Math.ceil((Math.min(...pending.map(row=>Date.parse(row.expires_at)))-now)/1000))+' seconds.':'';
    }
    function notifyProposals(count){
      if(!desktopAlerts||win.Notification?.permission!=='granted'||(!doc.hidden&&current==='paper'))return;
      try{const notice=new win.Notification('Paper proposal awaiting review',{body:count+' new proposal'+(count===1?'':'s')+'. Open Paper Trading and review before the deadline. An alert never approves a trade.',tag:'agentic-paper-proposals'});notifications.add(notice);notice.onclose=()=>notifications.delete(notice);notice.onclick=()=>{if(token){win.focus?.();win.location.hash='#paper';}notice.close?.();};}catch(_){el('workspace-alert-toggle').textContent='Desktop alerts unavailable';desktopAlerts=false;}
    }
    async function refreshAlerts(){
      if(!token||alertBusy)return;alertBusy=true;alertChecked=true;const version=generation,active=new AbortController();alertController=active;const timeout=win.setTimeout(()=>active.abort(),10000);
      try{const response=await request('/api/desk/alerts',{cache:'no-store',credentials:'omit',redirect:'error',signal:active.signal,headers:{Authorization:'Bearer '+token}});const data=await response.json();if(version!==generation)return;
        if(response.status===401||response.status===403){lock('Local authorization changed. Unlock the workspace again.');return;}
        if(!response.ok||!Array.isArray(data.decisions)||!Number.isFinite(Date.parse(data.observed_at)))throw Error();
        const rows=new Map(data.decisions.filter(row=>typeof row.id==='string'&&typeof row.state==='string'&&Number.isFinite(Date.parse(row.expires_at))).map(row=>[row.id,row]));
        const pending=[...rows.values()].filter(row=>row.state==='awaiting_approval'&&Date.parse(row.expires_at)>=Date.parse(data.observed_at));
        const added=pending.filter(row=>!alertRows.has(row.id));
        for(const [id,row] of alertRows)if(row.state==='awaiting_approval'&&rows.get(id)?.state==='expired')alertExpired=true;
        alertRows=rows;alertAt=Date.parse(data.observed_at);alertClock=Date.now();alertFresh=true;renderAlerts();if(added.length)notifyProposals(added.length);
      }catch(_){if(version===generation){alertFresh=false;renderAlerts();}}
      finally{win.clearTimeout(timeout);if(version===generation){alertBusy=false;alertController=null;}}
    }
    async function toggleAlerts(){
      if(!token)return;
      if(desktopAlerts){desktopAlerts=false;closeNotifications();el('workspace-alert-toggle').textContent='Enable desktop alerts';return;}
      if(!win.Notification){el('workspace-alert-toggle').textContent='Desktop alerts unavailable in this browser';return;}
      const version=generation;el('workspace-alert-toggle').disabled=true;
      try{const permission=win.Notification.permission==='default'?await win.Notification.requestPermission():win.Notification.permission;if(version!==generation)return;desktopAlerts=permission==='granted';el('workspace-alert-toggle').textContent=desktopAlerts?'Disable desktop alerts':'Desktop alerts blocked · use the proposal banner';if(desktopAlerts)await refreshAlerts();}
      catch(_){if(version===generation)el('workspace-alert-toggle').textContent='Desktop alerts unavailable · use the proposal banner';}
      finally{if(version===generation)el('workspace-alert-toggle').disabled=false;}
    }
    function showToast(text,error=false){
      el('workspace-toast').hidden=false;el('workspace-toast').className=error?'workspace-toast error':'workspace-toast';
      el('workspace-toast-text').textContent=text;
      el('workspace-error-alert').textContent=error?text:'';
    }
    function clearToast(){el('workspace-toast').hidden=true;el('workspace-toast-text').textContent='';el('workspace-error-alert').textContent='';}
    function message(text,error=false){el('workspace-message').textContent=text;el('workspace-message').className=error?'error':'';if(error)showToast(text,true);}
    function setMenu(open){el('workspace-nav').hidden=!open&&!!win.matchMedia?.('(max-width: 767px)').matches;el('workspace-menu-toggle').setAttribute('aria-expanded',String(open));el('workspace-sidebar').classList?.toggle('menu-open',open);}
    function setDialog(open){dialogOpen=open;el('workspace-sidebar').inert=open;el('workspace-footer').inert=open;el('workspace-nav').inert=open;el('workspace-menu-toggle').disabled=open;el('workspace-onboarding').inert=open;el('workspace-proposals').inert=open;el('workspace-toast').inert=open;}
    function send(type,value){if(frame.contentWindow)frame.contentWindow.postMessage({type,...(value?{token:value}:{})},win.location.origin);}
    function lock(text='Locked. Unlock again to access all workspace sections.'){
      generation++;token='';busy=false;if(controller)controller.abort();controller=null;if(alertController)alertController.abort();alertController=null;alertBusy=false;alertRows=new Map();alertExpired=false;desktopAlerts=false;alertFresh=false;alertChecked=false;closeNotifications();doc.title=baseTitle;el('workspace-proposals').hidden=true;el('workspace-proposal-status').textContent='';el('workspace-proposal-deadline').textContent='';el('workspace-alert-toggle').textContent='Enable desktop alerts';el('workspace-alert-toggle').disabled=false;setDialog(false);
      if(healthController)healthController.abort();healthController=null;healthBusy=false;healthChecked=0;el('workspace-feed-health').textContent='';el('workspace-feed-health').hidden=true;
      clearToast();send('workspace-lock');frame.src='about:blank';loaded='';surface='';frame.hidden=true;
      el('workspace-token').value='';el('workspace-access').hidden=false;el('workspace-lock').disabled=true;el('workspace-submit').disabled=false;el('workspace-refresh').disabled=true;
      el('workspace-state').textContent='Locked';el('workspace-onboarding').hidden=true;el('workspace-onboarding').open=false;
      el('workspace-mode').textContent='Unlock to inspect the current account and its actual settings.';
      for(const id of ['workspace-feed','workspace-time','workspace-hours'])el(id).textContent='';message(text);
    }
    function wanted(){
      const parts=win.location.hash.slice(1).split('/');let target=aliases[parts[0]]||parts[0],anchor=cleanAnchor(parts[1]);
      if(!Object.hasOwn(routes,target))target='dashboard';
      if(target==='dashboard'&&['strategy-setup','execution-shortlist','apply-shortlist'].includes(anchor)){target='strategies';if(anchor==='apply-shortlist')anchor='execution-shortlist';}
      if(parts[0]==='overview'&&!anchor)anchor='setup-checklist';
      return {target,anchor};
    }
    function canLeave(){try{return !dialogOpen&&(!frame.contentWindow||!frame.contentWindow.AgenticNavigation||frame.contentWindow.AgenticNavigation.canNavigate());}catch(_){return false;}}
    function navigate(){
      if(win.location.hash==='#workspace-main'&&current){win.history.replaceState(null,'','#'+current+(currentAnchor?'/'+currentAnchor:''));if(!dialogOpen)el('workspace-main').focus?.();return;}
      const {target,anchor}=wanted(),nextSurface=target==='portfolio'&&purchaseAnchors.has(anchor)?'/portfolio':target==='strategies'&&anchor==='investment-policy'?'/investment-policy':routes[target];
      const changed=current!==target||surface!==nextSurface;
      if((changed||currentAnchor!==anchor)&&!canLeave()){win.history.replaceState(null,'','#'+current+(currentAnchor?'/'+currentAnchor:''));message('Finish or cancel the active request, confirmation or login window before changing sections.',true);return;}
      const canonical='#'+target+(anchor?'/'+anchor:'');if(win.location.hash!==canonical)win.history.replaceState(null,'',canonical);
      current=target;currentAnchor=anchor;setMenu(false);if(changed&&win.scrollTo)win.scrollTo({top:0,behavior:'instant'});
      for(const name of Object.keys(routes)){const link=el('nav-'+name);link.className=name===target?'active':'';if(name===target)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');}
      el('workspace-title').textContent=titles[target];el('workspace-menu-label').textContent='Menu · '+titles[target];
      el('workspace-overview').hidden=true;el('workspace-section-note').hidden=true;frame.hidden=!token;
      if(!token){frame.src='about:blank';loaded='';surface='';return;}
      const childAnchor=anchor==='purchases'?'buy-heading':anchor;
      if(loaded!==target||surface!==nextSurface){setDialog(false);loaded=target;surface=nextSurface;frame.src=nextSurface+(childAnchor?'#'+childAnchor:'');frame.title=titles[target];}
      else if(frame.contentWindow)frame.contentWindow.postMessage({type:'workspace-anchor',anchor:childAnchor},win.location.origin);
      if(changed&&target==='dashboard')refreshInfo();
    }
    function render(data){
      const needsStrategy=!data.analysis_configured,needsCalendar=!data.calendar_today,needsFeed=!data.feed_connected&&!data.feed_requested;
      el('workspace-onboarding').hidden=!(needsStrategy||needsCalendar||needsFeed);
      el('onboarding-title').textContent=needsStrategy?'Prepare your paper strategy':needsCalendar?'Review the exchange session':'Connect your market data';
      el('onboarding-detail').textContent=needsStrategy?'A guided review helps you prepare genuine data and choose a decision policy. Manual purchases remain available.':needsCalendar?'Today has no saved reviewed session. Review the actual exchange date and hours before trading.':'Your strategy is configured. Check the saved broker session, then explicitly connect the read-only feed.';
      el('onboarding-action-label').textContent=needsStrategy?'Set up a strategy':'Open Broker & Data';el('onboarding-action').href=needsStrategy?'#strategies':'#broker/'+(needsCalendar?'setup-step-5':'feed-connection');
      el('workspace-mode').textContent=(data.investment_horizon==='long_term'?'Long-term paper':'Intraday paper')+' · '+(data.decision_mode||'manual')+' mode. Review Paper Trading for actual authority and blockers.';
      el('workspace-feed').textContent=data.feed_connected?'Market-data connection established. Freshness and price-basis gates still apply.':data.feed_requested?'Feed requested but disconnected/connecting. Inspect Broker & Data.':'Feed not started. Use Broker & Data → step 6 → Connect paper market data.';
      el('workspace-time').textContent='Last checked '+new Intl.DateTimeFormat('en-IN',{timeZone:'Asia/Kolkata',dateStyle:'medium',timeStyle:'short'}).format(new Date(data.observed_at))+' IST · '+(data.calendar_open?'Reviewed session currently open.':'No open reviewed session now.')+' Quotes must be no older than '+data.max_quote_age_seconds+' seconds.';
      el('workspace-hours').textContent='Configured entry window: '+data.entry_start+'–'+data.entry_end+' IST. '+(data.investment_horizon==='long_term'?'No forced end-of-day sale for long-term holdings.':'Intraday exit request time: '+data.flatten_at+' IST.');
    }
    async function refreshHealth(){
      if(!token||healthBusy||doc.hidden)return;
      const version=generation,active=new AbortController();healthController=active;healthBusy=true;
      const timeout=win.setTimeout(()=>active.abort(),10000);
      try{
        const response=await request('/api/feed/status',{cache:'no-store',credentials:'omit',redirect:'error',signal:active.signal,headers:{Authorization:'Bearer '+token}});
        if(version!==generation)return;
        if(response.status===401||response.status===403){lock('Local authorization changed. Unlock the workspace again.');return;}
        if(!response.ok)throw Error();const data=await response.json();if(version!==generation)return;
        if(data.schema_version!==1||typeof data.feed_connected!=='boolean'||!Number.isFinite(Date.parse(data.observed_at)))throw Error();
        healthChecked=Date.now();el('workspace-feed-health').hidden=false;
        el('workspace-feed-health').textContent=(data.faulted?'Account fault reported. Open Risk Management. ':data.feed_connected?'Feed connected. ':'Feed disconnected. ')+(data.last_tick_ms===null?'No accepted tick observed on this connection. ':data.last_tick_recent?'Latest accepted tick received '+data.last_tick_ms+' ms ago. ':'Latest accepted tick is old. ')+'Checked '+new Intl.DateTimeFormat('en-IN',{timeZone:'Asia/Kolkata',timeStyle:'medium'}).format(new Date(data.observed_at))+' IST. Per-stock prices and trading readiness require Paper Trading.';
      }catch(_){if(version===generation){healthChecked=0;el('workspace-feed-health').hidden=false;el('workspace-feed-health').textContent='Feed status unavailable or stale. Open Broker & Data to inspect the connection; do not infer trading readiness.';}}
      finally{win.clearTimeout(timeout);if(version===generation){healthBusy=false;healthController=null;}}
    }
    async function refreshInfo(){
      if(!token||busy)return;busy=true;el('workspace-refresh').disabled=true;const version=generation,active=new AbortController();controller=active;const timeout=win.setTimeout(()=>active.abort(),10000);
      try{const response=await request('/api/workspace',{cache:'no-store',credentials:'omit',redirect:'error',signal:active.signal,headers:{Authorization:'Bearer '+token}});const data=await response.json();if(version!==generation)return;if(response.status===401||response.status===403){lock('Local authorization changed. Unlock the workspace again.');return;}if(!response.ok||data.mode!=='paper')throw Error();render(data);}
      catch(_){if(version===generation)message('Status refresh failed or timed out. Displayed setup guidance may be stale; retry or open the relevant section.',true);}
      finally{win.clearTimeout(timeout);if(version===generation){busy=false;controller=null;el('workspace-refresh').disabled=!token;}}
    }
    async function unlock(){
      if(busy)return;const supplied=el('workspace-token').value.trim();el('workspace-token').value='';if(!supplied)return;lock('Checking local operator access…');busy=true;el('workspace-submit').disabled=true;
      const version=generation,active=new AbortController();controller=active;const timeout=win.setTimeout(()=>active.abort(),10000);
      try{const r=await request('/api/workspace',{cache:'no-store',credentials:'omit',redirect:'error',signal:active.signal,headers:{Authorization:'Bearer '+supplied}});const data=await r.json();if(version!==generation)return;
        if(!r.ok||data.mode!=='paper')throw Error(r.status===401||r.status===403?'Use TRADING_OPERATOR_TOKEN from your local .env. Zerodha tokens do not unlock this workspace.':'Workspace access unavailable. Check the server and local operator configuration.');
        token=supplied;render(data);el('workspace-access').hidden=true;el('workspace-lock').disabled=false;el('workspace-state').textContent='Unlocked';message('');navigate();renderAlerts();
      }catch(error){if(version===generation){lock();message(error.name==='AbortError'?'Access check timed out. Try again; no trading action was submitted.':String(error.message),true);}}
      finally{win.clearTimeout(timeout);if(version===generation){busy=false;controller=null;el('workspace-submit').disabled=false;el('workspace-refresh').disabled=!token;}}
    }
    win.addEventListener('message',event=>{
      if(event.origin!==win.location.origin||event.source!==frame.contentWindow||!event.data)return;
      const data=event.data;
      if(data.type==='workspace-feedback'&&token&&loaded===current&&data.path===surface&&typeof data.text==='string'&&data.text.trim()&&data.text.length<=1000)showToast(data.text,data.error===true);
      if(data.type==='workspace-ready'&&token&&loaded===current&&data.view===current&&data.path===surface)send('workspace-unlock',token);
      if(data.type==='workspace-locked'&&token)lock('The section locked or rejected authorization. Unlock the workspace again.');
      if(data.type==='workspace-dialog'&&token&&loaded===current)setDialog(data.open===true);
      if(data.type==='workspace-navigate'&&(Object.hasOwn(routes,data.view)||Object.hasOwn(aliases,data.view))){const anchor=cleanAnchor(data.anchor),hash='#'+data.view+(anchor?'/'+anchor:'');if(win.location.hash===hash)navigate();else win.location.hash=hash;}
      if(data.type==='workspace-scroll-target'&&token&&loaded===current&&Number.isFinite(data.top)&&data.top>=0&&data.top<=12000){const nav=el('workspace-nav'),navHeight=win.getComputedStyle(nav).position==='sticky'?nav.getBoundingClientRect().height:0;win.scrollTo({top:Math.max(0,win.scrollY+frame.getBoundingClientRect().top+data.top-navHeight-16),behavior:'instant'});}
      if(data.type==='workspace-height'&&Number.isFinite(data.height))frame.style.height=Math.max(450,Math.min(12000,data.height))+'px';
    });
    el('workspace-unlock').addEventListener('submit',event=>{event.preventDefault();unlock();});el('workspace-lock').addEventListener('click',()=>lock());el('workspace-refresh').addEventListener('click',refreshInfo);
    el('workspace-toast-dismiss').addEventListener('click',clearToast);
    el('workspace-alert-toggle').addEventListener('click',toggleAlerts);
    el('workspace-menu-toggle').addEventListener('click',()=>{setMenu(el('workspace-menu-toggle').getAttribute('aria-expanded')!=='true');});
    win.addEventListener('hashchange',navigate);win.addEventListener('pagehide',()=>lock());win.addEventListener('resize',()=>setMenu(false));
    if(doc.addEventListener)doc.addEventListener('visibilitychange',()=>{if(!doc.hidden){refreshAlerts();if(current==='dashboard')refreshInfo();}});
    win.setInterval?.(refreshAlerts,5000);
    win.setInterval?.(refreshHealth,10000);
    win.setInterval?.(()=>{if(token){if(alertFresh&&Date.now()-alertClock>15000)alertFresh=false;renderAlerts();}},1000);
    win.setInterval?.(()=>{if(token&&healthChecked&&Date.now()-healthChecked>20000){healthChecked=0;el('workspace-feed-health').textContent='Feed status stale. Open Broker & Data or wait for the next check; per-stock readiness is unavailable here.';}},1000);
    lock();navigate();return{lock,navigate,refreshAlerts,refreshHealth};
  }
  if(typeof module!=='undefined'&&module.exports)module.exports={createWorkspace};
  else createWorkspace(document,window,window.fetch.bind(window));
})();
