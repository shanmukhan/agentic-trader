(function () {
  'use strict';
  const money = typeof module !== 'undefined' && module.exports ? require('./money.js') : window.AgenticMoney;
  const createDialogs = typeof module !== 'undefined' && module.exports ? require('./dialogs.js').createDialogs : window.AgenticDialogs;
  const alive = new Set(['queued', 'running']);
  const monetary = new Set(['equity', 'cash', 'starting_cash', 'available_cash', 'initial_cash', 'ending_equity', 'net_pnl', 'net_profit', 'realized_pnl', 'fees', 'price', 'drawdown', 'max_drawdown', 'known_receivable', 'remaining_cost_basis', 'liquidation_value', 'unrealized_pnl', 'net_unrealized_pnl', 'reserved_cash', 'max_trade_risk', 'max_position_notional', 'max_total_notional', 'daily_loss_limit', 'long_term_drawdown_limit', 'net_equity_change', 'expectancy_per_completed_trade', 'net_observed_pnl', 'observed_drawdown', 'income_received']);
  const friendly = value => String(value ?? 'Unavailable').replaceAll('_', ' ');
  const exact = value => value === null || value === undefined ? 'Unavailable' : typeof value === 'object' ? JSON.stringify(value) : String(value);
  function createBacktesting(doc, win, fetcher) {
    const el = id => doc.getElementById(id);
    const node = (tag, value) => {const result = doc.createElement(tag); if (value !== undefined) result.textContent = String(value); return result;};
    const dialogs = createDialogs(doc, win), reports = new Map();
    let token = '', generation = 0, active = null, busy = false, pending = null, timer = null, delay = 15000;
    let jobButtons = [];
    let resources = [], jobs = [], jobLimits = {}, globalLimitations = [], capability = {available: false}, selectedResource = null, uncertain = null, reconciled = false;
    const dynamic = ['runner-limits', 'resource-summary', 'resource-limitations', 'jobs', 'report-summary', 'report-provenance', 'report-limitations', 'report-equity', 'report-drawdown', 'report-orders', 'report-fills', 'comparison', 'confirm-summary'];
    const privateText = ['resource-state', 'jobs-state', 'submission-state', 'report-state', 'report-metrics', 'comparison-state', 'confirm-text'];
    function definition(container, label, value) {const pair = node('div'); pair.append(node('dt', friendly(label)), node('dd', value)); container.append(pair);}
    function value(key, item) {return monetary.has(key) ? typeof item === 'string' ? money(item) : 'Unavailable (exact decimal not recorded)' : exact(item);}
    function definitions(id, object) {const container = el(id); container.replaceChildren(); for (const [key, item] of Object.entries(object || {})) definition(container, key, value(key, item));}
    function list(id, items) {el(id).replaceChildren(); for (const item of new Set(items || [])) el(id).append(node('li', item));}
    function message(text, error = false) {el('message').textContent = text; el('message').className = error ? 'error' : '';}
    function options(id, rows, label, selected) {el(id).replaceChildren(); const empty = node('option', label); empty.value = ''; el(id).append(empty); for (const row of rows) {const option = node('option', row.label || row.job_id); option.value = row.resource_id || row.job_id; el(id).append(option);} el(id).value = selected || '';}
    function controls() {
      for (const id of ['refresh', 'resource', 'compare-a', 'compare-b']) el(id).disabled = !token || busy || Boolean(pending);
      el('unlock').disabled = busy;
      for (const button of jobButtons) button.disabled = !token || busy || Boolean(pending);
      el('review-run').disabled = !token || busy || Boolean(pending) || !selectedResource || !capability.available || Boolean(uncertain) || !win.crypto?.getRandomValues;
      el('retry-run').hidden = !uncertain; el('retry-run').disabled = !token || busy || Boolean(pending) || !uncertain || !reconciled || !capability.available;
      el('compare').disabled = !token || busy || Boolean(pending) || !el('compare-a').value || !el('compare-b').value || el('compare-a').value === el('compare-b').value;
      el('confirm-action').disabled = !token || busy || !pending || !el('ack').checked;
    }
    function cancelTimer() {if (timer !== null) win.clearTimeout(timer); timer = null;}
    function schedule() {
      cancelTimer();
      if (token && !doc.hidden && win.setTimeout) timer = win.setTimeout(async () => {timer = null; if (token && !doc.hidden && !busy && !pending) await refresh(false); else schedule();}, delay);
    }
    function clearPending() {pending = null; el('ack').checked = false; controls();}
    function lock() {
      generation++; active?.abort(); active = null; cancelTimer(); token = ''; busy = false; uncertain = null; reconciled = false; resources = []; jobs = []; jobLimits = {}; globalLimitations = []; selectedResource = null; jobButtons = []; reports.clear();
      dialogs.cancel(el('confirm')); clearPending();
      el('token').value = ''; el('token').required = true; el('lock').disabled = true; el('main').hidden = true; el('report-panel').hidden = true;
      for (const id of dynamic) el(id).replaceChildren(); for (const id of privateText) el(id).textContent = '';
      options('resource', [], 'Choose reviewed inputs'); for (const id of ['compare-a', 'compare-b']) options(id, [], 'Choose a completed job');
      el('state').textContent = 'Locked'; message('Locked. No private research inputs or job results loaded.'); controls(); win.AgenticNavigation?.locked?.();
    }
    async function request(path, method = 'GET', body) {
      const controller = new AbortController(), version = generation; active = controller;
      const timeout = win.setTimeout(() => controller.abort(), 10000);
      try {
        const response = await fetcher(path, {method, signal: controller.signal, cache: 'no-store', credentials: 'omit', redirect: 'error', headers: {Authorization: 'Bearer ' + token, ...(body === undefined ? {} : {'Content-Type': 'application/json'})}, ...(body === undefined ? {} : {body: JSON.stringify(body)})});
        if (version !== generation || !token) return null;
        if (response.status === 401 || response.status === 403) {lock(); message('Operator authorization failed. Unlock with the local operator token.', true); return null;}
        if (!response.ok) {const error = Error('request'); error.definitive = response.status >= 400 && response.status < 500 && response.status !== 408; throw error;}
        const data = await response.json(); return version === generation && token ? data : null;
      } finally {win.clearTimeout(timeout); if (active === controller) active = null;}
    }
    function renderResource() {
      selectedResource = resources.find(resource => resource.resource_id === el('resource').value) || null;
      el('resource-summary').replaceChildren(); el('resource-limitations').replaceChildren();
      if (selectedResource) {
        const r = selectedResource;
        definitions('resource-summary', {label: r.label, source: r.synthetic === true ? 'SYNTHETIC INPUTS · simulated evidence only' : r.synthetic === false ? 'Non-synthetic source declaration · not broker acceptance' : 'Source origin not certified', resource_sha256: r.resource_sha256, strategy: r.strategy, maximum_holding_sessions: r.strategy?.max_hold_sessions ?? 'Unavailable', economic_policy: r.policy, charge_schedule: r.runtime?.charges || 'Unavailable', code_sha256: r.runtime?.code_sha256 || 'Unavailable', coverage: r.coverage, provenance: r.provenance});
        list('resource-limitations', [...(r.limitations || []), ...globalLimitations]);
      }
      controls();
    }
    function renderResources(data) {
      if (data.schema_version !== 1 || !Array.isArray(data.resources)) throw Error('schema');
      const selected = el('resource').value; resources = data.resources; jobLimits = data.limits || {}; globalLimitations = data.limitations || []; definitions('runner-limits', jobLimits); capability = data.capability || {available: false};
      options('resource', resources, resources.length ? 'Choose reviewed inputs' : 'No registered inputs', resources.some(r => r.resource_id === selected) ? selected : '');
      el('resource-state').textContent = resources.length ? resources.length + ' registered input ' + (resources.length === 1 ? 'bundle. ' : 'bundles. ') + (capability.available ? 'Review one bundle before starting a run.' : 'Job launch unavailable. ' + (capability.reason || 'Required process isolation is unavailable.')) : 'No input bundles are registered. Use the local registration command below, inspect its source and policy validation, then refresh. No data has been downloaded or substituted.';
      if (!resources.length && !capability.available) el('resource-state').textContent += ' Job launch unavailable. ' + (capability.reason || 'Required process isolation is unavailable.');
      if (!win.crypto?.getRandomValues) el('resource-state').textContent += ' This browser cannot create a secure idempotency key; launching is unavailable.';
      renderResource();
      if (data.limitations?.length) list('resource-limitations', [...(selectedResource?.limitations || []), ...data.limitations]);
    }
    function renderJobs(data) {
      if (data.schema_version !== 1 || !Array.isArray(data.jobs)) throw Error('schema'); jobs = data.jobs;
      if (uncertain) {
        const found = jobs.find(job => job.request_key === uncertain.request_key);
        if (found) {el('submission-state').textContent = 'The request was recorded as job ' + found.job_id + ' · ' + friendly(found.state) + '. No duplicate run was requested.'; uncertain = null; reconciled = false;}
        else {reconciled = true; el('submission-state').textContent = 'The previous submission outcome is unknown. This refreshed saved job list has no matching request key. An explicit retry reuses the original key and resource hash; it never creates a new key automatically.';}
      }
      el('jobs').replaceChildren(); jobButtons = [];
      for (const job of jobs) {
        const article = node('article'), heading = node('h3', job.job_id + ' · ' + friendly(job.state));
        article.append(heading, node('p', 'Stage: ' + friendly(job.stage) + ' · Updated ' + exact(job.updated_at) + '. ' + (job.state === 'succeeded' ? 'Execution finished; inspect the report for research and valuation coverage.' : alive.has(job.state) ? 'No completion percentage or ETA is inferred.' : 'This is a saved job outcome, not a financial order status.')));
        if (job.error) article.append(node('p', 'Job error: ' + exact(job.error.code) + '. ' + (job.error.message || 'Review the registered inputs and server diagnostics before retrying.')));
        if (job.report_id && job.state === 'succeeded') {const button = node('button', 'Inspect recorded report'); button.type = 'button'; button.disabled = busy; button.addEventListener('click', () => loadReport(job)); jobButtons.push(button); article.append(button);}
        if (alive.has(job.state)) {const button = node('button', 'Review cancellation'); button.type = 'button'; button.className = 'quiet'; button.disabled = busy; button.addEventListener('click', () => reviewCancel(job)); jobButtons.push(button); article.append(button);}
        el('jobs').append(article);
      }
      const a = el('compare-a').value, b = el('compare-b').value, completed = jobs.filter(job => job.state === 'succeeded' && job.report_id).map(job => ({job_id: job.job_id, label: job.job_id}));
      options('compare-a', completed, 'Choose a completed job', completed.some(j => j.job_id === a) ? a : ''); options('compare-b', completed, 'Choose a completed job', completed.some(j => j.job_id === b) ? b : '');
      el('jobs-state').textContent = jobs.length ? jobs.length + ' saved jobs returned. Refreshed job states do not start or retry work.' : 'No saved jobs. Reviewing inputs or refreshing this page does not start a simulation.'; controls();
    }
    async function refresh(withResources = true) {
      if (!token || busy || pending) return; const version = generation; busy = true; controls();
      try {
        if (withResources) {const data = await request('/api/backtests/resources'); if (!data) return; renderResources(data);}
        const data = await request('/api/backtests/jobs'); if (!data) return; renderJobs(data);
        el('main').hidden = false; el('state').textContent = 'Saved research · paper only'; delay = 15000; message('Saved research inputs and jobs loaded. Refresh only reads state.'); win.AgenticNavigation?.updated?.();
      } catch (_) {if (version === generation) {delay = Math.min(delay * 2, 120000); el('state').textContent = 'Display stale · refresh required'; message('Saved research could not be loaded. Check that the server is running this version, then refresh. No job was submitted by this read.', true);}}
      finally {if (version === generation) {busy = false; controls(); schedule();}}
    }
    function key() {const bytes = new Uint8Array(16); win.crypto.getRandomValues(bytes); return Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');}
    function openReview(kind, data) {
      if (!token || busy || pending) return;
      pending = {kind, data}; el('ack').checked = false; el('confirm-summary').replaceChildren();
      const cancelling = kind === 'cancel'; el('ack-text').textContent = cancelling ? 'I reviewed this job cancellation and its limits.' : 'I reviewed these inputs, policy, costs and limitations.'; el('confirm-title').textContent = cancelling ? 'Cancel isolated research job?' : 'Review isolated research run'; el('confirm-action').textContent = cancelling ? 'Request job cancellation' : 'Start isolated run';
      el('confirm-text').textContent = cancelling ? 'Request cancellation of this queued or running simulation. Its saved record remains visible; a running worker may take time to stop. This does not cancel a financial order, sell holdings or change account authority.' : 'Start a bounded, isolated simulation using exactly these registered inputs and policy. This creates a research job and saved report. It does not connect a broker, change your paper account, activate a strategy or authorize orders. Offline legacy semantics do not establish connected-feed parity or months-to-years investment validation.';
      if (cancelling) definitions('confirm-summary', {job_id: data.job_id, state_at_review: data.state, semantics: data.semantics});
      else {const r = data.resource; definitions('confirm-summary', {inputs: r.label, resource_id: r.resource_id, resource_sha256: data.resource_sha256, source: r.synthetic === true ? 'SYNTHETIC · simulated evidence only' : r.synthetic === false ? 'Non-synthetic declaration · not broker acceptance' : 'Origin not certified', strategy: r.strategy, maximum_holding_sessions: r.strategy?.max_hold_sessions ?? 'Unavailable', economic_policy: r.policy, charge_schedule: r.runtime?.charges || 'Unavailable', code_sha256: r.runtime?.code_sha256 || 'Unavailable', coverage: r.coverage, provenance: r.provenance, limitations: r.limitations, isolation_limits: jobLimits, request_key: data.request_key});}
      controls();
      if (!dialogs.open(el('confirm'), {cancel: clearPending, focus: el('cancel')})) {clearPending(); message('The confirmation could not be displayed. Reopen Backtesting and review again. Nothing was submitted.', true);}
    }
    function reviewRun(retry = false) {
      if (!token || busy || pending || !capability.available) return;
      if (retry) {if (uncertain && reconciled) openReview('run', uncertain); return;}
      if (!selectedResource || uncertain || !win.crypto?.getRandomValues) return;
      openReview('run', {resource: structuredClone(selectedResource), resource_id: selectedResource.resource_id, resource_sha256: selectedResource.resource_sha256, request_key: key()});
    }
    function reviewCancel(job) {if (alive.has(job.state)) openReview('cancel', {...job});}
    async function confirm() {
      if (!pending || !token || busy || !el('ack').checked) return;
      const review = pending, version = generation; pending = null; dialogs.close(el('confirm')); el('ack').checked = false; busy = true; controls();
      if (review.kind === 'run') {uncertain = review.data; reconciled = false;}
      try {
        const data = review.kind === 'run' ? await request('/api/backtests/jobs', 'POST', {resource_id: review.data.resource_id, resource_sha256: review.data.resource_sha256, request_key: review.data.request_key, acknowledged: true}) : await request('/api/backtests/jobs/' + encodeURIComponent(review.data.job_id) + '/cancel', 'POST', {acknowledged: true});
        if (!data) return;
        if (!data.job?.job_id) throw Error('schema');
        if (review.kind === 'run') {uncertain = null; el('submission-state').textContent = 'Recorded job ' + data.job.job_id + ' · ' + friendly(data.job.state) + '. Inspect its saved outcome; no paper account authority changed.';}
        else message('Cancellation requested for ' + data.job.job_id + '. The saved job record remains visible.');
        renderJobs({schema_version: 1, jobs: [data.job, ...jobs.filter(job => job.job_id !== data.job.job_id)]});
      } catch (error) {
        if (version !== generation) return;
        if (review.kind === 'run') {
          if (error.definitive) {uncertain = null; el('submission-state').textContent = 'The server rejected the job request. No retry was sent. Refresh registered inputs and review their current hash and launch capability.';}
          else el('submission-state').textContent = 'Submission outcome unknown. Refresh saved jobs before an explicit retry; the original request key is retained in this unlocked tab. No automatic retry will be sent.';
        }
        message(review.kind === 'cancel' ? 'Cancellation outcome is unknown. Refresh saved jobs to inspect its current state; no cancellation was retried automatically.' : 'The run request did not return a confirmed outcome. Inspect the submission message and refresh jobs.', true);
      } finally {if (version === generation) {busy = false; controls(); schedule();}}
    }
    function table(id, caption, rows, limit) {
      const target = el(id); target.replaceChildren(); const all = Array.isArray(rows) ? rows : [];
      if (!all.length) {target.append(node('p', caption + ': no rows recorded.')); return;}
      const data = all.slice(0, limit), keys = [...new Set(data.flatMap(row => Object.keys(row)))];
      const table = node('table'), head = node('thead'), heading = node('tr'); table.append(node('caption', caption + (all.length > limit ? ' · first ' + limit + ' returned rows shown' : ' · exact recorded values')));
      for (const key of keys) {const th = node('th', friendly(key)); th.setAttribute('scope', 'col'); heading.append(th);} head.append(heading); table.append(head); const body = node('tbody');
      for (const row of data) {const tr = node('tr'); for (const key of keys) tr.append(node('td', value(key, row[key]))); body.append(tr);} table.append(body); target.append(table);
    }
    function validateReport(report) {
      if (report.schema_version !== 1 || !report.summary || Array.isArray(report.summary) || !report.provenance || !/^[a-f0-9]{64}$/.test(report.artifact_sha256 || '') || !['equity_curve', 'drawdown_curve', 'orders', 'fills'].every(key => Array.isArray(report[key]))) throw Error('schema');
      return report;
    }
    function renderReport(report) {
      validateReport(report);
      const synthetic = report.synthetic === true || report.provenance.synthetic === true || report.provenance.dataset?.synthetic === true;
      el('report-state').textContent = (synthetic ? 'SYNTHETIC INPUTS · simulated evidence only. ' : 'Paper simulation · source declaration appears below. ') + 'Report ' + report.report_id + '. Completion is separate from valuation completeness and research eligibility.';
      definitions('report-summary', {...report.summary, final_snapshot: report.final_snapshot}); definitions('report-provenance', {...report.provenance, resource_sha256: report.resource_sha256, artifact_sha256: report.artifact_sha256}); list('report-limitations', [...(report.limitations || []), ...(Object.values(report.truncation || {}).some(Boolean) ? ['This bounded response omits some historical rows. Inspect the retained local artifacts for complete curves, orders, fills and trades.'] : [])]);
      el('report-metrics').textContent = 'Annualized return, CAGR, Sharpe, Sortino, monthly returns, benchmark and out-of-sample validation are unavailable unless this report explicitly supplies a supported metric with its methodology. Event observations are not daily return cuts.';
      table('report-equity', 'Equity history and valuation coverage', report.equity_curve, 3000); table('report-drawdown', 'Drawdown history', report.drawdown_curve, 3000); table('report-orders', 'Orders, including unfilled and rejected outcomes', report.orders, 1000); table('report-fills', 'Recorded simulated fills and charged costs', report.fills, 1000);
      el('report-panel').hidden = false; win.AgenticNavigation?.updated?.();
    }
    async function reportFor(job) {if (reports.has(job.report_id)) return reports.get(job.report_id); const report = await request('/api/backtests/reports/' + encodeURIComponent(job.report_id)); if (report) reports.set(job.report_id, validateReport(report)); return report;}
    async function loadReport(job) {
      if (!token || busy || pending) return; const version = generation; busy = true; controls();
      try {const report = await reportFor(job); if (report) {renderReport(report); message('Recorded report loaded. This read did not start a job or alter your paper account.');}}
      catch (_) {if (version === generation) message('The report could not be read or verified. Refresh jobs and inspect the server diagnostics. No result values were invented.', true);}
      finally {if (version === generation) {busy = false; controls(); schedule();}}
    }
    async function compare() {
      if (!token || busy || pending) return; const a = jobs.find(j => j.job_id === el('compare-a').value), b = jobs.find(j => j.job_id === el('compare-b').value); if (!a?.report_id || !b?.report_id || a.job_id === b.job_id) return;
      const version = generation; busy = true; controls(); el('comparison').replaceChildren();
      try {
        const left = await reportFor(a); if (!left) return; const right = await reportFor(b); if (!right) return;
        const semantics = report => report.provenance?.semantics || report.provenance?.resource?.semantics;
        if (!left.resource_sha256 || left.resource_sha256 !== right.resource_sha256 || semantics(left) !== 'legacy-offline-v1' || semantics(right) !== 'legacy-offline-v1') {el('comparison-state').textContent = 'Comparison blocked: matching input, strategy, cost, price-basis and source-period identity is not established. This view requires the same registered resource hash and declared legacy offline method.'; return;}
        const rows = [...new Set([...Object.keys(left.summary), ...Object.keys(right.summary)])].map(key => ({metric: friendly(key), [a.job_id]: value(key, left.summary[key]), [b.job_id]: value(key, right.summary[key])}));
        table('comparison', 'Same-resource recorded results', rows, 200); el('comparison-state').textContent = 'Same registered input, strategy and policy hash; declared legacy offline method. Values are simulated outcomes. Matching methodology does not establish out-of-sample or broker validation.';
      } catch (_) {if (version === generation) el('comparison-state').textContent = 'Comparison unavailable. Both recorded reports must be readable and verifiable; no missing values were replaced.';}
      finally {if (version === generation) {busy = false; controls(); schedule();}}
    }
    el('access').addEventListener('submit', event => {event.preventDefault(); const supplied = el('token').value; if (supplied) {lock(); token = supplied; el('token').value = ''; el('token').required = false; el('lock').disabled = false;} refresh();});
    el('lock').addEventListener('click', lock); el('refresh').addEventListener('click', () => refresh()); el('resource').addEventListener('change', renderResource);
    el('review-run').addEventListener('click', () => reviewRun()); el('retry-run').addEventListener('click', () => reviewRun(true));
    el('cancel').addEventListener('click', () => dialogs.cancel(el('confirm'))); el('ack').addEventListener('change', controls); el('confirm-action').addEventListener('click', confirm);
    for (const id of ['compare-a', 'compare-b']) el(id).addEventListener('change', controls); el('compare').addEventListener('click', compare);
    doc.addEventListener?.('visibilitychange', () => {cancelTimer(); if (!doc.hidden) schedule();}); win.addEventListener?.('pagehide', lock);
    lock(); return {refresh, lock, canNavigate: () => !busy && !pending};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {createBacktesting};
  if (typeof document !== 'undefined') {const view = createBacktesting(document, window, window.fetch.bind(window)); window.AgenticNavigation?.connect(view, 'access');}
})();
