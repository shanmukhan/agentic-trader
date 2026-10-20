/* No framework, external assets, browser persistence, or client-side risk calculations. */
(function () {
  'use strict';

  const formatMoney = typeof module !== 'undefined' && module.exports ? require('./money.js') : window.AgenticMoney;

  function createConsole(doc, win, request) {
    let token = '', generation = 0, busy = false, mutating = false, fresh = false;
    let controller = null, lastReceipt = 0, latest = null, pendingAction = null, holdingExitButtons = [];
    const el = id => doc.getElementById(id);
    const controls = ['kill', 'flatten', 'reset', 'arm', 'disarm'];
    const routes = { kill: '/api/control/kill', flatten: '/api/control/flatten',
      reset: '/api/control/reset', arm: '/api/paper/automation/arm', disarm: '/api/paper/automation/disarm',
      review: '/api/paper/long-term/reviews', exit: '/api/paper/long-term/exit' };
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
      for (const button of holdingExitButtons) button.disabled = !token || !latest || mutating;
      el('review-submit').disabled = !token || !latest || mutating || !fresh || latest.account.investment_horizon !== 'long_term';
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
      token = ''; fresh = false; latest = null; busy = false; mutating = false; holdingExitButtons = [];
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
      el('horizon').textContent = 'Paper account';
      el('long-term').hidden = true; el('long-term-state').textContent = '';
      ['lt-receivable', 'lt-fractions', 'lt-income', 'lt-guidance'].forEach(id => { el(id).textContent = ''; });
      for (const id of ['review-symbol', 'review-date', 'review-reference']) el(id).value = '';
      el('review-clear').checked = false;
      el('updated').textContent = 'No account data loaded';
      message('Locked. Enter an operator token to view the account.');
      buttons();
    }
    function render(data) {
      const a = data.account, auto = data.automation;
      latest = data; fresh = true; lastReceipt = win.Date.now();
      const longTerm = a.investment_horizon === 'long_term';
      el('horizon').textContent = longTerm ? 'Long-term paper' : 'Intraday paper';
      el('long-term').hidden = !longTerm;
      if (longTerm) {
        el('long-term-state').textContent = 'Observed peak ' + formatMoney(a.long_term.peak_equity) +
          ' · Drawdown ' + formatMoney(a.long_term.observed_drawdown) +
          ' / ' + formatMoney(a.long_term.drawdown_limit) + ' · Delivery fee buffer ' +
          formatMoney(a.delivery_fee_buffer) + ' · Quarantined: ' +
          (a.long_term.quarantined_symbols.join(', ') || 'none');
        el('lt-receivable').textContent = formatMoney(a.long_term.receivable || '0');
        el('lt-fractions').textContent = String(a.long_term.unvalued_fractional_claims || 0);
        el('lt-income').textContent = formatMoney(a.long_term.income_received || '0');
        el('lt-guidance').textContent = a.long_term.quarantined_symbols.length ?
          'Action needed: quarantined symbols cannot accept prices or fill orders. Stop the service and follow the reviewed offline adjustment workflow. A clear review alone cannot remove quarantine.' :
          a.long_term.unvalued_fractional_claims ?
          'Fractional payout pending: portfolio value is incomplete and new entries are paused. Review and record the cash-in-lieu receipt when available. Whole-share exits still require usable quotes.' :
          'Before using new prices, review the current session’s price basis. Unpaid dividends become spendable only after a separate reviewed receipt. Queued exits still need fresh quotes and liquidity.';
        if (!el('review-date').value)
          el('review-date').value = new Date(new Date(data.observed_at).getTime() + 19800000).toISOString().slice(0, 10);
      }
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
      holdingExitButtons = [];
      records('positions', a.positions, 'Flat · no open positions', (row, p) => {
        row.append(textNode('strong', p.symbol + ' · ' + p.quantity + ' shares'));
        row.append(textNode('p', 'Unrealized ' + formatMoney(p.unrealized_pnl), 'record-value'));
        row.append(textNode('p', 'Stop ' + formatMoney(p.stop) + ' · Target ' + formatMoney(p.target), 'muted'));
        if (longTerm) {
          const exit = textNode('button', 'Queue full paper exit', 'quiet');
          exit.type = 'button'; holdingExitButtons.push(exit);
          exit.addEventListener('click', () => confirmAction('exit', { symbol: p.symbol }));
          row.append(exit);
        }
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
    async function call(path, method, signal, body) {
      const response = await request(path, { method, signal, cache: 'no-store',
        credentials: 'omit', redirect: 'error', body: body ? JSON.stringify(body) : undefined,
        headers: { Authorization: 'Bearer ' + token, ...(body ? { 'Content-Type': 'application/json' } : {}) } });
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
    async function action(name, body) {
      if (!token || mutating || !latest) return;
      if (['arm', 'reset', 'review'].includes(name) && (!fresh || win.Date.now() - lastReceipt > 6000)) {
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
        await call(routes[name], 'POST', active.signal, body);
        if (actionVersion !== generation) return;
        outcome = name === 'exit' ? 'Paper exit queued. Inspect remaining holdings and subsequent fills.' : name === 'review' ? 'Paper review recorded; a fresh reviewed quote is still required.' : name === 'kill' || name === 'flatten' ? 'Kill active. Exits queued; inspect positions for remaining exposure.' : 'Paper action completed. Inspect current state.';
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
    function confirmAction(name, body) {
      if (!token || !latest || mutating) return;
      pendingAction = { name, body };
      el('confirm-title').textContent = name === 'review' ? 'Record ' + (body.no_corporate_action ? 'clear review' : 'persistent quarantine') + ' for ' + body.symbol + '?' : name === 'exit' ? 'Queue full paper exit for ' + body.symbol + '?' :
        name === 'arm' ? 'Arm paper automation?' : 'Reset the kill switch?';
      el('confirm-description').textContent = name === 'review' ?
        (body.no_corporate_action ? 'Confirm that your cited review covers all changes since the last accepted quote, including any applied action batch. This does not verify real custody or settlement.' : 'This blocks the symbol across sessions. Another review cannot remove it; a reviewed offline corporate-action batch is required. Stop the service and follow the corporate-actions usage guide.') : name === 'exit' ?
        'The entire remaining virtual holding will be queued for sale. This request persists across restarts; fresh reviewed quotes and liquidity are required for fills.' : name === 'arm' ?
        'This permits new virtual entries while all server-side readiness and risk checks pass. Protective exits remain active.' :
        'The server must verify a flat account and eligible risk state. This does not rearm automation.';
      el('confirm').showModal(); el('cancel-confirm').focus();
    }
    for (const name of controls) el(name).addEventListener('click', () => {
      if (['arm', 'reset'].includes(name)) confirmAction(name);
      else action(name);
    });
    el('holding-review').addEventListener('submit', event => {
      event.preventDefault();
      confirmAction('review', { symbol: el('review-symbol').value.trim(), session_date: el('review-date').value,
        no_corporate_action: el('review-clear').checked, reference: el('review-reference').value.trim() });
    });
    el('cancel-confirm').addEventListener('click', () => { pendingAction = null; el('confirm').close(); });
    el('confirm-action').addEventListener('click', () => {
      const pending = pendingAction; pendingAction = null; el('confirm').close();
      if (pending) action(pending.name, pending.body);
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
