(function () {
  'use strict';
  const createDialogs = typeof module !== 'undefined' && module.exports ? require('./dialogs.js').createDialogs : window.AgenticDialogs;
  function createSetup(doc, win, request) {
    const dialogs = createDialogs(doc, win);
    const el = id => doc.getElementById(id);
    let token = '', generation = 0, busy = false, controller = null, state = '', popup = null, pending = null, latest = null;
    let recommendedStep = 1;
    const secretFields = ['token', 'api-key', 'api-secret', 'request-token'];
    const actionIds = ['save-credentials', 'login', 'profile', 'exchange-button', 'catalog', 'save-symbols', 'save-session', 'connect', 'disconnect', 'refresh-status'];
    const stepIds = ['setup-step-1', 'setup-step-2', 'setup-step-3', 'setup-step-4', 'setup-step-5', 'feed-connection'];
    const stepTitles = ['Register your Kite app', 'Save app credentials', 'Sign in to Zerodha', 'Choose stock subscriptions', 'Review an exchange session', 'Connect market data'];
    function message(text, error = false) { el('message').textContent = text; el('message').className = error ? 'error' : ''; }
    function sessionMessage(text, error = false) { el('session-feedback').textContent = text; el('session-feedback').className = error ? 'error' : ''; }
    function sessionStatus(data) {
      el('session-state').textContent = (data.access_token_available ? 'A broker access token is available. ' : 'No broker access token is available. ') + (data.profile_verified_this_run ? 'Profile verified this run; streaming entitlement still needs a feed check.' : 'Saved credentials have not been verified this run.');
    }
    function stepProgress(number) { el('setup-progress').textContent = 'Step ' + number + ' of 6 · ' + stepTitles[number - 1]; }
    function openStep(number, focus = false) {
      if (!token || number < 1 || number > stepIds.length) return;
      stepIds.forEach((id, index) => { el(id).open = index === number - 1; });
      stepProgress(number);
      if (focus) el('setup-step-title-' + number).focus();
    }
    function overview(data) {
      const diagnostic = data.feed_diagnostics;
      const connected = data.feed_connected, requested = data.stream_requested;
      el('connection-status').textContent = connected ? 'Data connected' : requested ? diagnostic?.state === 'failed' ? 'Connection needs attention' : 'Connecting / reconnecting' : 'Data disconnected';
      el('connection-description').textContent = connected ? 'Zerodha market data is connected. Quote freshness, liquidity and today’s price-basis reviews determine whether a quote can be used for paper execution.' : requested ? 'A connection has been requested. The streaming status below explains progress and recovery; fresh usable quotes are still required.' : 'Your paper account is not receiving new market data. Review the next step below to prepare the connection.';
      el('overview-session').textContent = data.profile_verified_this_run ? 'Verified this run' : data.access_token_available ? 'Saved · not checked this run' : 'Sign-in needed';
      el('overview-symbols').textContent = data.selected.length + ' of 10 stocks';
      el('overview-calendar').textContent = data.calendar_today ? 'Today reviewed' : 'Today needs review';
      let label, guidance;
      if (!data.manual) {
        recommendedStep = 6; label = 'Review account connection';
        guidance = 'This account is managed by a dedicated automation/model workflow. Connection settings cannot be changed here.';
      } else if (!data.credentials_configured) {
        recommendedStep = 1; label = 'Start broker setup';
        guidance = 'Register a Kite app with market-data access, then save its API key and secret privately.';
      } else if (requested && !connected) {
        recommendedStep = 6; label = 'Review connection recovery';
        guidance = diagnostic?.state === 'failed' ? 'Connection retries are exhausted. Resolve the reported cause, then review Disconnect and Connect in step 6.' : 'Review the connection status in step 6. Refresh status to check progress; disconnect before replacing a broker session.';
      } else if (!data.access_token_available || (!data.profile_verified_this_run && !connected)) {
        recommendedStep = 3; label = data.access_token_available ? 'Check saved broker session' : 'Sign in to Zerodha';
        guidance = data.access_token_available ? 'A saved token can expire. Open step 3 and explicitly check the saved session before connecting.' : 'Open Zerodha login, complete 2FA and exchange the one-time request token in step 3.';
      } else if (!data.catalog_count || !data.selected.length) {
        recommendedStep = 4; label = 'Choose stock subscriptions';
        guidance = 'Download the NSE catalog and review up to ten saved stock subscriptions. Navigation alone does not save a selection.';
      } else if (!data.calendar_today) {
        recommendedStep = 5; label = 'Review today’s exchange session';
        guidance = 'Today’s session needs an explicit review against exchange notices. The default hours do not approve the date.';
      } else {
        recommendedStep = 6; label = connected ? 'Review feed & quote readiness' : 'Review market-data connection';
        guidance = connected ? 'Review trading readiness after checking the feed. A connected socket alone does not make a quote usable or authorize an order.' : 'Review the saved subscriptions and connection confirmation in step 6. Connecting can resume pending paper fills and protective exits.';
      }
      el('setup-next-action').textContent = label;
      el('connection-next').textContent = guidance;
      const states = ['Developer registration', data.credentials_configured ? 'Configured' : 'Needed', data.profile_verified_this_run ? 'Verified this run' : data.access_token_available ? 'Saved · check session' : 'Sign-in needed', data.selected.length ? data.selected.length + ' saved stocks' : 'Selection needed', data.calendar_today ? 'Today reviewed' : 'Review needed', connected ? 'Connected' : requested ? 'Requested' : 'Disconnected'];
      states.forEach((text, index) => { el('setup-step-state-' + (index + 1)).textContent = text; });
    }
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
      for (const id of ['connection-status', 'connection-description', 'overview-session', 'overview-symbols', 'overview-calendar', 'connection-next']) el(id).textContent = '';
      stepIds.forEach((id, index) => { el(id).open = false; el('setup-step-state-' + (index + 1)).textContent = ''; });
      el('setup-progress').textContent = 'Choose a step to review its settings.';
      el('setup-next-action').textContent = 'Review connection setup'; recommendedStep = 1;
      el('selected').replaceChildren(); el('sessions').replaceChildren();
      el('selected-title').textContent = 'Saved feed subscriptions';
      dialogs.cancel(el('confirm'));
      sessionMessage(''); el('profile').textContent = 'Check saved broker session';
      el('state').textContent = 'Locked'; buttons(); message('Locked. Broker credentials and setup status are hidden.');
      el('token').required = true;
    }
    function row(parent, text) { const p = doc.createElement('p'); p.textContent = text; el(parent).append(p); }
    function render(data) {
      const firstStatus = !latest;
      if (firstStatus) {
        el('session-open').value = '09:15';
        el('session-close').value = '15:30';
      }
      latest = data;
      el('private').hidden = false; el('lock').disabled = false; el('state').textContent = 'Local setup unlocked';
      el('token').required = false;
      el('redirect').textContent = 'Register this redirect URL: ' + win.location.origin + '/';
      el('credentials-state').textContent = data.credentials_configured ? 'API key and secret configured (values hidden).' : 'API key and secret not configured.';
      sessionStatus(data);
      sessionMessage('');
      el('catalog-state').textContent = data.catalog_count + ' catalog instruments stored. Selected tokens and tick sizes below are server-validated.';
      el('selected-title').textContent = 'Saved feed subscriptions (' + data.selected.length + ' of 10)';
      el('calendar-state').textContent = data.calendar_today ? 'Today has a reviewed session definition.' : 'Today is not in the reviewed calendar; entries remain blocked.';
      const diagnostic = data.feed_diagnostics;
      const failures = {
        handshake_rejected: 'Zerodha refused the WebSocket handshake. Check the saved broker session and streaming entitlement.',
        timeout: 'The connection or incoming data timed out. Check the network and refresh status.',
        broker_rejected: 'Zerodha reported a streaming error. Check the saved broker session and streaming entitlement.',
        invalid_data: 'The feed returned unsupported or invalid data. Trading quotes remain blocked; inspect the application before retrying.',
        processing_error: 'The application could not process a quote. Inspect account health and the server before reconnecting.',
        connection_lost: 'The market-data connection failed or closed. Check the network and broker session.'
      };
      let feedText = data.feed_connected ? 'WebSocket connected. A connection is not proof of fresh usable quotes. Check quote freshness and trading safeguards in the console.' : data.stream_requested ? 'Feed requested but not connected. Refresh status; check login, entitlement and network. Disconnect before trying another session.' : 'Feed disconnected. No new quotes can establish execution readiness.';
      if (data.stream_requested && diagnostic) {
        if (!data.feed_connected) {
          if (diagnostic.state === 'failed') feedText = 'Connection retries exhausted. Select Disconnect market data, then Connect paper market data after resolving the cause.';
          else if (diagnostic.state === 'retrying') feedText = 'Feed reconnecting after failure ' + diagnostic.failures + ' of 10. Refresh setup status to check progress.';
          else if (diagnostic.state === 'connecting') feedText = 'Connecting to Zerodha market data. Wait a few seconds, then select Refresh setup status.';
          if (failures[diagnostic.last_failure]) feedText += ' ' + failures[diagnostic.last_failure];
        }
        if (diagnostic.unusable_quotes > 0) feedText += ' Empty-sided/zero-liquidity quotes ignored: ' + diagnostic.unusable_quotes + '. This can occur after market hours or in an illiquid book. No price or liquidity is invented; these observations cannot fill orders.';
      }
      el('feed-state').textContent = feedText;
      overview(data);
      el('selected').replaceChildren(); for (const item of data.selected) row('selected', item.symbol + ' · token ' + item.token + ' · tick ' + item.tick);
      el('sessions').replaceChildren(); for (const session of data.sessions) row('sessions', session.date + ' · ' + session.open + '–' + session.close + ' IST · ' + session.source);
      if (!el('symbol-list').value) el('symbol-list').value = data.selected.map(s => s.symbol).join(', ');
      if (!el('session-date').value) el('session-date').value = data.today;
      if (!data.manual) message('This account is automation/model-bound. Setup changes are unavailable; use its dedicated workflow.', true);
      if (firstStatus) openStep(recommendedStep);
      if (win.AgenticNavigation?.updated) win.AgenticNavigation.updated();
    }
    async function call(path = '', body) {
      if (!token || busy) return;
      const version = generation; busy = true; buttons();
      const sessionAction = ['/profile', '/login', '/exchange'].includes(path);
      if (sessionAction) sessionMessage(path === '/profile' ? 'Checking saved broker session with Zerodha… Please wait (up to 30 seconds).' : path === '/exchange' ? 'Exchanging the request token and verifying the broker session…' : 'Opening Zerodha login…');
      if (path === '/profile') el('profile').textContent = 'Checking saved broker session…';
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
        if (sessionAction) sessionMessage(path === '/login' ? 'Complete login and 2FA in the Zerodha window, then exchange the returned request token here.' : 'Broker session verified successfully. This checks profile access only; connect paper market data in step 6 and check fresh usable quotes separately.');
        else if (path === '/credentials') sessionMessage('App credentials saved. Open Zerodha login to create a new broker session.');
        return data;
      } catch (error) {
        if (version === generation) {
          let text = error.name === 'AbortError' ? 'Outcome unknown after timeout. Refresh status before retrying. A consumed login token needs a fresh login.' : String(error.message);
          if (path === '/profile') {
            if (latest) { latest = { ...latest, profile_verified_this_run: false }; sessionStatus(latest); overview(latest); }
            text = (error.name === 'AbortError' ? 'Saved broker session check timed out.' : text) + ' The session could not be verified. Check your connection and retry. If the session has expired, disconnect any requested feed in step 6, then open Zerodha login and exchange a fresh request token.';
          }
          message(text, true); if (sessionAction) sessionMessage(text, true);
        }
      } finally { win.clearTimeout(timeout); if (version === generation) { busy = false; controller = null; el('profile').textContent = 'Check saved broker session'; buttons(); } }
    }
    function confirm(text, action) {
      if (!token || busy || el('confirm').open) return;
      pending = action; el('confirm-text').textContent = text;
      if (!dialogs.open(el('confirm'), { cancel: () => { pending = null; }, focus: el('cancel-confirm') }))
        message('The confirmation could not be displayed. Reopen Broker & Data and review the action again. Nothing was submitted.', true);
    }
    el('access').addEventListener('submit', event => { event.preventDefault(); if (busy) return; token = el('token').value.trim() || token; el('token').value = ''; generation++; call(); });
    el('setup-next-action').addEventListener('click', () => openStep(recommendedStep, true));
    stepIds.forEach((id, index) => {
      el(id).addEventListener('toggle', () => { if (token && el(id).open) stepProgress(index + 1); });
      if (index > 0) el('setup-back-' + (index + 1)).addEventListener('click', () => openStep(index, true));
      if (index < stepIds.length - 1) el('setup-next-' + (index + 1)).addEventListener('click', () => openStep(index + 2, true));
    });
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
    el('cancel-confirm').addEventListener('click', () => dialogs.cancel(el('confirm')));
    el('confirm-action').addEventListener('click', () => { const action = pending; pending = null; dialogs.close(el('confirm')); if (action && token && !busy) action(); });
    win.addEventListener?.('pagehide', lock);
    lock(); return { lock, refresh: () => call(), canNavigate: () => !busy && !el('confirm').open && (!popup || popup.closed) };
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { createSetup };
  else {
    const view = createSetup(document, window, window.fetch.bind(window));
    if (window.AgenticNavigation) window.AgenticNavigation.connect(view, 'access');
  }
})();
