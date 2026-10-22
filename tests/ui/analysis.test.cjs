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
 const calls=[],timeouts=[],intervals=[],events={};let locked=0,updated=0,now=1000;
 const doc={getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)};
 const win={Date:{now:()=>now},setTimeout:fn=>{timeouts.push(fn);return timeouts.length;},clearTimeout(){},setInterval:fn=>intervals.push(fn),addEventListener:(name,fn)=>{(events[name]||=[]).push(fn);},AgenticNavigation:{locked(){locked++;},updated(){updated++;}}};
 const instance=createAnalysis(doc,win,async(url,options)=>{calls.push({url,options});return fetcher(url,options);});
 async function unlock(){nodes.token.value='analysis-ephemeral-operator-token';nodes.access.fire('submit');await flush();}
 return{nodes,calls,timeouts,intervals,instance,unlock,fire:name=>{for(const fn of events[name]||[])fn();},advance:ms=>{now+=ms;},counts:()=>({locked,updated})};
}
test('analysis starts locked and performs authenticated GET only with no token persistence',async()=>{
 const s=setup();assert.equal(s.calls.length,0);assert.equal(s.nodes.main.hidden,true);await s.unlock();
 assert.equal(s.calls.length,1);assert.equal(s.calls[0].options.method,'GET');assert.equal(s.calls[0].options.cache,'no-store');assert.equal(s.calls[0].options.credentials,'omit');assert.equal(s.calls[0].options.redirect,'error');
 assert.match(s.calls[0].url,/^\/api\/research\/series\?/);
 assert.match(s.calls[0].options.headers.Authorization,/Bearer analysis-ephemeral/);assert.equal(s.nodes.token.value,'');assert.equal(s.nodes.main.hidden,false);assert.equal(s.counts().updated,1);
 s.nodes.lock.fire('click');assert.equal(s.nodes.main.hidden,true);assert.equal(s.nodes['candle-data'].children.length,0);assert.equal(s.nodes['price-chart'].children.length,0);assert.equal(s.nodes['screen-metrics'].children.length,0);assert.equal(s.nodes.stock.children.length,0);
});
function researchFixture(){
 const data=fixture();data.source.price_basis='Causal share-adjusted OHLC and adjusted share volume';data.research={formula_version:'research-v1',basis:'causal_share_adjusted_ohlc',indicator_status:{sma20:{value:'9007199254740993.50010001',state:'available',reason:'20 completed daily candles',basis:'causal_share_adjusted_ohlc',lookback:20,available_at:'2026-10-21T10:00:00Z'},sma200:{value:null,state:'warming_up',reason:'200 completed daily candles required; 40 available.',basis:'causal_share_adjusted_ohlc',lookback:200,available_at:null},rsi14:{value:'0.00000000000001',state:'available',reason:'Wilder calculation',basis:'causal_share_adjusted_ohlc',lookback:14,available_at:'2026-10-21T10:00:00Z'},drawdown_pct:{value:'-2.00000000000001',state:'available',basis:'gross_total_return_index',lookback:null,available_at:'2026-10-21T10:00:00Z'}},coverage:{calendar_verified:false,detail:'No independently reviewed holiday calendar is saved.'},partial_periods:[{period:'2026-10',state:'partial',reason:'Month is still open.',observations:15,expected_sessions:null}],benchmark:{state:'unavailable',relative_strength_pct:null,reason:'No matching benchmark input.',detail:'Coverage does not align.'},fundamentals:{state:'unavailable',reason:'No licensed statement provider configured.'},explanations:['A split adjusts the share-price history; cash dividends belong to the separate total-return index.']};return data;
}
test('daily, weekly and monthly research use the new read-only resource while minute intervals retain the legacy resource',async()=>{
 const s=setup(async url=>{const data=researchFixture();data.timeframe=new URL(url,'http://localhost').searchParams.get('timeframe');return ok(data);});await s.unlock();
 for(const [interval,title,endpoint]of [['1w','Weekly','research/series'],['1mo','Monthly','research/series'],['1m','1-minute','analysis'],['5m','5-minute','analysis'],['1d','Daily','research/series']]){
  s.nodes.timeframe.value=interval;s.nodes.timeframe.fire('change');await flush();assert.match(s.calls.at(-1).url,new RegExp('^/api/'+endpoint+'\\?timeframe='+interval));assert.match(s.nodes['chart-title'].textContent,new RegExp(title));
 }
 assert.ok(s.calls.every(call=>call.options.method==='GET'));assert.equal(s.calls.length,6);
});
test('research preserves exact decimal evidence and shows indicator warmup, definitions, basis and coverage',async()=>{
 const s=setup(async()=>ok(researchFixture()));await s.unlock();
 assert.match(s.nodes['research-indicators'].textContent,/9007199254740993\.50010001/);assert.match(s.nodes['research-indicators'].textContent,/0\.00000000000001/);assert.match(s.nodes['research-indicators'].textContent,/Warming up200 completed daily candles required; 40 available/);
 assert.match(s.nodes['indicator-data'].textContent,/-2\.00000000000001%/);assert.match(s.nodes['indicator-data'].textContent,/gross_total_return_index/);assert.match(s.nodes['indicator-data'].textContent,/not benchmark relative strength/);assert.match(s.nodes['indicator-data'].textContent,/Not recorded/);assert.match(s.nodes['research-basis'].textContent,/Formula version research-v1/);assert.match(s.nodes['research-basis'].textContent,/causal_share_adjusted_ohlc/);
 assert.equal(s.nodes['indicator-data'].children.length,15);assert.equal(s.nodes['indicator-data'].children[0].children[0].attributes.scope,'row');
 assert.match(s.nodes['research-coverage'].textContent,/review is unavailable/);assert.match(s.nodes['research-coverage'].textContent,/No independently reviewed/);assert.match(s.nodes['partial-periods'].textContent,/2026-10 · partial · 15 observed sessions; expected sessions unavailable · Month is still open/);
 assert.match(s.nodes['benchmark-state'].textContent,/unavailable/);assert.doesNotMatch(s.nodes['benchmark-state'].textContent,/0%/);assert.match(s.nodes['benchmark-detail'].textContent,/No matching benchmark input/);assert.match(s.nodes['fundamentals-state'].textContent,/No licensed statement provider/);assert.match(s.nodes['research-explanations'].textContent,/separate total-return index/);assert.match(s.nodes['data-caption'].textContent,/Causal share-adjusted OHLC and adjusted share volume/);
});
test('benchmark comparisons show exact percentages and provider metadata as text without suggesting certified source acceptance',async()=>{
 const data=researchFixture();data.research.coverage={calendar_verified:true,detail:'Calendar completeness is a local review assertion; not external certification.'};data.research.benchmark={state:'available',relative_strength_pct:'-0.00000000000001',detail:'Same saved observation window.',metadata:{synthetic:true,title:'Test benchmark <script>unsafe()</script>',provider:'Synthetic fixture',source_url:'https://example.invalid/input',input_identity:{sha256:'fixture-only'}}};
 const s=setup(async()=>ok(data));await s.unlock();assert.equal(s.nodes['benchmark-state'].textContent,'SIMULATED BENCHMARK · Relative strength: -0.00000000000001%');assert.match(s.nodes['benchmark-detail'].textContent,/<script>unsafe/);assert.match(s.nodes['benchmark-detail'].textContent,/Synthetic fixture/);assert.match(s.nodes['benchmark-detail'].textContent,/fixture-only/);assert.match(s.nodes['research-coverage'].textContent,/review recorded for the saved inputs/);assert.match(s.nodes['research-coverage'].textContent,/not external certification/);
});
test('chart display ranges slice saved candles without fetching or reseeding exact indicators',async()=>{
 const data=researchFixture();data.source.volume_basis='Known share actions applied; adjusted share units';data.bars=Array.from({length:120},(_,i)=>({time:new Date(Date.UTC(2026,0,i+1,10)).toISOString(),session:new Date(Date.UTC(2026,0,i+1)).toISOString().slice(0,10),open:'100',high:'105',low:'99',close:'103.00000000000000001',volume:'1000.00001',sma20:'101.00000000000000001',sma50:'100.00000000000000001'}));
 const s=setup(async()=>ok(data));assert.equal(s.nodes['chart-range'].disabled,true);assert.equal(s.nodes['chart-range'].value,'all');await s.unlock();assert.equal(s.nodes['chart-range'].disabled,false);assert.equal(s.nodes['candle-data'].children.length,120);const cards=s.nodes['research-indicators'].textContent;
 for(const [value,count]of [['50',50],['100',100],['all',120]]){s.nodes['chart-range'].value=value;s.nodes['chart-range'].fire('change');assert.equal(s.calls.length,1);assert.equal(s.nodes['candle-data'].children.length,count);assert.equal(s.nodes['candle-data'].children[0].children[6].textContent,'101.00000000000000001');assert.equal(s.nodes['research-indicators'].textContent,cards);assert.match(s.nodes['chart-count'].textContent,new RegExp('^'+count+' of 120 returned candles'));assert.match(s.nodes['chart-period'].textContent,/preserves the saved indicator values and their full history seed/);}
 assert.match(s.nodes['data-caption'].textContent,/adjusted share units/);assert.match(s.nodes['chart-source'].textContent,/Volume: Known share actions applied/);s.instance.lock();assert.equal(s.nodes['chart-range'].disabled,true);assert.equal(s.nodes['chart-range'].value,'all');assert.equal(s.nodes['candle-data'].children.length,0);assert.equal(s.calls.length,1);
});
test('accessible candle history retains exact SMA200 and changing drawdowns; absent minute history is unavailable and lock clears it',async()=>{
 const data=researchFixture();Object.assign(data.bars[0],{sma200:'9007199254740993.12340000000001',drawdown_pct:'-0.0000000000000000000000001',max_drawdown_pct:'-3.0000000000000000000000001'});Object.assign(data.bars[1],{sma200:'9007199254740993.12340000000002',drawdown_pct:'0',max_drawdown_pct:'-3.0000000000000000000000001'});
 const s=setup(async()=>ok(data));await s.unlock();const rows=s.nodes['candle-data'].children;assert.equal(rows[0].children[8].textContent,'9007199254740993.12340000000002');assert.equal(rows[1].children[8].textContent,'9007199254740993.12340000000001');assert.equal(rows[0].children[9].textContent,'0');assert.equal(rows[1].children[9].textContent,'-0.0000000000000000000000001');assert.equal(rows[0].children[10].textContent,'-3.0000000000000000000000001');
 s.nodes['chart-range'].value='50';s.nodes['chart-range'].fire('change');assert.equal(s.nodes['candle-data'].children[1].children[9].textContent,'-0.0000000000000000000000001');assert.equal(s.calls.length,1);s.nodes.lock.fire('click');assert.equal(s.nodes['candle-data'].children.length,0);assert.equal(s.calls.length,1);
 const legacy=setup();await legacy.unlock();for(const index of [8,9,10])assert.equal(legacy.nodes['candle-data'].children[0].children[index].textContent,'Unavailable');
 const html=readFileSync('src/trading_agent/api/static/analysis.html','utf8'),regions=[...html.matchAll(/<div class="analysis-table-wrap"([^>]+)>/g)];assert.equal(regions.length,2);for(const region of regions){assert.match(region[1],/role="region"/);assert.match(region[1],/tabindex="0"/);assert.match(region[1],/aria-label="[^"]+horizontally scrollable"/);}
});
test('actual series warmup reason codes, unavailable fundamentals and bounded period coverage remain understandable',async()=>{
 const data=researchFixture();data.research.indicator_status.sma200={value:null,state:'warming_up',reason:'INSUFFICIENT_CONSECUTIVE_HISTORY',first_valid_bar:200,lookback:200,basis:'Causal share-adjusted OHLC',available_at:'2026-10-21T10:00:00Z'};data.research.partial_periods_truncated=true;data.research.partial_period_limit=24;data.research.fundamentals={state:'unavailable',reason:'LICENSED_SOURCE_NOT_CONFIGURED'};
 const s=setup(async()=>ok(data));await s.unlock();assert.match(s.nodes['research-indicators'].textContent,/Needs 200 consecutive completed candles at this interval/);assert.match(s.nodes['partial-periods'].textContent,/Only the latest 24 excluded periods are returned/);assert.match(s.nodes['fundamentals-state'].textContent,/A licensed company-data source is not configured/);
});
test('moving-average chart segments break at explicit gaps and missing optional keys do not become zero or invalidate candles',async()=>{
 const data=researchFixture();data.bars=Array.from({length:5},(_,i)=>({time:'2026-10-'+String(i+12).padStart(2,'0')+'T10:00:00Z',session:'2026-10-'+String(i+12).padStart(2,'0'),open:'100',high:'105',low:'98',close:'103',volume:'1000',sma20:String(100+i),segment_break:i===2}));
 const s=setup(async()=>ok(data));await s.unlock();const svg=s.nodes['price-chart'].children[0];assert.equal(svg.tag,'svg');const lines=svg.children.filter(n=>n.tag==='polyline');assert.equal(lines.length,2);assert.equal(lines[0].attributes.points.split(' ').length,2);assert.equal(lines[1].attributes.points.split(' ').length,3);assert.ok(lines.every(n=>n.attributes.class==='indicator-line'));assert.match(svg.textContent,/explicit segment boundaries/);
});
test('pagehide clears all private research evidence and rejects JSON completed after locking',async()=>{
 let resolveJson;const s=setup(async()=>({ok:true,status:200,json:()=>new Promise(resolve=>{resolveJson=resolve;})}));await s.unlock();assert.equal(s.instance.canNavigate(),false);s.fire('pagehide');assert.equal(s.calls[0].options.signal.aborted,true);resolveJson(researchFixture());await flush();assert.equal(s.nodes.main.hidden,true);assert.equal(s.nodes['indicator-data'].children.length,0);assert.equal(s.nodes['research-indicators'].children.length,0);assert.equal(s.nodes['research-basis'].textContent,'');assert.equal(s.nodes['benchmark-detail'].textContent,'');assert.equal(s.instance.canNavigate(),true);
 const loaded=setup(async()=>ok(researchFixture()));await loaded.unlock();loaded.fire('pagehide');for(const id of ['indicator-data','research-indicators','partial-periods','research-explanations'])assert.equal(loaded.nodes[id].children.length,0);for(const id of ['research-basis','research-coverage','benchmark-state','benchmark-detail','fundamentals-state'])assert.equal(loaded.nodes[id].textContent,'');
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
