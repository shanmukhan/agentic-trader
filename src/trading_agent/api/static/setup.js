(function () {
  'use strict';
  function createSetup(doc, win, request) {
    const el = id => doc.getElementById(id);
    let token = '', generation = 0, busy = false, controller = null, state = '', popup = null, pending = null, latest = null;
    const secretFields = ['token', 'api-key', 'api-secret', 'request-token'];
    const actionIds = ['save-credentials', 'login', 'profile', 'exchange-button', 'catalog', 'save-symbols', 'save-session', 'connect', 'disconnect', 'refresh-status'];
    function message(text, error = false) { el('message').textContent = text; el('message').className = error ? 'error' : ''; }
    function buttons() {
      for (const id of actionIds) el(id).disabled = !token || busy;
      el('unlock').disabled = busy;
      if (!token || busy || !latest) return;
      if (!latest.manual) { for (const id of actionIds) el(id).disabled = true; el('refresh-status').disabled = false; return; }
      for (const id of ['save-credentials', 'login', 'exchange-button', 'catalog', 'save-symbols']) el(id).disabled = latest.stream_requested;
      el('connect').disabled = latest.stream_requested || !latest.access_token_available || !latest.selected.length;
      el('disconnect').disabled = !latest.stream_requested;
    }
    function lock() {
      if (win.AgenticNavigation) win.AgenticNavigation.locked();
      generation++; token = ''; state = ''; busy = false; pending = null; latest = null;
      if (controller) controller.abort(); controller = null;
      if (popup && !popup.closed) popup.close(); popup = null;
      for (const id of secretFields.concat(['symbol-list', 'session-date', 'session-open', 'session-close', 'session-source'])) el(id).value = '';
      el('session-reviewed').checked = false; el('private').hidden = true; el('lock').disabled = true;
      for (const id of ['credentials-state', 'session-state', 'catalog-state', 'calendar-state', 'feed-state', 'redirect']) el(id).textContent = '';
      el('selected').replaceChildren(); el('sessions').replaceChildren();
      if (el('confirm').open) el('confirm').close();
      el('state').textContent = 'Locked'; buttons(); message('Locked. Broker credentials and setup status are hidden.');
      el('token').required = true;
    }
    function row(parent, text) { const p = doc.createElement('p'); p.textContent = text; el(parent).append(p); }
    function render(data) {
      latest = data;
      el('private').hidden = false; el('lock').disabled = false; el('state').textContent = 'Local setup unlocked';
      el('token').required = false;
      el('redirect').textContent = 'Register this redirect URL: ' + win.location.origin + '/';
      el('credentials-state').textContent = data.credentials_configured ? 'API key and secret configured (values hidden).' : 'API key and secret not configured.';
      el('session-state').textContent = (data.access_token_available ? 'A broker access token is available. ' : 'No broker access token is available. ') + (data.profile_verified_this_run ? 'Profile verified this run; streaming entitlement still needs a feed check.' : 'Saved credentials have not been verified this run.');
      el('catalog-state').textContent = data.catalog_count + ' catalog instruments stored. Selected tokens and tick sizes below are server-validated.';
      el('calendar-state').textContent = data.calendar_today ? 'Today has a reviewed session definition.' : 'Today is not in the reviewed calendar; entries remain blocked.';
      el('feed-state').textContent = data.feed_connected ? 'WebSocket connected. Check accepted quote freshness and remaining trading safeguards in the console.' : data.stream_requested ? 'Feed requested but not connected. Refresh status; check login, entitlement and network. Disconnect before trying another session.' : 'Feed disconnected. No new quotes can establish execution readiness.';
      el('selected').replaceChildren(); for (const item of data.selected) row('selected', item.symbol + ' · token ' + item.token + ' · tick ' + item.tick);
      el('sessions').replaceChildren(); for (const session of data.sessions) row('sessions', session.date + ' · ' + session.open + '–' + session.close + ' IST · ' + session.source);
      if (!el('symbol-list').value) el('symbol-list').value = data.selected.map(s => s.symbol).join(', ');
      if (!el('session-date').value) el('session-date').value = data.today;
      if (!data.manual) message('This account is automation/model-bound. Setup changes are unavailable; use its dedicated workflow.', true);
    }
    async function call(path = '', body) {
      if (!token || busy) return;
      const version = generation; busy = true; buttons();
      const active = new AbortController(); controller = active;
      const timeout = win.setTimeout(() => active.abort(), 30000);
      try {
        const response = await request('/api/setup' + path, { method: body === undefined ? 'GET' : 'POST', cache: 'no-store', credentials: 'omit', redirect: 'error', signal: active.signal,
          headers: { Authorization: 'Bearer ' + token, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) }, body: body === undefined ? undefined : JSON.stringify(body) });
        const data = await response.json();
        if (version !== generation) return;
        if (response.status === 401 || response.status === 403) { lock(); message('Use TRADING_OPERATOR_TOKEN from your local .env. Zerodha request/access tokens do not unlock this app.', true); return; }
        if (!response.ok) throw Error(typeof data.detail === 'string' ? data.detail : 'Setup request failed.');
        if (path !== '/login') render(data);
        message(path ? 'Setup action completed. Review the updated status; no orders were submitted.' : 'Setup status updated. All trading safeguards remain active.');
        return data;
      } catch (error) {
        if (version === generation) message(error.name === 'AbortError' ? 'Outcome unknown after timeout. Refresh status before retrying. A consumed login token needs a fresh login.' : String(error.message), true);
      } finally { win.clearTimeout(timeout); if (version === generation) { busy = false; controller = null; buttons(); } }
    }
    function confirm(text, action) { if (!token || busy) return; pending = action; el('confirm-text').textContent = text; el('confirm').showModal(); }
    el('access').addEventListener('submit', event => { event.preventDefault(); if (busy) return; token = el('token').value.trim() || token; el('token').value = ''; generation++; call(); });
    el('lock').addEventListener('click', lock);
    el('refresh-status').addEventListener('click', () => call());
    el('credentials').addEventListener('submit', event => { event.preventDefault(); if (!token || busy) return;
      // Clear secret fields before awaiting any network response. Never put them in a dialog.
      const body = { api_key: el('api-key').value.trim(), api_secret: el('api-secret').value.trim() };
      el('api-key').value = ''; el('api-secret').value = ''; state = ''; call('/credentials', body); });
    el('login').addEventListener('click', async () => {
      if (!token || busy) return;
      state = ''; el('request-token').value = '';
      if (popup && !popup.closed) popup.close();
      popup = win.open('about:blank', 'agentic-kite-login');
      const data = await call('/login', {});
      if (!data || !token) { if (popup && !popup.closed) popup.close(); return; }
      state = data.state;
      const url = new URL(data.login_url);
      if (url.protocol !== 'https:' || url.hostname !== 'kite.zerodha.com') { message('Unexpected broker login destination.', true); if (popup) popup.close(); return; }
      if (popup) popup.location = url.href;
      else message('Allow popups for this local site, then open a new Zerodha login.', true);
    });
    win.addEventListener('message', event => {
      if (!token || !state || event.origin !== win.location.origin || event.source !== popup || !event.data || event.data.type !== 'kite-request-token' || event.data.state !== state || typeof event.data.request_token !== 'string' || !/^[A-Za-z0-9_-]{1,256}$/.test(event.data.request_token)) return;
      el('request-token').value = event.data.request_token;
      message('Zerodha returned a request token. Select “Exchange and verify session” promptly.');
      if (popup && !popup.closed) popup.close();
    });
    el('exchange').addEventListener('submit', event => { event.preventDefault(); if (!token || busy) return;
      const value = el('request-token').value.trim(); el('request-token').value = '';
      if (!state) { message('Open a fresh Zerodha login from this page first.', true); return; }
      const activeState = state; state = ''; call('/exchange', { request_token: value, state: activeState }); });
    for (const operation of ['profile', 'catalog']) el(operation).addEventListener('click', () => call('/' + operation, {}));
    el('connect').addEventListener('click', () => confirm('Connect market data for ' + (latest ? latest.selected.map(s => s.symbol).join(', ') : 'the selected symbols') + '? Fresh quotes can resume pending fills and protective exits. This does not submit a new intent or arm automation.', () => call('/connect', {})));
    el('disconnect').addEventListener('click', () => confirm('Disconnect market data? Holdings stay open, and pending fills or exits must wait for quotes after reconnection.', () => call('/disconnect', {})));
    el('symbols').addEventListener('submit', event => { event.preventDefault(); const symbols = el('symbol-list').value.split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
      confirm('Save feed selection: ' + symbols.join(', ') + '? It must include all held symbols. This does not approve ETF costs or submit any order.', () => call('/symbols', { symbols })); });
    el('calendar').addEventListener('submit', event => { event.preventDefault(); const body = { date: el('session-date').value, open: el('session-open').value, close: el('session-close').value, source: el('session-source').value.trim(), reviewed: el('session-reviewed').checked };
      confirm('Add ' + body.date + ', ' + body.open + '–' + body.close + ' IST? Source: ' + body.source + '. Confirm against NSE notices. Existing session history cannot be overwritten.', async () => { const result = await call('/session', body); if (result) el('session-reviewed').checked = false; }); });
    el('cancel-confirm').addEventListener('click', () => { pending = null; el('confirm').close(); });
    el('confirm').addEventListener('cancel', () => { pending = null; });
    el('confirm-action').addEventListener('click', () => { const action = pending; pending = null; el('confirm').close(); if (action && token && !busy) action(); });
    lock(); return { lock, refresh: () => call(), canNavigate: () => !busy && !el('confirm').open && (!popup || popup.closed) };
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { createSetup };
  else {
    const view = createSetup(document, window, window.fetch.bind(window));
    if (window.AgenticNavigation) window.AgenticNavigation.connect(view, 'access');
  }
})();
