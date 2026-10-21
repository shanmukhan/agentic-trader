(function () {
  'use strict';
  function createWorkspace(doc, win, request) {
    const el = id => doc.getElementById(id), frame = el('workspace-frame');
    const routes = { console: '/console', setup: '/setup', portfolio: '/portfolio' };
    let token = '', generation = 0, busy = false, controller = null, current = '', loaded = '';
    function message(text, error = false) { el('workspace-message').textContent = text; el('workspace-message').className = error ? 'error' : ''; }
    function wanted() { const key = win.location.hash.slice(1); return ['overview','console','setup','portfolio'].includes(key) ? key : 'overview'; }
    function send(type, value) { if (frame.contentWindow) frame.contentWindow.postMessage({ type, ...(value ? { token: value } : {}) }, win.location.origin); }
    function lock(text = 'Locked. Unlock again to access all menu sections.') {
      generation++; token = ''; busy = false; if (controller) controller.abort(); controller = null;
      send('workspace-lock'); frame.src = 'about:blank'; loaded = ''; frame.hidden = true;
      el('workspace-token').value = ''; el('workspace-access').hidden = false;
      el('workspace-lock').disabled = true; el('workspace-submit').disabled = false;
      el('workspace-refresh').disabled = true;
      el('workspace-state').textContent = 'Locked';
      el('workspace-mode').textContent = 'Unlock to inspect the current account and its actual settings.';
      for (const id of ['workspace-feed', 'workspace-time', 'workspace-hours']) el(id).textContent = '';
      message(text);
    }
    function canLeave() {
      try { return !frame.contentWindow || !frame.contentWindow.AgenticNavigation || frame.contentWindow.AgenticNavigation.canNavigate(); }
      catch (_) { return true; }
    }
    function navigate() {
      const target = wanted();
      if (target !== current && !canLeave()) {
        win.history.replaceState(null, '', '#'+current);
        message('Finish or cancel the active request, confirmation or login window before changing sections.', true); return;
      }
      current = target;
      for (const name of ['overview', ...Object.keys(routes)]) {
        const link = el('nav-'+name); link.className = name === target ? 'active' : '';
        if (name === target) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
      }
      el('workspace-overview').hidden = target !== 'overview';
      el('workspace-section-note').hidden = target === 'overview';
      frame.hidden = target === 'overview' || !token;
      if (target === 'overview' || !token) { frame.src = 'about:blank'; loaded = ''; if (token) refreshInfo(); return; }
      if (loaded !== target) { loaded = target; frame.src = routes[target]; frame.title = el('nav-'+target).textContent; }
    }
    function render(data) {
      const manual = !data.automation_enabled;
      el('workspace-mode').textContent = (data.investment_horizon === 'long_term' ? 'Long-term paper' : 'Intraday paper') + (manual ? ' · Manual: entries require explicit operator instructions. No automatic stock picking or trading is running.' : data.automation_armed ? ' · Supervised automation armed; independent gates still apply.' : ' · Supervised automation disarmed; no new automatic entries.');
      el('workspace-feed').textContent = data.feed_connected ? 'Market-data connection established. Freshness and price-basis gates still apply.' : data.feed_requested ? 'Feed requested but disconnected/connecting. Inspect Broker & feed setup; check the session, entitlement and network.' : 'Feed not started. The startup shortcut opens the UI without a feed. Use Broker & feed setup → step 6 → Connect paper market data.';
      el('workspace-time').textContent = 'Last checked ' + new Intl.DateTimeFormat('en-IN', {timeZone:'Asia/Kolkata',dateStyle:'medium',timeStyle:'short'}).format(new Date(data.observed_at)) + ' IST · ' + (data.calendar_open ? 'Reviewed session currently open.' : 'No open reviewed session now.') + ' Quotes must be no older than ' + data.max_quote_age_seconds + ' seconds.';
      el('workspace-hours').textContent = 'Configured entry window: ' + data.entry_start + '–' + data.entry_end + ' IST on reviewed sessions, subject to earlier close cutoffs. ' + (data.investment_horizon === 'long_term' ? 'No forced end-of-day sale for long-term holdings.' : 'Intraday exit request time: '+data.flatten_at+' IST or the earlier session cutoff.') + (data.automation_enabled ? ' Proposal cap: '+data.candidate_cap_per_symbol_day+' per symbol/session; signals can be rejected and are not guaranteed fills.' : 'Unlocking does not enable automation.');
    }
    async function refreshInfo() {
      if (!token || busy) return;
      busy = true; el('workspace-refresh').disabled = true;
      const version = generation, active = new AbortController(); controller = active;
      const timeout = win.setTimeout(() => active.abort(), 10000);
      try {
        const response = await request('/api/workspace', {cache:'no-store',credentials:'omit',redirect:'error',signal:active.signal,headers:{Authorization:'Bearer '+token}});
        const data = await response.json(); if (version !== generation) return;
        if (response.status === 401 || response.status === 403) { lock('Local authorization changed. Unlock the workspace again.'); return; }
        if (!response.ok || data.mode !== 'paper') throw Error('Operating status could not be refreshed. Displayed guidance may be stale.');
        render(data);
      } catch (error) { if (version === generation) message('Status refresh failed or timed out. Displayed operating information may be stale; retry Refresh operating status.', true); }
      finally { win.clearTimeout(timeout); if (version === generation) {busy = false; controller = null; el('workspace-refresh').disabled = !token;} }
    }
    async function unlock() {
      if (busy) return;
      const supplied = el('workspace-token').value.trim(); el('workspace-token').value = '';
      if (!supplied) return;
      lock('Checking local operator access…'); busy = true; el('workspace-submit').disabled = true;
      const version = generation, active = new AbortController(); controller = active;
      const timeout = win.setTimeout(() => active.abort(), 10000);
      try {
        const r = await request('/api/workspace', {cache:'no-store',credentials:'omit',redirect:'error',signal:active.signal,headers:{Authorization:'Bearer '+supplied}});
        const data = await r.json(); if (version !== generation) return;
        if (!r.ok || data.mode !== 'paper') throw Error(r.status === 401 || r.status === 403 ? 'Use TRADING_OPERATOR_TOKEN from your local .env. Zerodha tokens do not unlock this workspace.' : 'Workspace access unavailable. Check the server and local operator configuration.');
        token = supplied; render(data); el('workspace-access').hidden = true; el('workspace-lock').disabled = false; el('workspace-state').textContent = 'Workspace unlocked';
        message('Unlocked for all menu sections in this tab. Reloading requires a new unlock.'); navigate();
      } catch (error) { if (version === generation) { lock(); message(error.name === 'AbortError' ? 'Access check timed out. Try again; no trading action was submitted.' : String(error.message), true); } }
      finally { win.clearTimeout(timeout); if (version === generation) { busy = false; controller = null; el('workspace-submit').disabled = false; el('workspace-refresh').disabled = !token; } }
    }
    win.addEventListener('message', event => {
      if (event.origin !== win.location.origin || event.source !== frame.contentWindow || !event.data) return;
      if (event.data.type === 'workspace-ready' && token && loaded === current && event.data.view === current) send('workspace-unlock', token);
      if (event.data.type === 'workspace-locked' && token) lock('The section locked or rejected authorization. Unlock the workspace again.');
      if (event.data.type === 'workspace-navigate' && ['overview','console','setup','portfolio'].includes(event.data.view)) { win.location.hash = '#'+event.data.view; }
      if (event.data.type === 'workspace-height' && Number.isFinite(event.data.height)) frame.style.height = Math.max(450, Math.min(12000, event.data.height))+'px';
    });
    el('workspace-unlock').addEventListener('submit', event => { event.preventDefault(); unlock(); });
    el('workspace-lock').addEventListener('click', () => lock());
    el('workspace-refresh').addEventListener('click', refreshInfo);
    win.addEventListener('hashchange', navigate);
    win.addEventListener('pagehide', () => lock());
    if (doc.addEventListener) doc.addEventListener('visibilitychange', () => { if (!doc.hidden && current === 'overview') refreshInfo(); });
    lock(); navigate();
    return { lock, navigate };
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { createWorkspace };
  else createWorkspace(document, window, window.fetch.bind(window));
})();
