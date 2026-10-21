'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const {readFileSync}=require('node:fs');
const {createDesk}=require('../../src/trading_agent/api/static/desk.js');
class Element{
 constructor(){this.events={};this.children=[];this.value='';this.disabled=false;this.open=false;this.style={};}
 set textContent(v){this.text=String(v);this.children=[];}get textContent(){return(this.text||'')+this.children.map(n=>n.textContent).join('');}
 set innerHTML(_){throw Error('unsafe HTML sink');}
 append(...n){this.children.push(...n);}replaceChildren(...n){this.text='';this.children=n;}
 addEventListener(n,f){(this.events[n]||=[]).push(f);}fire(n){if(!this.disabled)for(const f of this.events[n]||[])f({preventDefault(){}});}
 showModal(){this.open=true;}close(){this.open=false;}
}
const flush=()=>new Promise(r=>setImmediate(r));const ok=data=>({ok:true,status:200,json:async()=>data});
const decision=(extra={})=>({id:'signal',side:'BUY',symbol:'NSE:DEMO',created_at:'2026-10-20T04:30:00Z',expires_at:'2026-10-20T04:32:00Z',state:'awaiting_approval',mode:'approval',candidate:{reason:'Completed daily trend',stop:'490',target:'520'},context:{kind:'daily'},...extra});
const status=(extra={})=>({mode:'manual',revision:'a'.repeat(32),mode_reason:'STARTUP_DISARMED',horizon:'long_term',observed_at:'2026-10-20T04:30:00Z',blockers:['NO_ANALYSIS_PROFILE'],selected:[{symbol:'NSE:DEMO'}],decisions:[],selection_basis:'operator_watchlist',strategy_mode:'unconfigured',model_available:false,bound_intraday_controller:false,account:{equity:'25000.00',cash:'25000.00'},...extra});
function setup(fetcher=async()=>ok(status()),activity=false,windowOptions={}){
 const nodes=Object.fromEntries([...readFileSync('src/trading_agent/api/static/'+(activity?'activity':'desk')+'.html','utf8').matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 if(activity)nodes['side-filter'].value='ALL';
 const calls=[],intervals=[];const win={AgenticMoney:require('../../src/trading_agent/api/static/money.js'),setTimeout:()=>1,clearTimeout(){},setInterval:f=>intervals.push(f),...windowOptions};
 const doc={getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:()=>new Element(),hidden:false};
 const instance=createDesk(doc,win,async(url,opts)=>{calls.push({url,opts});return fetcher(url,opts);},activity);
 async function unlock(){nodes.token.value='test-token-long-enough-1234567890';nodes.access.fire('submit');await flush();}
 return{nodes,calls,instance,unlock,intervals};
}
test('desk keeps private data locked and explicitly says the current selection is a manual watchlist',async()=>{
 const s=setup();assert.equal(s.calls.length,0);assert.ok(s.nodes.main.hidden);await s.unlock();
 assert.match(s.nodes.universe.textContent,/not automatically finding/);assert.match(s.nodes.watchlist.textContent,/NSE:DEMO/);
 assert.match(s.nodes.blockers.textContent,/reviewed real-data analysis profile/);assert.equal(s.nodes['mode-automatic'].disabled,true);
 assert.match(s.nodes.balance.textContent,/₹25,000.00/);assert.equal(s.nodes.token.value,'');
 assert.equal(s.calls[0].opts.headers.Authorization,'Bearer test-token-long-enough-1234567890');assert.equal(s.calls[0].opts.credentials,'omit');
});
test('automatic paper mode requires a reviewable confirmation and one explicit submission',async()=>{
 const s=setup(async()=>ok(status({blockers:[]})));await s.unlock();s.nodes['mode-automatic'].fire('click');
 assert.ok(s.nodes.confirm.open);assert.equal(s.calls.length,1);assert.match(s.nodes['confirm-text'].textContent,/without individual approval/);
 assert.equal(s.instance.canNavigate(),false);s.nodes['confirm-action'].fire('click');s.nodes['confirm-action'].fire('click');await flush();
 const posts=s.calls.filter(c=>c.url==='/api/desk/mode');assert.equal(posts.length,1);assert.deepEqual(JSON.parse(posts[0].opts.body),{mode:'automatic',revision:'a'.repeat(32),acknowledged:true});
});
test('mode confirmation stays in the visible embedded viewport and clears parent listeners on lock',async()=>{
 const listeners=new Map(),parent={innerHeight:844,addEventListener:(type,fn)=>listeners.set(type,fn),removeEventListener:type=>listeners.delete(type)};
 const s=setup(async()=>ok(status({blockers:[]})),false,{parent,frameElement:{getBoundingClientRect:()=>({top:-1800})}});await s.unlock();s.nodes['mode-automatic'].fire('click');
 assert.equal(s.nodes.confirm.style.top,'1876px');assert.equal(s.nodes.confirm.style.maxHeight,'692px');assert.equal(listeners.size,2);
 s.instance.lock();assert.equal(listeners.size,0);assert.equal(s.nodes.confirm.open,false);assert.equal(s.calls.filter(c=>c.url==='/api/desk/mode').length,0);
});
test('connected feed still explains missing strategy and quotes beside disabled mode buttons',async()=>{
 const s=setup(async()=>ok(status({blockers:['NO_ANALYSIS_PROFILE','NO_FRESH_EXECUTION_QUOTES'],account:{equity:'25000',cash:'25000',feed_connected:true},readiness:{now_ist:'2026-10-21T20:00:00+05:30',next_action:'Prepare and review a strategy below first.',checks:[{key:'strategy',title:'Strategy and historical data',ready:false,detail:'No strategy installed.',action:'Prepare strategy data',href:'#strategy-setup'}],quotes:[{symbol:'NSE:DEMO',usable:false,exchange_time:null,basis_reviewed:false}]}})));
 await s.unlock();assert.equal(s.nodes.state.textContent,'Feed connected');assert.equal(s.nodes['mode-automatic'].disabled,true);
 assert.match(s.nodes['mode-status'].textContent,/2 prerequisites/);assert.match(s.nodes['next-action'].textContent,/Prepare and review/);assert.match(s.nodes['readiness-checks'].textContent,/Prepare strategy data/);assert.match(s.nodes['quote-observations'].textContent,/no accepted quote/);
 assert.equal(s.nodes['readiness-checks'].children[0].children.at(-1).href,'#strategy-setup');
});
test('trade preview shows maximum shares/cash/risk before approval and preserves raw signal text safely',async()=>{
 const d=decision({candidate:{reason:'<script>unsafe</script>',stop:'490',target:'520'}});
 const s=setup(async(url)=>url.endsWith('/preview')?ok({...d,preview_sha256:'b'.repeat(64),review:{allowed:true,maximum_quantity:14,maximum_price:'501.00',maximum_cash:'7014.00',maximum_risk:'250.00'}}):ok(status({mode:'approval',blockers:[],decisions:[d]})));
 await s.unlock();assert.match(s.nodes.queue.textContent,/<script>unsafe<\/script>/);
 const card=s.nodes.queue.children[0];card.children.find(n=>n.textContent==='Review buy proposal').fire('click');await flush();
 assert.ok(s.nodes.confirm.open);assert.match(s.nodes['confirm-text'].textContent,/Maximum 14 shares/);assert.match(s.nodes['confirm-text'].textContent,/₹7,014.00/);
 assert.equal(s.calls.filter(c=>c.url.endsWith('/approve')).length,0);s.nodes['cancel-confirm'].fire('click');assert.equal(s.calls.filter(c=>c.url.endsWith('/approve')).length,0);
});
test('lock aborts late previews, clears private values and prevents a delayed approval dialog',async()=>{
 let finish,hold=false;const d=decision();
 const s=setup(async url=>hold?new Promise(r=>{finish=r;}):ok(status({mode:'approval',blockers:[],decisions:[d]})));await s.unlock();hold=true;
 s.nodes.queue.children[0].children.find(n=>n.textContent==='Review buy proposal').fire('click');s.instance.lock();
 finish(ok({...d,preview_sha256:'b'.repeat(64),review:{allowed:true}}));await flush();
 assert.ok(s.nodes.main.hidden);assert.equal(s.nodes.confirm.open,false);assert.equal(s.nodes.watchlist.textContent,'');assert.equal(s.nodes.balance.textContent,'');
});
test('authorization failure clears the section and distinguishes operator access from broker tokens',async()=>{
 const s=setup(async()=>({ok:false,status:401,json:async()=>({})}));await s.unlock();
 assert.ok(s.nodes.main.hidden);assert.match(s.nodes.message.textContent,/TRADING_OPERATOR_TOKEN/);
});
test('activity separates accepted orders from fills and uses exact decimal display',async()=>{
 const page={observed_at:'2026-10-20T04:30:00Z',entries:[{order:{id:'one',symbol:'NSE:DEMO',side:'BUY',state:'ACCEPTED',filled:0,quantity:14,fees:'0.00',created:'2026-10-20T04:30:00Z',reason:''},decision:null,original_instruction:{reason:'Reviewed trend reason'},fills:[],average_fill_price:null,cash_debit:'0'}],next_before:9,limit:50};
 const s=setup(async url=>ok(url.startsWith('/api/activity')?page:status({decisions:[decision({state:'expired',outcome:'APPROVAL_WINDOW_ENDED'})]})),true);await s.unlock();
 assert.match(s.nodes.activity.textContent,/ACCEPTED/);assert.match(s.nodes.activity.textContent,/0 of 14 shares filled/);assert.match(s.nodes.activity.textContent,/Reviewed trend reason/);
 assert.match(s.nodes['decision-history'].textContent,/expired/);assert.equal(s.nodes.older.disabled,false);s.nodes.older.fire('click');await flush();assert.ok(s.calls.some(c=>c.url==='/api/activity?before=9'));
 assert.equal(s.intervals.length,0);
});
