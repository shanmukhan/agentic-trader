(function () {
  'use strict';
  const createDialogs = typeof module !== 'undefined' && module.exports ? require('./dialogs.js').createDialogs : window.AgenticDialogs;
  function createPolicyDrafts(doc, win, fetcher) {
    const el = id => doc.getElementById(id);
    const node = (tag, text) => {const item = doc.createElement(tag); if (text !== undefined) item.textContent = String(text); return item;};
    const dialogs = createDialogs(doc, win), inputs = new Map();
    let token = '', generation = 0, controller = null, busy = false, pending = null, uncertain = null, reconciled = false, dirty = false, definitions = [], drafts = [], buttons = [];
    function message(text, error = false) {el('message').textContent = text; el('message').className = error ? 'error' : '';}
    function controls() {
      const blocked = !token || busy || Boolean(pending);
      for (const id of ['refresh', 'discard']) el(id).disabled = blocked;
      el('unlock').disabled = busy; el('review').disabled = blocked || !definitions.length || Boolean(uncertain);
      el('policy-label').disabled = blocked || Boolean(uncertain);
      for (const input of inputs.values()) input.disabled = blocked || Boolean(uncertain);
      for (const button of buttons) button.disabled = blocked || dirty || Boolean(uncertain);
      el('retry').hidden = !uncertain; el('retry').disabled = blocked || !uncertain || !reconciled;
      el('save').disabled = !token || busy || !pending || !el('ack').checked;
      el('editing-state').textContent = dirty ? 'Unsaved changes. Review and save, or discard before leaving this screen.' : 'No unsaved changes. Blank choices remain unresolved.';
    }
    function clearPending() {pending = null; el('ack').checked = false; el('confirm-rows').replaceChildren(); el('confirm-identity').replaceChildren(); el('confirm-state').textContent = ''; controls();}
    function lock() {
      generation++; controller?.abort(); controller = null; token = ''; busy = false; uncertain = null; reconciled = false; dirty = false; drafts = []; definitions = []; inputs.clear(); buttons = [];
      dialogs.cancel(el('confirm')); clearPending(); el('token').value = ''; el('token').required = true; el('lock').disabled = true; el('main').hidden = true; el('policy-label').value = '';
      for (const id of ['policy-fields', 'saved-drafts', 'limitations']) el(id).replaceChildren();
      for (const id of ['editing-state', 'saved-state', 'save-state']) el(id).textContent = '';
      el('state').textContent = 'Locked'; message('Locked. No private policy choices are displayed.'); controls(); win.AgenticNavigation?.locked?.();
    }
    async function request(path, method = 'GET', body) {
      const current = new AbortController(), version = generation; controller = current;
      const timeout = win.setTimeout(() => current.abort(), 10000);
      try {
        const response = await fetcher(path, {method, signal: current.signal, cache: 'no-store', credentials: 'omit', redirect: 'error', headers: {Authorization: 'Bearer ' + token, ...(body === undefined ? {} : {'Content-Type': 'application/json'})}, ...(body === undefined ? {} : {body: JSON.stringify(body)})});
        if (version !== generation || !token) return null;
        if (response.status === 401 || response.status === 403) {lock(); message('Operator authorization failed. Unlock the workspace again.', true); return null;}
        if (!response.ok) {const error = Error('request'); error.definitive = response.status >= 400 && response.status < 500 && response.status !== 408; throw error;}
        const data = await response.json(); return version === generation && token ? data : null;
      } finally {win.clearTimeout(timeout); if (controller === current) controller = null;}
    }
    function changed() {dirty = true; el('save-state').textContent = ''; controls();}
    function buildFields(rows) {
      if (!rows.length || rows.length > 50 || new Set(rows.map(field => field.name)).size !== rows.length || rows.some(field => typeof field.group !== 'string' || typeof field.label !== 'string' || !/^[a-z][a-z0-9_]{0,63}$/.test(field.name) || !['choice', 'integer', 'decimal'].includes(field.kind) || field.kind === 'choice' && (!Array.isArray(field.choices) || field.choices.some(choice => typeof choice.value !== 'string' || typeof choice.label !== 'string')))) throw Error('schema');
      definitions = rows; el('policy-fields').replaceChildren(); inputs.clear(); const groups = new Map();
      for (const field of definitions) {
        if (!/^[a-z][a-z0-9_]{0,63}$/.test(field.name) || !['choice', 'integer', 'decimal'].includes(field.kind)) throw Error('schema');
        if (!groups.has(field.group)) {const section = node('fieldset'), legend = node('legend', field.group); section.append(legend); section.className = 'policy-field-group'; groups.set(field.group, section); el('policy-fields').append(section);}
        const wrapper = node('div'); wrapper.className = 'policy-field'; const id = 'policy-' + field.name, label = node('label', field.label); label.setAttribute('for', id);
        const input = node(field.kind === 'choice' ? 'select' : 'input'); input.id = id;
        if (field.kind === 'choice') {const empty = node('option', 'Unresolved — choose explicitly'); empty.value = ''; input.append(empty); for (const choice of field.choices || []) {const option = node('option', choice.label); option.value = choice.value; input.append(option);}}
        else {input.type = field.kind === 'integer' ? 'number' : 'text'; input.setAttribute('inputmode', field.kind === 'integer' ? 'numeric' : 'decimal'); if (field.kind === 'integer') {input.min = field.minimum; input.max = field.maximum; input.step = 1;}}
        const help = node('p'); help.id = id + '-help'; help.className = 'muted';
        help.textContent = field.kind === 'choice' ? 'No choice is preselected.' : 'Unit: ' + (field.unit || 'count') + '. ' + (field.exclusive_minimum ? 'Greater than ' : 'Minimum ') + field.minimum + '; ' + (field.exclusive_maximum ? 'less than ' : 'maximum ') + field.maximum + '.' + (field.name === 'horizon_count' ? ' Months: 1–1200; years: 1–100.' : '') + (field.kind === 'decimal' ? ' Keep exact decimal values; no thousands separators.' : '');
        input.setAttribute('aria-describedby', help.id); input.value = ''; input.addEventListener('input', changed); input.addEventListener('change', changed); inputs.set(field.name, input); wrapper.append(label, input, help); groups.get(field.group).append(wrapper);
      }
    }
    function clearForm() {el('policy-label').value = ''; for (const input of inputs.values()) input.value = ''; dirty = false; uncertain = null; reconciled = false; el('save-state').textContent = ''; controls();}
    function draftPayload() {
      const parameters = {};
      for (const field of definitions) {const raw = inputs.get(field.name).value.trim(); if (!raw) parameters[field.name] = null; else if (field.kind === 'integer') {if (!/^[0-9]+$/.test(raw)) throw Error('integer'); parameters[field.name] = Number(raw); if (!Number.isSafeInteger(parameters[field.name])) throw Error('integer');} else parameters[field.name] = raw;}
      return {label: el('policy-label').value.trim() || null, parameters};
    }
    function fillForm(draft) {el('policy-label').value = draft.label || ''; for (const field of definitions) inputs.get(field.name).value = draft.parameters[field.name] === null ? '' : String(draft.parameters[field.name]);}
    function editCopy(saved) {if (busy || pending || dirty || uncertain) return; fillForm(saved); dirty = true; el('save-state').textContent = 'Editing a copy of ' + saved.draft_id + '. The saved snapshot remains intact.'; controls(); el('policy-label').focus?.();}
    function renderSaved() {
      buttons = []; el('saved-drafts').replaceChildren();
      for (const draft of drafts) {const article = node('article'); article.append(node('h3', draft.label || 'Unnamed policy draft'), node('p', draft.state === 'specified' ? 'All draft parameters specified. Execution and installation remain unavailable.' : (draft.missing_fields?.length ?? 'Some') + ' unresolved choices. This draft cannot be activated.'), node('p', 'Snapshot: ' + draft.draft_id)); const details = node('details'); details.append(node('summary', 'Exact saved choices'), node('pre', JSON.stringify(draft.parameters, null, 2))); article.append(details); const button = node('button', 'Edit a copy'); button.type = 'button'; button.className = 'quiet'; button.addEventListener('click', () => editCopy(draft)); buttons.push(button); article.append(button); el('saved-drafts').append(article);}
      el('saved-state').textContent = drafts.length ? drafts.length + ' saved snapshot' + (drafts.length === 1 ? '.' : 's.') : 'No saved policy drafts. Your current strategy is separate.';
    }
    function validateDraft(draft) {
      if (!draft || draft.schema_version !== 1 || draft.family !== 'nse-investment-policy-v2' || draft.decision_semantics !== 'investment-decisions-v2.1' || draft.activation_supported !== false || draft.backtest_supported !== false || !draft.parameters || typeof draft.parameters !== 'object' || Array.isArray(draft.parameters) || !Array.isArray(draft.missing_fields) || !/^[a-f0-9]{64}$/.test(draft.draft_sha256 || '')) throw Error('schema');
      const names = definitions.map(field => field.name), missing = names.filter(name => draft.parameters[name] === null);
      if (Object.keys(draft.parameters).length !== names.length || names.some(name => !Object.hasOwn(draft.parameters, name)) || JSON.stringify(missing) !== JSON.stringify(draft.missing_fields) || draft.state !== (missing.length ? 'incomplete' : 'specified') || draft.policy_version_id !== (missing.length ? null : draft.draft_sha256)) throw Error('schema');
      for (const field of definitions) {const value = draft.parameters[field.name]; if (value !== null && (field.kind === 'integer' ? !Number.isSafeInteger(value) : typeof value !== 'string')) throw Error('schema');}
      return draft;
    }
    async function refresh() {
      if (!token || busy || pending) return; const version = generation; busy = true; controls();
      try {const data = await request('/api/investment-policies'); if (!data) return; if (data.schema_version !== 1 || !Array.isArray(data.field_definitions) || !Array.isArray(data.drafts) || data.drafts.length > 100) throw Error('schema'); if (!definitions.length) buildFields(data.field_definitions); for (const draft of data.drafts) {validateDraft(draft); if (!/^draft-[a-f0-9]{64}$/.test(draft.draft_id || '')) throw Error('schema');} drafts = data.drafts; renderSaved(); el('limitations').replaceChildren(); for (const text of data.limitations || []) el('limitations').append(node('li', text));
        if (uncertain) {const found = drafts.find(draft => draft.draft_id === 'draft-' + uncertain.preview_sha256); if (found) {fillForm(found); uncertain = null; reconciled = false; dirty = false; el('save-state').textContent = 'The previous save was recorded. Its immutable snapshot is listed below.';} else {reconciled = true; el('save-state').textContent = 'No matching snapshot appeared in this refreshed list. Review an explicit retry using the same reviewed draft and hash.';}}
        el('main').hidden = false; el('token').required = false; el('state').textContent = 'Policy drafts · no active change'; message('Saved drafts loaded. Refresh only reads research storage.'); win.AgenticNavigation?.updated?.();
      } catch (_) {if (version === generation) {el('state').textContent = 'Display stale · refresh required'; message('Drafts could not be read safely. Check local research storage and refresh. No account policy changed.', true);}}
      finally {if (version === generation) {busy = false; controls();}}
    }
    function showReview(data) {
      if (data.schema_version !== 1 || !/^[a-f0-9]{64}$/.test(data.preview_sha256 || '')) throw Error('schema'); validateDraft(data.draft);
      el('ack').checked = false; el('confirm-rows').replaceChildren(); el('confirm-identity').replaceChildren();
      el('confirm-state').textContent = data.draft.state === 'specified' ? 'All parameters specified. This is a saved research policy only; execution adapters and validation remain unavailable.' : data.draft.missing_fields.length + ' choices remain unresolved; saving will preserve those empty fields.';
      const nameRow = node('tr'); nameRow.append(node('td', 'Draft name'), node('td', data.draft.label || 'Unnamed')); el('confirm-rows').append(nameRow);
      for (const field of definitions) {const row = node('tr'), value = data.draft.parameters[field.name]; let text = value === null || value === undefined ? 'Unresolved' : String(value); if (field.kind === 'choice') text = field.choices?.find(choice => choice.value === value)?.label || text; row.append(node('td', field.label), node('td', text + (value !== null && field.unit ? ' ' + field.unit : ''))); el('confirm-rows').append(row);}
      for (const [label, value] of Object.entries({family: data.draft.family, decision_semantics: data.draft.decision_semantics, semantic_hash: data.draft.draft_sha256, policy_version_id: data.draft.policy_version_id || 'Unavailable until all parameters are specified', reviewed_snapshot_hash: data.preview_sha256})) {const pair = node('div'); pair.append(node('dt', label.replaceAll('_', ' ')), node('dd', value)); el('confirm-identity').append(pair);}
      pending = structuredClone(data); controls(); if (!dialogs.open(el('confirm'), {cancel: clearPending, focus: el('cancel')})) {clearPending(); message('The review dialog could not be displayed. No snapshot was saved.', true);}
    }
    async function review() {
      if (!token || busy || pending || uncertain) return; const version = generation; busy = true; controls();
      try {const payload = draftPayload(), data = await request('/api/investment-policies/preview', 'POST', {draft: payload}); if (!data) return; if (!data.draft?.parameters || !/^[a-f0-9]{64}$/.test(data.preview_sha256 || '')) throw Error('schema'); busy = false; showReview(data);}
      catch (_) {if (version === generation) {dialogs.cancel(el('confirm')); clearPending(); message('The draft could not be reviewed. Check ranges and exact decimal values, and ensure invested cap plus reserve is at most 100% and stock/sector caps fit. No snapshot was saved.', true);}}
      finally {if (version === generation) {busy = false; controls();}}
    }
    async function save() {
      if (!token || busy || !pending || !el('ack').checked) return; const reviewed = pending, version = generation; pending = null; dialogs.close(el('confirm')); clearPending(); uncertain = reviewed; reconciled = false; busy = true; controls();
      try {const data = await request('/api/investment-policies', 'POST', {draft: {label: reviewed.draft.label, parameters: reviewed.draft.parameters}, preview_sha256: reviewed.preview_sha256, acknowledged: true}); if (!data) return; validateDraft(data.draft); if (data.schema_version !== 1 || data.draft.draft_id !== 'draft-' + reviewed.preview_sha256) throw Error('schema'); fillForm(data.draft); uncertain = null; dirty = false; drafts = [data.draft, ...drafts.filter(draft => draft.draft_id !== data.draft.draft_id)]; renderSaved(); el('save-state').textContent = 'Saved ' + data.draft.draft_id + '. Your installed strategy and mode are unchanged.'; message('Draft snapshot saved in private research storage.');}
      catch (error) {if (version === generation) {if (error.definitive) {uncertain = null; el('save-state').textContent = 'The server rejected this save. Refresh and review the draft again; no automatic retry was sent.';} else el('save-state').textContent = 'Save outcome unknown. Refresh saved drafts before an explicit retry. The same reviewed choices and hash are retained in this unlocked tab.';}}
      finally {if (version === generation) {busy = false; controls(); win.AgenticNavigation?.updated?.();}}
    }
    el('access').addEventListener('submit', event => {event.preventDefault(); const supplied = el('token').value; if (supplied) {lock(); token = supplied; el('token').value = ''; el('token').required = false; el('lock').disabled = false;} refresh();});
    el('lock').addEventListener('click', lock); el('refresh').addEventListener('click', refresh); el('discard').addEventListener('click', () => {if (!busy && !pending) clearForm();}); el('policy-label').addEventListener('input', changed); el('review').addEventListener('click', review); el('ack').addEventListener('change', controls); el('save').addEventListener('click', save); el('cancel').addEventListener('click', () => dialogs.cancel(el('confirm'))); el('retry').addEventListener('click', () => {if (uncertain && reconciled && !busy && !pending) showReview(uncertain);}); win.addEventListener?.('pagehide', lock);
    win.addEventListener?.('beforeunload', event => {if (busy || pending || dirty || uncertain) {event.preventDefault(); event.returnValue = '';}});
    lock(); return {refresh, lock, canNavigate: () => !busy && !pending && !dirty && !uncertain};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {createPolicyDrafts};
  if (typeof document !== 'undefined') {const view = createPolicyDrafts(document, window, window.fetch.bind(window)); window.AgenticNavigation?.connect(view, 'access');}
})();
