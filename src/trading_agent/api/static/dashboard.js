/* No framework, external assets, browser persistence, or client-side risk calculations. */
(function () {
  'use strict';

  function formatMoney(value) {
    if (typeof value !== 'string') return '—';
    const match = /^(-?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(value);
    if (!match) return '—';
    const sign = match[1], exponent = Number(match[4] || 0);
    // Only the decimal-point position is numeric; money never passes through Number.
    // Preserve unusual huge representations literally rather than allocate an unbounded expansion.
    if (!Number.isSafeInteger(exponent) || Math.abs(exponent) > 1000 || value.length > 1000)
      return sign + '₹' + value.replace(/^-/, '');
    const digits = match[2] + (match[3] || ''), point = match[2].length + exponent;
    let whole, fraction;
    if (point <= 0) { whole = '0'; fraction = '0'.repeat(-point) + digits; }
    else if (point >= digits.length) { whole = digits + '0'.repeat(point - digits.length); fraction = ''; }
    else { whole = digits.slice(0, point); fraction = digits.slice(point); }
    whole = whole.replace(/^0+(?=\d)/, '');
    const tail = whole.slice(-3);
    const head = whole.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ',');
    return sign + '₹' + (head ? head + ',' : '') + tail + '.' + fraction.padEnd(2, '0');
  }

  function createConsole(doc, win, request) {
    let token = '', generation = 0, busy = false, mutating = false, fresh = false;
    let controller = null, lastReceipt = 0, latest = null, pendingAction = null;
    const el = id => doc.getElementById(id);
    const controls = ['kill', 'flatten', 'reset', 'arm', 'disarm'];
    const routes = { kill: '/api/control/kill', flatten: '/api/control/flatten',
      reset: '/api/control/reset', arm: '/api/paper/automation/arm', disarm: '/api/paper/automation/disarm' };
    const human = reason => reason.toLowerCase().replaceAll('_', ' ');
    const message = (text, error = false) => {
      el('message').textContent = text;
      el('message').className = error ? 'error' : '';
    };
    const badge = (id, text, good = false) => {
      el(id).textContent = text;
      el(id).className = 'badge ' + (good ? 'good' : 'warn');
    };
    function textNode(tag, text, className = '') {
      const node = doc.createElement(tag);
      node.textContent = text;
      node.className = className;
      return node;
    }
    function records(id, items, empty, render) {
      const target = el(id);
      target.replaceChildren();
      if (!items.length) target.append(textNode('p', empty, 'muted'));
      for (const item of items) {
        const row = doc.createElement('article');
        row.className = 'record';
        render(row, item);
        target.append(row);
      }
    }
    function buttons() {
      for (const name of controls) el(name).disabled = !token || !latest || mutating;
      if (!token || !latest || mutating) return;
      const a = latest.account, auto = latest.automation;
      el('arm').disabled = !fresh || !auto.enabled || auto.armed || a.kill || a.faulted ||
        auto.readiness_reasons.length > 0;
      el('reset').disabled = !fresh || !a.kill || a.faulted || a.positions.length > 0;
      el('disarm').disabled = !auto.enabled;
    }
    function stale(text) {
      fresh = false;
      badge('feed', 'Display stale');
      badge('readiness', 'Update required');
      el('valuation').textContent = 'Displayed values are stale estimates';
      message(text, true);
      buttons();
    }
    function lock() {
      generation += 1;
      token = ''; fresh = false; latest = null; busy = false; mutating = false;
      if (controller) controller.abort();
      controller = null;
      pendingAction = null;
      if (el('confirm').open) el('confirm').close();
      el('token').value = ''; el('token').required = true; el('lock').disabled = true;
      for (const id of ['equity', 'cash', 'pnl']) el(id).textContent = '—';
      for (const id of ['reserved', 'fees', 'risk', 'valuation', 'order-count', 'details'])
        el(id).textContent = 'Locked';
      for (const id of ['orders', 'positions', 'quotes'])
        el(id).replaceChildren(textNode('p', 'Locked', 'muted'));
      el('reasons').replaceChildren(textNode('li', 'Unlock to inspect readiness.'));
      for (const id of ['feed', 'readiness', 'armed']) badge(id, 'Locked');
      el('updated').textContent = 'No account data loaded';
      message('Locked. Enter an operator token to view the account.');
      buttons();
    }
    function render(data) {
      const a = data.account, auto = data.automation;
      latest = data; fresh = true; lastReceipt = win.Date.now();
      el('equity').textContent = formatMoney(a.equity);
      el('cash').textContent = formatMoney(a.available_cash);
      el('pnl').textContent = formatMoney(a.day_pnl);
      el('reserved').textContent = 'Reserved: ' + formatMoney(a.reserved_cash);
      el('fees').textContent = 'Charged fees: ' + formatMoney(a.fees);
      badge('feed', a.faulted ? 'Runtime fault' : a.feed_connected ? 'Feed connected' : 'Feed offline',
        a.feed_connected && !a.faulted);
      badge('readiness', data.entry_readiness.ready ? 'Prerequisites met' : 'Entries blocked', data.entry_readiness.ready);
      badge('armed', !auto.enabled ? 'Manual paper' : auto.armed ? 'Armed' : 'Disarmed', auto.armed);
      el('risk').textContent = (a.kill ? 'Kill active: ' + a.kill_reason : 'Kill switch inactive') +
        ' · Planned risk: ' + formatMoney(a.reserved_risk);
      el('valuation').textContent = a.valuation_fresh ? 'Held-position quotes fresh (or account flat)' : 'Stale valuation · estimate only';
      el('reasons').replaceChildren();
      for (const reason of data.entry_readiness.reasons)
        el('reasons').append(textNode('li', human(reason)));
      if (!data.entry_readiness.reasons.length)
        el('reasons').append(textNode('li', 'Data prerequisites met; candidate risk checks still apply.'));
      records('quotes', data.quotes, 'No observed quotes. Connect a reviewed read-only feed.', (row, q) => {
        row.append(textNode('strong', q.symbol));
        row.append(textNode('p', q.fresh ? 'Fresh' : 'Stale or missing', 'record-value'));
      });
      records('positions', a.positions, 'Flat · no open positions', (row, p) => {
        row.append(textNode('strong', p.symbol + ' · ' + p.quantity + ' shares'));
        row.append(textNode('p', 'Unrealized ' + formatMoney(p.unrealized_pnl), 'record-value'));
        row.append(textNode('p', 'Stop ' + formatMoney(p.stop) + ' · Target ' + formatMoney(p.target), 'muted'));
      });
      el('order-count').textContent = data.orders_truncated ? 'Showing latest ' + data.order_limit + ' · older orders omitted' : data.orders.length + ' recorded';
      records('orders', data.orders, 'No paper orders recorded', (row, o) => {
        const title = doc.createElement('div');
        title.append(textNode('strong', o.symbol + ' · ' + o.side + ' · ' + o.state));
        title.append(textNode('p', o.id, 'muted'));
        title.append(textNode('p', o.reason, 'muted'));
        row.append(title);
        row.append(textNode('p', 'Filled ' + o.filled + ' / ' + o.quantity, 'record-value'));
      });
      el('details').textContent = JSON.stringify({ observed_at: data.observed_at, account: a, automation: auto }, null, 2);
      el('updated').textContent = 'Updated ' + new Intl.DateTimeFormat('en-IN', {
        timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'medium'
      }).format(new Date(data.observed_at)) + ' IST';
      message('Account updated. All amounts are virtual INR.');
      buttons();
    }
    async function call(path, method, signal) {
      const response = await request(path, { method, signal, cache: 'no-store',
        credentials: 'omit', redirect: 'error', headers: { Authorization: 'Bearer ' + token } });
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          const error = Error('Operator authorization failed. Unlock again.');
          error.authorization = true;
          throw error;
        }
        const data = await response.json();
        throw Error(typeof data.detail === 'string' ? data.detail : 'Request failed (' + response.status + ')');
      }
      return response.json();
    }
    async function refresh() {
      if (!token || busy || mutating) return;
      busy = true;
      const version = generation;
      const active = new AbortController(); controller = active;
      const timeout = win.setTimeout(() => active.abort(), 10000);
      try {
        const data = await call('/api/console', 'GET', active.signal);
        if (version !== generation) return;
        if (data.schema_version !== 1 || data.account.mode !== 'paper') throw Error('Unexpected console response');
        render(data);
      } catch (error) {
        if (version !== generation) return;
        if (error.authorization) { lock(); message(error.message, true); }
        else stale(error.name === 'AbortError' ? 'Update timed out. Displayed values may be stale.' : error.message);
      } finally {
        win.clearTimeout(timeout);
        if (version === generation) { busy = false; controller = null; }
      }
    }
    async function action(name) {
      if (!token || mutating || !latest) return;
      if (['arm', 'reset'].includes(name) && (!fresh || win.Date.now() - lastReceipt > 6000)) {
        stale('Refresh the account before confirming this action.'); return;
      }
      const version = generation;
      // Invalidate any earlier poll, so it cannot overwrite post-action state.
      generation += 1;
      if (controller) controller.abort();
      busy = false; mutating = true; buttons();
      const actionVersion = generation;
      const active = new AbortController(); controller = active;
      const timeout = win.setTimeout(() => active.abort(), 10000);
      let outcome = '', outcomeError = false;
      try {
        await call(routes[name], 'POST', active.signal);
        if (actionVersion !== generation) return;
        outcome = name === 'kill' || name === 'flatten' ? 'Kill active. Exits queued; inspect positions for remaining exposure.' : 'Paper action completed. Inspect current state.';
      } catch (error) {
        if (actionVersion !== generation) return;
        if (error.authorization) { lock(); message(error.message, true); return; }
        outcomeError = true;
        outcome = error.name === 'AbortError' ? 'Action outcome unknown after timeout. Refresh before retrying.' : error.message;
        stale(outcome);
      } finally {
        win.clearTimeout(timeout);
        if (actionVersion === generation) { mutating = false; controller = null; buttons(); }
      }
      if (generation === version + 1) { await refresh(); if (outcome) message(outcome, outcomeError); }
    }
    el('unlock').addEventListener('submit', event => {
      event.preventDefault();
      const supplied = el('token').value;
      if (supplied) { lock(); token = supplied; el('token').required = false; el('lock').disabled = false; }
      refresh();
    });
    el('lock').addEventListener('click', lock);
    for (const name of controls) el(name).addEventListener('click', () => {
      if (['arm', 'reset'].includes(name)) {
        pendingAction = name;
        el('confirm-title').textContent = name === 'arm' ? 'Arm paper automation?' : 'Reset the kill switch?';
        el('confirm-description').textContent = name === 'arm' ?
          'This permits new virtual entries while all server-side readiness and risk checks pass. Protective exits remain active.' :
          'The server must verify a flat account and eligible risk state. This does not rearm automation.';
        el('confirm').showModal(); el('cancel-confirm').focus();
      } else action(name);
    });
    el('cancel-confirm').addEventListener('click', () => { pendingAction = null; el('confirm').close(); });
    el('confirm-action').addEventListener('click', () => {
      const name = pendingAction; pendingAction = null; el('confirm').close();
      if (name) action(name);
    });
    el('confirm').addEventListener('cancel', () => { pendingAction = null; });
    doc.addEventListener('visibilitychange', () => { if (!doc.hidden) refresh(); });
    win.setInterval(() => { if (token && !doc.hidden) refresh(); }, 3000);
    win.setInterval(() => {
      if (token && fresh && win.Date.now() - lastReceipt > 6000)
        stale('No fresh update for over 6 seconds. Displayed values may be stale.');
    }, 1000);
    lock();
    return { refresh, lock };
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { formatMoney, createConsole };
  if (typeof document !== 'undefined') createConsole(document, window, window.fetch.bind(window));
})();
