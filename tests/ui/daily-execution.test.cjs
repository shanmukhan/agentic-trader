'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const root='src/trading_agent/daily_execution/static/';
class Element{
 constructor(){this.children=[];this.listeners={};this.value='';}
 set textContent(v){this.text=String(v);this.children=[];}
 get textContent(){return (this.text||'')+this.children.map(n=>n.textContent).join('');}
 set innerHTML(_){throw Error('unsafe HTML');}
 append(...c){this.children.push(...c);}
 replaceChildren(...c){this.text='';this.children=c;}
 addEventListener(n,f){this.listeners[n]=f;}
 fire(n){this.listeners[n]?.();}
 focus(){this.focused=true;}
}
const metrics={net_observed_pnl:'9007199254740993.12',completed_trades:0,pending_orders:1,unpaid_claims:1,income_received:'126.00'};
const base={kind:'daily-delivery-replay-v1',synthetic:true,status:'incomplete',first_event:'2025-01-01T04:30:00Z',source_available_through:'2025-01-02T04:30:00Z',metrics,final_snapshot:{fees:'42.11',positions:[{}],valuation_fresh:false},gates:{held_quote_coverage:false},trades:[],decisions:[{time:'2025-01-01T04:30:00Z',symbol:'NSE:TEST',reasons:['DAILY_ENTRY_GAP'],order_state:'REJECTED'}],label_counts:{LABELED:2,SOURCE_ENDED:3},limitations:['<img onerror=attack()>'],strategy:{},risk_policy:{}};
function setup(overrides={}){
 const nodes=Object.fromEntries([...readFileSync(root+'report.html','utf8').matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 nodes.data.textContent=JSON.stringify({...base,...overrides});nodes.view.value='trades';
 const document={getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:()=>new Element()};
 const context={document};vm.runInNewContext(readFileSync(root+'report.js','utf8'),context);
 return {nodes,context};
}
test('execution dashboard preserves exact money and makes unresolved exposure clear',()=>{
 const {nodes:n}=setup();assert.equal(n['value-one'].textContent,'₹9,00,71,99,25,47,40,993.12');
 assert.match(n['next-step'].textContent,/incomplete/);assert.match(n.exposure.textContent,/Open positions: 1/);
 assert.match(n.exposure.textContent,/stale/);assert.match(n.provenance.textContent,/Invented/);
 assert.match(n.empty.textContent,/No completed trades/);assert.match(n.limits.textContent,/<img onerror/);
});
test('labels dashboard never treats observer cash or independent P&L as portfolio returns',()=>{
 const {nodes:n}=setup({kind:'daily-delivery-labels-v1'});
 assert.equal(n['value-one'].textContent,'2');assert.equal(n['value-two'].textContent,'3');
 assert.equal(n['value-three'].textContent,'Not measured');assert.match(n.meaning.textContent,/counterfactual/);
});
test('decision view is searchable, has a useful empty state and clear restores focus',()=>{
 const {nodes:n}=setup();n.view.value='decisions';n.view.fire('input');
 assert.match(n.rows.textContent,/daily entry gap/);assert.match(n.rows.textContent,/REJECTED/);
 n.search.value='missing';n.search.fire('input');assert.equal(n.empty.hidden,false);
 n.clear.fire('click');assert.equal(n.rows.children.length,1);assert.ok(n.search.focused);
});
test('validation dashboard distinguishes failed model gates and labels selected net P&L',()=>{
 const m={count:12,roc_auc:0.5,brier:0.25,expected_calibration_error:0.3,selected_count:4,selected_net_pnl:'-15.25',passed:false,gates:{calibration:false}};
 const {nodes:n}=setup({kind:'daily-delivery-validation-v1',gates:{walk_forward:true,holdout:false},splits:[{name:'holdout',evaluation_first:base.first_event,evaluation_last:base.source_available_through,metrics:m}]});
 assert.equal(n['value-one'].textContent,'Failed');assert.match(n['next-step'].textContent,/blocked/);
 assert.match(n['note-three'].textContent,/not portfolio/);assert.match(n.rows.textContent,/-₹15.25/);
 assert.match(n.rows.textContent,/Failed: calibration/);
});
test('dashboard bounds large evidence tables and discloses full artifact access',()=>{
 const {nodes:n}=setup({decisions:Array.from({length:205},()=>base.decisions[0])});
 n.view.value='decisions';n.view.fire('input');assert.equal(n.rows.children.length,200);
 assert.match(n['result-count'].textContent,/200 of 205/);assert.match(n['result-count'].textContent,/JSON/);
});
test('money formatter retains exponents and avoids non-finite values',()=>{
 const {context:c}=setup();assert.equal(c.formatMoney('1e-2'),'₹0.01');
 assert.equal(c.formatMoney('NaN'),'—');assert.equal(c.formatMoney('1E+1001'),'₹1E+1001');
});
