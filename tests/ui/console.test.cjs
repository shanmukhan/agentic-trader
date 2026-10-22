'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { createConsole, formatMoney } = require('../../src/trading_agent/api/static/dashboard.js');

class Element {
  constructor() { this.children = []; this.listeners = {}; this.value = ''; this.open = false; }
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return (this.text || '') + this.children.map(c => c.textContent).join(''); }
  set innerHTML(_) { throw Error('HTML injection sink used'); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.text = ''; this.children = nodes; }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  fire(name) { if (this.disabled) return; for (const callback of this.listeners[name] || []) callback({ preventDefault() {} }); }
  showModal() { this.open = true; }
  close() { this.open = false; }
  focus() { this.focused = true; }
}
function data(overrides = {}) {
  return { schema_version: 1, observed_at: '2026-10-20T04:30:00+00:00',
    account: { mode: 'paper', equity: '25000.00', available_cash: '25000.00', day_pnl: '0.00',
      reserved_cash: '0', fees: '0', kill: false, faulted: false, feed_connected: true,
      reserved_risk: '0', valuation_fresh: true, positions: [] },
    automation: { enabled: true, armed: false, readiness_reasons: [] },
    entry_readiness: { ready: false, reasons: ['AUTOMATION_DISARMED'] },
    orders: [], quotes: [], order_limit: 200, orders_truncated: false, ...overrides };
}
const ok = value => ({ ok: true, status: 200, json: async () => value });
const flush = () => new Promise(resolve => setImmediate(resolve));
function setup(fetcher = async () => ok(data())) {
  const nodes = Object.fromEntries([...readFileSync('src/trading_agent/api/static/index.html', 'utf8')
    .matchAll(/\bid="([^"]+)"/g)].map(match => [match[1], new Element()]));
  const events = {}, intervals = [], timeouts = new Map(), calls = [];
  let now = 1000, sequence = 0;
  const doc = { hidden: false, getElementById: id => { assert.ok(nodes[id], id); return nodes[id]; },
    createElement: () => new Element(), addEventListener: (name, cb) => { events[name] = cb; } };
  const win = { Date: { now: () => now }, setInterval: (cb, ms) => intervals.push({ cb, ms }),
    setTimeout: cb => { timeouts.set(++sequence, cb); return sequence; }, clearTimeout: id => timeouts.delete(id) };
  const instance = createConsole(doc, win, async (url, options) => { calls.push({ url, options }); return fetcher(url, options); });
  async function unlock(value = 'ephemeral-unit-test-operator-token') {
    nodes.token.value = value; nodes.unlock.fire('submit'); await flush();
  }
  return { nodes, doc, events, intervals, timeouts, calls, instance, unlock, advance: ms => { now += ms; } };
}

test('money retains all server decimal digits and groups Indian rupees without float rounding', () => {
  for (const [value, expected] of [['25000.00', '₹25,000.00'], ['10000000', '₹1,00,00,000.00'],
    ['-23.240000000000000001', '-₹23.240000000000000001'], ['0.1', '₹0.10'],
    ['123', '₹123.00'], ['1234.50', '₹1,234.50'], ['2.5E+4', '₹25,000.00'],
    ['0E-5', '₹0.00000'], ['-1.234E-2', '-₹0.01234'], ['1E+100000', '₹1E+100000']]) assert.equal(formatMoney(value), expected);
  for (const bad of [undefined, null, 25000, 'NaN', 'Infinity', '<img src=x>']) assert.equal(formatMoney(bad), '—');
});
test('observed quote rows explain daily review blocking instead of claiming a stale feed',async()=>{
 const s=setup(async()=>ok(data({quotes:[{symbol:'NSE:DEMO',fresh:false,detail:"Today's price-basis review is missing. Incoming quotes cannot be accepted."}]})));
 await s.unlock();assert.match(s.nodes.quotes.textContent,/price-basis review is missing/);
 assert.doesNotMatch(s.nodes.quotes.textContent,/Stale or missing/);
});

test('locked shell loads no private data; unlocking clears input, uses only bearer, and renders text safely', async () => {
  const view = data({ orders: [{ symbol: '<img src=x onerror=alert(1)>', id: 'id', side: 'BUY', state: 'REJECTED',
    reason: '<script>attack()</script>', filled: 0, quantity: 0 }] });
  const s = setup(async () => ok(view));
  assert.equal(s.calls.length, 0);
  assert.ok(s.nodes.arm.disabled && s.nodes.kill.disabled);
  await s.unlock();
  assert.equal(s.calls.length, 1);
  assert.equal(s.calls[0].url, '/api/console');
  assert.equal(s.calls[0].options.headers.Authorization, 'Bearer ephemeral-unit-test-operator-token');
  assert.equal(s.calls[0].options.credentials, 'omit');
  assert.equal(s.calls[0].options.redirect, 'error');
  assert.equal(s.nodes.token.value, '');
  assert.equal(s.nodes.equity.textContent, '₹25,000.00');
  assert.match(s.nodes.orders.textContent, /<script>attack\(\)<\/script>/);
  assert.ok(!s.nodes.arm.disabled);
});

test('locking clears all private data and discards a late poll response', async () => {
  let resolve;
  const s = setup(() => new Promise(done => { resolve = done; }));
  await s.unlock();
  s.nodes.lock.fire('click');
  resolve(ok(data())); await flush();
  assert.equal(s.nodes.equity.textContent, '—');
  assert.equal(s.nodes.orders.textContent, 'Locked');
  assert.equal(s.nodes.details.textContent, 'Locked');
  assert.ok(s.nodes.arm.disabled && s.nodes.kill.disabled);
  assert.equal(s.calls[0].options.signal.aborted, true);
});

test('stale data blocks arm/reset, keeps emergency controls, and never silently retries an action', async () => {
  let fail = false;
  const s = setup(async () => { if (fail) throw Error('network unavailable'); return ok(data()); });
  await s.unlock(); fail = true;
  await s.instance.refresh();
  assert.equal(s.nodes.feed.textContent, 'Display stale');
  assert.ok(s.nodes.arm.disabled && s.nodes.reset.disabled);
  assert.ok(!s.nodes.kill.disabled && !s.nodes.flatten.disabled);
  assert.equal(s.calls.filter(c => c.options.method === 'POST').length, 0);
});

test('six-second update age disables entry controls even while a slow request is pending', async () => {
  const s = setup(); await s.unlock();
  s.advance(6001);
  s.intervals.find(i => i.ms === 1000).cb();
  assert.ok(s.nodes.arm.disabled);
  assert.equal(s.nodes.feed.textContent, 'Display stale');
});

test('arming requires explicit confirmation; cancel and locking a dialog submit nothing', async () => {
  const s = setup(); await s.unlock();
  s.nodes.arm.fire('click');
  assert.ok(s.nodes.confirm.open && s.nodes['cancel-confirm'].focused);
  assert.equal(s.calls.length, 1);
  s.nodes['cancel-confirm'].fire('click');
  assert.ok(!s.nodes.confirm.open);
  s.nodes.arm.fire('click'); s.nodes.lock.fire('click'); s.nodes['confirm-action'].fire('click');
  await flush();
  assert.equal(s.calls.filter(c => c.options.method === 'POST').length, 0);
});

test('confirmation posts once then refreshes; an old poll cannot overwrite post-action data', async () => {
  let resolveOld;
  const s = setup(async (url, options) => {
    if (options.method === 'POST') return ok({ armed: true });
    if (s.calls.length === 2) return new Promise(done => { resolveOld = done; });
    return ok(data({ automation: { enabled: true, armed: s.calls.length > 2, readiness_reasons: [] } }));
  });
  await s.unlock();
  const old = s.instance.refresh(); await flush();
  s.nodes.arm.fire('click'); s.nodes['confirm-action'].fire('click');
  await flush();
  assert.equal(s.calls.filter(c => c.options.method === 'POST').length, 1);
  assert.equal(s.calls[2].url, '/api/paper/automation/arm');
  assert.equal(s.nodes.armed.textContent, 'Armed');
  resolveOld(ok(data())); await old;
  assert.equal(s.nodes.armed.textContent, 'Armed');
});

test('authorization failure locks and clears values; network errors preserve explicitly stale estimates', async () => {
  let unauthorized = false;
  const s = setup(async () => unauthorized ? { ok: false, status: 401 } : ok(data()));
  await s.unlock(); unauthorized = true;
  await s.instance.refresh();
  assert.equal(s.nodes.equity.textContent, '—');
  assert.equal(s.nodes.details.textContent, 'Locked');
  assert.match(s.nodes.message.textContent, /authorization failed/);
  assert.ok(s.nodes.kill.disabled);
});

test('hidden tabs pause polling and fetch fresh data when visible; overlapping polls are suppressed', async () => {
  const s = setup(); await s.unlock();
  s.doc.hidden = true;
  s.intervals.find(i => i.ms === 3000).cb(); await flush();
  assert.equal(s.calls.length, 1);
  s.doc.hidden = false; s.events.visibilitychange(); await flush();
  assert.equal(s.calls.length, 2);
  let resolve;
  const pending = setup(() => new Promise(done => { resolve = done; }));
  await pending.unlock(); await pending.instance.refresh();
  assert.equal(pending.calls.length, 1);
  resolve(ok(data())); await flush();
});

test('manual account disables automation and stale confirmation cannot arm', async () => {
  const manual = setup(async () => ok(data({ automation: { enabled: false, armed: false } })));
  await manual.unlock(); assert.ok(manual.nodes.arm.disabled && manual.nodes.disarm.disabled);
  const s = setup(); await s.unlock(); s.nodes.arm.fire('click'); s.advance(6001);
  s.nodes['confirm-action'].fire('click'); await flush();
  assert.equal(s.calls.filter(c => c.options.method === 'POST').length, 0);
  assert.equal(s.nodes.feed.textContent, 'Display stale');
});

test('kill is immediate and queued-exit messaging does not claim a completed fill', async () => {
  const s = setup(async (url, opts) => opts.method === 'POST' ? ok({ kill: true }) : ok(data()));
  await s.unlock();
  s.nodes.kill.fire('click'); await flush();
  assert.equal(s.calls.filter(c => c.options.method === 'POST').length, 1);
  assert.equal(s.calls[1].url, '/api/control/kill');
  assert.ok(!s.nodes.confirm.open);
  assert.match(s.nodes.message.textContent, /Exits queued; inspect positions/);
});

test('an aborted action has an unknown outcome and is never auto-retried', async () => {
  const s = setup(async (url, opts) => {
    if (opts.method !== 'POST') return ok(data());
    return new Promise((_, reject) => opts.signal.addEventListener('abort', () => {
      const error = Error('aborted'); error.name = 'AbortError'; reject(error);
    }));
  });
  await s.unlock(); s.nodes.flatten.fire('click'); await flush();
  for (const callback of s.timeouts.values()) callback();
  await flush();
  assert.equal(s.calls.filter(c => c.options.method === 'POST').length, 1);
  assert.match(s.nodes.message.textContent, /outcome unknown/);
});

test('reset asks for confirmation and server rejection remains visible after refresh', async () => {
  const view = data(); view.account.kill = true;
  const s = setup(async (url, opts) => opts.method === 'POST' ?
    { ok: false, status: 409, json: async () => ({ detail: 'account must be flat' }) } : ok(view));
  await s.unlock(); s.nodes.reset.fire('click');
  assert.ok(s.nodes.confirm.open);
  s.nodes['confirm-action'].fire('click'); await flush();
  assert.equal(s.calls[1].url, '/api/control/reset');
  assert.match(s.nodes.message.textContent, /account must be flat/);
});

function deliveryView() {
  const view = data();
  view.account.investment_horizon = 'long_term';
  view.account.delivery_fee_buffer = '76.70';
  view.account.long_term = { peak_equity: '25000', observed_drawdown: '30', drawdown_limit: '2500', quarantined_symbols: [] };
  return view;
}

test('long-term view labels the account, fills IST review date and clears private review values on lock', async () => {
  const s = setup(async () => ok(deliveryView())); await s.unlock();
  assert.equal(s.nodes.horizon.textContent, 'Long-term paper');
  assert.equal(s.nodes['long-term'].hidden, false);
  assert.equal(s.nodes['review-date'].value, '2026-10-20');
  assert.ok(!s.nodes['review-submit'].disabled);
  s.nodes['review-symbol'].value = 'NSE:DEMO'; s.nodes['review-reference'].value = 'private review note';
  s.nodes.lock.fire('click');
  assert.equal(s.nodes['long-term'].hidden, true);
  assert.equal(s.nodes['review-reference'].value, '');
  assert.equal(s.nodes['long-term-state'].textContent, '');
});

test('corporate-action review is confirmed with explicit quarantine warning and typed JSON body', async () => {
  const s = setup(async (url, options) => ok(options.method === 'POST' ? { paper_only: true } : deliveryView()));
  await s.unlock(); s.nodes['review-symbol'].value = 'NSE:DEMO';
  s.nodes['review-reference'].value = 'reviewed notice'; s.nodes['review-clear'].checked = false;
  s.nodes['holding-review'].fire('submit'); await flush();
  assert.equal(s.calls.length, 1);
  assert.match(s.nodes['confirm-title'].textContent, /persistent quarantine/);
  assert.match(s.nodes['confirm-description'].textContent, /reviewed offline corporate-action batch/);
  s.nodes['confirm-action'].fire('click'); await flush();
  assert.equal(s.calls[1].url, '/api/paper/long-term/reviews');
  assert.deepEqual(JSON.parse(s.calls[1].options.body), { symbol: 'NSE:DEMO', session_date: '2026-10-20', no_corporate_action: false, reference: 'reviewed notice' });
  assert.equal(s.calls[1].options.headers['Content-Type'], 'application/json');
});

test('long-term claims are disclosed separately from cash and cleared on lock', async () => {
  const view = deliveryView();
  Object.assign(view.account.long_term, { receivable: '126.00', unvalued_fractional_claims: 1, income_received: '50.40' });
  const s = setup(async () => ok(view)); await s.unlock();
  assert.equal(s.nodes['lt-receivable'].textContent, '₹126.00');
  assert.equal(s.nodes['lt-fractions'].textContent, '1');
  assert.equal(s.nodes['lt-income'].textContent, '₹50.40');
  assert.match(s.nodes['lt-guidance'].textContent, /portfolio value is incomplete/);
  s.nodes.lock.fire('click');
  assert.equal(s.nodes['long-term-state'].textContent, '');
  assert.equal(s.nodes['lt-receivable'].textContent, '');
  assert.equal(s.nodes['lt-guidance'].textContent, '');
});

test('long-term guidance explains quarantine resolution and the ordinary next step', async () => {
  const view = deliveryView(); view.account.long_term.quarantined_symbols = ['NSE:DEMO'];
  const s = setup(async () => ok(view)); await s.unlock();
  assert.match(s.nodes['lt-guidance'].textContent, /Stop the service/);
  assert.match(s.nodes['lt-guidance'].textContent, /cannot remove quarantine/);
  view.account.long_term.quarantined_symbols = []; await s.instance.refresh();
  assert.match(s.nodes['lt-guidance'].textContent, /review the current session/);
});

test('holding exit identifies the symbol and posts no client-supplied quantity only after confirmation', async () => {
  const view = deliveryView();
  view.account.positions = [{ symbol: 'NSE:DEMO', quantity: 14, unrealized_pnl: '0', stop: '490', target: '600' }];
  const s = setup(async (url, options) => ok(options.method === 'POST' ? { exit_queued: true } : view));
  await s.unlock();
  const exit = s.nodes.positions.children[0].children.find(node => node.textContent === 'Queue full paper exit');
  exit.fire('click'); assert.match(s.nodes['confirm-title'].textContent, /NSE:DEMO/);
  assert.equal(s.calls.length, 1);
  s.nodes['confirm-action'].fire('click'); await flush();
  assert.equal(s.calls[1].url, '/api/paper/long-term/exit');
  assert.deepEqual(JSON.parse(s.calls[1].options.body), { symbol: 'NSE:DEMO' });
  assert.match(s.nodes.message.textContent, /exit queued/);
});

test('intraday view hides delivery actions; stale delivery review is blocked at confirmation', async () => {
  const manual = setup(); await manual.unlock();
  assert.equal(manual.nodes['long-term'].hidden, true);
  assert.ok(manual.nodes['review-submit'].disabled);
  const s = setup(async () => ok(deliveryView())); await s.unlock();
  s.nodes['review-symbol'].value = 'NSE:DEMO'; s.nodes['review-reference'].value = 'reviewed note';
  s.nodes['review-clear'].checked = true; s.nodes['holding-review'].fire('submit');
  s.advance(6001); s.nodes['confirm-action'].fire('click'); await flush();
  assert.equal(s.calls.filter(c => c.options.method === 'POST').length, 0);
});
