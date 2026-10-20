/* Exact decimal-string INR display, shared by operator pages. */
(function(){
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

if(typeof module !== 'undefined' && module.exports) module.exports = formatMoney;
else window.AgenticMoney = formatMoney;
})();
