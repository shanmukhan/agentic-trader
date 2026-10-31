(function () {
  'use strict';
  const createDialogs = typeof module !== 'undefined' && module.exports ? require('./dialogs.js').createDialogs : window.AgenticDialogs;
  function createWatchlist(doc, win, fetcher) {
    const el = id => doc.getElementById(id), dialogs = createDialogs(doc, win);
    const node = (tag, text) => {const item = doc.createElement(tag); if (text !== undefined) item.textContent = text; return item;};
    let token = '', generation = 0, controller = null, busy = false, pending = false, stale = true, latest = null, draft = new Set(), items = [];
    const dirty = () => latest && JSON.stringify([...draft].sort()) !== JSON.stringify(latest.safety.symbols);
    function message(text, error = false) {el('message').textContent = text; el('message').className = error ? 'error' : ''; el('error-alert').textContent = error ? text : '';}
    function controls() {
      const blocked = !token || busy || pending;
      for (const id of ['review', 'discard', 'refresh', 'search-button', 'search', 'resume']) el(id).disabled = blocked;
      el('review').disabled = blocked || stale || !dirty(); el('discard').disabled = blocked || !dirty();
      el('refresh').disabled = blocked || dirty(); el('resume').disabled = blocked || stale || dirty() || !latest?.safety.paused || latest?.mode !== 'manual';
      el('unlock').disabled = busy; el('confirm-action').disabled = !pending || !el('ack').checked || busy;
      el('selection-state').textContent = latest ? draft.size + ' permitted stock' + (draft.size === 1 ? '' : 's') + (dirty() ? ' · Unsaved edits. Review and save, or discard before leaving.' : ' · Saved list.') : '';
      for (const list of ['selected', 'results']) for (const button of el(list).querySelectorAll('button')) button.disabled = blocked;
      win.AgenticFeedback?.setBusy(busy);
    }
    function clearConfirmation() {pending = false; el('ack').checked = false; for (const id of ['confirm-title', 'confirm-text', 'confirm-symbols']) el(id).textContent = ''; controls();}
    function lock() {
      generation++; controller?.abort(); controller = null; token = ''; busy = false; latest = null; stale = true; draft.clear(); items = [];
      dialogs.cancel(el('confirm')); clearConfirmation(); el('token').value = ''; el('token').required = true; el('main').hidden = true; el('lock').disabled = true; el('state').textContent = 'Locked';
      for (const id of ['selected', 'results']) el(id).replaceChildren();
      for (const id of ['updated', 'held-note', 'safety-state', 'safety-values', 'safety-data', 'catalog-state', 'search-state']) el(id).textContent = '';
      el('search').value = ''; message('Locked. Watchlist and account details are hidden.'); controls(); win.AgenticNavigation?.locked?.();
    }
    async function request(path, method = 'GET', body) {
      const version = generation, active = new AbortController(); controller = active;
      const timeout = win.setTimeout(() => active.abort(), 10000);
      try {
        const response = await fetcher(path, {method, cache: 'no-store', credentials: 'omit', redirect: 'error', signal: active.signal,
          headers: {Authorization: 'Bearer ' + token, ...(body === undefined ? {} : {'Content-Type': 'application/json'})}, ...(body === undefined ? {} : {body: JSON.stringify(body)})});
        if (version !== generation || !token) return null;
        if (response.status === 401 || response.status === 403) {lock(); message('Authorization failed. Unlock the workspace again.', true); return null;}
        if (!response.ok) throw Error('The request was rejected. Refresh the saved state and review again.');
        const data = await response.json(); return version === generation && token ? data : null;
      } finally {win.clearTimeout(timeout); if (controller === active) controller = null;}
    }
    function renderLists() {
      el('selected').replaceChildren(); el('results').replaceChildren();
      if (!draft.size) el('selected').append(node('li', 'No permitted stocks. All new purchases are blocked.'));
      for (const symbol of [...draft].sort()) {
        const item = node('li'), saved = latest?.selected.find(row => row.symbol === symbol), button = node('button', 'Remove'); button.type = 'button'; button.className = 'quiet'; button.setAttribute('aria-label', 'Remove ' + symbol + ' from watchlist');
        item.append(node('span', symbol + (saved && !saved.feed_selected ? ' · Not selected for market data' : '') + (saved?.held ? ' · Currently held' : '')));
        button.addEventListener('click', () => {if (busy || pending) return; draft.delete(symbol); renderLists(); controls();}); item.append(button); el('selected').append(item);
      }
      for (const row of items) {
        const item = node('li'), selected = draft.has(row.symbol), button = node('button', selected ? 'Added' : 'Add'); button.type = 'button'; button.className = 'quiet'; button.setAttribute('aria-label', (selected ? 'Remove ' : 'Add ') + row.symbol + (selected ? ' from watchlist' : ' to watchlist'));
        item.append(node('span', row.symbol)); button.textContent = selected ? 'Remove' : 'Add';
        button.addEventListener('click', () => {if (busy || pending) return; if (draft.has(row.symbol)) draft.delete(row.symbol); else draft.add(row.symbol); renderLists(); controls();}); item.append(button); el('results').append(item);
      }
      win.AgenticNavigation?.updated?.();
    }
    function render(data) {
      if (data.schema_version !== 1 || !Array.isArray(data.safety?.symbols) || !Number.isInteger(data.safety.revision) || !Array.isArray(data.selected)) throw Error('Invalid watchlist response');
      latest = data; draft = new Set(data.safety.symbols); stale = false;
      const s = data.safety, format = value => new Intl.NumberFormat('en-IN', {style:'currency',currency:'INR',maximumFractionDigits:2}).format(value);
      el('main').hidden = false; el('token').required = false; el('lock').disabled = false; el('state').textContent = s.paused ? 'Entries paused' : s.data_blocked_today ? 'Data incident · entries blocked today' : 'Watchlist enforced';
      el('updated').textContent = 'Saved state checked ' + new Intl.DateTimeFormat('en-IN', {timeZone:'Asia/Kolkata',dateStyle:'medium',timeStyle:'short'}).format(new Date(data.observed_at)) + ' IST.';
      el('safety-state').textContent = s.paused ? '25% drawdown pause is latched. Review the account before resetting its reference; recovery and restart cannot resume entries.' : 'Drawdown pause is clear. All other trading safeguards still apply.';
      el('safety-values').textContent = s.entries_today + ' / 5 entry slots used today · Current maximum order cost ' + format(s.max_order_cost) + ' · Observed reference ' + format(s.peak_equity) + ' · Drawdown ' + Number(s.drawdown_pct).toFixed(2) + '%' + (s.valuation_fresh ? '.' : ' · Valuation is stale or incomplete; do not use this amount for trading.');
      el('safety-data').textContent = s.data_blocked_today ? 'Price integrity incident: ' + s.data_reason + '. No new entries for the rest of this IST day. Refreshing or resetting the drawdown pause cannot clear it.' : 'Fresh, consistent prices and a readable account ledger are required for entries.';
      el('held-note').textContent = data.held_outside_watchlist.length ? 'Exit only: ' + data.held_outside_watchlist.join(', ') + '. Keep their feed subscriptions for protective exits.' : '';
      el('catalog-state').textContent = data.catalog_count + ' supported NSE catalog instruments. ' + (data.catalog_imported_at ? 'Catalog imported ' + data.catalog_imported_at + '. This is a saved catalog; refresh it in Broker & Data when needed.' : 'Catalog import time is unavailable. Import it in Broker & Data before relying on its coverage.');
      el('resume').hidden = !s.paused; renderLists(); controls();
    }
    async function refresh() {
      if (!token || busy || pending || dirty()) return; const version = generation; busy = true; controls();
      try {const data = await request('/api/desk/watchlist'); if (data) {render(data); message('Saved watchlist loaded. Search the NSE catalog to edit permitted stocks.');}}
      catch (_) {if (version === generation) {stale = true; el('state').textContent = 'Display stale'; message('Watchlist unavailable. Refresh before changing permissions.', true);}}
      finally {if (version === generation) {busy = false; controls();}}
    }
    async function search() {
      if (!token || busy || pending) return; const version = generation; busy = true; controls();
      try {const data = await request('/api/desk/watchlist/catalog?q=' + encodeURIComponent(el('search').value.trim())); if (data) {
        if (data.schema_version !== 1 || !Array.isArray(data.items)) throw Error('schema'); items = data.items; renderLists(); el('search-state').textContent = data.matches ? 'Showing ' + items.length + ' of ' + data.matches + ' matches. Narrow the search to find another symbol.' : 'No matches. Check the symbol or import the NSE catalog in Broker & Data.';
      }} catch (_) {if (version === generation) {items = []; renderLists(); el('search-state').textContent = 'Catalog search failed. Retry the search; your edits are retained.';}}
      finally {if (version === generation) {busy = false; controls();}}
    }
    async function mutate(path, body) {
      if (!token || busy) return; const version = generation; busy = true; controls();
      try {const data = await request(path, 'POST', body); if (data) {render(data); message(path.endsWith('/resume') ? 'Drawdown reference reset. Review Paper Trading before explicitly starting a mode.' : 'Watchlist saved. Pending buys cancelled and decisions paused. Review feed selection and Paper Trading before restarting.');}}
      catch (_) {if (version === generation) {stale = true; draft = new Set(latest.safety.symbols); renderLists(); el('state').textContent = 'Outcome unverified'; message('Save outcome is unverified. Refresh saved state before editing or retrying. No automatic retry was sent.', true);}}
      finally {if (version === generation) {busy = false; controls();}}
    }
    function review(resume = false) {
      if (!latest || stale || busy || pending || resume && dirty() || !resume && !dirty()) return;
      pending = true; el('ack').checked = false;
      el('confirm-title').textContent = resume ? 'Reset the drawdown reference?' : 'Replace the permitted watchlist?';
      el('confirm-text').textContent = resume ? 'Acknowledge the loss and use current equity as the new peak reference. Trading stays in manual mode. Daily loss, kill switch, five-entry limit and today’s data block remain active.' : 'Cancel every pending buy and pause strategy decisions. Existing holdings remain and may be sold. Only the stocks below may be bought; all other risk checks still apply.';
      el('confirm-symbols').textContent = resume ? 'Current observed drawdown: ' + latest.safety.drawdown_pct + '%.' : [...draft].sort().join(', ') || 'Empty list: block all new purchases.';
      const body = {revision: latest.safety.revision, acknowledged: true, ...(!resume ? {symbols:[...draft].sort()} : {})};
      dialogs.confirmWith(el('confirm'), reviewed => {clearConfirmation(); mutate(resume ? '/api/desk/safety/resume' : '/api/desk/watchlist', reviewed);}, body, {cancel:clearConfirmation}); controls();
    }
    el('access').addEventListener('submit', event => {event.preventDefault(); if (busy) return; const supplied = el('token').value.trim(); lock(); token = supplied; refresh();});
    el('lock').addEventListener('click', lock); el('refresh').addEventListener('click', refresh);
    el('search-form').addEventListener('submit', event => {event.preventDefault(); search();});
    el('review').addEventListener('click', () => review()); el('resume').addEventListener('click', () => review(true));
    el('discard').addEventListener('click', () => {if (!latest || busy || pending) return; draft = new Set(latest.safety.symbols); renderLists(); controls(); message('Edits discarded. Refresh to check the saved state.');});
    el('ack').addEventListener('change', controls); el('cancel').addEventListener('click', () => dialogs.cancel(el('confirm'))); el('confirm-action').addEventListener('click', () => {if (el('ack').checked && !busy) dialogs.confirm(el('confirm'));});
    win.addEventListener('pagehide', lock); lock();
    const api = {lock, refresh, search, canNavigate: () => !busy && !pending && !dirty()}; win.AgenticNavigation?.connect(api, 'access'); return api;
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {createWatchlist};
  else createWatchlist(document, window, window.fetch.bind(window));
})();
