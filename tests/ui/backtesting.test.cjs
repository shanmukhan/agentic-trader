'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {createBacktesting}=require('../../src/trading_agent/api/static/backtesting.js');
class Element {
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.events={};this.children=[];this.attributes={};this.style={};this.value='';this.disabled=false;this.open=false;this.isConnected=true;}
 set textContent(value){this.text=String(value);this.children=[];}
 get textContent(){return (this.text||'')+this.children.map(child=>child.textContent).join('');}
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
const hash='a'.repeat(64);
function resource(){return {resource_id:'fixture-v1',resource_sha256:hash,label:'Reviewed <script>fixture</script>',synthetic:true,runtime:{code_sha256:'c'.repeat(64),charges:{version:'invented-charge-v1',dp_sell:'15.34',observed_on:'2026-10-20'}},strategy:{hypothesis:'momentum',max_hold_sessions:20},policy:{starting_cash:'9007199254740993.125',slippage_bps:'2',max_trade_risk:'62.50'},coverage:{daily_sessions:60,execution_sessions:2,first_session:'2026-09-01',last_session:'2026-10-21'},provenance:{semantics:'legacy-offline-v1',fill_model:'later-observed-bid-ask-v1',connected_parity:'not_established',out_of_sample:'not_declared'},limitations:['Current source is simulated evidence, not market acceptance']};}
function job(extra={}){return {job_id:'job-1',resource_id:'fixture-v1',resource_sha256:hash,request_key:'01'.repeat(16),state:'running',stage:'replaying',updated_at:'2026-10-22T04:00:00Z',semantics:'legacy-offline-v1',...extra};}
function report(extra={}){return {schema_version:1,report_id:'report-1',resource_sha256:hash,artifact_sha256:'b'.repeat(64),summary:{net_pnl:'-12.3456',initial_cash:'9007199254740993.125',completed_trades:1,sharpe:null},final_snapshot:{cash:'9007199254740993.125',valuation_fresh:false},equity_curve:[{time:'2026-10-22T04:00:00Z',equity:'9007199254740993.125',cash:'50.005',valuation_fresh:false,known_receivable:'12.001'}],drawdown_curve:[{time:'2026-10-22T04:00:00Z',drawdown:'12.3456',drawdown_pct:'0.00000001'}],orders:[{symbol:'NSE:<img>',state:'REJECTED',quantity:1,reason:'PRICE_BASIS'}],fills:[{symbol:'NSE:A',side:'BUY',price:'123.4567',fees:'0.0005',quantity:1}],provenance:{synthetic:true,semantics:'legacy-offline-v1',strategy_sha256:'s',risk_policy_sha256:'p'},limitations:['Not an out-of-sample evaluation'],...extra};}
function setup(custom){
 const html=readFileSync('src/trading_agent/api/static/backtesting.html','utf8');
 const nodes=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const calls=[],events={},docEvents={},timers=new Map();let timerId=0;
 const win={location:{pathname:'/backtesting'},innerWidth:1000,innerHeight:700,crypto:{getRandomValues:bytes=>{bytes.fill(1);return bytes;}},setTimeout:(handler,ms)=>{const id=++timerId;timers.set(id,{handler,ms});return id;},clearTimeout:id=>timers.delete(id),addEventListener:(type,handler)=>{(events[type]||=[]).push(handler);},removeEventListener:(type,handler)=>{events[type]=(events[type]||[]).filter(h=>h!==handler);}};
 const doc={hidden:false,activeElement:null,getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:tag=>new Element(tag),addEventListener:(type,handler)=>{docEvents[type]=handler;}};
 const defaultFetch=(url,options)=>url==='/api/backtests/resources'?ok({schema_version:1,resources:[resource()],capability:{available:true},limitations:['Declared legacy replay only']}):url==='/api/backtests/jobs'&&options.method==='GET'?ok({schema_version:1,jobs:[]}):url.startsWith('/api/backtests/reports/')?ok(report()):ok({schema_version:1,job:job()});
 const view=createBacktesting(doc,win,async(url,options)=>{calls.push({url,options});return custom?custom(url,options,defaultFetch):defaultFetch(url,options);});
 const unlock=async()=>{nodes.token.value='test-operator-token-long-enough-123456789';nodes.access.fire('submit');await flush();};
 const choose=()=>{nodes.resource.value='fixture-v1';nodes.resource.fire('change');};
 const review=()=>{choose();nodes['review-run'].fire('click');};
 const confirm=async()=>{nodes.ack.checked=true;nodes.ack.fire('change');nodes['confirm-action'].fire('click');await flush();};
 const post=()=>calls.filter(c=>c.options.method==='POST');
 const poll=async()=>{const found=[...timers].find(([,t])=>t.ms>=15000);assert.ok(found,'poll scheduled');timers.delete(found[0]);await found[1].handler();await flush();};
 return {nodes,calls,events,docEvents,win,doc,view,unlock,choose,review,confirm,post,poll,timers};
}
test('private data only loads after memory-token unlock; reads cannot submit a run',async()=>{
 const s=setup();assert.equal(s.calls.length,0);assert.equal(s.nodes.main.hidden,true);await s.unlock();
 assert.deepEqual(s.calls.map(c=>c.url),['/api/backtests/resources','/api/backtests/jobs']);
 for(const call of s.calls){assert.equal(call.options.method,'GET');assert.equal(call.options.credentials,'omit');assert.equal(call.options.cache,'no-store');assert.equal(call.options.redirect,'error');assert.equal(call.options.headers.Authorization,'Bearer test-operator-token-long-enough-123456789');}
 assert.equal(s.nodes.token.value,'');assert.equal(s.nodes.main.hidden,false);assert.equal(s.post().length,0);
 s.choose();assert.match(s.nodes['resource-summary'].textContent,/SYNTHETIC INPUTS/);assert.match(s.nodes['resource-summary'].textContent,/maximum holding sessions20/);assert.match(s.nodes['resource-summary'].textContent,/<script>fixture/);
 const html=readFileSync('src/trading_agent/api/static/backtesting.html','utf8');assert.match(html,/register-backtest --help/);assert.match(html,/Event observations|simulated result|simulated evidence|synthetic fixtures/);
});
test('launch requires visible review and unchecked acknowledgment; Cancel and Escape issue no POST',async()=>{
 const s=setup();await s.unlock();s.review();assert.equal(s.nodes.confirm.open,true);assert.equal(s.view.canNavigate(),false);assert.equal(s.nodes.ack.checked,false);assert.equal(s.nodes['confirm-action'].disabled,true);
 assert.match(s.nodes['confirm-text'].textContent,/does not connect a broker/);assert.match(s.nodes['confirm-summary'].textContent,/legacy-offline-v1/);assert.match(s.nodes['confirm-summary'].textContent,/"max_hold_sessions":20/);assert.match(s.nodes['confirm-summary'].textContent,/invented-charge-v1/);assert.match(s.nodes['confirm-summary'].textContent,/15.34/);assert.match(s.nodes['confirm-summary'].textContent,RegExp('c'.repeat(64)));
 s.nodes['confirm-action'].fire('click');assert.equal(s.post().length,0);s.nodes.cancel.fire('click');assert.equal(s.nodes.confirm.open,false);assert.equal(s.post().length,0);assert.equal(s.view.canNavigate(),true);
 s.review();s.nodes.confirm.fire('cancel');assert.equal(s.nodes.confirm.open,false);assert.equal(s.post().length,0);assert.equal(s.view.canNavigate(),true);
});
test('confirmed launch submits exactly one strict immutable-resource request with a secure stable key',async()=>{
 let finish;const s=setup((url,options,base)=>options.method==='POST'?new Promise(resolve=>{finish=resolve;}):base(url,options));await s.unlock();s.review();s.nodes.ack.checked=true;s.nodes.ack.fire('change');s.nodes['confirm-action'].fire('click');s.nodes['confirm-action'].fire('click');await flush();
 assert.equal(s.post().length,1);assert.equal(s.view.canNavigate(),false);assert.deepEqual(JSON.parse(s.post()[0].options.body),{resource_id:'fixture-v1',resource_sha256:hash,request_key:'01'.repeat(16),acknowledged:true});
 finish(ok({schema_version:1,job:job()}));await flush();assert.equal(s.view.canNavigate(),true);assert.match(s.nodes['submission-state'].textContent,/Recorded job job-1/);assert.equal(s.post().length,1);
});
test('unknown submission never creates a new key or automatically retries; refreshed matching job resolves it',async()=>{
 let submitted=false;const s=setup((url,options,base)=>{if(options.method==='POST'){submitted=true;throw Error('network');}if(submitted&&url==='/api/backtests/jobs')return ok({schema_version:1,jobs:[job()]});return base(url,options);});await s.unlock();s.review();await s.confirm();
 assert.equal(s.post().length,1);assert.match(s.nodes['submission-state'].textContent,/outcome unknown/);assert.equal(s.nodes['review-run'].disabled,true);assert.equal(s.nodes['retry-run'].disabled,true);
 s.nodes.refresh.fire('click');await flush();assert.match(s.nodes['submission-state'].textContent,/request was recorded as job job-1/);assert.equal(s.nodes['retry-run'].hidden,true);assert.equal(s.post().length,1);
});
test('explicit unknown-outcome retry is enabled only after saved-job lookup and reuses reviewed key and hash',async()=>{
 let failures=1;const s=setup((url,options,base)=>{if(options.method==='POST'&&failures-- >0)throw Error('timeout');return base(url,options);});await s.unlock();s.review();await s.confirm();assert.equal(s.nodes['retry-run'].disabled,true);
 s.nodes.refresh.fire('click');await flush();assert.equal(s.nodes['retry-run'].disabled,false);s.nodes['retry-run'].fire('click');assert.equal(s.nodes.ack.checked,false);await s.confirm();
 assert.equal(s.post().length,2);assert.equal(s.post()[0].options.body,s.post()[1].options.body);assert.match(s.nodes['submission-state'].textContent,/Recorded job/);
});
test('authorization failures clear results; lock aborts pending reads and discards late JSON',async()=>{
 let finish;const s=setup((url,options,base)=>url==='/api/backtests/jobs'?{ok:true,status:200,json:()=>new Promise(resolve=>{finish=resolve;})}:base(url,options));await s.unlock();assert.equal(s.view.canNavigate(),false);const signal=s.calls.at(-1).options.signal;
 s.view.lock();assert.equal(signal.aborted,true);finish({schema_version:1,jobs:[job()]});await flush();assert.equal(s.nodes.main.hidden,true);assert.equal(s.nodes.jobs.textContent,'');assert.equal(s.view.canNavigate(),true);assert.equal(s.timers.size,0);
 const a=setup(()=>({ok:false,status:401}));await a.unlock();assert.equal(a.nodes.main.hidden,true);assert.match(a.nodes.message.textContent,/authorization failed/);assert.equal(a.calls.length,1);
});
test('pagehide revokes a pending launch and discards late mutation response',async()=>{
 let finish;const s=setup((url,options,base)=>options.method==='POST'?{ok:true,status:202,json:()=>new Promise(resolve=>{finish=resolve;})}:base(url,options));await s.unlock();s.review();s.nodes.ack.checked=true;s.nodes.ack.fire('change');s.nodes['confirm-action'].fire('click');await flush();
 for(const handler of [...s.events.pagehide])handler();finish({schema_version:1,job:job()});await flush();assert.equal(s.nodes.main.hidden,true);assert.equal(s.nodes.jobs.textContent,'');assert.equal(s.nodes['confirm-summary'].textContent,'');assert.equal(s.nodes.token.value,'');assert.equal(s.post().length,1);
});
test('polls read-only every visible interval, pause when hidden and back off after a failure',async()=>{
 let fail=false;const s=setup((url,options,base)=>fail&&url==='/api/backtests/jobs'?{ok:false,status:503}:base(url,options));await s.unlock();await s.poll();assert.equal(s.calls.at(-1).url,'/api/backtests/jobs');assert.equal(s.calls.length,3);
 s.doc.hidden=true;s.docEvents.visibilitychange();assert.equal(s.timers.size,0);s.doc.hidden=false;s.docEvents.visibilitychange();fail=true;await s.poll();assert.match(s.nodes.state.textContent,/stale/);assert.ok([...s.timers.values()].some(t=>t.ms===30000));assert.equal(s.post().length,0);
});
test('empty registry, unavailable process isolation and missing secure-key support cannot launch',async()=>{
 const e=setup((url,options,base)=>url.endsWith('/resources')?ok({schema_version:1,resources:[],capability:{available:false,reason:'OS sandbox unavailable'}}):base(url,options));await e.unlock();assert.match(e.nodes['resource-state'].textContent,/No input bundles are registered/);assert.equal(e.nodes['review-run'].disabled,true);assert.equal(e.post().length,0);
 const p=setup((url,options,base)=>url.endsWith('/resources')?ok({schema_version:1,resources:[resource()],capability:{available:false,reason:'OS sandbox unavailable'}}):base(url,options));await p.unlock();p.choose();assert.match(p.nodes['resource-state'].textContent,/OS sandbox unavailable/);assert.equal(p.nodes['review-run'].disabled,true);
 const n=setup();n.win.crypto=null;await n.unlock();n.choose();assert.match(n.nodes['resource-state'].textContent,/secure idempotency key/);assert.equal(n.nodes['review-run'].disabled,true);
});
test('job cancellation has separate review, retains its record and never sends an order endpoint',async()=>{
 const s=setup((url,options,base)=>url==='/api/backtests/jobs'&&options.method==='GET'?ok({schema_version:1,jobs:[job()]}):base(url,options));await s.unlock();const button=s.nodes.jobs.children[0].children.find(e=>e.tagName==='BUTTON');assert.equal(button.disabled,false);button.fire('click');assert.match(s.nodes['confirm-text'].textContent,/does not cancel a financial order/);assert.equal(s.post().length,0);await s.confirm();
 assert.equal(s.post().length,1);assert.equal(s.post()[0].url,'/api/backtests/jobs/job-1/cancel');assert.deepEqual(JSON.parse(s.post()[0].options.body),{acknowledged:true});assert.match(s.nodes.jobs.textContent,/job-1/);
});
test('reports show exact ledger values, missing metrics, synthetic provenance and order outcomes accessibly',async()=>{
 const s=setup((url,options,base)=>url==='/api/backtests/jobs'&&options.method==='GET'?ok({schema_version:1,jobs:[job({state:'succeeded',report_id:'report-1'})]}):base(url,options));await s.unlock();s.nodes.jobs.children[0].children.find(e=>e.tagName==='BUTTON').fire('click');await flush();
 assert.equal(s.nodes['report-panel'].hidden,false);assert.match(s.nodes['report-state'].textContent,/SYNTHETIC INPUTS/);assert.match(s.nodes['report-summary'].textContent,/-₹12.3456/);assert.match(s.nodes['report-summary'].textContent,/sharpeUnavailable/);assert.match(s.nodes['report-equity'].textContent,/₹9,00,71,99,25,47,40,993.125/);assert.match(s.nodes['report-equity'].textContent,/false/);assert.match(s.nodes['report-fills'].textContent,/₹123.4567/);assert.match(s.nodes['report-fills'].textContent,/₹0.0005/);assert.match(s.nodes['report-orders'].textContent,/REJECTED/);assert.match(s.nodes['report-orders'].textContent,/<img>/);assert.match(s.nodes['report-metrics'].textContent,/Event observations are not daily return cuts/);
 const table=s.nodes['report-equity'].children[0];assert.equal(table.children[0].tagName,'CAPTION');assert.equal(table.children[1].children[0].children[0].attributes.scope,'col');assert.equal(s.post().length,0);
 s.view.lock();for(const id of ['report-summary','report-provenance','report-equity','report-fills'])assert.equal(s.nodes[id].textContent,'');
});
test('comparison blocks differing resources and compares only exact same-resource methodology',async()=>{
 let different=true;const s=setup((url,options,base)=>{if(url==='/api/backtests/jobs'&&options.method==='GET')return ok({schema_version:1,jobs:[job({state:'succeeded',report_id:'report-1'}),job({job_id:'job-2',state:'succeeded',report_id:'report-2'})]});if(url==='/api/backtests/reports/report-2')return ok(report({report_id:'report-2',resource_sha256:different?'c'.repeat(64):hash}));return base(url,options);});await s.unlock();s.nodes['compare-a'].value='job-1';s.nodes['compare-b'].value='job-2';s.nodes['compare-a'].fire('change');s.nodes.compare.fire('click');await flush();assert.match(s.nodes['comparison-state'].textContent,/Comparison blocked/);assert.equal(s.nodes.comparison.textContent,'');assert.equal(s.post().length,0);
 s.view.lock();different=false;await s.unlock();s.nodes['compare-a'].value='job-1';s.nodes['compare-b'].value='job-2';s.nodes['compare-a'].fire('change');s.nodes.compare.fire('click');await flush();assert.match(s.nodes['comparison-state'].textContent,/Same registered input/);assert.match(s.nodes.comparison.textContent,/-₹12.3456/);assert.match(s.nodes.comparison.textContent,/Unavailable/);
});

test('wide evidence tables are keyboard-scrollable labelled regions and technical budgets are disclosed on demand',()=>{const html=readFileSync('src/trading_agent/api/static/backtesting.html','utf8');for(const id of ['report-equity','report-drawdown','report-orders','report-fills','comparison'])assert.match(html,RegExp('<div id="'+id+'"[^>]*role="region"[^>]*aria-label="[^"]+"[^>]*tabindex="0"'));assert.match(html,/<details><summary>Worker limits and storage budgets<\/summary>/);});
