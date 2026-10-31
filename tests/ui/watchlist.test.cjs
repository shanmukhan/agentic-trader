'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {createWatchlist} = require('../../src/trading_agent/api/static/watchlist.js');
class Element {
  constructor(tag = 'div') {this.tagName = tag.toUpperCase(); this.children = []; this.events = {}; this.attributes = {}; this.style = {}; this.value = ''; this.checked = false; this.open = false;}
  set textContent(text) {this.text = String(text); this.children = [];}
  get textContent() {return (this.text || '') + this.children.map(n => n.textContent).join('');}
  append(...children) {this.children.push(...children);}
  replaceChildren(...children) {this.text = ''; this.children = children;}
  addEventListener(name, fn) {(this.events[name] ||= []).push(fn);}
  removeEventListener() {}
  setAttribute(name, value) {this.attributes[name] = value;}
  querySelectorAll(tag) {return this.children.flatMap(item => [...(item.tagName === tag.toUpperCase() ? [item] : []), ...item.querySelectorAll(tag)]);}
  fire(name = 'click') {if (!this.disabled) for (const fn of this.events[name] || []) fn({preventDefault() {}});}
  showModal() {this.open = true;}
  close() {this.open = false;}
}
const flush = () => new Promise(resolve => setImmediate(resolve));
const response = value => ({ok:true, status:200, json:async () => value});
const state = symbols => ({schema_version:1,observed_at:'2026-10-20T04:30:00+00:00',mode:'manual',catalog_count:2,catalog_imported_at:null,
  held_outside_watchlist:[],selected:symbols.map(symbol => ({symbol,feed_selected:false,held:false})),
  safety:{revision:2,symbols,paused:false,entries_today:0,max_order_cost:'6250.00',peak_equity:'25000.00',drawdown_pct:'0',valuation_fresh:true,data_blocked_today:false}});
function setup(handler) {
  const html = readFileSync('src/trading_agent/api/static/watchlist.html', 'utf8');
  const nodes = Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m => [m[1],new Element()]));
  const calls = [], events = {}, doc = {getElementById:id => nodes[id],createElement:tag => new Element(tag)};
  const win = {location:{origin:'http://127.0.0.1'},addEventListener:(n,fn) => {events[n] = fn;},setTimeout:()=>1,clearTimeout(){}};
  const api = createWatchlist(doc, win, async (path, options) => {calls.push({path,options}); return handler(path, options);});
  async function unlock() {nodes.token.value = 'invented-operator-token-1234567890123456'; nodes.access.fire('submit'); await flush();}
  return {nodes,calls,api,events,unlock};
}
test('NSE selection needs an acknowledged immutable confirmation and pauses with visible consequences', async () => {
  const s = setup(async (path, options) => {
    if (path.includes('/catalog?')) return response({schema_version:1,matches:1,items:[{symbol:'NSE:DEMO'}]});
    return response(state(options.method === 'POST' ? JSON.parse(options.body).symbols : []));
  });
  assert.equal(s.calls.length, 0); await s.unlock();
  s.nodes['search-form'].fire('submit'); await flush();
  s.nodes.results.querySelectorAll('button')[0].fire();
  assert.equal(s.api.canNavigate(), false);
  s.nodes.review.fire(); assert.equal(s.nodes.confirm.open, true);
  assert.match(s.nodes['confirm-text'].textContent, /Cancel every pending buy/);
  s.nodes['confirm-action'].fire(); assert.equal(s.calls.filter(c => c.options.method === 'POST').length, 0);
  s.nodes.ack.checked = true; s.nodes.ack.fire('change'); s.nodes['confirm-action'].fire(); await flush();
  const posts = s.calls.filter(c => c.options.method === 'POST'); assert.equal(posts.length, 1);
  assert.deepEqual(JSON.parse(posts[0].options.body), {revision:2,acknowledged:true,symbols:['NSE:DEMO']});
  assert.match(s.nodes.message.textContent, /Pending buys cancelled/); assert.equal(s.api.canNavigate(), true);
  assert.match(s.nodes.selected.textContent, /Not selected for market data/);
});
test('unknown save outcome requires refresh and never retries a mutation', async () => {
  let symbols = [];
  const s = setup(async (path, options) => {
    if (path.includes('/catalog?')) return response({schema_version:1,matches:1,items:[{symbol:'NSE:DEMO'}]});
    if (options.method === 'POST') {symbols = ['NSE:DEMO']; throw Error('lost response');}
    return response(state(symbols));
  });
  await s.unlock(); s.nodes['search-form'].fire('submit'); await flush(); s.nodes.results.querySelectorAll('button')[0].fire(); s.nodes.review.fire();
  s.nodes.ack.checked = true; s.nodes.ack.fire('change'); s.nodes['confirm-action'].fire(); await flush();
  assert.match(s.nodes.message.textContent, /outcome is unverified/); assert.equal(s.nodes.review.disabled, true);
  s.nodes.refresh.fire(); await flush(); assert.match(s.nodes.selected.textContent, /NSE:DEMO/);
  assert.equal(s.calls.filter(c => c.options.method === 'POST').length, 1);
});
test('lock clears private choices and ignores late reads', async () => {
  let finish; const s = setup(() => new Promise(resolve => {finish = resolve;}));
  await s.unlock(); s.api.lock(); finish(response(state(['NSE:PRIVATE']))); await flush();
  assert.equal(s.nodes.main.hidden, true); assert.equal(s.nodes.selected.textContent, ''); assert.equal(s.nodes['safety-values'].textContent, '');
  assert.equal(s.nodes.token.value, ''); assert.equal(s.nodes.state.textContent, 'Locked');
});
test('watchlist is an accessible workspace destination and preserves private frame handoff', () => {
  const html = readFileSync('src/trading_agent/api/static/watchlist.html', 'utf8');
  assert.match(html, /<label for="search">NSE symbol/); assert.match(html, /role="alert"/); assert.match(html, /aria-labelledby="confirm-title"/);
  assert.match(readFileSync('src/trading_agent/api/static/workspace.html','utf8'), /id="nav-watchlist" href="#watchlist"/);
  assert.match(readFileSync('src/trading_agent/api/static/workspace-bridge.js','utf8'), /'\/watchlist':'watchlist'/);
});
