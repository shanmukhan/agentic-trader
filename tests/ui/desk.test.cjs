'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const {readFileSync}=require('node:fs');
const {createDesk}=require('../../src/trading_agent/api/static/desk.js');
class Element{
 constructor(){this.events={};this.children=[];this.value='';this.disabled=false;this.open=false;this.style={};this.attributes={};}
 setAttribute(name,value){this.attributes[name]=String(value);}getAttribute(name){return this.attributes[name];}
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
 const html=readFileSync('src/trading_agent/api/static/'+(activity?'activity':'desk')+'.html','utf8');
 const nodes=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const sections=[...html.matchAll(/\bdata-desk-section="([^"]+)"/g)].map(m=>{const n=new Element();n.setAttribute('data-desk-section',m[1]);return n;});
 if(activity)nodes['side-filter'].value='ALL';
 const calls=[],intervals=[];const win={AgenticMoney:require('../../src/trading_agent/api/static/money.js'),setTimeout:()=>1,clearTimeout(){},setInterval:f=>intervals.push(f),...windowOptions};
 const doc={body:new Element(),querySelectorAll:()=>sections,getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:()=>new Element(),hidden:false};
 const instance=createDesk(doc,win,async(url,opts)=>{calls.push({url,opts});return fetcher(url,opts);},activity);
 async function unlock(){nodes.token.value='test-token-long-enough-1234567890';nodes.access.fire('submit');await flush();}
 return{nodes,calls,instance,unlock,intervals,doc,sections};
}
test('desk keeps private data locked and explicitly says the current selection is a manual watchlist',async()=>{
 const s=setup();assert.equal(s.calls.length,0);assert.ok(s.nodes.main.hidden);await s.unlock();
 assert.match(s.nodes.universe.textContent,/not automatically finding/);assert.match(s.nodes.watchlist.textContent,/NSE:DEMO/);
 assert.match(s.nodes.blockers.textContent,/reviewed real-data analysis profile/);assert.equal(s.nodes['mode-automatic'].disabled,true);
 assert.match(s.nodes.balance.textContent,/₹25,000.00/);assert.equal(s.nodes.token.value,'');
 assert.equal(s.calls[0].opts.headers.Authorization,'Bearer test-token-long-enough-1234567890');assert.equal(s.calls[0].opts.credentials,'omit');
});
test('dashboard leads with exact account values and labels stale valuation without inventing missing money',async()=>{
 const account={equity:'9007199254740993.125',cash:'24990.01',available_cash:'20000.005',reserved_cash:'4990.005',day_pnl:'-12.3456',day:'2026-10-19',realized_pnl:'8.7654',positions:[{symbol:'NSE:DEMO'}],valuation_fresh:false};
 const s=setup(async()=>ok(status({account})));await s.unlock();
 assert.equal(s.nodes['portfolio-equity'].textContent,'₹9,00,71,99,25,47,40,993.125');
 assert.equal(s.nodes.balance.textContent,'₹24,990.01');
 assert.match(s.nodes['cash-available'].textContent,/₹20,000.005/);
 assert.match(s.nodes['cash-reserved'].textContent,/₹4,990.005/);
 assert.equal(s.nodes['day-pnl'].textContent,'-₹12.3456');assert.match(s.nodes['day-pnl'].className,/financial-loss/);
 assert.equal(s.nodes['pnl-session'].textContent,'Account session: 2026-10-19 (IST)');
 assert.match(s.nodes['realized-pnl'].textContent,/₹8.7654.*stale/);
 assert.match(s.nodes['valuation-state'].textContent,/Valuation stale or incomplete.*estimates/);
 assert.equal(s.nodes['position-count'].textContent,'1');assert.equal(s.nodes['market-status'].textContent,'Session unverified');
 s.instance.lock();for(const id of ['portfolio-equity','balance','cash-available','cash-reserved','day-pnl','pnl-session','realized-pnl','position-count','valuation-state'])assert.equal(s.nodes[id].textContent,'',id);
 assert.equal(s.nodes['day-pnl'].className,'desk-value');
 const missing=setup();await missing.unlock();assert.equal(missing.nodes['day-pnl'].textContent,'—');assert.equal(missing.nodes['position-count'].textContent,'—');
 assert.match(missing.nodes['valuation-state'].textContent,/unavailable/);
});
test('Strategies has a separate view with focused setup links and no mode activation on entry',async()=>{
 const s=setup(async()=>ok(status({readiness:{now_ist:'2026-10-22T10:00:00+05:30',checks:[{title:'Strategy',ready:false,action:'Prepare data',href:'#strategy-setup'}]}})),false,{location:{pathname:'/strategies'}});
 assert.equal(s.doc.body.getAttribute('data-desk-view'),'strategies');assert.equal(s.doc.title,'Strategies · Paper only');
 assert.equal(s.nodes['page-title'].textContent,'Strategies');assert.equal(s.calls.length,0);
 for(const section of s.sections)assert.equal(section.hidden,section.getAttribute('data-desk-section')!=='strategies');
 await s.unlock();assert.equal(s.nodes['next-step-link'].href,'#strategy-setup');
 assert.equal(s.nodes['readiness-checks'].children[0].children.at(-1).href,'#strategy-setup');assert.equal(s.calls.length,1);
 const dashboard=setup();for(const section of dashboard.sections)assert.equal(section.hidden,section.getAttribute('data-desk-section')!=='dashboard');
 assert.equal(dashboard.nodes['page-title'].textContent,'Dashboard');
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
 assert.equal(s.nodes['readiness-checks'].children[0].children.at(-1).href,'/strategies#strategy-setup');
});
test('daily-review quote blocker explains missing acceptance and links to a focusable shortlist section',async()=>{
 const detail="Today's price-basis review is missing. Incoming quotes cannot be accepted.";
 const s=setup(async()=>ok(status({blockers:['EXECUTION_SHORTLIST_NOT_REVIEWED','LONG_TERM_REVIEW_REQUIRED'],readiness:{now_ist:'2026-10-22T10:00:00+05:30',session_open:true,checks:[{title:'Supported execution shortlist',ready:false,action:'Review the ranked shortlist',href:'#execution-shortlist'}],quotes:[{symbol:'NSE:DEMO',detail,usable:false,exchange_time:null,basis_reviewed:false}]}})));
 await s.unlock();assert.equal(s.nodes['next-step-link'].href,'/strategies#execution-shortlist');
 assert.match(s.nodes['quote-observations'].textContent,/Incoming quotes cannot be accepted/);
 assert.doesNotMatch(s.nodes['quote-observations'].textContent,/Stale or unavailable/);
 assert.match(s.nodes['session-clock'].textContent,/Reviewed session open now/);
 assert.equal(s.calls.length,1);
 const html=readFileSync('src/trading_agent/api/static/desk.html','utf8');
 assert.match(html,/<section id="execution-shortlist" class="panel strategy-section" data-desk-section="strategies" tabindex="-1"/);
 assert.match(html,/href="\/setup#feed-connection"/);
});
test('readiness cards offer the same explicit daily review after preparation is rendered',async()=>{
 let rendered=false,opened=0;
 const s=setup(async()=>ok(status({blockers:['LONG_TERM_REVIEW_REQUIRED'],readiness:{now_ist:'2026-10-22T10:00:00+05:30',checks:[{key:'basis',title:'Today’s basis review',ready:false,detail:'Review missing.',action:'Review individually',href:'/console#long-term'}]}})),false,{AgenticPreparation:()=>({clear(){},controls(){},render(){rendered=true;},currentReviewReady:()=>rendered,reviewCurrent(){opened++;}})});
 await s.unlock();const card=s.nodes['readiness-checks'].children[0];
 const action=card.children.find(n=>n.textContent==='Review today’s setup');assert.ok(action);
 action.fire('click');assert.equal(opened,1);assert.equal(s.calls.length,1);
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
test('activity overview scopes counts to displayed orders and latest proposal window',async()=>{
 const entry=(id,side,filled)=>({order:{id,symbol:'NSE:DEMO',side,state:filled?'PARTIALLY_FILLED':'ACCEPTED',filled,quantity:2,fees:'0',created:'2026-10-20T04:30:00Z',reason:''},fills:[],average_fill_price:filled?'10.00':null,cash_debit:'0'});
 const page={observed_at:'2026-10-20T04:30:00Z',entries:[entry('buy','BUY',1),entry('sell','SELL',0)],next_before:9,limit:50};
 const s=setup(async url=>ok(url.startsWith('/api/activity')?page:status({decisions:[decision(),decision({id:'old',state:'cancelled'})]})),true);await s.unlock();
 let metrics=s.nodes.activity.children[0];assert.equal(metrics.children[0].children[1].textContent,'2');assert.equal(metrics.children[1].children[1].textContent,'1');assert.equal(metrics.children[2].children[1].textContent,'1');
 assert.match(metrics.textContent,/Current page and side filter/);assert.match(metrics.textContent,/Latest returned proposal records/);
 s.nodes['side-filter'].value='SELL';s.nodes['side-filter'].fire('change');await flush();metrics=s.nodes.activity.children[0];
 assert.equal(metrics.children[0].children[1].textContent,'1');assert.equal(metrics.children[1].children[1].textContent,'0');
 assert.equal(s.calls.filter(c=>c.opts.method==='POST').length,0);
});
test('automatic daily signal history explains why cancelled signals do not create new orders',async()=>{
 const s=setup(async()=>ok(status({mode:'automatic',blockers:[],daily_signal_summary:{message:'Today’s signals: 6 cancelled. Changing mode does not replay these signals.'}})));
 await s.unlock();assert.match(s.nodes['daily-signal-status'].textContent,/6 cancelled/);
 assert.match(s.nodes['daily-signal-status'].textContent,/does not replay/);
 assert.equal(s.calls.length,1);s.instance.lock();assert.equal(s.nodes['daily-signal-status'].textContent,'');
});
test('cancelled activity distinguishes a proposal from an order and shows updated time and pause triggers',async()=>{
 const proposal=decision({state:'cancelled',updated_at:'2026-10-20T04:30:05Z',outcome:'SESSION_FEED_OR_RISK_PAUSE',pause_reasons:['NO_FRESH_EXECUTION_QUOTES'],order_id:null,context:{kind:'daily'}});
 const s=setup(async url=>ok(url.startsWith('/api/activity')?{observed_at:'2026-10-20T04:30:05Z',entries:[],next_before:null}:status({decisions:[proposal]})),true);
 await s.unlock();const text=s.nodes['decision-history'].textContent;
 assert.match(text,/proposal cancelled · no order created/);assert.match(text,/last updated.*10:00:05/);
 assert.match(text,/Pause triggers: No fresh usable quote/);assert.match(text,/Switching to Automatic does not retry/);
 assert.match(text,/Proposal mode: Approval/);
});
