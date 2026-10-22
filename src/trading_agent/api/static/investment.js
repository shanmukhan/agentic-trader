(function () {
  'use strict';
  const money = typeof module !== 'undefined' && module.exports ? require('./money.js') : window.AgenticMoney;
  const screens = {
    '/dashboard': ['dashboard', 'Dashboard', 'Your paper portfolio, market status and next safe action.'],
    '/discovery': ['discovery', 'Stock Discovery', 'Understand and compare the evidence in saved research.'],
    '/holdings': ['holdings', 'Portfolio', 'Held shares, exact accounting values and valuation coverage.'],
    '/backtesting': ['backtesting', 'Backtesting', 'Use the existing isolated historical research workflow.'],
    '/settings': ['settings', 'Settings', 'Inspect active paper configuration and find reviewed change workflows.'],
    '/learn': ['learn', 'Learning Center', 'Understand the terms, limits and decisions in your paper account.']
  };
  const lessons = [
    ['paper-only', 'Paper trading and real orders', 'This application records simulated orders, fills and fees against virtual cash. A connected Zerodha market-data feed supplies observations; it does not turn a paper order into a real broker order.', '/paper', 'Review paper operating modes'],
    ['quote-freshness', 'Connected feed, fresh quote and usable quote', 'Connected means the market-data socket is connected. A usable quote also needs a sufficiently recent exchange timestamp, valid bid/ask depth and the applicable price-basis review. A historical candle is not a fresh execution quote. Refreshing this screen only reads saved state.', '/setup#feed-connection', 'Troubleshoot the market-data feed'],
    ['price-basis', 'Daily price-basis review', 'Corporate actions and price-basis changes can make a historical reference incompatible with today’s prices. The reviewed daily setup must cover the applicable session. A restart does not approve it. Incoming observations can be blocked until the review is resolved and a new valid quote arrives.', '/strategies#strategy-setup', 'Review strategy data and today’s setup'],
    ['proposal-states', 'Proposal, approval, order and fill', 'A research candidate is not a proposal. An awaiting proposal still needs its mode-specific authorization and fresh risk checks before an order is created. Accepted orders reserve capacity; they do not prove shares were bought. Only fills change holdings. Cancelled proposals without an order did not buy or sell shares.', '/activity', 'Inspect recorded decisions and fills'],
    ['automatic-mode', 'Approval and Automatic modes', 'Approval requests an operator decision on eligible proposals. Automatic can authorize eligible proposals under the installed rules while the account is armed and ready. Neither mode buys every selected stock. Feed or risk pauses revoke authority; switching modes does not replay already-handled daily signals.', '/paper', 'Review mode, readiness and proposals'],
    ['cost-basis', 'Cost basis, liquidation value and P&L', 'Remaining cost basis allocates the actual purchase cost, including applicable entry costs, to held shares. Estimated net liquidation value uses the saved mark and configured exit-cost estimate. Net unrealized P&L is that net estimate less remaining basis. It is neither a completed sale nor a guaranteed sale price.', '/holdings', 'Inspect portfolio values'],
    ['fees', 'Fees, reservations and available cash', 'Charged fees are recorded when fills occur. A pending purchase can reserve cash before a fill. Available cash is the server-calculated amount remaining after its applicable reservations and buffers. Estimated exit fees already included in a net liquidation value must not be deducted a second time.', '/portfolio#purchase-orders-heading', 'Review purchases and cash reservations'],
    ['research-rank', 'Research rank and missing evidence', 'The current prior-daily screen ranks passing research candidates using its declared historical metrics. Gross historical return is before trading costs and is not an expected return. A rank is not a probability of profit. Missing history, share-class review or source evidence can prevent a candidate from passing.', '/discovery', 'Inspect saved screening evidence'],
    ['backtesting-bias', 'Backtest bias and incomplete evidence', 'A backtest simulates declared rules on historical observations. Future information, today’s surviving universe, parameter selection on the test period and omitted costs can distort results. Keep source dates, corporate actions, failed orders and chronological holdouts explicit. A simulated result does not certify real-market profitability.', '/backtesting', 'Open the existing backtest workflow'],
    ['risk-controls', 'Stops, emergency controls and liquidity', 'A stop is a rule that can request an exit; it is not a guaranteed fill price. Exit fills still need fresh usable quotes and liquidity. A kill switch blocks new entries and queues the configured protective actions. Disconnection does not sell holdings, and resetting a kill switch does not automatically rearm the account.', '/console', 'Open Risk Management'],
    ['scope-and-returns', 'Account value, income and performance coverage', 'A dated daily accounting change is not an account lifetime return. Cash contributions, purchases, income, fees, corporate-action claims and unknown marks need separate treatment. Unavailable benchmark, allocation and return calculations are shown as unavailable rather than zero.', '/holdings', 'Review valuation scope and limitations']
  ];

  // Exact decimal ordering for server strings. Monetary values never pass through Number.
  function compareDecimal(left, right) {
    const parse = value => {
      const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(String(value ?? ''));
      return match ? {negative: match[1] === '-', whole: match[2].replace(/^0+(?=\d)/, ''), fraction: match[3] || ''} : null;
    };
    const a = parse(left), b = parse(right);
    if (!a || !b) return a ? -1 : b ? 1 : 0;
    const zero = v => /^0+$/.test(v.whole + v.fraction);
    if (zero(a)) a.negative = false;
    if (zero(b)) b.negative = false;
    if (a.negative !== b.negative) return a.negative ? -1 : 1;
    const length = Math.max(a.fraction.length, b.fraction.length);
    const whole = a.whole.length - b.whole.length || (a.whole < b.whole ? -1 : a.whole > b.whole ? 1 : 0);
    const af = a.fraction.padEnd(length, '0'), bf = b.fraction.padEnd(length, '0');
    const result = whole || (af < bf ? -1 : af > bf ? 1 : 0);
    return a.negative ? -result : result;
  }

  function createInvestment(doc, win, fetcher) {
    const el = id => doc.getElementById(id);
    const node = (tag, text) => {const n = doc.createElement(tag); if (text !== undefined) n.textContent = String(text); return n;};
    const path = win.location?.pathname || '/dashboard';
    const [screen, title, description] = screens[path] || screens['/dashboard'];
    const dynamic = ['dashboard-metrics', 'market-status', 'dashboard-candidates', 'recent-decisions', 'research-rows', 'research-limitations', 'comparison-table', 'portfolio-metrics', 'portfolio-scope', 'holding-rows', 'portfolio-limitations', 'backtest-commands', 'backtest-limitations', 'settings-summary', 'settings-limits', 'settings-limitations', 'lessons', 'allocation-rows'];
    const privateText = ['observed', 'next-title', 'next-detail', 'dashboard-valuation', 'dashboard-research-context', 'performance-coverage', 'research-context', 'research-source', 'research-count', 'fundamental-state', 'valuation-state', 'portfolio-provenance', 'day-baseline', 'holdings-status', 'portfolio-performance', 'backtest-state', 'lesson-count', 'checklist-status', 'allocation-status', 'allocation-basis', 'allocation-exclusions', 'allocation-commitments'];
    let token = '', generation = 0, active = null, busy = false, latest = null, lastReceipt = 0;
    const selected = new Set();
    const clock = () => win.Date ? win.Date.now() : Date.now();
    const date = value => {
      if (!value) return 'Not recorded';
      const time = new Date(value); if (!Number.isFinite(time.getTime())) return 'Not recorded';
      return time.toLocaleString('en-IN', {timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false}) + ' IST';
    };
    const friendly = value => String(value ?? 'not recorded').toLowerCase().replaceAll('_', ' ');
    const percentage = value => value === undefined || value === null ? 'Unavailable' : String(value) + '%';
    const amount = value => typeof value === 'string' ? money(value) : 'Unavailable';
    const textList = (id, values) => {el(id).replaceChildren(); for (const value of values || []) el(id).append(node('li', value));};
    const definition = (container, label, value) => {const pair = node('div'); pair.append(node('dt', label), node('dd', value)); container.append(pair);};
    const link = (label, href) => {const a = node('a', label); a.setAttribute('href', href); return a;};
    function controls() {
      for (const id of ['refresh', 'research-search', 'research-status', 'research-sort', 'clear-comparison', 'lesson-search']) el(id).disabled = !token || busy;
      el('unlock').disabled = busy;
    }
    function lock() {
      if (win.AgenticNavigation) win.AgenticNavigation.locked();
      generation++; active?.abort(); active = null; token = ''; busy = false; latest = null; lastReceipt = 0; selected.clear();
      el('token').value = ''; el('token').required = true; el('lock').disabled = true; el('main').hidden = true;
      for (const id of dynamic) el(id).replaceChildren();
      for (const id of privateText) el(id).textContent = '';
      el('research-search').value = ''; el('research-status').value = 'all'; el('research-sort').value = 'rank'; el('lesson-search').value = '';
      el('comparison-status').textContent = 'Select two to four stocks above. Comparisons use this saved calculation and price basis only.';
      el('next-link').setAttribute('href', '/paper'); el('next-link').textContent = 'Review Paper Trading →';
      el('state').textContent = 'Locked'; el('message').className = ''; el('message').textContent = 'Locked. No private account or research data loaded.'; controls();
    }
    function metric(container, label, value, detail) {
      const card = node('article'); card.className = 'panel metric';
      const figure = node('p', amount(value)); figure.className = 'desk-value';
      const explanation = node('p', detail); explanation.className = 'muted';
      card.append(node('h2', label), figure, explanation); container.append(card);
    }
    function portfolioMetrics(container, p) {
      metric(container, 'Estimated net portfolio value', p.equity, 'Saved cash, net held-share estimates and recorded valued receivables. Coverage is shown below.');
      metric(container, 'Available virtual cash', p.available_cash, 'Server-calculated cash after applicable reservations and buffers.');
      metric(container, 'Remaining holding cost basis', p.remaining_cost_basis, 'Allocated actual purchase cost of currently held shares.');
      metric(container, 'Net unrealized P&L', p.net_unrealized_pnl, 'Estimated net sale proceeds less remaining holding basis; not a completed sale.');
    }
    function renderDashboard(data) {
      const p = data.portfolio, s = data.settings, d = data.discovery;
      const metrics = el('dashboard-metrics'); metrics.replaceChildren(); portfolioMetrics(metrics, p);
      el('dashboard-valuation').textContent = 'Valuation: ' + friendly(p.valuation_state) + ' at last refresh. ' + (p.valuation_detail || 'Inspect Portfolio for valuation scope and quote coverage.');
      let action = ['Review paper readiness', 'Inspect current proposals and the independent readiness checks before choosing an operating mode.', '/paper', 'Open Paper Trading →'];
      if (p.faulted || p.kill) action = ['Resolve the account pause', p.kill ? 'The kill switch is active. Review its recorded reason and the consequences before taking a recovery action.' : 'The account reports a fault. Review Risk Management and server diagnostics before resuming.', '/console', 'Open Risk Management →'];
      else if (!s.feed_connected) action = ['Connect and verify market data', 'The read-only feed is disconnected. Review the broker session and connection confirmation; a connection alone does not establish usable quotes.', '/setup#feed-connection', 'Review Broker & Data →'];
      else if (d.state !== 'available') action = ['Prepare reviewed strategy data', 'Saved research is unavailable. Complete the existing preparation and explicit review workflow before relying on research ranks.', '/strategies#strategy-setup', 'Open Strategies →'];
      else if (p.valuation_state === 'stale' || p.valuation_state === 'incomplete') action = ['Inspect valuation coverage', p.valuation_detail || 'Some portfolio estimates have stale or incomplete evidence. Review their scope before interpreting the total.', '/holdings', 'Inspect Portfolio →'];
      el('next-title').textContent = action[0]; el('next-detail').textContent = action[1]; el('next-link').setAttribute('href', action[2]); el('next-link').textContent = action[3];
      el('market-status').replaceChildren();
      for (const [label, value] of [['Read-only data feed', s.feed_connected ? 'Connected at last refresh' : 'Disconnected at last refresh'], ['Reviewed exchange session', s.session_open ? 'Open at last refresh' : 'Closed or unreviewed at last refresh'], ['Operating mode', friendly(s.decision_mode)], ['Paper automation', s.automation_armed ? 'Armed at last refresh' : 'Disarmed at last refresh'], ['Portfolio valuation', friendly(p.valuation_state) + ' at last refresh']]) definition(el('market-status'), label, value);
      el('dashboard-research-context').textContent = d.as_of ? 'Saved calculation ' + date(d.as_of) + '. Candidates still require an independent signal, current basis and risk checks.' : 'No saved research calculation is available.';
      el('dashboard-candidates').replaceChildren();
      const candidates = (d.rows || []).filter(row => row.status === 'research_candidate').sort((a, b) => compareDecimal(a.rank, b.rank)).slice(0, 5);
      for (const row of candidates) el('dashboard-candidates').append(node('li', row.symbol + ' · rank ' + (row.rank ?? 'not recorded') + ' · gross historical return ' + percentage(row.gross_total_return_pct)));
      if (!candidates.length) el('dashboard-candidates').append(node('li', 'No passing research candidates are present in this saved calculation.'));
      el('recent-decisions').replaceChildren();
      for (const decision of data.dashboard?.recent_decisions || []) {
        const item = node('article'); item.append(node('h3', decision.side + ' ' + decision.symbol + ' · ' + friendly(decision.state)), node('p', (decision.order_id ? 'Linked order: ' + decision.order_id : 'No linked order recorded') + ' · Updated ' + date(decision.updated_at)), node('p', 'Outcome: ' + friendly(decision.outcome))); el('recent-decisions').append(item);
      }
      if (!(data.dashboard?.recent_decisions || []).length) el('recent-decisions').append(node('p', 'No saved proposals are available in this bounded history view.'));
      el('performance-coverage').textContent = performanceDetail(p);
    }
    function researchRows() {
      if (!latest) return;
      const d = latest.discovery, query = el('research-search').value.trim().toUpperCase(), status = el('research-status').value, sort = el('research-sort').value;
      const rows = (d.rows || []).filter(row => row.symbol.toUpperCase().includes(query) && (status === 'all' || row.status === status));
      const keys = {rank: 'rank', momentum: 'gross_total_return_pct', volatility: 'daily_volatility_pct', turnover: 'average_turnover'};
      rows.sort((a, b) => {
        if (sort === 'symbol') return a.symbol.localeCompare(b.symbol);
        const key = keys[sort] || 'rank', av = a[key], bv = b[key];
        if (av === undefined || av === null) return bv === undefined || bv === null ? a.symbol.localeCompare(b.symbol) : 1;
        if (bv === undefined || bv === null) return -1;
        return compareDecimal(av, bv) * (sort === 'momentum' || sort === 'turnover' ? -1 : 1) || a.symbol.localeCompare(b.symbol);
      });
      el('research-rows').replaceChildren();
      for (const row of rows) {
        const tr = node('tr'), select = node('td'), checkbox = node('input'); checkbox.type = 'checkbox'; checkbox.checked = selected.has(row.symbol); checkbox.setAttribute('aria-label', 'Compare ' + row.symbol); checkbox.disabled = row.status === 'needs_data';
        checkbox.addEventListener('change', () => {
          if (!token || busy) return;
          if (checkbox.checked && selected.size >= 4) {checkbox.checked = false; el('comparison-status').textContent = 'Compare at most four stocks. Clear a selection before adding another.'; return;}
          if (checkbox.checked) selected.add(row.symbol); else selected.delete(row.symbol);
          renderComparison();
        });
        select.append(checkbox); tr.append(select);
        const evidence = node('td'); evidence.append(node('strong', row.symbol)); const details = node('details'); details.className = 'invest-evidence'; details.append(node('summary', 'Why this result?'));
        details.append(node('p', row.reasons?.length ? 'Checks: ' + row.reasons.map(friendly).join('; ') + '.' : row.status === 'research_candidate' ? 'Passed the configured prior-daily momentum, trend, turnover and volatility checks.' : 'The saved result does not include passing evidence.'));
        details.append(node('p', 'Completed observations: ' + (row.observations ?? 'not recorded') + '. Last completed session: ' + (row.last_session || 'not recorded') + '. Raw close: ' + amount(row.last_close) + '. Available at: ' + date(row.available_at) + '.'));
        details.append(node('p', 'Trend index: ' + (row.index_level ?? 'unavailable') + '; trend index average: ' + (row.trend_index_average ?? 'unavailable') + '. ' + (row.subscribed ? 'In the saved live-feed subscription list.' : 'Not in the saved live-feed subscription list.') + ' Fundamentals, drawdown and future returns are not supplied by this screen.'));
        if (row.evidence?.length) {
          const list = node('ul');
          for (const item of row.evidence) list.append(node('li', friendly(item.metric) + ': ' + friendly(item.state) + '. Observed ' + (item.observed ?? 'unavailable') + '; rule ' + item.rule + '; threshold ' + (item.threshold ?? 'unavailable') + '. ' + (item.detail || '')));
          details.append(list);
        }
        details.append(link('Open Stock Analysis →', '/analysis')); evidence.append(details); tr.append(evidence);
        for (const value of [row.rank ?? '—', friendly(row.status), percentage(row.gross_total_return_pct), percentage(row.daily_volatility_pct), amount(row.average_turnover)]) tr.append(node('td', value));
        el('research-rows').append(tr);
      }
      if (!rows.length) {const tr = node('tr'), td = node('td', d.rows?.length ? 'No saved stocks match these filters. Clear the search or change the result filter.' : 'No saved research rows are available. Prepare and explicitly review data in Strategies.'); td.setAttribute('colspan', '7'); tr.append(td); el('research-rows').append(tr);}
      el('research-count').textContent = rows.length + ' of ' + (d.rows || []).length + ' returned stocks shown' + (d.truncated ? ' · response is bounded to ' + d.row_limit + ' rows' : '') + '. Comparison selections: ' + selected.size + '.';
    }
    function renderComparison() {
      el('comparison-table').replaceChildren();
      const rows = (latest?.discovery.rows || []).filter(row => selected.has(row.symbol));
      if (rows.length < 2) {el('comparison-status').textContent = rows.length + ' selected. Select two to four stocks from the saved calculation.'; return;}
      if (rows.some(row => !row.last_session) || new Set(rows.map(row => row.last_session)).size !== 1) {el('comparison-status').textContent = 'Comparison unavailable: selected stocks do not have the same recorded completed session. Choose stocks with matching coverage.'; return;}
      el('comparison-status').textContent = rows.length + ' stocks · calculation ' + date(latest.discovery.as_of) + ' · completed session ' + rows[0].last_session + '. Same saved screen and price basis; no live subscription changes.';
      const table = node('table'), caption = node('caption', 'Exact saved research metrics for selected stocks'), head = node('thead'), heading = node('tr'); heading.append(node('th', 'Metric')); for (const row of rows) heading.append(node('th', row.symbol)); head.append(heading); table.append(caption, head);
      const body = node('tbody');
      for (const [label, value] of [['Result', row => friendly(row.status)], ['Rank', row => row.rank ?? 'Unavailable'], ['Gross historical return', row => percentage(row.gross_total_return_pct)], ['Daily volatility', row => percentage(row.daily_volatility_pct)], ['Average turnover (INR/day)', row => amount(row.average_turnover)], ['Last raw close', row => amount(row.last_close)], ['Completed observations', row => row.observations ?? 'Unavailable'], ['Missing or failed checks', row => row.reasons?.map(friendly).join('; ') || 'None recorded by the screen'], ['Fundamentals', () => 'Unavailable']]) {const tr = node('tr'), th = node('th', label); th.setAttribute('scope', 'row'); tr.append(th); for (const row of rows) tr.append(node('td', value(row))); body.append(tr);}
      table.append(body); el('comparison-table').append(table);
    }
    function renderDiscovery(data) {
      const d = data.discovery;
      el('research-context').textContent = d.state === 'available' ? 'Saved calculation ' + date(d.as_of) + '. Latest reviewed completed session: ' + (d.latest_reviewed_completed_session || 'not recorded') + '.' : 'No saved reviewed research is available. Prepare source data in Strategies; opening this screen starts no download.';
      el('research-source').textContent = (d.source?.synthetic === true ? 'SIMULATED SOURCE · ' : '') + (d.source?.description || 'Source provenance is not recorded.') + ' Universe: ' + friendly(d.source?.universe_kind) + '. ' + (d.source?.synthetic === null ? 'Broker/replay provenance is not certified.' : '');
      textList('research-limitations', [...(d.limitations || []), ...(d.ranking ? [d.ranking.detail, d.ranking.tie_rule] : [])]); el('fundamental-state').textContent = data.capabilities?.fundamentals?.detail || 'Fundamental data is unavailable. No fundamental filters or invented scores are applied.';
      selected.clear(); researchRows(); renderComparison();
    }
    function performanceDetail(p) {
      return p.performance?.detail || 'Account returns, benchmark comparison and received-income performance are unavailable in this view. Existing paper ledger amounts are not a validated performance series. Missing metrics are not zero.';
    }
    function renderPortfolio(data) {
      const p = data.portfolio; el('portfolio-metrics').replaceChildren(); portfolioMetrics(el('portfolio-metrics'), p);
      metric(el('portfolio-metrics'), 'Realized capital P&L', p.realized_pnl, 'Recorded realized result; distinct from current unrealized estimates.');
      metric(el('portfolio-metrics'), 'Charged fees', p.fees, 'Fees already recorded on actual paper fills.');
      metric(el('portfolio-metrics'), 'Reserved purchase cash', p.reserved_cash, 'Pending buy reservations, not completed purchases.');
      metric(el('portfolio-metrics'), 'Dated daily accounting change', p.day_pnl, 'Baseline day: ' + (p.day || 'not recorded') + '. Not a lifetime investment return.');
      el('valuation-state').textContent = friendly(p.valuation_state) + ' at last refresh. ' + (p.valuation_detail || 'Inspect saved quote and price-basis coverage before interpreting estimates.');
      el('portfolio-provenance').textContent = (p.provenance?.synthetic === true ? 'SIMULATED SOURCE · ' : '') + (p.provenance?.detail || 'Paper ledger; quote provenance is not certified.');
      el('day-baseline').textContent = 'Accounting baseline day: ' + (p.day || 'not recorded') + ' · ' + (p.accounting_day_current ? 'matches the current IST date at refresh.' : 'does not match the current IST date; this read does not roll the accounting day.');
      el('portfolio-scope').replaceChildren();
      for (const [label, value] of [['Ledger cash', amount(p.cash)], ['Accounting-day equity baseline', amount(p.day_equity)], ['Delivery fee buffer', amount(p.delivery_fee_buffer)], ['Recorded valued receivables', amount(p.long_term?.receivable)], ['Unvalued fractional claims', p.long_term?.unvalued_fractional_claims === undefined ? 'Not applicable or not recorded' : String(p.long_term.unvalued_fractional_claims) + ' · excluded from the value estimate'], ['Recorded income received', amount(p.long_term?.income_received)]]) definition(el('portfolio-scope'), label, value);
      el('holding-rows').replaceChildren();
      for (const position of p.positions || []) {
        const tr = node('tr');
        for (const value of [position.symbol, String(position.quantity), amount(position.cost), amount(position.liquidation_value), amount(position.unrealized_pnl), amount(position.stop) + ' / ' + amount(position.target), position.quote ? friendly(position.quote.status) + ' at last refresh. ' + (position.quote.detail || '') + ' Exchange: ' + date(position.quote.exchange_time) : 'No certified quote coverage recorded.']) tr.append(node('td', value));
        el('holding-rows').append(tr);
      }
      el('holdings-status').textContent = p.positions?.length ? p.positions.length + ' of ' + (p.position_count ?? p.positions.length) + ' held stocks shown' + (p.positions_truncated ? ' · response bounded to ' + p.position_limit : '') + '. Estimates do not imply an executable exit or guaranteed liquidity.' : 'No held shares are recorded. An unfilled order or cancelled proposal is not a holding.';
      const allocation = p.allocation;
      el('allocation-rows').replaceChildren();
      el('allocation-status').textContent = allocation?.state === 'available' ? 'Weights available at last refresh · base ' + amount(allocation.allocation_base) : 'Current weights unavailable. ' + (allocation?.reason_codes?.map(friendly).join('; ') || 'Accepted held-price coverage is not recorded.');
      el('allocation-basis').textContent = allocation?.basis || 'Weights require actual cash and current accepted bid marks for every held share.';
      if (allocation?.state === 'available') {
        for (const row of [{symbol: 'Cash', gross_value: allocation.cash_balance, weight_pct: allocation.cash_weight_pct}, ...(allocation.positions || [])]) {
          const tr = node('tr'); for (const text of [row.symbol, amount(row.gross_value), row.weight_pct === null || row.weight_pct === undefined ? 'Unavailable' : String(row.weight_pct) + '%']) tr.append(node('td', text)); el('allocation-rows').append(tr);
        }
      }
      el('allocation-exclusions').textContent = allocation ? 'Excluded from every weight: valued dividend receivables ' + amount(allocation.excluded_claims?.dividend_receivable) + '; unvalued fractional claims ' + (allocation.excluded_claims?.unvalued_fractional_claims ?? 'not recorded') + '. This is cash and held-share allocation, not complete liquidation equity.' : '';
      const commitments = allocation?.commitments;
      el('allocation-commitments').textContent = commitments ? 'Separate commitments: reserved cash ' + amount(commitments.reserved_cash) + '; delivery fee buffer ' + amount(commitments.delivery_fee_buffer) + '; pending orders ' + (commitments.pending_order_count ?? 'not recorded') + '. These amounts stay within ledger cash; reservations are not owned shares or extra deductions from allocation value.' : '';
      el('portfolio-performance').textContent = performanceDetail(p); textList('portfolio-limitations', p.limitations);
    }
    function renderBacktesting(data) {
      const b = data.backtests; el('backtest-state').textContent = data.capabilities?.backtests?.detail || 'The browser job runner and graphical result explorer are not implemented. Existing CLI backtesting remains available.';
      el('backtest-commands').replaceChildren();
      for (const item of b.commands || []) {const article = node('article'), pre = node('pre'); pre.append(node('code', item.command)); article.append(node('h3', item.label), pre, node('p', item.detail)); el('backtest-commands').append(article);}
      textList('backtest-limitations', b.limitations);
    }
    function renderSettings(data) {
      const s = data.settings; el('settings-summary').replaceChildren();
      for (const [label, value] of [['Account environment', friendly(s.mode)], ['Investment horizon', friendly(s.investment_horizon)], ['Decision mode', friendly(s.decision_mode)], ['Mode reason', friendly(s.mode_reason)], ['Market-data connection', s.feed_connected ? 'Connected at last refresh' : 'Disconnected at last refresh'], ['Automation configured', s.automation_configured ? 'Yes' : 'No'], ['Automation armed', s.automation_armed ? 'Yes at last refresh' : 'No at last refresh'], ['Current local date', s.local_day || 'Not recorded'], ['Entry window (IST)', (s.entry_start || 'Not recorded') + ' to ' + (s.entry_end || 'Not recorded')], ['Configured flatten time (IST)', s.flatten_at || 'Not recorded'], ['Strategy configuration', s.strategy?.configured ? friendly(s.strategy.mode) + (s.strategy.holding_sessions ? ' · ' + s.strategy.holding_sessions + ' holding sessions' : '') : 'No strategy configured']]) definition(el('settings-summary'), label, value);
      el('settings-limits').replaceChildren();
      const monetary = new Set(['starting_cash', 'max_position_notional', 'max_total_notional', 'max_trade_risk', 'daily_loss_limit', 'long_term_drawdown_limit']);
      const units = {max_quote_age_seconds: ' seconds', max_spread_bps: ' basis points', slippage_bps: ' basis points', latency_ms: ' milliseconds', order_ttl_seconds: ' seconds'};
      for (const [key, value] of Object.entries(s.limits || {})) definition(el('settings-limits'), friendly(key), monetary.has(key) ? amount(value) : (typeof value === 'boolean' ? value ? 'Yes' : 'No' : String(value ?? 'Not recorded')) + (units[key] || ''));
      textList('settings-limitations', s.limitations);
    }
    function renderLessons() {
      const query = el('lesson-search').value.trim().toLowerCase(), matches = lessons.filter(item => item.join(' ').toLowerCase().includes(query)); el('lessons').replaceChildren();
      for (const [id, heading, text, href, action] of matches) {const article = node('article'); article.id = id; article.className = 'panel'; article.append(node('h2', heading), node('p', text), link(action + ' →', href)); el('lessons').append(article);}
      el('lesson-count').textContent = matches.length ? matches.length + ' concepts shown.' : 'No concepts match. Try quote, cost, approval or risk.';
      if (win.AgenticNavigation?.updated) win.AgenticNavigation.updated();
    }
    function render(data) {
      if (data.schema_version !== 1 || !data.portfolio || !data.discovery || !data.settings || !data.backtests || !Array.isArray(data.discovery.rows) || !Array.isArray(data.portfolio.positions)) throw Error('schema');
      latest = data; lastReceipt = clock();
      for (const name of ['dashboard', 'discovery', 'holdings', 'backtesting', 'settings', 'learn']) el(name + '-view').hidden = name !== screen;
      ({dashboard: renderDashboard, discovery: renderDiscovery, holdings: renderPortfolio, backtesting: renderBacktesting, settings: renderSettings, learn: renderLessons}[screen])(data);
      if (screen === 'learn') el('checklist-status').textContent = 'At last refresh: feed ' + (data.settings.feed_connected ? 'connected' : 'disconnected') + '; saved research ' + friendly(data.discovery.state) + '; decision mode ' + friendly(data.settings.decision_mode) + '. Readiness remains a separate check in Paper Trading.';
      el('main').hidden = false; el('state').textContent = 'Saved status · paper only'; el('observed').textContent = 'Observed ' + date(data.observed_at) + '. Values and readiness are a saved snapshot; refresh to check current state.';
      el('message').className = ''; el('message').textContent = 'Saved data loaded. This screen only reads state; it does not download, subscribe, approve or submit orders.';
      if (win.AgenticNavigation?.updated) win.AgenticNavigation.updated();
    }
    async function refresh() {
      if (!token || busy) return;
      const version = ++generation; active?.abort(); const controller = new AbortController(); active = controller; busy = true; controls(); el('message').textContent = 'Reading saved state…';
      const timeout = win.setTimeout(() => controller.abort(), 10000);
      try {
        const response = await fetcher('/api/workspace/views', {method: 'GET', signal: controller.signal, cache: 'no-store', credentials: 'omit', redirect: 'error', headers: {Authorization: 'Bearer ' + token}});
        if (version !== generation) return;
        if (response.status === 401 || response.status === 403) {lock(); el('message').className = 'error'; el('message').textContent = 'Operator authorization failed. Unlock with the local operator token.'; return;}
        if (!response.ok) throw Error('request');
        const data = await response.json(); if (version === generation) render(data);
      } catch (error) {
        if (version !== generation) return;
        el('state').textContent = 'Display stale · refresh required'; el('message').className = 'error'; el('message').textContent = error.name === 'AbortError' ? 'Reading saved state timed out. Refresh to retry; no account changes were requested.' : 'Saved state could not be loaded. Check that the server is running the current version, then refresh. No account changes were requested.';
      } finally {win.clearTimeout(timeout); if (version === generation) {busy = false; active = null; controls();}}
    }
    el('screen-title').textContent = title; el('screen-description').textContent = description; doc.title = title + ' · Paper only';
    el('access').addEventListener('submit', event => {event.preventDefault(); const supplied = el('token').value; if (supplied) {lock(); token = supplied; el('token').required = false; el('lock').disabled = false;} refresh();});
    el('lock').addEventListener('click', lock); el('refresh').addEventListener('click', refresh);
    el('research-search').addEventListener('input', researchRows); el('research-status').addEventListener('change', researchRows); el('research-sort').addEventListener('change', researchRows);
    el('clear-comparison').addEventListener('click', () => {selected.clear(); researchRows(); renderComparison();});
    el('lesson-search').addEventListener('input', () => {if (token && !busy) renderLessons();});
    if (win.setInterval) win.setInterval(() => {if (token && latest && clock() - lastReceipt > 6000) {el('state').textContent = 'Display stale · refresh required'; el('observed').textContent = 'Snapshot observed ' + date(latest.observed_at) + ' is stale. Refresh to check current quote, valuation and operating state.';}}, 1000);
    win.addEventListener?.('pagehide', lock);
    lock(); return {refresh, lock, canNavigate: () => !busy};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {createInvestment, compareDecimal};
  if (typeof document !== 'undefined') {const view = createInvestment(document, window, window.fetch.bind(window)); if (window.AgenticNavigation) window.AgenticNavigation.connect(view, 'access');}
})();
