
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

const report=JSON.parse(document.getElementById('data').textContent), el=id=>document.getElementById(id);
const validation=report.kind==='daily-delivery-validation-v1', labels=report.kind==='daily-delivery-labels-v1';
const set=(id,value)=>{el(id).textContent=value;};
const at=value=>new Date(value).toLocaleString('en-IN',{timeZone:'Asia/Kolkata',dateStyle:'medium',timeStyle:'short'})+' IST';
const human=value=>String(value).toLowerCase().replaceAll('_',' ');
set('title',validation?'Daily model: inspect the held-out evidence':labels?'Daily labels: inspect independent outcomes':'Daily strategy: inspect actual simulated fills');
set('provenance',report.synthetic?'Invented evidence · software demonstration only':'Supplied evidence · external provenance and acceptance remain unverified');
set('period',validation?'Validation source through '+at(report.source_available_through):at(report.first_event)+' to '+at(report.source_available_through));
const card=(which,label,value,note)=>{set('label-'+which,label);set('value-'+which,value);set('note-'+which,note);};
if(validation){
 const last=report.splits.at(-1).metrics;
 card('one','Holdout checks',last.passed?'Passed':'Failed','The final holdout was evaluated after coefficients were frozen.');
 card('two','Holdout ROC-AUC',last.roc_auc==null?'Unavailable':last.roc_auc.toFixed(3),'Ranking diagnostic; not expected investment return.');
 card('three','Selected independent-label P&L',formatMoney(last.selected_net_pnl),'Separate virtual trials; not portfolio profit.');
 set('meaning','Offline daily model only. Passing statistical checks does not verify market profitability, live execution, custody or deployment readiness.');
 set('next-step',report.gates.walk_forward&&report.gates.holdout?'Statistical checks passed. Use only a separate later offline replay after validation and embargo; synthetic evidence requires the explicit synthetic override.':'Model checks failed. Preserve this experiment. Loading for scoring is blocked; do not change gates or tune against this holdout.');
 el('view').replaceChildren();const option=document.createElement('option');option.value='splits';option.textContent='Chronological validation splits';el('view').append(option);el('view').value='splits';
 set('exposure','Training, calibration and evaluation diagnostics are retained per split. Reliability bins and interval boundaries are in validation.json.');
}else{
 const m=report.metrics,a=report.final_snapshot;
 if(labels){
  card('one','Completed labels',String(report.label_counts.LABELED||0),'Both profitable and unfavorable completed trials remain in the sample bundle.');
  card('two','Excluded / censored trials',String(Object.entries(report.label_counts).filter(([key])=>key!=='LABELED').reduce((sum,[,n])=>sum+n,0)),'See label_audit.jsonl for unfilled, partial, interrupted and unfinished outcomes.');
  card('three','Portfolio return','Not measured','The observer places no trades. Label accounts each use independent virtual capital.');
 }else{
  card('one','Observed net liquidation P&L',formatMoney(m.net_observed_pnl),'Includes estimated liquidation and known receivables. Stale marks make it incomplete.');
  card('two','Fees charged',formatMoney(a.fees),'Delivery estimates include actual virtual fill fees and symbol/day DP allocation.');
  card('three','Completed trades',String(m.completed_trades),'Unfinished positions/orders/claims are retained separately.');
 }
 set('meaning',labels?'Independent labels are counterfactual trials, not a portfolio. Censored intervals never become guessed negative labels.':'Paper replay only. All fills require later observed quotes; these are simulated outcomes, not actual broker executions.');
 set('next-step',labels?'Review label counts and censored audits before training. Chronological validation must pass before a later scored replay.':report.status==='complete'?'Execution evidence is internally complete under its configured coverage assumptions. Review historical costs and a sufficient real-data sample before drawing conclusions.':'Execution evidence is incomplete. Inspect open exposure, claim balances, coverage gaps and rejected quotes; preserve the account rather than invent a final sale.');
 set('exposure','Open positions: '+a.positions.length+' · Pending orders: '+m.pending_orders+' · Unpaid claims: '+m.unpaid_claims+' · Valuation: '+(a.valuation_fresh?'fresh at final observation':'stale / incomplete')+' · Received dividend income: '+formatMoney(m.income_received));
}
for(const [name,passed]of Object.entries(report.gates)){const li=document.createElement('li');li.textContent=(passed?'Passed: ':'Needs review: ')+human(name);el('gates').append(li);}
for(const value of report.limitations||['Selected-label P&L is not a portfolio result.','Synthetic evidence does not validate a market edge.','Full boundaries, purge counts, calibration bins and counts remain in validation.json.']){const li=document.createElement('li');li.textContent=value;el('limits').append(li);}
set('details',JSON.stringify(validation?{settings:report.settings,counts:report.samples_counts,model_sha256:report.model_sha256}:{strategy:report.strategy,risk_policy:report.risk_policy,event_counts:report.event_counts,label_counts:report.label_counts,model_sha256:report.model_sha256,model_available_after:report.model_available_after},null,2));
function refresh(){
 const kind=el('view').value,query=el('search').value.trim().toUpperCase();
 let items=validation?report.splits:kind==='decisions'?report.decisions:report.trades;
 const total=items.length;items=items.filter(item=>JSON.stringify(item).toUpperCase().includes(query));
 const columns=validation?['Split / windows','Samples','ROC-AUC / Brier','ECE','Selected labels / P&L','Checks']:kind==='decisions'?['Decision time','Symbol','Research / model','Risk result','Reasons']:['Symbol','Entry / exit','Original quantity / share changes','Fees','Net capital P&L','Exit reason'];
 const header=document.createElement('tr');for(const name of columns){const th=document.createElement('th');th.scope='col';th.textContent=name;header.append(th);}el('columns').replaceChildren(header);el('rows').replaceChildren();
 for(const item of items.slice(0,200)){const row=document.createElement('tr');let values;
 if(validation)values=[item.name+' · evaluation '+at(item.evaluation_first)+' to '+at(item.evaluation_last),String(item.metrics.count),String(item.metrics.roc_auc)+' / '+item.metrics.brier.toFixed(4),item.metrics.expected_calibration_error.toFixed(4),item.metrics.selected_count+' / '+formatMoney(item.metrics.selected_net_pnl),item.metrics.passed?'Passed':'Failed: '+Object.entries(item.metrics.gates).filter(([,ok])=>!ok).map(([key])=>human(key)).join(', ')];
 else if(kind==='decisions')values=[at(item.time),item.symbol,item.probability==null?'Rule screen':item.probability.toFixed(3),item.order_state||(item.label_trial_requested?'Independent trial requested':'No order'),[...(item.reasons||[]),item.risk_reasons||''].filter(Boolean).map(human).join(', ')||'No rejection'];
 else values=[item.symbol,at(item.entry_time)+' / '+at(item.exit_time),item.quantity+' / '+(item.corporate_share_delta||0),formatMoney(item.fees),formatMoney(item.net_pnl),human(item.exit_reason)];
 for(const value of values){const td=document.createElement('td');td.textContent=value;row.append(td);}el('rows').append(row);}
 set('result-count',Math.min(200,items.length)+' of '+items.length+' matching records shown ('+total+' total). Full evidence remains in JSON/JSONL.');
 el('empty').hidden=items.length>0;set('empty',query?'No records match this search. Clear it or change the evidence view.':validation?'No validation splits are available.':kind==='decisions'?'No decisions were eligible in the observed interval. Review quote, session and daily-data coverage.':'No completed trades. Check decisions and unresolved exposure; an exit request alone is not a fill.');
}
el('search').addEventListener('input',refresh);el('view').addEventListener('input',refresh);el('clear').addEventListener('click',()=>{el('search').value='';refresh();el('search').focus();});refresh();
