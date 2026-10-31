'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/trading_agent/api/static/mobile-return.js', 'utf8');

test('broker callback query is removed without retaining, broadcasting or echoing secrets', () => {
  const calls = [];
  vm.runInNewContext(source, {window: {
    location: {search: '?request_token=PRIVATE-invented&setup_state=PRIVATE-nonce', pathname: '/agentic-trader/'},
    history: {replaceState: (...args) => calls.push(args)},
  }});
  assert.deepEqual(calls, [[null, '', '/agentic-trader/']]);
});

test('ordinary root visit does not rewrite browser history', () => {
  vm.runInNewContext(source, {window: {location: {search: '', pathname: '/agentic-trader/'},
    history: {replaceState: () => assert.fail('no callback query')}}});
});
