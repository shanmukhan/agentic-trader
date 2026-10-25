'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),{readFileSync}=require('node:fs');
const {createPortfolio}=require('../../src/trading_agent/api/static/portfolio.js');
class Element{
 constructor(){this.children=[];this.listeners={};this.value='';this.open=false;}
 set textContent(v){this.text=String(v);this.children=[];}
 get textContent(){return (this.text||'')+this.children.map(n=>n.textContent).join('');}
 set innerHTML(_){throw Error('unsafe HTML sink');}
 append(...n){this.children.push(...n);}replaceChildren(...n){this.text='';this.children=n;}
 addEventListener(n,f){(this.listeners[n]||=[]).push(f);}fire(n){if(this.disabled)return;for(const f of this.listeners[n]||[])f({preventDefault(){}});}
 showModal(){this.open=true;}close(){this.open=false;}focus(){this.focused=true;}
}
const data=()=>({schema_version:1,observed_at:'2026-10-20T04:30:00Z',account:{investment_horizon:'long_term',available_cash:'9007199254740993.12',reserved_cash:'0',kill:false,feed_connected:true,valuation_fresh:true},plans:[],lots:[],orders:[]});
const ok=value=>({ok:true,status:200,json:async()=>value}),flush=()=>new Promise(resolve=>setImmediate(resolve));
const proposal={preview_sha256:'a'.repeat(64),decision:{allowed:true,quantity:2,cash_reservation:'1001.80',price_cap:'500.35',risk_reservation:'42.10',reasons:[]},candidate:{stop:'490',target:'600'},holding:{}};
function setup(fetcher=async()=>ok(data())){
 const nodes=Object.fromEntries([...readFileSync('src/trading_agent/api/static/portfolio.html','utf8').matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const calls=[],intervals=[],timeouts=[];let now=1000;
 const doc={getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:()=>new Element(),addEventListener(){},hidden:false};
 const win={Date:{now:()=>now},crypto:{randomUUID:()=> 'fixed-test-id'},setTimeout:f=>{timeouts.push(f);return timeouts.length;},clearTimeout(){},setInterval:f=>intervals.push(f)};
 const instance=createPortfolio(doc,win,async(url,options)=>{calls.push({url,options});return fetcher(url,options);});
 async function unlock(){nodes.token.value='ephemeral-portfolio-test-token';nodes.access.fire('submit');await flush();}
 async function preview(){for(const [id,value]of Object.entries({symbol:'NSE:DEMO',budget:'2000',reference:'reviewed test'}))nodes[id].value=value;nodes.purchase.fire('submit');await flush();}
 return {nodes,calls,intervals,timeouts,instance,unlock,preview,advance:ms=>{now+=ms;}};
}
test('portfolio locks private forms, large exact money and late responses safely',async()=>{
 let resolve;const s=setup(()=>new Promise(done=>{resolve=done;}));assert.equal(s.calls.length,0);await s.unlock();s.nodes.lock.fire('click');resolve(ok(data()));await flush();
 assert.equal(s.nodes.cash.textContent,'—');assert.equal(s.nodes.details.textContent,'Locked');assert.equal(s.nodes.symbol.value,'');assert.ok(s.calls[0].options.signal.aborted);
});
test('portfolio renders text safely and discloses original lot basis and empty orders',async()=>{
 const d=data();d.lots=[{symbol:'<script>attack()</script>',original_quantity:2,original_cost:'1001.80',fees:'1.10',lot_id:'id',order_state:'FILLED'}];
 const s=setup(async()=>ok(d));await s.unlock();assert.equal(s.nodes.cash.textContent,'₹9,00,71,99,25,47,40,993.12');assert.match(s.nodes.lots.textContent,/<script>attack/);assert.match(s.nodes.orders.textContent,/No contribution intents/);
 assert.equal(s.calls[0].options.credentials,'omit');assert.equal(s.calls[0].options.redirect,'error');assert.equal(s.nodes.token.value,'');
});
test('purchase needs a concrete preview then confirmation and duplicate clicks never retry',async()=>{
 const s=setup(async url=>ok(url.endsWith('/preview')?proposal:url.endsWith('/contributions')?{id:'contrib-fixed-test-id',state:'ACCEPTED'}:data()));await s.unlock();await s.preview();
 assert.match(s.nodes['preview-summary'].textContent,/maximum debit ₹1,001.80/);assert.match(s.nodes['preview-summary'].textContent,/Existing stop\/target retained/);
 assert.equal(s.calls.filter(c=>c.url.endsWith('/contributions')).length,0);
 s.nodes['submit-purchase'].fire('click');assert.ok(s.nodes.confirm.open);assert.match(s.nodes['confirm-text'].textContent,/₹1,001.80/);
 s.nodes['confirm-action'].fire('click');s.nodes['confirm-action'].fire('click');await flush();
 assert.equal(s.calls.filter(c=>c.url.endsWith('/contributions')).length,1);assert.match(s.nodes.message.textContent,/ACCEPTED/);
 await s.preview();assert.equal(s.calls.filter(c=>c.url.endsWith('/preview')).length,1);
});
test('blocked previews show reasons and cannot open a purchase confirmation',async()=>{
 const s=setup(async url=>ok(url.endsWith('/preview')?{...proposal,decision:{allowed:false,reasons:['HOLDING_EXIT_ALREADY_REQUESTED']}}:data()));await s.unlock();await s.preview();
 assert.match(s.nodes['preview-reasons'].textContent,/holding exit already requested/);assert.ok(s.nodes['submit-purchase'].disabled);assert.match(s.nodes['preview-summary'].textContent,/No order/);
});
test('a confirmation cannot use an aged display; cancelling submits nothing',async()=>{
 const s=setup(async url=>ok(url.endsWith('/preview')?proposal:data()));await s.unlock();await s.preview();s.nodes['submit-purchase'].fire('click');
 s.nodes['cancel-confirm'].fire('click');assert.equal(s.calls.length,2);s.nodes['submit-purchase'].fire('click');s.advance(6001);s.nodes['confirm-action'].fire('click');await flush();assert.equal(s.calls.length,2);assert.match(s.nodes.message.textContent,/Refresh/);
});
test('Escape discards a purchase confirmation and cannot submit its earlier server preview',async()=>{
 const s=setup(async url=>ok(url.endsWith('/preview')?proposal:data()));await s.unlock();await s.preview();s.nodes['submit-purchase'].fire('click');
 assert.equal(s.nodes.confirm.open,true);s.nodes.confirm.fire('cancel');assert.equal(s.nodes.confirm.open,false);
 s.nodes['confirm-action'].fire('click');await flush();assert.equal(s.calls.filter(c=>c.options.method==='POST').length,1);assert.equal(s.calls.at(-1).url.endsWith('/preview'),true);
});
test('saving a SIP plan and cancelling it require review with explicit dates',async()=>{
 const d=data();d.plans=[{plan:{plan_id:'monthly',symbol:'NSE:DEMO',budget:'1000',reference:'reviewed'},occurrences:[{status:'DUE',session:'2026-10-20',request:{intent_id:'sip-fixed',plan_id:'monthly',occurrence:'2026-10-20',symbol:'NSE:DEMO',budget:'1000',reference:'reviewed'}}],cancelled:false}];
 const s=setup(async url=>ok(url.endsWith('/preview')?proposal:d));await s.unlock();
 const due=s.nodes.plans.children[0].children.find(n=>n.textContent.startsWith('Preview due'));due.fire('click');await flush();
 const body=JSON.parse(s.calls.at(-1).options.body);assert.equal(body.intent_id,'sip-fixed');assert.equal(body.occurrence,'2026-10-20');
 const cancel=s.nodes.plans.children[0].children.find(n=>n.textContent.startsWith('Cancel plan'));cancel.fire('click');assert.match(s.nodes['confirm-text'].textContent,/Existing filled shares remain/);
 s.nodes['cancel-confirm'].fire('click');assert.equal(s.calls.filter(c=>c.url.endsWith('/plans/cancel')).length,0);
 for(const [id,value]of Object.entries({'plan-id':'next-plan','plan-symbol':'NSE:DEMO','plan-budget':'1500','plan-stop':'2','plan-target':'4','plan-dates':'2026-11-02, 2026-12-01','plan-reference':'reviewed dates'}))s.nodes[id].value=value;
 s.nodes['plan-form'].fire('submit');assert.match(s.nodes['confirm-text'].textContent,/₹1,500.00/);s.nodes['confirm-action'].fire('click');await flush();
 const saved=s.calls.find(c=>c.url.endsWith('/plans'));assert.deepEqual(JSON.parse(saved.options.body).sessions,['2026-11-02','2026-12-01']);

});
test('unknown outcomes stop retries and structured validation errors stay readable',async()=>{
 const s=setup(async url=>{if(url.endsWith('/contributions')){const e=Error('timeout');e.name='AbortError';throw e;}return ok(url.endsWith('/preview')?proposal:data());});await s.unlock();await s.preview();s.nodes['submit-purchase'].fire('click');s.nodes['confirm-action'].fire('click');await flush();
 assert.match(s.nodes.message.textContent,/Outcome unknown/);await s.preview();assert.equal(s.calls.filter(c=>c.url.endsWith('/contributions')).length,1);assert.ok(s.nodes['submit-purchase'].disabled);
 const invalid=setup(async url=>url.endsWith('/preview')?{ok:false,status:422,json:async()=>({detail:[{loc:['body','budget'],msg:'Invalid decimal'}]})}:ok(data()));await invalid.unlock();await invalid.preview();assert.match(invalid.nodes.message.textContent,/budget: Invalid decimal/);

});
test('refreshing revokes a purchase review before replacing account evidence',async()=>{
 let resolve,hold=false;
 const s=setup(async url=>url.endsWith('/preview')?ok(proposal):hold?new Promise(done=>{resolve=done;}):ok(data()));
 await s.unlock();await s.preview();s.nodes['submit-purchase'].fire('click');assert.equal(s.nodes.confirm.open,true);
 hold=true;const refreshed=s.instance.refresh();assert.equal(s.nodes.confirm.open,false);
 s.nodes['confirm-action'].fire('click');assert.equal(s.calls.filter(c=>c.url.endsWith('/contributions')).length,0);
 resolve(ok(data()));await refreshed;s.nodes['confirm-action'].fire('click');await flush();
 assert.equal(s.calls.filter(c=>c.url.endsWith('/contributions')).length,0);
});
test('changing reviewed purchase fields revokes its pending confirmation',async()=>{
 const s=setup(async url=>ok(url.endsWith('/preview')?proposal:data()));await s.unlock();await s.preview();
 s.nodes['submit-purchase'].fire('click');s.nodes.budget.value='9000';s.nodes.budget.fire('input');
 assert.equal(s.nodes.confirm.open,false);s.nodes['confirm-action'].fire('click');await flush();
 assert.equal(s.calls.filter(c=>c.url.endsWith('/contributions')).length,0);assert.equal(s.nodes.preview.hidden,true);
});
