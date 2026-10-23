(function () {
'use strict';
const SVG='http://www.w3.org/2000/svg';
const money=typeof module!=='undefined'&&module.exports?require('./money.js'):window.AgenticMoney;
const indicatorDefinitions=[
 ['sma20','SMA 20','Mean close over 20 completed candles.'],['sma50','SMA 50','Mean close over 50 completed candles.'],['sma200','SMA 200','Mean close over 200 completed candles.'],
 ['ema12','EMA 12','Exponential average of completed closes with period 12, seeded by a 12-candle mean.'],['ema26','EMA 26','Exponential average of completed closes with period 26, seeded by a 26-candle mean.'],
 ['rsi14','RSI 14','Wilder relative strength index from 14 close differences; this is not benchmark relative strength.'],
 ['macd','MACD','EMA 12 minus EMA 26.'],['macd_signal','MACD signal','Nine-period exponential average of valid MACD values, seeded by their mean.'],['macd_histogram','MACD histogram','MACD minus its signal line.'],
 ['atr14','ATR 14','Wilder average true range over 14 close differences, including gaps from the previous close; expressed in candle price units.'],
 ['support20','Support 20','Lowest low of the prior 20 candles, excluding the current candle; a historical range, not a guaranteed price floor.'],['resistance20','Resistance 20','Highest high of the prior 20 candles, excluding the current candle; a historical range, not a guaranteed price ceiling.'],
 ['drawdown_pct','Drawdown','Close relative to the running peak close since the current continuous segment began, in percent.'],['max_drawdown_pct','Maximum drawdown','Most negative drawdown since the current continuous segment began, on the stated basis.'],['volatility20_pct','Volatility 20','Population standard deviation of 20 consecutive simple close returns, in percent. This value is not annualized.']
];
function createAnalysis(doc,win,fetcher){
 const el=id=>doc.getElementById(id),node=(tag,text)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=String(text);return n;};
 const svgNode=(tag,attrs,text)=>{const n=doc.createElementNS(SVG,tag);for(const [key,value]of Object.entries(attrs))n.setAttribute(key,String(value));if(text!==undefined)n.textContent=String(text);return n;};
 let token='',generation=0,active=null,busy=false,latest=null,options=[],lastReceipt=0;
 const clock=()=>win.Date?win.Date.now():Date.now();
 const date=value=>value?new Date(value).toLocaleString('en-IN',{timeZone:'Asia/Kolkata',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}):'—';
 const friendly=value=>String(value||'').toLowerCase().replaceAll('_',' ');
 function controls(){for(const id of ['stock','timeframe','open-chart','refresh','stock-search'])el(id).disabled=!token||busy;el('chart-range').disabled=!token||busy||!latest;el('unlock').disabled=busy;el('open-chart').disabled=!token||busy||!el('stock').children.length;}
 function lock(){
  if(win.AgenticNavigation)win.AgenticNavigation.locked();generation++;active?.abort();active=null;token='';busy=false;latest=null;options=[];lastReceipt=0;
  el('token').value='';el('token').required=true;el('lock').disabled=true;el('main').hidden=true;el('stock-search').value='';el('timeframe').value='1d';el('chart-range').value='all';
  for(const id of ['stock','price-chart','screen-metrics','candle-data','limitations','research-indicators','indicator-data','partial-periods','research-explanations'])el(id).replaceChildren();
  for(const id of ['last-price','quote-state','screen-state','session-state'])el(id).textContent='—';
  for(const id of ['quote-time','quote-detail','subscription','chart-status','chart-source','chart-period','screen-reasons','screen-date','chart-count','updated','research-basis','research-coverage','benchmark-state','benchmark-detail','fundamentals-state'])el(id).textContent='';
  el('indicator-caption').textContent='Latest completed-candle indicator values';
  el('chart-title').textContent='Saved candles';el('data-caption').textContent='Saved OHLC and volume';el('state').textContent='Locked';el('message').textContent='Locked. No private market data loaded.';el('message').className='';controls();
 }
 function stockOptions(selected){
  const query=el('stock-search').value.trim().toUpperCase();el('stock').replaceChildren();
  const filtered=options.filter(item=>item.symbol.toUpperCase().includes(query));
  for(const item of filtered){const option=node('option',item.symbol+(item.subscribed?' · subscribed':''));option.value=item.symbol;el('stock').append(option);}
  if(filtered.some(item=>item.symbol===selected))el('stock').value=selected;
  else if(filtered.length)el('stock').value=filtered[0].symbol;else el('stock').value='';
  el('stock-help').textContent=filtered.length?filtered.length+' saved stocks match. Select Open chart to view a result. Charts never download data or change subscriptions.':options.length?'No saved stocks match this search. Clear the search to see all available stocks.':'No saved stocks are available. Prepare reviewed history in Strategies or select stocks in Broker & Data, then refresh.';controls();
 }
 function chart(bars,symbol,timeframe){
  el('price-chart').replaceChildren();if(!bars.length){el('price-chart').append(node('p','No chart is drawn until real completed candles are available.'));return;}
  const optional=value=>value===null||value===undefined||value===''?null:Number(value);
  const numeric=bars.map(b=>({open:Number(b.open),high:Number(b.high),low:Number(b.low),close:Number(b.close),volume:Number(b.volume),sma20:optional(b.sma20),sma50:optional(b.sma50),sma200:optional(b.sma200)}));
  const values=numeric.flatMap(b=>[b.high,b.low,...[b.sma20,b.sma50,b.sma200].filter(v=>v!==null)]);
  if(!values.every(Number.isFinite)||!numeric.every(b=>Number.isFinite(b.volume)&&b.volume>=0)){el('price-chart').append(node('p','Chart coordinates could not be rendered. Inspect the exact saved candle table below.'));return;}
  const W=920,H=420,L=68,R=20,T=20,P=286,V=370,B=400,width=W-L-R,step=width/bars.length;
  let min=Math.min(...values),max=Math.max(...values);const pad=(max-min)*.08||Math.abs(max)*.005||1;min-=pad;max+=pad;
  const y=value=>T+(max-value)/(max-min)*(P-T),x=index=>L+(index+.5)*step,maxVolume=Math.max(...numeric.map(b=>b.volume),1);
  const svg=svgNode('svg',{viewBox:'0 0 '+W+' '+H,role:'img','aria-labelledby':'price-chart-title price-chart-description',width:'100%'});
  svg.append(svgNode('title',{id:'price-chart-title'},symbol+' '+timeframe+' saved candlestick chart'));
  svg.append(svgNode('desc',{id:'price-chart-description'},bars.length+' completed candles with available SMA 20, SMA 50, SMA 200 and volume. Exact OHLC, volume and averages are in the accessible data tables below. Moving-average lines break at missing intervals and explicit segment boundaries.'));
  for(let line=0;line<=4;line++){const value=min+(max-min)*line/4,yy=y(value);svg.append(svgNode('line',{x1:L,y1:yy,x2:W-R,y2:yy,class:'chart-grid'}));svg.append(svgNode('text',{x:L-9,y:yy+4,'text-anchor':'end',class:'chart-label'},value.toLocaleString('en-IN',{maximumFractionDigits:2})));}
  svg.append(svgNode('text',{x:L,y:P+25,class:'chart-label'},'VOLUME'));
  for(let i=0;i<bars.length;i++){
   const b=numeric[i],xx=x(i),bw=Math.max(.8,Math.min(11,step*.65)),cls=b.close>=b.open?'candle-up':'candle-down';
   const g=svgNode('g',{});g.append(svgNode('title',{},date(bars[i].time)+' IST · O '+bars[i].open+' H '+bars[i].high+' L '+bars[i].low+' C '+bars[i].close+' · volume '+bars[i].volume));
   g.append(svgNode('line',{x1:xx,y1:y(b.high),x2:xx,y2:y(b.low),class:cls}));
   g.append(svgNode('rect',{x:xx-bw/2,y:Math.min(y(b.open),y(b.close)),width:bw,height:Math.max(1,Math.abs(y(b.open)-y(b.close))),class:cls}));
   g.append(svgNode('rect',{x:xx-bw/2,y:V-b.volume/maxVolume*45,width:bw,height:b.volume/maxVolume*45,class:'volume-bar'}));svg.append(g);
  }
  for(const [key,cls]of [['sma20','indicator-line'],['sma50','indicator-line indicator-long'],['sma200','indicator-line indicator-longest']]){
   let points=[];const flush=()=>{if(points.length>1)svg.append(svgNode('polyline',{points:points.join(' '),class:cls,fill:'none'}));points=[];};
   numeric.forEach((b,i)=>{if(bars[i].segment_break)flush();if(b[key]===null)flush();else points.push(x(i)+','+y(b[key]));});flush();
  }
  const indices=[...new Set([0,Math.floor((bars.length-1)/2),bars.length-1])];
  for(const i of indices)svg.append(svgNode('text',{x:x(i),y:B,'text-anchor':i===0?'start':i===bars.length-1?'end':'middle',class:'chart-label'},['1d','1w','1mo'].includes(timeframe)?bars[i].session:date(bars[i].time)));
  el('price-chart').append(svg);
 }
 function renderResearch(data){
  const research=data.research,states=research?.indicator_status||{},last=data.bars.at(-1),basis=research?.basis||data.source?.price_basis||'Basis not recorded';
  el('research-basis').textContent=(research?.formula_version?'Formula version '+research.formula_version+'. ':'')+'Basis: '+basis+'. Values use completed saved candles at the selected interval.';
  el('research-indicators').replaceChildren();el('indicator-data').replaceChildren();
  const headline=new Set(['sma20','sma50','sma200','rsi14','macd','atr14']);
  for(const [key,label,definition]of indicatorDefinitions){
   const supplied=states[key],legacyValue=!research?last?.[key]:undefined;
   const item=supplied||{state:legacyValue===null||legacyValue===undefined?'unavailable':'available',value:legacyValue,reason:research?'This indicator is not available for this series.':'Detailed indicator availability is not recorded for this saved dataset.',basis,lookback:null,available_at:null};
   const available=item.state==='available'&&item.value!==null&&item.value!==undefined;
   const state=available?'Available':item.state==='warming_up'?'Warming up':'Unavailable';
   const value=available?String(item.value)+(key.endsWith('_pct')?'%':''):state;
   const reason=item.reason==='INSUFFICIENT_CONSECUTIVE_HISTORY'?'Needs '+(item.first_valid_bar||'more')+' consecutive completed candles at this interval.':item.reason==='NO_COMPLETE_BARS'?'No complete candles are available.':item.reason;
   if(headline.has(key)){const card=node('div');card.append(node('span',label),node('strong',value),node('p',available?'Available on the stated basis.':reason||state));el('research-indicators').append(card);}
   const row=node('tr'),meaning=node('th');meaning.setAttribute('scope','row');meaning.append(node('strong',label),node('p',definition));row.append(meaning);
   for(const text of [value,state+(reason?' · '+reason:''),item.lookback===null||item.lookback===undefined?'Not recorded':String(item.lookback),item.basis||basis,item.available_at?date(item.available_at):'Not recorded'])row.append(node('td',text));
   el('indicator-data').append(row);
  }
  el('indicator-caption').textContent=(data.symbol||'No stock selected')+' · latest completed '+({ '1d':'daily','1w':'weekly','1mo':'monthly','1m':'one-minute','5m':'five-minute'}[data.timeframe]||'saved')+' candle indicators';
  const coverage=research?.coverage;
  el('research-coverage').textContent=coverage?(coverage.calendar_verified?'Calendar completeness review recorded for the saved inputs. ':'Calendar completeness review is unavailable. ')+(coverage.detail||'Review the saved session evidence before interpreting this history.'):'Detailed calendar coverage is unavailable for this saved dataset.';
  el('partial-periods').replaceChildren();for(const period of research?.partial_periods||[]){const observations=period.observations===undefined?'':String(period.observations)+' observed sessions',expected=period.expected_sessions===null||period.expected_sessions===undefined?'expected sessions unavailable':String(period.expected_sessions)+' expected sessions';el('partial-periods').append(node('li',String(period.period)+' · '+friendly(period.state)+' · '+[observations,expected].filter(Boolean).join('; ')+(period.reason?' · '+period.reason:'')));}
  if(research?.partial_periods_truncated)el('partial-periods').append(node('li','Only the latest '+(research.partial_period_limit||research.partial_periods.length)+' excluded periods are returned; earlier period details are not shown.'));
  const benchmark=research?.benchmark;
  el('benchmark-state').textContent=(benchmark?.metadata?.synthetic===true?'SIMULATED BENCHMARK · ':'')+(benchmark?.state==='available'&&benchmark.relative_strength_pct!==null&&benchmark.relative_strength_pct!==undefined?'Relative strength: '+String(benchmark.relative_strength_pct)+'%':'Benchmark comparison unavailable');
  const metadata=benchmark?.metadata?Object.entries(benchmark.metadata).map(([key,value])=>friendly(key)+': '+(typeof value==='object'?JSON.stringify(value):String(value))).join(' · '):'';
  el('benchmark-detail').textContent=[benchmark?.reason,benchmark?.detail,metadata].filter(Boolean).join(' · ')||'No matching benchmark history is available. A missing comparison is not a zero return.';
  el('fundamentals-state').textContent='Unavailable · '+(research?.fundamentals?.reason==='LICENSED_SOURCE_NOT_CONFIGURED'?'A licensed company-data source is not configured.':research?.fundamentals?.reason||'Company fundamentals are not available from the saved price series.');
  el('research-explanations').replaceChildren();for(const explanation of research?.explanations||[])el('research-explanations').append(node('li',explanation));
 }
 function renderChart(data){
  const range=el('chart-range').value,limit=range==='50'?50:range==='100'?100:null,bars=limit?data.bars.slice(-limit):data.bars;
  el('chart-count').textContent=bars.length+' of '+data.bars.length+' returned candles'+(data.truncated?' · response capped at '+data.bar_limit:'');
  el('chart-period').textContent=(bars.length?'Displayed interval: '+date(bars[0].time)+' to '+date(bars.at(-1).time)+' IST. ':'')+(data.excluded_candles?data.excluded_candles+' low-quality/incomplete candles excluded. ':'')+'Display selection preserves the saved indicator values and their full history seed. At most '+data.bar_limit+' candles are returned. No live candle is inferred.';
  chart(bars,data.symbol||'No stock',data.timeframe);
  el('candle-data').replaceChildren();for(const bar of [...bars].reverse()){const row=node('tr');for(const value of [date(bar.time),bar.open,bar.high,bar.low,bar.close,String(bar.volume),bar.sma20??'Not enough bars',bar.sma50??'Not enough bars',bar.sma200??'Unavailable',bar.drawdown_pct??'Unavailable',bar.max_drawdown_pct??'Unavailable'])row.append(node('td',value));el('candle-data').append(row);}
  el('data-caption').textContent=(data.symbol||'No stock selected')+' · exact saved prices in INR · '+data.source.price_basis+' · volume: '+(data.source.volume_basis||'basis not separately recorded');
 }
 function render(data){
  if(data.schema_version!==1||!Array.isArray(data.bars)||!Array.isArray(data.symbols))throw Error('Analysis response is unavailable. Restart the server and refresh.');
  latest=data;lastReceipt=clock();options=data.symbols;stockOptions(data.symbol);el('timeframe').value=data.timeframe;el('main').hidden=false;
  el('state').textContent='Saved data · paper only';el('message').className='';el('message').textContent='Analysis refreshed. Viewing does not change your account.';
  const q=data.quote;el('last-price').textContent=q?.last?money(q.last):'No accepted quote';
  el('quote-state').textContent=q?(q.usable?'Usable at last refresh':friendly(q.status)+' · at last refresh'):'No stock selected';
  el('quote-detail').textContent=q?.detail||'Choose a saved stock to inspect quote status.';
  el('quote-time').textContent=q?.exchange_time?'Exchange '+date(q.exchange_time)+' IST · '+(q.usable?'usable at last refresh':'not usable at last refresh'):'No accepted exchange timestamp';
  el('session-state').textContent=data.market_session_open?'Open · reviewed hours':'Closed or unreviewed';
  el('subscription').textContent=q?.subscribed?'Stock is in the saved live-feed shortlist.':'Stock is not in the saved live-feed shortlist. Daily chart history does not create a subscription.';
  el('chart-title').textContent=(data.symbol||'No stock selected')+' · '+({ '1d':'Daily','1w':'Weekly','1mo':'Monthly','1m':'1-minute','5m':'5-minute'}[data.timeframe]||'Saved')+' candles';
  el('chart-status').textContent=data.message;el('chart-status').className=data.data_state==='unavailable'?'error':'muted';
  el('chart-source').textContent=(data.source.synthetic?'SIMULATED SOURCE · ':'')+data.source.description+' · '+data.source.price_basis+' · Volume: '+(data.source.volume_basis||'basis not separately recorded');
  renderChart(data);
  renderResearch(data);
  const s=data.screen;el('screen-state').textContent=s?friendly(s.status)+(s.rank?' · rank '+s.rank:''):'No daily screen available';
  el('screen-metrics').replaceChildren();if(s)for(const [label,value]of [['Last daily close',s.last_close?money(s.last_close):'—'],[(data.policy?.momentum_sessions||20)+'-session gross return',s.gross_total_return_pct===undefined?'—':s.gross_total_return_pct+'%'],['Daily volatility',s.daily_volatility_pct===undefined?'—':s.daily_volatility_pct+'%'],['Average daily turnover',s.average_turnover===undefined?'—':money(s.average_turnover)]]){const item=node('div');item.append(node('span',label),node('strong',value));el('screen-metrics').append(item);}
  el('screen-reasons').textContent=s?.reasons?.length?'Screen checks: '+s.reasons.map(friendly).join('; '):s?'Passed the configured prior-daily screen. An executable signal still requires separate strategy and risk checks.':'Prepare and review genuine daily data in Strategies. No score is invented.';
  el('screen-date').textContent=(s?.last_session?'Last completed research session '+s.last_session+'. ':'')+(data.screen_as_of?'Screen calculated '+date(data.screen_as_of)+' IST.':'');
  el('limitations').replaceChildren();for(const text of data.limitations||[])el('limitations').append(node('li',text));
  el('updated').textContent='Observed '+date(data.observed_at)+' IST. Refresh saved data to update this display.';
  if(win.AgenticNavigation?.updated)win.AgenticNavigation.updated();
 }
 async function refresh(){
  if(!token||busy)return;const version=++generation;active?.abort();const controller=new AbortController();active=controller;busy=true;controls();
  el('message').textContent='Reading saved market data…';const timeout=win.setTimeout(()=>controller.abort(),10000);
  const query=new URLSearchParams({timeframe:el('timeframe').value||'1d'});if(el('stock').value)query.set('symbol',el('stock').value);
  try{
   const endpoint=['1d','1w','1mo'].includes(query.get('timeframe'))?'/api/research/series':'/api/analysis';
   const response=await fetcher(endpoint+'?'+query.toString(),{method:'GET',signal:controller.signal,cache:'no-store',credentials:'omit',redirect:'error',headers:{Authorization:'Bearer '+token}});
   if(version!==generation)return;
   if(response.status===401||response.status===403){lock();el('message').textContent='Operator authorization failed. Unlock with the local operator token.';el('message').className='error';return;}
   if(!response.ok)throw Error('Saved analysis could not be loaded. Refresh after checking the saved stock and server status.');
   const data=await response.json();if(version===generation)render(data);
  }catch(error){if(version!==generation)return;el('state').textContent='Display stale · refresh required';el('message').className='error';el('message').textContent=error.name==='AbortError'?'Reading saved data timed out. Refresh to retry; no account changes were requested.':String(error.message);}
  finally{win.clearTimeout(timeout);if(version===generation){busy=false;active=null;controls();}}
 }
 el('access').addEventListener('submit',event=>{event.preventDefault();const supplied=el('token').value;if(supplied){lock();token=supplied;el('token').required=false;el('lock').disabled=false;}refresh();});
 el('lock').addEventListener('click',lock);el('open-chart').addEventListener('click',refresh);el('refresh').addEventListener('click',refresh);el('stock').addEventListener('change',refresh);el('timeframe').addEventListener('change',refresh);
 el('stock-search').addEventListener('input',()=>{stockOptions(latest?.symbol);});
 el('chart-range').addEventListener('change',()=>{if(token&&!busy&&latest){renderChart(latest);if(win.AgenticNavigation?.updated)win.AgenticNavigation.updated();}});
 if(win.addEventListener)win.addEventListener('pagehide',lock);
 if(win.setInterval)win.setInterval(()=>{if(token&&latest&&clock()-lastReceipt>6000){el('state').textContent='Display stale · refresh required';el('quote-state').textContent='Snapshot stale';el('quote-time').textContent=(latest.quote?.exchange_time?'Exchange '+date(latest.quote.exchange_time)+' IST. ':'')+'Snapshot stale; refresh to check current quote usability.';}},1000);
 lock();return{refresh,lock,canNavigate:()=>!busy};
}
if(typeof module!=='undefined'&&module.exports)module.exports={createAnalysis};
if(typeof document!=='undefined'){const view=createAnalysis(document,window,window.fetch.bind(window));if(window.AgenticNavigation)window.AgenticNavigation.connect(view,'access');}
})();
