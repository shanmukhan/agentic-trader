'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {createInvestment,compareDecimal}=require('../../src/trading_agent/api/static/investment.js');
class Element {
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.events={};this.children=[];this.attributes={};this.value='';this.disabled=false;}
 set textContent(value){this.text=String(value);this.children=[];}
 get textContent(){return (this.text||'')+this.children.map(child=>child.textContent).join('');}
 set innerHTML(_){throw Error('Unsafe HTML sink');}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.text='';this.children=children;}
 setAttribute(name,value){this.attributes[name]=String(value);}
 addEventListener(type,handler){(this.events[type]||=[]).push(handler);}
 fire(type){if(!this.disabled)for(const handler of this.events[type]||[])handler({preventDefault(){}});}
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const ok=data=>({ok:true,status:200,json:async()=>data});
function fixture(){return {
 schema_version:1,observed_at:'2026-10-22T05:00:00Z',
 capabilities:{fundamentals:{detail:'Fundamentals unavailable'},backtests:{detail:'Browser job execution unavailable'}},
 portfolio:{equity:'9007199254740993.125',available_cash:'20000.005',remaining_cost_basis:'5100.10',net_unrealized_pnl:'-12.3456',cash:'24000.000',day:'2026-10-21',accounting_day_current:false,valuation_state:'stale',valuation_detail:'Saved bids are stale; estimates are not current.',realized_pnl:'1.002',fees:'2.003',reserved_cash:'999.995',day_pnl:'-3.004',day_equity:'25000.00',provenance:{synthetic:true,detail:'Synthetic ledger'},performance:{detail:'Returns and benchmarks unavailable'},limitations:['Paper only'],positions:[{symbol:'NSE:A',quantity:2,cost:'5100.10',liquidation_value:'5087.7544',unrealized_pnl:'-12.3456',stop:'2400',target:'3000',quote:{status:'stale',detail:'Quote too old',exchange_time:'2026-10-21T05:00:00Z'}}]},
 discovery:{state:'available',as_of:'2026-10-22T04:00:00Z',latest_reviewed_completed_session:'2026-10-21',source:{synthetic:true,description:'Invented test source',universe_kind:'fixed'},limitations:['Gross before costs'],rows:Array.from({length:6},(_,i)=>({symbol:'NSE:'+String.fromCharCode(65+i),rank:i+1,status:i===5?'needs_data':'research_candidate',gross_total_return_pct:String(10+i)+'.0000000000000001',daily_volatility_pct:'2.00',average_turnover:'9007199254740993.125',last_close:'123.456',last_session:'2026-10-21',available_at:'2026-10-21T16:00:00Z',observations:60,reasons:i===5?['missing_history']:[],subscribed:i===0}))},
 settings:{mode:'paper',investment_horizon:'long_term',decision_mode:'manual',feed_connected:true,automation_armed:false,local_day:'2026-10-22',entry_start:'09:30',entry_end:'14:30',limits:{max_trade_risk:'62.50',max_quote_age_seconds:5},strategy:{configured:true,mode:'rules',holding_sessions:20},limitations:['Finite holding cap']},
 backtests:{commands:[{label:'Daily help',command:'.venv/bin/trading-agent daily-backtest --help',detail:'Needs reviewed inputs'}],limitations:['No browser jobs']},
 dashboard:{recent_decisions:[{side:'BUY',symbol:'NSE:A',state:'cancelled',updated_at:'2026-10-22T04:00:00Z',outcome:'session_feed_or_risk_pause'}]}
};}
function setup(path='/dashboard',fetcher=async()=>ok(fixture())){
 const html=readFileSync('src/trading_agent/api/static/investment.html','utf8');
 const nodes=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const calls=[],events={},intervals=[];let now=10000;
 const win={location:{pathname:path},Date:{now:()=>now},setTimeout:()=>1,clearTimeout(){},setInterval:handler=>intervals.push(handler),addEventListener:(type,handler)=>{events[type]=handler;}};
 const doc={getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:tag=>new Element(tag)};
 const view=createInvestment(doc,win,async(url,options)=>{calls.push({url,options});return fetcher(url,options);});
 async function unlock(){nodes.token.value='test-operator-token-long-enough-123456789';nodes.access.fire('submit');await flush();}
 return {nodes,calls,events,intervals,win,doc,view,unlock,advance:ms=>{now+=ms;intervals.forEach(handler=>handler());}};
}
function select(s,index,checked=true){const checkbox=s.nodes['research-rows'].children[index].children[0].children[0];checkbox.checked=checked;checkbox.fire('change');return checkbox;}
test('all six new screens are locked until handoff, load only the authenticated read model, and expose one destination',async()=>{
 for(const [path,screen] of [['/dashboard','dashboard'],['/discovery','discovery'],['/holdings','holdings'],['/backtesting','backtesting'],['/settings','settings'],['/learn','learn']]){
  const s=setup(path);assert.equal(s.calls.length,0);assert.equal(s.nodes.main.hidden,true);await s.unlock();
  assert.equal(s.calls.length,1);assert.equal(s.calls[0].url,'/api/workspace/views');
  assert.equal(s.calls[0].options.method,'GET');assert.equal(s.calls[0].options.credentials,'omit');assert.equal(s.calls[0].options.redirect,'error');assert.equal(s.calls[0].options.cache,'no-store');
  assert.equal(s.calls[0].options.headers.Authorization,'Bearer test-operator-token-long-enough-123456789');assert.equal(s.nodes.token.value,'');
  assert.equal(s.nodes.main.hidden,false);for(const name of ['dashboard','discovery','holdings','backtesting','settings','learn'])assert.equal(s.nodes[name+'-view'].hidden,name!==screen);
 }
});
test('Dashboard shows exact values, materialized cancellation and next action without suggesting a completed trade',async()=>{
 const s=setup();await s.unlock();assert.match(s.nodes['dashboard-metrics'].textContent,/₹9,00,71,99,25,47,40,993.125/);assert.match(s.nodes['dashboard-metrics'].textContent,/-₹12.3456/);
 assert.match(s.nodes['recent-decisions'].textContent,/cancelled/);assert.match(s.nodes['recent-decisions'].textContent,/No linked order/);
 assert.match(s.nodes['dashboard-valuation'].textContent,/stale/);assert.equal(s.nodes['next-link'].attributes.href,'/holdings');
 assert.match(s.nodes['performance-coverage'].textContent,/unavailable/);assert.equal(s.calls.length,1);
});
test('Portfolio keeps accounting day, incomplete claims and saved quote coverage explicit without rounding',async()=>{
 const data=fixture();data.portfolio.valuation_state='incomplete';data.portfolio.long_term={unvalued_fractional_claims:1,receivable:'0.00',income_received:'9.001'};
 const s=setup('/holdings',async()=>ok(data));await s.unlock();assert.match(s.nodes['portfolio-metrics'].textContent,/₹999.995/);assert.match(s.nodes['holding-rows'].textContent,/₹5,087.7544/);
 assert.match(s.nodes['holding-rows'].textContent,/Quote too old/);assert.match(s.nodes['valuation-state'].textContent,/incomplete/);assert.match(s.nodes['day-baseline'].textContent,/does not match/);
 assert.match(s.nodes['portfolio-scope'].textContent,/1 · excluded/);assert.match(s.nodes['portfolio-scope'].textContent,/₹9.001/);assert.match(s.nodes['portfolio-performance'].textContent,/unavailable/);
});
test('held allocation preserves exact money and ratio strings with separate commitments and excludes claims',async()=>{
 const data=fixture();data.portfolio.allocation={state:'available',basis:'Actual cash and accepted bid marks; claims excluded.',allocation_base:'9007199254740993.125',cash_balance:'20000.005',cash_weight_pct:'0.0000000002220446604360209025073101',positions:[{symbol:'NSE:A',gross_value:'9007199254720993.120',weight_pct:'99.99999999977795533956397909749269'}],excluded_claims:{dividend_receivable:'17.001',unvalued_fractional_claims:1},commitments:{reserved_cash:'999.995',delivery_fee_buffer:'15.345',pending_order_count:2}};
 const s=setup('/holdings',async()=>ok(data));await s.unlock();
 assert.match(s.nodes['allocation-status'].textContent,/₹9,00,71,99,25,47,40,993.125/);
 assert.match(s.nodes['allocation-rows'].textContent,/99.99999999977795533956397909749269%/);
 assert.match(s.nodes['allocation-rows'].textContent,/0.0000000002220446604360209025073101%/);
 assert.match(s.nodes['allocation-exclusions'].textContent,/₹17.001/);assert.match(s.nodes['allocation-exclusions'].textContent,/claims 1/);
 assert.match(s.nodes['allocation-commitments'].textContent,/₹999.995/);assert.match(s.nodes['allocation-commitments'].textContent,/pending orders 2/);
 assert.equal(s.calls.length,1);s.view.lock();for(const id of ['allocation-rows','allocation-status','allocation-basis','allocation-exclusions','allocation-commitments'])assert.equal(s.nodes[id].textContent,'');
});
test('stale allocation displays its reason and no current weights even if partial numbers are present',async()=>{
 const data=fixture();data.portfolio.allocation={state:'unavailable',reason_codes:['STALE_PRICE'],cash_weight_pct:'90',positions:[{symbol:'NSE:A',weight_pct:'10',gross_value:'100'}]};
 const s=setup('/holdings',async()=>ok(data));await s.unlock();assert.match(s.nodes['allocation-status'].textContent,/unavailable.*stale price/i);assert.equal(s.nodes['allocation-rows'].children.length,0);assert.equal(s.calls.length,1);
});
test('Discovery filters and sorts exact decimal evidence; comparison is bounded and never changes subscriptions',async()=>{
 const data=fixture();data.discovery.rows[0].symbol='NSE:<script>alert(1)</script>';
 const s=setup('/discovery',async()=>ok(data));await s.unlock();assert.equal(s.nodes['research-rows'].children.length,6);assert.match(s.nodes['research-rows'].textContent,/<script>alert/);
 assert.equal(select(s,5).disabled,true);select(s,0);select(s,1);assert.match(s.nodes['comparison-status'].textContent,/2 stocks/);assert.match(s.nodes['comparison-table'].textContent,/₹9,00,71,99,25,47,40,993.125/);
 select(s,2);select(s,3);assert.equal(select(s,4).checked,false);assert.match(s.nodes['comparison-status'].textContent,/at most four/);
 s.nodes['research-search'].value='NSE:B';s.nodes['research-search'].fire('input');assert.equal(s.nodes['research-rows'].children.length,1);assert.match(s.nodes['research-rows'].textContent,/NSE:B/);
 s.nodes['research-search'].value='';s.nodes['research-status'].value='needs_data';s.nodes['research-status'].fire('change');assert.match(s.nodes['research-rows'].textContent,/missing history/);
 s.nodes['clear-comparison'].fire('click');assert.match(s.nodes['comparison-status'].textContent,/0 selected/);assert.equal(s.calls.length,1);
});
test('Discovery explains installed ranking with exact threshold evidence and missing values without changing rank or subscriptions',async()=>{
 const data=fixture();
 data.discovery.ranking={method_id:'legacy-prior-daily-momentum-v1',detail:'Explains the installed screen; no new score or eligibility decision is calculated.',tie_rule:'Candidate returns descending, then symbol ascending; existing ranks are retained.',thresholds:{momentum_sessions:'20',trend_sessions:'50',min_average_turnover:'10000000.00',max_daily_volatility_pct:'5.0000'}};
 Object.assign(data.discovery.rows[0],{status:'screened_out',rank:null,reasons:['BELOW_TREND_AVERAGE'],equity_share_class_reviewed:true,index_level:'9007199254740993.12340001',trend_index_average:'9007199254740993.12340002',evidence:[{metric:'index_level',observed:'9007199254740993.12340001',threshold:'9007199254740993.12340002',rule:'index_level >= trend_index_average',state:'failed',detail:'Equality passes; this exact index is below the threshold.'}]});
 data.discovery.rows[1].evidence=[{metric:'gross_total_return_pct',observed:'0.0000000000000000000000001',threshold:'0',rule:'gross_total_return_pct > 0',state:'passed',detail:'20 completed sessions; zero fails.'}];
 Object.assign(data.discovery.rows[2],{status:'screened_out',rank:null,reasons:['EQUITY_SHARE_CLASS_NOT_REVIEWED'],equity_share_class_reviewed:false,evidence:[{metric:'equity_share_class_reviewed',observed:'not_reviewed',threshold:'reviewed',rule:'Reviewed equity share class required',state:'failed',detail:'A numeric screen pass does not supply a share-class review.'}]});
 data.discovery.rows[5].evidence=[{metric:'average_turnover',observed:null,threshold:null,rule:'average_turnover >= min_average_turnover <script>not HTML</script>',state:'unavailable',detail:'A finite exact observed value or threshold is missing.'}];
 const original=structuredClone(data);const s=setup('/discovery',async()=>ok(data));await s.unlock();
 const rowFor=symbol=>s.nodes['research-rows'].children.find(row=>row.children[1].textContent.startsWith(symbol));
 const below=rowFor('NSE:A');assert.match(below.textContent,/index level: failed\. Observed 9007199254740993\.12340001; rule index_level >= trend_index_average; threshold 9007199254740993\.12340002/);assert.equal(below.children[2].textContent,'—');assert.match(below.textContent,/screened out/);
 const passing=rowFor('NSE:B');assert.match(passing.textContent,/gross total return pct: passed\. Observed 0\.0000000000000000000000001/);assert.match(passing.textContent,/threshold 0\. 20 completed sessions; zero fails/);assert.equal(passing.children[2].textContent,'2');
 assert.match(rowFor('NSE:C').textContent,/equity share class reviewed: failed/);assert.match(rowFor('NSE:F').textContent,/average turnover: unavailable\. Observed unavailable/);assert.match(rowFor('NSE:F').textContent,/threshold unavailable/);assert.match(rowFor('NSE:F').textContent,/<script>not HTML<\/script>/);
 assert.match(s.nodes['research-limitations'].textContent,/no new score or eligibility decision/);assert.match(s.nodes['research-limitations'].textContent,/symbol ascending; existing ranks are retained/);
 s.nodes['research-search'].value='NSE:A';s.nodes['research-search'].fire('input');s.nodes['research-search'].value='';s.nodes['research-search'].fire('input');select(s,0);select(s,1);assert.equal(s.calls.length,1);assert.equal(s.calls[0].options.method,'GET');assert.deepEqual(data,original);
 s.events.pagehide();assert.equal(s.nodes['research-rows'].textContent,'');assert.equal(s.nodes['research-limitations'].textContent,'');
});
test('comparison refuses unlike coverage and refresh clears old selections',async()=>{
 const data=fixture();data.discovery.rows[1].last_session='2026-10-20';const s=setup('/discovery',async()=>ok(data));await s.unlock();select(s,0);select(s,1);
 assert.match(s.nodes['comparison-status'].textContent,/not have the same/);assert.equal(s.nodes['comparison-table'].children.length,0);
 s.nodes.refresh.fire('click');await flush();assert.match(s.nodes['comparison-status'].textContent,/0 selected/);assert.equal(s.calls.length,2);
});
test('exact ordering handles negative, fractional and unsafe integer values without Number conversion',()=>{
 assert.ok(compareDecimal('9007199254740993.125','9007199254740993.124999999999')>0);
 assert.ok(compareDecimal('-0.0001','-0.00001')<0);assert.equal(compareDecimal('-000.000','0'),0);assert.equal(compareDecimal('01.20','1.2'),0);
 assert.ok(compareDecimal('2',null)<0);
});
test('Settings, CLI guidance and learning describe available behavior without writable or fabricated workflows',async()=>{
 const settings=setup('/settings');await settings.unlock();assert.match(settings.nodes['settings-limits'].textContent,/₹62.50/);assert.match(settings.nodes['settings-summary'].textContent,/20 holding sessions/);
 const b=setup('/backtesting');await b.unlock();assert.match(b.nodes['backtest-commands'].textContent,/daily-backtest --help/);assert.match(b.nodes['backtest-state'].textContent,/unavailable/);
 const l=setup('/learn');await l.unlock();l.nodes['lesson-search'].value='approval';l.nodes['lesson-search'].fire('input');assert.ok(l.nodes.lessons.children.length>0);assert.match(l.nodes.lessons.textContent,/Cancelled proposals/);
 l.nodes['lesson-search'].value='unmatchable';l.nodes['lesson-search'].fire('input');assert.equal(l.nodes.lessons.children.length,0);assert.match(l.nodes['lesson-count'].textContent,/No concepts/);
 for(const s of [settings,b,l])assert.equal(s.calls.length,1);
});
test('pending reads guard navigation and locking aborts and discards late private responses',async()=>{
 let resolve;const s=setup('/dashboard',()=>new Promise(r=>{resolve=r;}));await s.unlock();assert.equal(s.view.canNavigate(),false);assert.equal(s.nodes.refresh.disabled,true);
 const signal=s.calls[0].options.signal;s.view.lock();assert.equal(signal.aborted,true);resolve(ok(fixture()));await flush();assert.equal(s.nodes.main.hidden,true);assert.equal(s.nodes['dashboard-metrics'].textContent,'');assert.equal(s.nodes.token.value,'');assert.equal(s.view.canNavigate(),true);
});
test('pagehide clears all private fields, selections and late JSON and cannot restore after a new unlock',async()=>{
 let finish;let read=0;const s=setup('/discovery',async()=>++read===1?{ok:true,status:200,json:()=>new Promise(r=>{finish=r;})}:ok(fixture()));await s.unlock();s.events.pagehide();await s.unlock();
 select(s,0);select(s,1);assert.match(s.nodes['comparison-status'].textContent,/2 stocks/);finish(fixture());await flush();assert.match(s.nodes['comparison-status'].textContent,/2 stocks/);
 s.events.pagehide();assert.equal(s.nodes.main.hidden,true);for(const id of ['research-rows','portfolio-metrics','settings-summary','lessons','research-source','day-baseline'])assert.equal(s.nodes[id].textContent,'',id);
 assert.match(s.nodes['comparison-status'].textContent,/Select two to four/);
});
test('failed refresh preserves values only as explicitly stale; authorization rejection clears them',async()=>{
 let mode='ok';const s=setup('/holdings',async()=>mode==='ok'?ok(fixture()):mode==='error'?{ok:false,status:503}:{ok:false,status:401});await s.unlock();s.advance(6001);assert.match(s.nodes.state.textContent,/stale/);
 mode='error';s.nodes.refresh.fire('click');await flush();assert.match(s.nodes.message.textContent,/could not be loaded/);assert.match(s.nodes.state.textContent,/stale/);assert.match(s.nodes['holding-rows'].textContent,/NSE:A/);
 mode='auth';s.nodes.refresh.fire('click');await flush();assert.equal(s.nodes.main.hidden,true);assert.equal(s.nodes['holding-rows'].textContent,'');assert.match(s.nodes.message.textContent,/authorization failed/);
});
test('missing research, holdings and invalid schema stay honest; no network actions are exposed',async()=>{
 const data=fixture();data.discovery={state:'missing',rows:[],limitations:[]};data.portfolio.positions=[];data.portfolio.positions_truncated=false;
 const d=setup('/discovery',async()=>ok(data));await d.unlock();assert.match(d.nodes['research-context'].textContent,/No saved/);assert.match(d.nodes['research-rows'].textContent,/No saved research rows/);assert.match(d.nodes['fundamental-state'].textContent,/unavailable/);
 const p=setup('/holdings',async()=>ok(data));await p.unlock();assert.match(p.nodes['holdings-status'].textContent,/No held shares/);
 const invalid=setup('/dashboard',async()=>ok({schema_version:2}));await invalid.unlock();assert.equal(invalid.nodes.main.hidden,true);assert.match(invalid.nodes.message.textContent,/could not be loaded/);
});
