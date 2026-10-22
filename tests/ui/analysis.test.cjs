'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),{readFileSync}=require('node:fs');
const {createAnalysis}=require('../../src/trading_agent/api/static/analysis.js');
class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.listeners={};this.attributes={};this.value='';}
 set textContent(value){this.text=String(value);this.children=[];}
 get textContent(){return(this.text||'')+this.children.map(n=>n.textContent).join('');}
 set innerHTML(_){throw Error('Unsafe HTML sink');}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.text='';this.children=children;}
 setAttribute(key,value){this.attributes[key]=String(value);}
 addEventListener(name,fn){(this.listeners[name]||=[]).push(fn);}
 fire(name){if(this.disabled)return;for(const fn of this.listeners[name]||[])fn({preventDefault(){}});}
}
const ok=value=>({ok:true,status:200,json:async()=>value}),flush=()=>new Promise(resolve=>setImmediate(resolve));
const fixture=()=>({schema_version:1,observed_at:'2026-10-22T05:00:00Z',symbol:'NSE:DEMO',timeframe:'1d',symbols:[{symbol:'NSE:DEMO',subscribed:true,daily_history:true},{symbol:'NSE:BROAD',subscribed:false,daily_history:true}],quote:{status:'STALE_QUOTE',detail:'Saved quote is too old. Wait for a new valid quote.',usable:false,last:'9007199254740993.1234',exchange_time:'2026-10-21T09:59:00Z',subscribed:true},bars:[{time:'2026-10-20T10:00:00Z',session:'2026-10-20',open:'9007199254740993.0001',high:'9007199254740994.0001',low:'9007199254740992.0001',close:'9007199254740993.1234',volume:120,sma20:null,sma50:null},{time:'2026-10-21T10:00:00Z',session:'2026-10-21',open:'9007199254740993.0001',high:'9007199254740995.0001',low:'9007199254740992.0001',close:'9007199254740994.1234',volume:140,sma20:'9007199254740993.5001',sma50:null}],bar_limit:300,truncated:false,excluded_candles:0,data_state:'available',message:'Saved completed daily candles; these are historical prices, not live quotes.',source:{synthetic:true,description:'INVENTED tests <script>bad()</script>',price_basis:'Raw OHLC'},screen:{status:'research_candidate',rank:1,last_session:'2026-10-21',last_close:'500.0001',gross_total_return_pct:'2.5',daily_volatility_pct:'1.2',average_turnover:'10000001.55',reasons:[]},screen_as_of:'2026-10-22T05:00:00Z',policy:{momentum_sessions:20},market_session_open:true,limitations:['Historical screen is not a trade.']});
function setup(fetcher=async()=>ok(fixture())){
 const nodes=Object.fromEntries([...readFileSync('src/trading_agent/api/static/analysis.html','utf8').matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const calls=[],timeouts=[],intervals=[];let locked=0,updated=0,now=1000;
 const doc={getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)};
 const win={Date:{now:()=>now},setTimeout:fn=>{timeouts.push(fn);return timeouts.length;},clearTimeout(){},setInterval:fn=>intervals.push(fn),AgenticNavigation:{locked(){locked++;},updated(){updated++;}}};
 const instance=createAnalysis(doc,win,async(url,options)=>{calls.push({url,options});return fetcher(url,options);});
 async function unlock(){nodes.token.value='analysis-ephemeral-operator-token';nodes.access.fire('submit');await flush();}
 return{nodes,calls,timeouts,intervals,instance,unlock,advance:ms=>{now+=ms;},counts:()=>({locked,updated})};
}
test('analysis starts locked and performs authenticated GET only with no token persistence',async()=>{
 const s=setup();assert.equal(s.calls.length,0);assert.equal(s.nodes.main.hidden,true);await s.unlock();
 assert.equal(s.calls.length,1);assert.equal(s.calls[0].options.method,'GET');assert.equal(s.calls[0].options.cache,'no-store');assert.equal(s.calls[0].options.credentials,'omit');assert.equal(s.calls[0].options.redirect,'error');
 assert.match(s.calls[0].options.headers.Authorization,/Bearer analysis-ephemeral/);assert.equal(s.nodes.token.value,'');assert.equal(s.nodes.main.hidden,false);assert.equal(s.counts().updated,1);
 s.nodes.lock.fire('click');assert.equal(s.nodes.main.hidden,true);assert.equal(s.nodes['candle-data'].children.length,0);assert.equal(s.nodes['price-chart'].children.length,0);assert.equal(s.nodes['screen-metrics'].children.length,0);assert.equal(s.nodes.stock.children.length,0);
});
test('analysis exposes stale status separately from genuine historical candles and preserves exact table decimals',async()=>{
 const s=setup();await s.unlock();assert.match(s.nodes['quote-state'].textContent,/stale quote · at last refresh/);assert.match(s.nodes['quote-time'].textContent,/not usable at last refresh/);assert.match(s.nodes['chart-status'].textContent,/not live quotes/);
 assert.match(s.nodes['candle-data'].textContent,/9007199254740993\.1234/);assert.match(s.nodes['candle-data'].textContent,/9007199254740993\.5001/);assert.match(s.nodes['last-price'].textContent,/9,00,71,99,25,47,40,993\.12/);
 assert.equal(s.nodes['price-chart'].children[0].tag,'svg');assert.equal(s.nodes['price-chart'].children[0].attributes.role,'img');assert.match(s.nodes['price-chart'].textContent,/Exact OHLC/);assert.match(s.nodes['chart-source'].textContent,/SIMULATED SOURCE/);assert.match(s.nodes['chart-source'].textContent,/<script>bad/);
 assert.match(s.nodes['screen-state'].textContent,/research candidate · rank 1/);assert.match(s.nodes['screen-metrics'].textContent,/20-session gross return/);
});
test('analysis search filters saved symbols without a request then explicitly opens the chosen real dataset',async()=>{
 const s=setup(async url=>{const data=fixture();if(url.includes('NSE%3ABROAD')){data.symbol='NSE:BROAD';data.quote={status:'NO_ACCEPTED_QUOTE',last:null,usable:false,subscribed:false,detail:'No accepted quote is stored.'};}return ok(data);});
 await s.unlock();s.nodes['stock-search'].value='broad';s.nodes['stock-search'].fire('input');assert.equal(s.calls.length,1);assert.equal(s.nodes.stock.children.length,1);assert.equal(s.nodes.stock.value,'NSE:BROAD');
 s.nodes['open-chart'].fire('click');await flush();assert.equal(s.calls.length,2);assert.match(s.calls[1].url,/symbol=NSE%3ABROAD/);assert.match(s.nodes['chart-title'].textContent,/NSE:BROAD/);assert.match(s.nodes.subscription.textContent,/not in the saved live-feed shortlist/);
 s.nodes.timeframe.value='5m';s.nodes.timeframe.fire('change');await flush();assert.match(s.calls[2].url,/timeframe=5m/);
});
test('missing history draws no fake chart and shows recovery; insufficient averages remain explicit',async()=>{
 const d=fixture();d.bars=[];d.data_state='missing';d.message='No completed candles are saved. Connect market data.';d.screen=null;
 const s=setup(async()=>ok(d));await s.unlock();assert.equal(s.nodes['candle-data'].children.length,0);assert.equal(s.nodes['price-chart'].children[0].tag,'p');assert.match(s.nodes['price-chart'].textContent,/No chart is drawn/);assert.match(s.nodes['chart-status'].textContent,/Connect market data/);assert.match(s.nodes['screen-reasons'].textContent,/No score is invented/);
 const full=setup();await full.unlock();assert.match(full.nodes['candle-data'].textContent,/Not enough bars/);
});
test('minute history exposes unknown provenance without presenting it as certified broker data',async()=>{
 const d=fixture();d.timeframe='1m';d.source={synthetic:null,description:'Saved local completed candles; broker/replay provenance is not certified',price_basis:'Raw OHLC'};d.message='Saved local completed candles. Per-candle broker/replay provenance is not recorded.';
 const s=setup(async()=>ok(d));await s.unlock();assert.match(s.nodes['chart-source'].textContent,/provenance is not certified/);assert.doesNotMatch(s.nodes['chart-source'].textContent,/SIMULATED SOURCE/);assert.match(s.nodes['chart-status'].textContent,/provenance is not recorded/);
});
test('quote usability is explicitly tied to the last refresh and aging does not fetch or change history',async()=>{
 const d=fixture();d.quote.status='USABLE';d.quote.usable=true;d.quote.age_seconds=4;const s=setup(async()=>ok(d));await s.unlock();assert.equal(s.nodes['quote-state'].textContent,'Usable at last refresh');assert.match(s.nodes['quote-time'].textContent,/usable at last refresh/);assert.doesNotMatch(s.nodes['quote-time'].textContent,/usable now/);const chart=s.nodes['price-chart'].children[0];
 s.advance(6001);s.intervals[0]();assert.equal(s.calls.length,1);assert.match(s.nodes.state.textContent,/Display stale/);assert.equal(s.nodes['quote-state'].textContent,'Snapshot stale');assert.match(s.nodes['quote-time'].textContent,/refresh to check current quote usability/);assert.equal(s.nodes['price-chart'].children[0],chart);
});
test('locking discards late analysis responses and aborts reads',async()=>{
 let resolve;const s=setup(()=>new Promise(done=>{resolve=done;}));await s.unlock();assert.equal(s.instance.canNavigate(),false);s.nodes.lock.fire('click');assert.equal(s.calls[0].options.signal.aborted,true);resolve(ok(fixture()));await flush();assert.equal(s.nodes.main.hidden,true);assert.equal(s.nodes['candle-data'].children.length,0);assert.equal(s.instance.canNavigate(),true);
});
test('authorization failure clears prior data and timeout leaves a clear stale display with manual retry',async()=>{
 let auth=false;const s=setup(async()=>auth?{status:403,ok:false}:ok(fixture()));await s.unlock();auth=true;s.nodes.refresh.fire('click');await flush();assert.equal(s.nodes.main.hidden,true);assert.match(s.nodes.message.textContent,/authorization failed/);assert.equal(s.nodes['candle-data'].children.length,0);
 const t=setup(async(_,options)=>new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(Object.assign(Error('aborted'),{name:'AbortError'})))));await t.unlock();t.timeouts[0]();await flush();assert.match(t.nodes.message.textContent,/timed out/);assert.match(t.nodes.state.textContent,/Display stale/);assert.equal(t.calls.length,1);assert.equal(t.instance.canNavigate(),true);
});
