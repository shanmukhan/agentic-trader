'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const money = require('../../src/trading_agent/api/static/money.js');

test('shared money display preserves exact signed decimal strings and Indian grouping', () => {
  const cases = [
    ['0', '₹0.00'], ['-0.00', '-₹0.00'], ['0.00000001', '₹0.00000001'],
    ['-12345678901234567890.123456789', '-₹1,23,45,67,89,01,23,45,67,890.123456789'],
    ['0001000.0500', '₹1,000.0500'], ['1e-2', '₹0.01'], ['2.5E+4', '₹25,000.00'],
    ['-1.234E-2', '-₹0.01234'], ['1e1001', '₹1e1001'], ['-1E-1001', '-₹1E-1001']
  ];
  for (const [value, expected] of cases) assert.equal(money(value), expected);
});

test('unavailable or malformed money stays unavailable instead of becoming a zero value', () => {
  for (const value of [null, undefined, 0, 1.2, NaN, Infinity, {}, [], '', ' ', 'NaN',
    'Infinity', '0x10', '1,000', '+2', '.5', '1.', '₹500', '<script>', '1e', '--1']) {
    assert.equal(money(value), '—');
  }
});

test('huge exponent and digit representations stay bounded and literal', () => {
  for (const value of ['1E+999999999999999999999999', '9'.repeat(1001), '-1E-9999999999999']) {
    assert.equal(money(value), value.startsWith('-') ? '-₹' + value.slice(1) : '₹' + value);
    assert.ok(money(value).length <= value.length + 1);
  }
});
