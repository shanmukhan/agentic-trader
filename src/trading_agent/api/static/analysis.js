(function () {
'use strict';
const SVG='http://www.w3.org/2000/svg';
const money=typeof module!=='undefined'&&module.exports?require('./money.js'):window.AgenticMoney;
function createAnalysis(doc,win,fetcher){
 const el=id=>doc.getElementById(id),node=(tag,text)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=String(text);return n;};
 const svgNode=(tag,attrs,text)=>{const n=doc.createElementNS(SVG,tag);for(const [key,value]of Object.entries(attrs))n.setAttribute(key,String(value));if(text!==undefined)n.textContent=String(text);return n;};
 let token='',generation=0,active=null,busy=false,latest=null,options=[],lastReceipt=0;
 const clock=()=>win.Date?win.Date.now():Date.now();
 const date=value=>value?new Date(value).toLocaleString('en-IN',{timeZone:'Asia/Kolkata',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}):'—';
 const friendly=value=>String(value||'').toLowerCase().replaceAll('_',' ');
 function controls(){for(const id of ['stock','timeframe','open-chart','refresh','stock-search'])el(id).disabled=!token||busy;el('unlock').disabled=busy;}
 function lock(){
  if(win.AgenticNavigation)win.AgenticNavigation.locked();generation++;active?.abort();active=null;token='';busy=false;latest=null;options=[];lastReceipt=0;
  el('token').value='';el('token').required=true;el('lock').disabled=true;el('main').hidden=true;el('stock-search').value='';el('timeframe').value='1d';
  for(const id of ['stock','price-chart','screen-metrics','candle-data','limitations'])el(id).replaceChildren();
  for(const id of ['last-price','quote-state','screen-state','session-state'])el(id).textContent='—';
  for(const id of ['quote-time','quote-detail','subscription','chart-status','chart-source','chart-period','screen-reasons','screen-date','chart-count','updated'])el(id).textContent='';
  el('chart-title').textContent='Saved candles';el('data-caption').textContent='Saved OHLC and volume';el('state').textContent='Locked';el('message').textContent='Locked. No private market data loaded.';el('message').className='';controls();
 }
 function stockOptions(selected){
  const query=el('stock-search').value.trim().toUpperCase();el('stock').replaceChildren();
  const filtered=options.filter(item=>item.symbol.toUpperCase().includes(query));
  for(const item of filtered){const option=node('option',item.symbol+(item.subscribed?' · subscribed':''));option.value=item.symbol;el('stock').append(option);}
  if(filtered.some(item=>item.symbol===selected))el('stock').value=selected;
  else if(filtered.length)el('stock').value=filtered[0].symbol;
  el('stock-help').textContent=filtered.length?filtered.length+' saved stocks match. Select Open chart to view a result. Charts never download data or change subscriptions.':'No saved stocks match this search. Clear the search to see all available stocks.';
 }
 function chart(bars,symbol,timeframe){
  el('price-chart').replaceChildren();if(!bars.length){el('price-chart').append(node('p','No chart is drawn until real completed candles are available.'));return;}
  const numeric=bars.map(b=>({open:Number(b.open),high:Number(b.high),low:Number(b.low),close:Number(b.close),volume:Number(b.volume),sma20:b.sma20===null?null:Number(b.sma20),sma50:b.sma50===null?null:Number(b.sma50)}));
  const values=numeric.flatMap(b=>[b.high,b.low,...[b.sma20,b.sma50].filter(v=>v!==null)]);
  if(!values.every(Number.isFinite)||!numeric.every(b=>Number.isFinite(b.volume)&&b.volume>=0)){el('price-chart').append(node('p','Chart coordinates could not be rendered. Inspect the exact saved candle table below.'));return;}
  const W=920,H=420,L=68,R=20,T=20,P=286,V=370,B=400,width=W-L-R,step=width/bars.length;
  let min=Math.min(...values),max=Math.max(...values);const pad=(max-min)*.08||Math.abs(max)*.005||1;min-=pad;max+=pad;
  const y=value=>T+(max-value)/(max-min)*(P-T),x=index=>L+(index+.5)*step,maxVolume=Math.max(...numeric.map(b=>b.volume),1);
  const svg=svgNode('svg',{viewBox:'0 0 '+W+' '+H,role:'img','aria-labelledby':'price-chart-title price-chart-description',width:'100%'});
  svg.append(svgNode('title',{id:'price-chart-title'},symbol+' '+timeframe+' saved candlestick chart'));
  svg.append(svgNode('desc',{id:'price-chart-description'},bars.length+' completed candles with SMA 20, SMA 50 and volume. Exact OHLC, volume and averages are in the accessible data table below. Missing intervals are not interpolated.'));
  for(let line=0;line<=4;line++){const value=min+(max-min)*line/4,yy=y(value);svg.append(svgNode('line',{x1:L,y1:yy,x2:W-R,y2:yy,class:'chart-grid'}));svg.append(svgNode('text',{x:L-9,y:yy+4,'text-anchor':'end',class:'chart-label'},value.toLocaleString('en-IN',{maximumFractionDigits:2})));}
  svg.append(svgNode('text',{x:L,y:P+25,class:'chart-label'},'VOLUME'));
  for(let i=0;i<bars.length;i++){
   const b=numeric[i],xx=x(i),bw=Math.max(.8,Math.min(11,step*.65)),cls=b.close>=b.open?'candle-up':'candle-down';
   const g=svgNode('g',{});g.append(svgNode('title',{},date(bars[i].time)+' IST · O '+bars[i].open+' H '+bars[i].high+' L '+bars[i].low+' C '+bars[i].close+' · volume '+bars[i].volume));
   g.append(svgNode('line',{x1:xx,y1:y(b.high),x2:xx,y2:y(b.low),class:cls}));
   g.append(svgNode('rect',{x:xx-bw/2,y:Math.min(y(b.open),y(b.close)),width:bw,height:Math.max(1,Math.abs(y(b.open)-y(b.close))),class:cls}));
   g.append(svgNode('rect',{x:xx-bw/2,y:V-b.volume/maxVolume*45,width:bw,height:b.volume/maxVolume*45,class:'volume-bar'}));svg.append(g);
  }
  for(const [key,cls]of [['sma20','indicator-line'],['sma50','indicator-line indicator-long']]){
   let points=[];const flush=()=>{if(points.length>1)svg.append(svgNode('polyline',{points:points.join(' '),class:cls,fill:'none'}));points=[];};
   numeric.forEach((b,i)=>{if(b[key]===null)flush();else points.push(x(i)+','+y(b[key]));});flush();
  }
  const indices=[...new Set([0,Math.floor((bars.length-1)/2),bars.length-1])];
  for(const i of indices)svg.append(svgNode('text',{x:x(i),y:B,'text-anchor':i===0?'start':i===bars.length-1?'end':'middle',class:'chart-label'},timeframe==='1d'?bars[i].session:date(bars[i].time)));
  el('price-chart').append(svg);
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
  el('chart-title').textContent=(data.symbol||'No stock selected')+' · '+({ '1d':'Daily','1m':'1-minute','5m':'5-minute'}[data.timeframe]||'Saved')+' candles';
  el('chart-count').textContent=data.bars.length+' candles'+(data.truncated?' · latest '+data.bar_limit:'');
  el('chart-status').textContent=data.message;el('chart-status').className=data.data_state==='unavailable'?'error':'muted';
  el('chart-source').textContent=(data.source.synthetic?'SIMULATED SOURCE · ':'')+data.source.description+' · '+data.source.price_basis;
  el('chart-period').textContent=(data.bars.length?'Saved interval: '+date(data.bars[0].time)+' to '+date(data.bars.at(-1).time)+' IST. ':'')+(data.excluded_candles?data.excluded_candles+' low-quality/incomplete candles excluded. ':'')+'At most '+data.bar_limit+' candles are displayed. No live candle is inferred.';
  chart(data.bars,data.symbol||'No stock',data.timeframe);
  el('candle-data').replaceChildren();for(const bar of [...data.bars].reverse()){const row=node('tr');for(const value of [date(bar.time),bar.open,bar.high,bar.low,bar.close,String(bar.volume),bar.sma20??'Not enough bars',bar.sma50??'Not enough bars'])row.append(node('td',value));el('candle-data').append(row);}
  el('data-caption').textContent=(data.symbol||'No stock selected')+' · exact saved prices in INR and volume in shares';
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
   const response=await fetcher('/api/analysis?'+query.toString(),{method:'GET',signal:controller.signal,cache:'no-store',credentials:'omit',redirect:'error',headers:{Authorization:'Bearer '+token}});
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
 if(win.setInterval)win.setInterval(()=>{if(token&&latest&&clock()-lastReceipt>6000){el('state').textContent='Display stale · refresh required';el('quote-state').textContent='Snapshot stale';el('quote-time').textContent=(latest.quote?.exchange_time?'Exchange '+date(latest.quote.exchange_time)+' IST. ':'')+'Snapshot stale; refresh to check current quote usability.';}},1000);
 lock();return{refresh,lock,canNavigate:()=>!busy};
}
if(typeof module!=='undefined'&&module.exports)module.exports={createAnalysis};
if(typeof document!=='undefined'){const view=createAnalysis(document,window,window.fetch.bind(window));if(window.AgenticNavigation)window.AgenticNavigation.connect(view,'access');}
})();
