'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {createHash}=require('node:crypto');
const {createPolicyDrafts}=require('../../src/trading_agent/api/static/investment-policy.js');
class Element {
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.events={};this.children=[];this.attributes={};this.style={};this.value='';this.disabled=false;this.open=false;this.isConnected=true;}
 set textContent(value){this.text=String(value);this.children=[];}
 get textContent(){return(this.text||'')+this.children.map(child=>child.textContent).join('');}
 set innerHTML(_){throw Error('Unsafe HTML sink');}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.text='';this.children=children;}
 setAttribute(name,value){this.attributes[name]=String(value);}
 addEventListener(type,handler){(this.events[type]||=[]).push(handler);}
 removeEventListener(type,handler){this.events[type]=(this.events[type]||[]).filter(h=>h!==handler);}
 fire(type){if(!this.disabled)for(const handler of [...this.events[type]||[]])handler({preventDefault(){}});}
 focus(){this.focused=true;}
 showModal(){this.open=true;}
 close(){this.open=false;this.fire('close');}
}
const flush=async()=>{await new Promise(resolve=>setImmediate(resolve));await new Promise(resolve=>setImmediate(resolve));};
const ok=data=>({ok:true,status:200,json:async()=>data});
const definitions=[
 {name:'horizon_unit',label:'Horizon unit',group:'Horizon and reviews',kind:'choice',choices:[{value:'months',label:'Months'},{value:'years',label:'Years'}]},
 {name:'horizon_count',label:'Horizon count',group:'Horizon and reviews',kind:'integer',minimum:1,maximum:1200,unit:'selected horizon units'},
 {name:'review_cadence',label:'Review cadence',group:'Horizon and reviews',kind:'choice',choices:[{value:'monthly',label:'Monthly'},{value:'quarterly',label:'Quarterly'}]},
 {name:'min_average_turnover',label:'Minimum turnover',group:'Screening',kind:'decimal',minimum:'0',maximum:'1000000000000',scale:2,unit:'INR'},
 {name:'max_invested_pct',label:'Invested cap',group:'Allocation',kind:'decimal',minimum:'0',maximum:'100',scale:4,unit:'%'},
 {name:'cash_reserve_pct',label:'Cash reserve',group:'Allocation',kind:'decimal',minimum:'0',maximum:'100',scale:4,unit:'%'},
 {name:'max_sector_weight_pct',label:'Sector cap',group:'Allocation',kind:'decimal',minimum:'0',maximum:'100',scale:4,unit:'%'},
 {name:'stop_loss_pct',label:'Stop loss',group:'Execution and exits',kind:'decimal',minimum:'0',maximum:'100',scale:4,unit:'%',exclusive_minimum:true,exclusive_maximum:true},
 {name:'max_stock_weight_pct',label:'Stock cap',group:'Allocation',kind:'decimal',minimum:'0',maximum:'100',scale:4,unit:'%'},
];
function preview(input){const parameters=Object.fromEntries(definitions.map(f=>[f.name,input.parameters?.[f.name]??null]));const draft={schema_version:1,family:'nse-investment-policy-v2',decision_semantics:'investment-decisions-v2.1',label:input.label||null,parameters,state:'incomplete',missing_fields:Object.keys(parameters).filter(key=>parameters[key]===null),draft_sha256:'a'.repeat(64),policy_version_id:null,activation_supported:false,backtest_supported:false};return {schema_version:1,draft,preview_sha256:createHash('sha256').update(JSON.stringify(draft)).digest('hex')};}
function setup(custom){
 const html=readFileSync('src/trading_agent/api/static/investment-policy.html','utf8');const nodes=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const calls=[],events={},timers=new Map();let timer=0,stored=[];
 const win={innerWidth:1000,innerHeight:700,setTimeout:(handler,ms)=>{timers.set(++timer,{handler,ms});return timer;},clearTimeout:id=>timers.delete(id),addEventListener:(type,handler)=>{(events[type]||=[]).push(handler);},removeEventListener:(type,handler)=>{events[type]=(events[type]||[]).filter(h=>h!==handler);}};
 const doc={activeElement:null,getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:tag=>new Element(tag)};
 const base=(url,options)=>{if(options.method==='GET')return ok({schema_version:1,field_definitions:definitions,drafts:stored,limitations:['Research only']});const body=JSON.parse(options.body);const data=preview(body.draft);if(url.endsWith('/preview'))return ok(data);const draft={draft_id:'draft-'+data.preview_sha256,...data.draft};stored=[draft];return ok({schema_version:1,draft});};
 const view=createPolicyDrafts(doc,win,async(url,options)=>{calls.push({url,options});return custom?custom(url,options,base):base(url,options);});
 const descendants=element=>[element,...element.children.flatMap(descendants)];
 const input=name=>descendants(nodes['policy-fields']).find(element=>element.id==='policy-'+name);
 const change=(name,value)=>{input(name).value=value;input(name).fire('input');};
 async function unlock(){nodes.token.value='invented-operator-token-123456789012345';nodes.access.fire('submit');await flush();}
 async function review(){nodes.review.fire('click');await flush();}
 async function confirm(){nodes.ack.checked=true;nodes.ack.fire('change');nodes.save.fire('click');await flush();}
 const saves=()=>calls.filter(c=>c.url==='/api/investment-policies'&&c.options.method==='POST');
 return {nodes,calls,events,win,doc,view,input,change,unlock,review,confirm,saves,timers,setStored:value=>{stored=value;}};
}
test('draft screen is locked until memory-token handoff and only reads metadata; all choices start unresolved',async()=>{
 const s=setup();assert.equal(s.calls.length,0);assert.equal(s.nodes.main.hidden,true);await s.unlock();assert.equal(s.calls.length,1);assert.equal(s.calls[0].url,'/api/investment-policies');assert.equal(s.calls[0].options.method,'GET');assert.equal(s.calls[0].options.credentials,'omit');assert.equal(s.calls[0].options.cache,'no-store');assert.equal(s.calls[0].options.redirect,'error');assert.match(s.calls[0].options.headers.Authorization,/Bearer invented-/);assert.equal(s.nodes.token.value,'');assert.equal(s.nodes.main.hidden,false);assert.equal(s.view.canNavigate(),true);for(const field of definitions)assert.equal(s.input(field.name).value,'');assert.equal(s.saves().length,0);
});
test('generated controls retain labels, help, units and separate groups without HTML interpretation',async()=>{
 const s=setup();await s.unlock();const groups=s.nodes['policy-fields'].children;assert.equal(groups.length,4);for(const group of groups){assert.equal(group.tagName,'FIELDSET');assert.equal(group.children[0].tagName,'LEGEND');for(const field of group.children.filter(child=>child.className==='policy-field')){const [label,input,help]=field.children;assert.equal(label.attributes.for,input.id);assert.equal(input.attributes['aria-describedby'],help.id);}}
 assert.equal(s.input('min_average_turnover').type,'text');assert.equal(s.input('min_average_turnover').attributes.inputmode,'decimal');assert.equal(s.input('horizon_count').type,'number');
});
test('unsaved changes guard navigation; read refresh preserves form and discard restores blank planning state',async()=>{
 const s=setup();await s.unlock();s.change('horizon_unit','years');s.change('horizon_count','5');s.change('review_cadence','quarterly');assert.equal(s.view.canNavigate(),false);assert.match(s.nodes['editing-state'].textContent,/Unsaved/);await s.view.refresh();assert.equal(s.input('horizon_count').value,'5');assert.equal(s.saves().length,0);s.nodes.discard.fire('click');assert.equal(s.view.canNavigate(),true);for(const field of definitions)assert.equal(s.input(field.name).value,'');
});
test('preview submits exact strings and unresolved nulls; dialog acknowledgement starts unchecked and Cancel or Escape never saves',async()=>{
 const s=setup();await s.unlock();s.change('horizon_unit','months');s.change('horizon_count','12');s.change('min_average_turnover','999999999999.99');s.nodes['policy-label'].value='<script>research</script>';s.nodes['policy-label'].fire('input');await s.review();const body=JSON.parse(s.calls.at(-1).options.body);assert.equal(body.draft.parameters.min_average_turnover,'999999999999.99');assert.equal(body.draft.parameters.horizon_count,12);assert.equal(body.draft.parameters.review_cadence,null);assert.match(s.nodes['confirm-rows'].textContent,/<script>research/);assert.match(s.nodes['confirm-rows'].textContent,/Unresolved/);assert.equal(s.nodes.confirm.open,true);assert.equal(s.nodes.ack.checked,false);assert.equal(s.nodes.save.disabled,true);s.nodes.save.fire('click');assert.equal(s.saves().length,0);s.nodes.cancel.fire('click');assert.equal(s.nodes.confirm.open,false);assert.equal(s.saves().length,0);await s.review();s.nodes.confirm.fire('cancel');assert.equal(s.nodes.confirm.open,false);assert.equal(s.saves().length,0);
});
test('confirmed save sends one reviewed immutable snapshot and never installs or arms an account',async()=>{
 let finish;const s=setup((url,options,base)=>url==='/api/investment-policies'&&options.method==='POST'?new Promise(resolve=>{finish=()=>resolve(base(url,options));}):base(url,options));await s.unlock();s.change('horizon_count','12');await s.review();s.input('horizon_count').value='24';s.nodes.ack.checked=true;s.nodes.ack.fire('change');s.nodes.save.fire('click');s.nodes.save.fire('click');await flush();assert.equal(s.saves().length,1);const body=JSON.parse(s.saves()[0].options.body);assert.equal(body.draft.parameters.horizon_count,12);assert.equal(body.acknowledged,true);assert.match(body.preview_sha256,/^[a-f0-9]{64}$/);assert.equal(s.view.canNavigate(),false);finish();await flush();assert.match(s.nodes['save-state'].textContent,/installed strategy and mode are unchanged/);assert.equal(s.view.canNavigate(),true);assert.ok(s.calls.every(c=>c.url.startsWith('/api/investment-policies')));
});
test('unknown save waits for a fresh saved list and explicit retry uses identical reviewed content',async()=>{
 let fail=true;const s=setup((url,options,base)=>{if(url==='/api/investment-policies'&&options.method==='POST'&&fail){fail=false;throw Error('lost response');}return base(url,options);});await s.unlock();s.change('review_cadence','monthly');await s.review();await s.confirm();assert.equal(s.saves().length,1);assert.match(s.nodes['save-state'].textContent,/outcome unknown/);assert.equal(s.nodes.retry.disabled,true);assert.equal(s.nodes.review.disabled,true);await s.view.refresh();assert.equal(s.nodes.retry.disabled,false);s.nodes.retry.fire('click');assert.equal(s.nodes.ack.checked,false);await s.confirm();assert.equal(s.saves().length,2);assert.equal(s.saves()[0].options.body,s.saves()[1].options.body);assert.equal(s.view.canNavigate(),true);
});
test('read reconciliation finds an already recorded uncertain save without issuing another save',async()=>{
 const s=setup((url,options,base)=>{if(url==='/api/investment-policies'&&options.method==='POST'){base(url,options);throw Error('lost response after persistence');}return base(url,options);});await s.unlock();s.change('horizon_count','3');await s.review();await s.confirm();await s.view.refresh();assert.equal(s.saves().length,1);assert.match(s.nodes['save-state'].textContent,/previous save was recorded/);assert.equal(s.nodes.retry.hidden,true);assert.equal(s.view.canNavigate(),true);
});
test('editing a saved copy preserves its original snapshot and blocks navigation until save/discard',async()=>{
 const s=setup();await s.unlock();s.change('horizon_count','3');await s.review();await s.confirm();const before=s.nodes['saved-drafts'].textContent;const copy=s.nodes['saved-drafts'].children[0].children.find(c=>c.tagName==='BUTTON');copy.fire('click');assert.equal(s.input('horizon_count').value,'3');assert.match(s.nodes['save-state'].textContent,/Editing a copy/);s.change('horizon_count','4');assert.equal(s.nodes['saved-drafts'].textContent,before);assert.equal(s.view.canNavigate(),false);s.nodes.discard.fire('click');assert.equal(s.view.canNavigate(),true);
});
test('integer errors and server validation failures never save; explicit rejection requires another review',async()=>{
 const bad=setup();await bad.unlock();bad.change('horizon_count','1.5');await bad.review();assert.equal(bad.calls.length,1);assert.equal(bad.saves().length,0);assert.match(bad.nodes.message.textContent,/could not be reviewed/);
 const s=setup((url,options,base)=>url==='/api/investment-policies'&&options.method==='POST'?{ok:false,status:409}:base(url,options));await s.unlock();await s.review();await s.confirm();assert.equal(s.saves().length,1);assert.match(s.nodes['save-state'].textContent,/server rejected/);assert.equal(s.nodes.retry.hidden,true);assert.equal(s.nodes.review.disabled,false);
});
test('pagehide and authorization failure clear fields, saved content, pending confirmation and late responses',async()=>{
 let finish;const s=setup((url,options,base)=>url.endsWith('/preview')?{ok:true,status:200,json:()=>new Promise(resolve=>{finish=resolve;})}:base(url,options));await s.unlock();s.change('horizon_count','5');s.nodes.review.fire('click');await flush();const signal=s.calls.at(-1).options.signal;for(const handler of [...s.events.pagehide])handler();assert.equal(signal.aborted,true);finish(preview({label:'private',parameters:{horizon_count:5}}));await flush();assert.equal(s.nodes.main.hidden,true);for(const id of ['policy-fields','saved-drafts','confirm-rows','confirm-identity'])assert.equal(s.nodes[id].textContent,'');assert.equal(s.nodes.confirm.open,false);assert.equal(s.saves().length,0);assert.equal(s.timers.size,0);
 const a=setup(()=>({ok:false,status:401}));await a.unlock();assert.equal(a.nodes.main.hidden,true);assert.match(a.nodes.message.textContent,/authorization failed/);
});
test('saved-data failures preserve edits with stale status and no implicit retry',async()=>{
 let fail=false;const s=setup((url,options,base)=>fail?{ok:false,status:503}:base(url,options));await s.unlock();s.change('horizon_count','8');fail=true;await s.view.refresh();assert.equal(s.input('horizon_count').value,'8');assert.match(s.nodes.state.textContent,/stale/);assert.equal(s.saves().length,0);assert.equal(s.view.canNavigate(),false);
});

test('malformed preview cannot leave an invisible pending review or trap navigation',async()=>{
 const s=setup((url,options,base)=>url.endsWith('/preview')?ok({schema_version:1,draft:{parameters:{}},preview_sha256:'a'.repeat(64)}):base(url,options));await s.unlock();await s.review();assert.equal(s.nodes.confirm.open,false);assert.equal(s.nodes.review.disabled,false);assert.equal(s.nodes.refresh.disabled,false);assert.equal(s.nodes.discard.disabled,false);assert.equal(s.view.canNavigate(),true);assert.equal(s.saves().length,0);assert.match(s.nodes.message.textContent,/could not be reviewed/);
});
test('browser unload guards unsaved choices and pending review; discard and lock remove the guard',async()=>{
 const s=setup();await s.unlock();let prevented=0;const event=()=>({preventDefault(){prevented++;},returnValue:null});let e=event();for(const h of s.events.beforeunload)h(e);assert.equal(prevented,0);s.change('horizon_count','6');e=event();for(const h of s.events.beforeunload)h(e);assert.equal(e.returnValue,'');assert.equal(prevented,1);s.nodes.discard.fire('click');e=event();for(const h of s.events.beforeunload)h(e);assert.equal(prevented,1);await s.review();e=event();for(const h of s.events.beforeunload)h(e);assert.equal(prevented,2);s.view.lock();e=event();for(const h of s.events.beforeunload)h(e);assert.equal(prevented,2);
});

test('four step navigation retains blank or entered values without a request, save or default',async()=>{
 const s=setup();await s.unlock();const groups=s.nodes['policy-fields'].children,steps=s.nodes['policy-steps'].children;
 assert.equal(steps.length,4);assert.equal(groups[0].hidden,false);assert.ok(groups.slice(1).every(g=>g.hidden));assert.equal(steps[0].attributes['aria-current'],'step');assert.equal(s.nodes['previous-step'].disabled,true);
 s.change('horizon_count','12');s.nodes['next-step'].fire('click');assert.equal(groups[0].hidden,true);assert.equal(groups[1].hidden,false);assert.equal(groups[1].focused,true);assert.equal(steps[1].attributes['aria-current'],'step');assert.equal(steps[0].attributes['aria-current'],'false');
 steps[3].fire('click');assert.equal(groups[3].hidden,false);assert.equal(s.nodes['next-step'].disabled,true);s.nodes['previous-step'].fire('click');assert.equal(groups[2].hidden,false);steps[0].fire('click');assert.equal(s.input('horizon_count').value,'12');assert.match(s.nodes['policy-progress'].textContent,/1 of 9 choices entered/);assert.equal(s.calls.length,1);assert.equal(s.saves().length,0);assert.equal(s.view.canNavigate(),false);
 s.nodes.discard.fire('click');assert.equal(groups[0].hidden,false);assert.match(s.nodes['policy-progress'].textContent,/0 of 9/);assert.equal(s.view.canNavigate(),true);
});
test('years bounds follow the chosen unit without converting values and invalid review focuses its group',async()=>{
 const s=setup();await s.unlock();s.change('horizon_count','101');s.change('horizon_unit','years');assert.equal(s.input('horizon_count').max,100);assert.equal(s.input('horizon_count').value,'101');s.nodes['policy-steps'].children[3].fire('click');await s.review();assert.equal(s.calls.length,1);assert.equal(s.nodes['policy-fields'].children[0].hidden,false);assert.equal(s.input('horizon_count').focused,true);assert.equal(s.input('horizon_count').attributes['aria-invalid'],'true');assert.match(s.input('horizon_count').attributes['aria-describedby'],/error/);assert.match(s.nodes['policy-errors'].textContent,/1 entered choice/);
 s.change('horizon_unit','months');assert.equal(s.input('horizon_count').max,1200);assert.equal(s.input('horizon_count').value,'101');assert.equal(s.input('horizon_count').attributes['aria-invalid'],'false');await s.review();assert.equal(s.nodes.confirm.open,true);assert.equal(JSON.parse(s.calls.at(-1).options.body).draft.parameters.horizon_count,101);assert.equal(s.saves().length,0);
});
test('exact cross-field validation detects a one ten-thousandth percent violation without binary rounding',async()=>{
 const s=setup();await s.unlock();s.change('max_invested_pct','80.0001');s.change('cash_reserve_pct','20');s.change('max_sector_weight_pct','15');s.change('max_stock_weight_pct','15.0001');await s.review();assert.equal(s.calls.length,1);assert.equal(s.input('max_invested_pct').attributes['aria-invalid'],'true');assert.equal(s.input('cash_reserve_pct').attributes['aria-invalid'],'true');assert.equal(s.input('max_stock_weight_pct').attributes['aria-invalid'],'true');assert.equal(s.nodes['policy-fields'].children[2].hidden,false);
 s.change('max_invested_pct','80.0000');s.change('max_stock_weight_pct','15');await s.review();assert.equal(s.nodes.confirm.open,true);assert.equal(s.nodes.message.className,'');assert.match(s.nodes.message.textContent,/preview loaded/);const body=JSON.parse(s.calls.at(-1).options.body);assert.equal(body.draft.parameters.max_invested_pct,'80.0000');assert.equal(body.draft.parameters.cash_reserve_pct,'20');assert.equal(s.saves().length,0);
});
test('decimal precision, non-finite values and exclusive bounds stay invalid until corrected or unresolved',async()=>{
 const s=setup();await s.unlock();for(const value of ['0','100','NaN','Infinity','1.00001']){s.change('stop_loss_pct',value);await s.review();assert.equal(s.calls.length,1);assert.equal(s.input('stop_loss_pct').attributes['aria-invalid'],'true');assert.equal(s.nodes['policy-fields'].children[3].hidden,false);}
 s.change('stop_loss_pct','');s.change('min_average_turnover','999999999999.991');await s.review();assert.equal(s.calls.length,1);assert.equal(s.input('min_average_turnover').attributes['aria-invalid'],'true');s.change('min_average_turnover','9.9999999999999e11');await s.review();assert.equal(s.nodes.confirm.open,true);assert.equal(JSON.parse(s.calls.at(-1).options.body).draft.parameters.min_average_turnover,'9.9999999999999e11');assert.equal(s.saves().length,0);
});
test('saved policy details use labelled exact choices and lock clears step progress and private errors',async()=>{
 const s=setup();await s.unlock();s.change('horizon_count','7');await s.review();await s.confirm();assert.match(s.nodes['saved-drafts'].textContent,/Exact saved policy choices/);assert.match(s.nodes['saved-drafts'].textContent,/Horizon count7/);assert.doesNotMatch(s.nodes['saved-drafts'].textContent,/horizon_count/);s.nodes['policy-steps'].children[2].fire('click');s.view.lock();for(const id of ['policy-steps','policy-progress','policy-errors','saved-drafts'])assert.equal(s.nodes[id].textContent,'');assert.equal(s.nodes['policy-errors'].hidden,true);
});
