/* No client-side sizing, persistence or automatic purchase retry. */
(function(){
'use strict';
const money=typeof module!=='undefined'&&module.exports?require('./money.js'):window.AgenticMoney;
function createPortfolio(doc,win,fetcher){
 const el=id=>doc.getElementById(id), base='/api/paper/portfolio';
 let token='',generation=0,active=null,busy=false,latest=null,lastReceipt=0,review=null,pending=null,request=null,submitted=false,dynamic=[];
 const fields=['symbol','budget','stop','target','reference'];
 const msg=(value,error=false)=>{el('message').textContent=value;el('message').className=error?'error':'';};
 const node=(tag,text)=>{const n=doc.createElement(tag);n.textContent=text;return n;};
 const fresh=()=>latest&&lastReceipt>0&&win.Date.now()-lastReceipt<=6000;
 function buttons(){
  const disabled=!token||!latest||busy||!fresh();
  for(const id of ['preview-button','save-plan','new-purchase'])el(id).disabled=disabled;
  for(const b of dynamic)b.disabled=disabled;
  el('submit-purchase').disabled=disabled||!review?.decision.allowed||submitted;
 }
 function clearPreview(){review=null;el('preview').hidden=true;el('preview-summary').textContent='';el('preview-reasons').replaceChildren();buttons();}
 function lock(){
  generation++;active?.abort();active=null;token='';latest=null;request=null;review=null;pending=null;submitted=false;busy=false;dynamic=[];
  el('token').value='';el('lock').disabled=true;el('token').required=true;
  if(el('confirm').open)el('confirm').close();
  for(const id of [...fields,'plan-id','plan-symbol','plan-budget','plan-stop','plan-target','plan-dates','plan-reference'])el(id).value='';
  fields.forEach(id=>{el(id).readOnly=false;});
  for(const id of ['cash','reserved'])el(id).textContent='—';
  for(const id of ['plans','lots','orders','holdings'])el(id).replaceChildren(node('p','Locked'));
  for(const id of ['details','risk','updated','state'])el(id).textContent='Locked';
  el('intent').textContent='';el('lots-count').textContent='';el('orders-count').textContent='';clearPreview();msg('Locked. No private account data loaded.');buttons();
 }
 async function call(path,method,body,signal){
  const r=await fetcher(base+path,{method,signal,cache:'no-store',credentials:'omit',redirect:'error',headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});
  if(!r.ok){const data=await r.json();const detail=Array.isArray(data.detail)?data.detail.map(d=>d.loc.slice(1).join('.')+': '+d.msg).join('; '):data.detail;const error=Error(r.status===401||r.status===403?'Authorization failed. Unlock again.':detail||'Request failed');error.authorization=r.status===401||r.status===403;error.status=r.status;throw error;}
  return r.json();
 }
 async function operation(path,body,success){
  if(!token||busy)return;
  const version=++generation;active?.abort();const controller=new AbortController();active=controller;busy=true;buttons();
  const timeout=win.setTimeout(()=>controller.abort(),10000);
  try{const data=await call(path,body?'POST':'GET',body,controller.signal);if(version===generation)success(data);}
  catch(error){if(version!==generation)return;if(error.authorization){lock();msg(error.message,true);}else{if(path==='/contributions'&&[409,422].includes(error.status))submitted=false;lastReceipt=0;clearPreview();msg(error.name==='AbortError'?'Outcome unknown after timeout. Refresh to inspect this intent before any new purchase; no automatic retry.':String(error.message),true);}}
  finally{win.clearTimeout(timeout);if(version===generation){busy=false;active=null;buttons();}}
 }
 function rows(id,items,empty,render){el(id).replaceChildren();if(!items.length)el(id).append(node('p',empty));for(const item of items){const row=doc.createElement('article');row.className='record';render(row,item);el(id).append(row);}}
 function render(data){
  if(data.schema_version!==1||data.account.investment_horizon!=='long_term')throw Error('Manual long-term account required');
  latest=data;lastReceipt=win.Date.now();dynamic=[];
  el('state').textContent='Long-term paper · refreshed';el('cash').textContent=money(data.account.available_cash);el('reserved').textContent=money(data.account.reserved_cash);
  el('risk').textContent=(data.account.kill?'Kill active · ':'')+(data.account.feed_connected?'Feed connected':'Feed offline')+' · '+(data.account.valuation_fresh?'Valuation fresh or flat':'Valuation stale');
  el('updated').textContent='Observed '+new Date(data.observed_at).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})+' IST';
  rows('plans',data.plans,'No SIP plans. Save explicitly reviewed dates below to begin.',(row,item)=>{
   const p=item.plan;row.append(node('strong',p.symbol+' · '+p.plan_id+' · '+(item.cancelled?'Cancelled':'Manual confirmation required')));
   row.append(node('p','Cash cap per occurrence '+money(p.budget)+' · '+p.reference));
   const summary=Object.entries(item.occurrences.reduce((a,o)=>{a[o.status]=(a[o.status]||0)+1;return a;},{})).map(([k,n])=>n+' '+k.toLowerCase()).join(' · ');row.append(node('p',summary));
   for(const occurrence of item.occurrences.filter(o=>o.status==='DUE')){
    const button=node('button','Preview due '+occurrence.session);button.type='button';dynamic.push(button);
    button.addEventListener('click',()=>{if(!fresh()||busy)return;request=occurrence.request;submitted=false;fields.forEach(id=>{el(id).value=request[id]||'';el(id).readOnly=true;});getPreview();});row.append(button);
   }
   if(!item.cancelled){const button=node('button','Cancel plan and pending buys');button.type='button';button.className='quiet';dynamic.push(button);button.addEventListener('click',()=>confirm('/plans/cancel',{plan_id:p.plan_id,reference:'operator confirmed cancellation'},'Cancel '+p.plan_id+'?','Future occurrences and pending plan buys will be cancelled. Existing filled shares remain held with their protections.'));row.append(button);}
  });
  el('orders-count').textContent=data.orders_truncated?'Latest 100 contribution intents shown':data.orders.length+' contribution intents';
  rows('orders',data.orders,'No contribution intents yet.',(row,o)=>{row.append(node('strong',o.symbol+' · '+o.state+' · '+o.filled+' / '+o.quantity+' filled'));row.append(node('p',o.id));row.append(node('p','Actual debit '+money(o.actual_debit)+' · reserved remainder '+money(o.reserved_cash)+(o.reason?' · '+o.reason:'')));});
  rows('holdings',data.account.positions||[],'Flat · no current holdings',(row,p)=>{row.append(node('strong',p.symbol+' · '+p.quantity+' current shares'));row.append(node('p','Current pooled basis '+money(p.cost)+' · estimated unrealized P&L '+money(p.unrealized_pnl)));row.append(node('p','Stop '+money(p.stop)+' · target '+money(p.target)));});
  el('lots-count').textContent=data.lots_truncated?'Latest 100 acquisition lots shown; older purchases remain in the ledger.':data.lots.length+' filled acquisition lots';
  rows('lots',data.lots,'No filled purchases yet. Accepted orders appear here only after actual quote-driven fills.',(row,lot)=>{row.append(node('strong',lot.symbol+' · '+lot.original_quantity+' original shares'));row.append(node('p','Original debit '+money(lot.original_cost)+' · buy fees '+money(lot.fees)));row.append(node('p',lot.lot_id+' · '+lot.order_state+(lot.plan_id?' · SIP '+lot.plan_id:'')));});
  el('details').textContent=JSON.stringify(data,null,2);msg('Account refreshed. Choose a due occurrence or preview a purchase.');buttons();
 }
 const refresh=()=>operation('',null,render);
 function getPreview(){
  if(!fresh()||submitted){msg('Refresh before reviewing. Use Start a different purchase only for a new instruction.',true);return;}
  clearPreview();el('intent').textContent='Purchase intent: '+request.intent_id;
  operation('/preview',request,data=>{
   review=data;el('preview').hidden=false;el('preview-reasons').replaceChildren();
   const d=data.decision;
   el('preview-summary').textContent=d.allowed?d.quantity+' shares · maximum debit '+money(d.cash_reservation)+' · cap per share '+money(d.price_cap)+' · planned stop risk '+money(d.risk_reservation)+' · '+(data.holding?'Existing stop/target retained':'New holding protections')+' · stop '+money(data.candidate.stop)+' / target '+money(data.candidate.target):'Purchase blocked. No order or cash reservation was created.';
   for(const reason of d.reasons)el('preview-reasons').append(node('li',reason.toLowerCase().replaceAll('_',' ')));
   msg(d.allowed?'Inspect the preview, then explicitly confirm.':'Resolve the listed conditions and calculate another preview.',!d.allowed);buttons();
  });
 }
 function confirm(path,body,title,text){if(!fresh()||busy)return;pending={path,body};el('confirm-title').textContent=title;el('confirm-text').textContent=text;el('confirm').showModal();el('cancel-confirm').focus();}
 el('access').addEventListener('submit',event=>{event.preventDefault();const supplied=el('token').value;if(supplied){lock();token=supplied;el('lock').disabled=false;el('token').required=false;}refresh();});
 el('lock').addEventListener('click',lock);
 el('purchase').addEventListener('submit',event=>{event.preventDefault();if(!request){request={intent_id:'contrib-'+win.crypto.randomUUID(),symbol:el('symbol').value.trim(),budget:el('budget').value.trim(),reference:el('reference').value.trim()};if(el('stop').value.trim()||el('target').value.trim()){request.stop=el('stop').value.trim();request.target=el('target').value.trim();}}getPreview();});
 for(const id of fields)el(id).addEventListener('input',()=>{clearPreview();if(!submitted){request=null;el('intent').textContent='';}});
 el('new-purchase').addEventListener('click',()=>{request=null;submitted=false;clearPreview();fields.forEach(id=>{el(id).value='';el(id).readOnly=false;});el('intent').textContent='';el('symbol').focus();});
 el('submit-purchase').addEventListener('click',()=>{if(review?.decision.allowed&&!submitted)confirm('/contributions',{request,preview_sha256:review.preview_sha256},'Confirm '+review.decision.quantity+' virtual shares of '+request.symbol+'?','Maximum cash debit including buy fees '+money(review.decision.cash_reservation)+'. Fresh later quotes and depth determine fills. This reserves existing virtual cash and preserves existing holding protections.');});
 el('plan-form').addEventListener('submit',event=>{event.preventDefault();const body={plan_id:el('plan-id').value.trim(),symbol:el('plan-symbol').value.trim(),budget:el('plan-budget').value.trim(),stop_pct:el('plan-stop').value.trim(),target_pct:el('plan-target').value.trim(),sessions:el('plan-dates').value.split(',').map(s=>s.trim()),reference:el('plan-reference').value.trim()};confirm('/plans',body,'Save reviewed SIP plan '+body.plan_id+'?','Cash cap '+money(body.budget)+' per date. Each listed exchange session requires a separate preview and confirmation. Missed dates stay missed.');});
 el('cancel-confirm').addEventListener('click',()=>{pending=null;el('confirm').close();});
 el('confirm').addEventListener('cancel',()=>{pending=null;});
 el('confirm-action').addEventListener('click',()=>{const action=pending;pending=null;el('confirm').close();if(!action||!fresh()||busy){msg('Refresh and review again before confirming.',true);return;}if(action.path==='/contributions')submitted=true;clearPreview();operation(action.path,action.body,data=>{msg(action.path==='/contributions'?'Paper order '+data.id+' · '+data.state+'. Inspect order fills; no automatic retry.':'Plan updated. Refresh the account to inspect its state.');});});
 doc.addEventListener('visibilitychange',()=>{if(!doc.hidden&&!busy)refresh();});
 win.setInterval(()=>{if(token&&!doc.hidden&&!busy&&!el('confirm').open)refresh();},3000);
 win.setInterval(()=>{if(token&&latest&&!fresh()){el('state').textContent='Display stale · refresh required';buttons();}},1000);
 lock();return {refresh,lock};
}
if(typeof module!=='undefined'&&module.exports)module.exports={createPortfolio};
if(typeof document!=='undefined')createPortfolio(document,window,window.fetch.bind(window));
})();
