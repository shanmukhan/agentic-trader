
'use strict';
const report = JSON.parse(document.getElementById('report-data').textContent);
const byId = id => document.getElementById(id);
const labels = {research_candidate:'Research candidate',screened_out:'Screened out',needs_data:'Needs data',outside_universe:'Outside universe'};
const reasons = {INSUFFICIENT_CONSECUTIVE_HISTORY:'Not enough consecutive completed sessions to evaluate this policy.',LATEST_SESSION_UNAVAILABLE_OR_MISSING:'The latest declared completed session is missing or was not yet knowable at the selected time.',EXCLUDED_BY_POINT_IN_TIME_UNIVERSE:'Excluded by the reviewed universe at this session.',NONPOSITIVE_MOMENTUM:'Trailing gross total return is zero or negative.',BELOW_TREND_AVERAGE:'The gross return index is below its trailing trend average.',LOW_AVERAGE_TURNOVER:'Average raw close × volume is below this research threshold.',HIGH_DAILY_VOLATILITY:'Observed daily return volatility exceeds this research threshold.'};
const number = (value, suffix='') => value == null ? '—' : (Number.isFinite(Number(value)) ? Number(value).toLocaleString('en-IN',{maximumFractionDigits:2,minimumFractionDigits:2}) : String(value)) + suffix;
const text = (node, value) => { node.textContent=value; };
function cell(row,value,detail){const td=document.createElement('td');td.textContent=value;if(detail){const small=document.createElement('small');small.textContent=detail;td.append(small);}row.append(td);}
text(byId('as-of'),new Date(report.as_of).toLocaleString('en-IN',{timeZone:'Asia/Kolkata',dateStyle:'medium',timeStyle:'short'})+' IST');
text(byId('latest'),report.latest_reviewed_completed_session || 'No completed session');
text(byId('provenance'),report.synthetic ? 'Invented dataset · software demonstration' : 'Supplied dataset · external provenance unverified');
text(byId('candidate-count'),String(report.candidate_count));
text(byId('symbol-count'),String(report.rows.length));
text(byId('coverage-count'),String(report.rows.filter(r=>r.status==='needs_data').length));
text(byId('source'),report.dataset.source);text(byId('source-notes'),report.dataset.notes);
text(byId('policy'),JSON.stringify(report.policy,null,2));text(byId('quality'),JSON.stringify(report.quality,null,2));
for(const item of report.limitations){const li=document.createElement('li');li.textContent=item;byId('limits').append(li);}
function refresh(){
 const query=byId('search').value.trim().toUpperCase(),status=byId('status').value,sort=byId('sort').value;
 const rows=report.rows.filter(r=>r.symbol.includes(query) && (status==='all'||r.status===status));
 rows.sort((a,b)=>sort==='symbol'?a.symbol.localeCompare(b.symbol):(a.rank||1e9)-(b.rank||1e9)||a.symbol.localeCompare(b.symbol));
 byId('rows').replaceChildren();
 for(const value of rows){const row=document.createElement('tr');
  cell(row,value.symbol,value.rank?'Research rank '+value.rank:'Unranked');
  cell(row,labels[value.status],value.reasons.length?value.reasons.map(r=>reasons[r]||r).join(' '):'Passes these screening rules. Review evidence before further strategy research.');
  cell(row,number(value.gross_total_return_pct,'%'),'Gross; before fees/tax');
  cell(row,number(value.daily_volatility_pct,'%'),'Observed daily, not a forecast');
  cell(row,number(value.average_turnover),'INR/day · close × volume');
  cell(row,value.last_session||'Unavailable',value.observations?value.observations+' consecutive observations':'No complete latest observation');
  byId('rows').append(row);
 }
 byId('empty').hidden=rows.length>0;
 text(byId('empty'),report.rows.length?'No symbols match these filters. Clear the search or show all statuses.':'No universe members are effective for a declared completed session at this time. Review the as-of clock and calendar.');
 text(byId('result-count'),rows.length+' of '+report.rows.length+' symbols shown');
}
for(const id of ['search','status','sort'])byId(id).addEventListener('input',refresh);
byId('clear').addEventListener('click',()=>{byId('search').value='';byId('status').value='all';byId('sort').value='rank';refresh();byId('search').focus();});
refresh();
