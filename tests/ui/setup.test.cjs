'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const {createSetup} = require('../../src/trading_agent/api/static/setup.js');
class Element {
  constructor(){this.children=[];this.events={};this.value='';this.open=false;}
  set textContent(v){this.text=String(v);this.children=[];}
  get textContent(){return(this.text||'')+this.children.map(n=>n.textContent).join('');}
  set innerHTML(_){throw Error('unsafe HTML sink');}
  append(n){this.children.push(n);}
  replaceChildren(...n){this.text='';this.children=n;}
  addEventListener(n,f){(this.events[n]||=[]).push(f);}
  fire(n){if(!this.disabled)for(const f of this.events[n]||[])f({preventDefault(){}});}
  showModal(){this.open=true;}
  close(){this.open=false;}
  focus(){this.focused=true;}
}
const flush=()=>new Promise(r=>setImmediate(r));
const status=(extra={})=>({manual:true,credentials_configured:true,access_token_available:true,profile_verified_this_run:false,stream_requested:false,feed_connected:false,catalog_count:3,stream_limit:10,selected:[{symbol:'NSE:DEMO',token:1,tick:'0.05'}],sessions:[],today:'2026-10-21',calendar_today:false,...extra});
const ok=data=>({ok:true,status:200,json:async()=>data});
function setup(fetcher=async()=>ok(status())){
  const nodes=Object.fromEntries([...readFileSync('src/trading_agent/api/static/setup.html','utf8').matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
  const events={},calls=[],timeouts=new Map();let sequence=0;
  const popup={closed:false,close(){this.closed=true;}};
  const win={location:{origin:'http://127.0.0.1:8004'},open:()=>{popup.closed=false;return popup;},addEventListener:(n,f)=>{events[n]=f;},setTimeout:f=>{timeouts.set(++sequence,f);return sequence;},clearTimeout:n=>timeouts.delete(n)};
  const doc={getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:()=>new Element()};
  const instance=createSetup(doc,win,async(url,options)=>{calls.push({url,options});return fetcher(url,options);});
  async function unlock(){nodes.token.value='local-test-token';nodes.access.fire('submit');await flush();}
  return {nodes,events,calls,popup,instance,unlock,timeouts};
}
test('setup loads no private data while locked, uses only bearer and renders safe text',async()=>{
  const s=setup(async()=>ok(status({sessions:[{date:'2026-10-21',open:'09:15',close:'15:30',source:'<script>bad</script>'}]})));
  assert.equal(s.calls.length,0);assert.ok(s.nodes.private.hidden);
  await s.unlock();
  assert.equal(s.calls[0].options.headers.Authorization,'Bearer local-test-token');
  assert.equal(s.calls[0].options.credentials,'omit');assert.equal(s.calls[0].options.redirect,'error');
  assert.equal(s.nodes.token.value,'');assert.match(s.nodes.sessions.textContent,/<script>bad/);
  assert.match(s.nodes.redirect.textContent,/http:\/\/127.0.0.1:8004\//);
  assert.match(s.nodes['calendar-state'].textContent,/blocked/);
});
test('broker overview leads with actual connection state and guided troubleshooting, without mutation',async()=>{
  const s=setup();await s.unlock();
  assert.equal(s.nodes['connection-status'].textContent,'Data disconnected');
  assert.equal(s.nodes['overview-session'].textContent,'Saved · not checked this run');
  assert.equal(s.nodes['overview-symbols'].textContent,'1 of 10 stocks');
  assert.equal(s.nodes['overview-calendar'].textContent,'Today needs review');
  assert.match(s.nodes['connection-next'].textContent,/saved token can expire/);
  assert.equal(s.nodes['setup-step-3'].open,true);
  assert.match(s.nodes['setup-progress'].textContent,/Step 3 of 6/);
  s.nodes['setup-next-action'].fire('click');
  assert.equal(s.nodes['setup-step-title-3'].focused,true);
  assert.equal(s.calls.length,1);assert.equal(s.calls[0].options.method,'GET');
  assert.equal(s.nodes.confirm.open,false);
});
test('first unlocked status chooses the next relevant step while refresh preserves manual navigation and edits',async()=>{
  const cases=[
    [{credentials_configured:false,access_token_available:false},'setup-step-1'],
    [{access_token_available:false},'setup-step-3'],
    [{profile_verified_this_run:true,catalog_count:0,selected:[]},'setup-step-4'],
    [{profile_verified_this_run:true},'setup-step-5'],
    [{profile_verified_this_run:true,calendar_today:true},'feed-connection'],
    [{stream_requested:true,feed_diagnostics:{state:'failed',failures:10}},'feed-connection']
  ];
  for(const [extra,id] of cases){
    const s=setup(async()=>ok(status(extra)));await s.unlock();
    assert.equal(s.nodes[id].open,true,id);
    assert.equal(['setup-step-1','setup-step-2','setup-step-3','setup-step-4','setup-step-5','feed-connection'].filter(key=>s.nodes[key].open).length,1);
    s.nodes['setup-next-1'].fire('click');
    assert.equal(s.nodes['setup-step-2'].open,true);
    s.nodes['api-key'].value='unsaved-key';s.nodes['symbol-list'].value='UNSAVED';
    s.nodes['refresh-status'].fire('click');await flush();
    assert.equal(s.nodes['setup-step-2'].open,true);
    assert.equal(s.nodes['api-key'].value,'unsaved-key');assert.equal(s.nodes['symbol-list'].value,'UNSAVED');
    assert.equal(s.calls.length,2);assert.ok(s.calls.every(call=>call.options.method==='GET'));
  }
});
test('wizard Back and Continue focus steps but never save, check a broker session, or attest to a date',async()=>{
  const s=setup();await s.unlock();
  s.nodes['setup-next-1'].fire('click');assert.equal(s.nodes['setup-step-2'].open,true);
  for(let number=2;number<=5;number++)s.nodes['setup-next-'+number].fire('click');
  assert.equal(s.nodes['feed-connection'].open,true);assert.equal(s.nodes['setup-step-title-6'].focused,true);
  for(let number=6;number>=2;number--)s.nodes['setup-back-'+number].fire('click');
  assert.equal(s.nodes['setup-step-1'].open,true);assert.equal(s.nodes['setup-step-title-1'].focused,true);
  assert.equal(s.nodes['session-reviewed'].checked,false);assert.equal(s.nodes.confirm.open,false);assert.equal(s.calls.length,1);
  s.nodes['setup-step-4'].open=true;s.nodes['setup-step-4'].fire('toggle');assert.match(s.nodes['setup-progress'].textContent,/Step 4 of 6/);
  s.nodes.lock.fire('click');
  for(const id of ['connection-status','overview-session','overview-symbols','overview-calendar','connection-next'])assert.equal(s.nodes[id].textContent,'');
  assert.equal(s.nodes['setup-step-1'].open,false);assert.equal(s.nodes['setup-step-4'].open,false);
  s.nodes['setup-next-action'].fire('click');assert.equal(s.nodes['setup-step-1'].open,false);
});
test('connected overview keeps execution readiness separate and failed feed guidance uses safe status',async()=>{
  const connected=setup(async()=>ok(status({stream_requested:true,feed_connected:true,calendar_today:true})));await connected.unlock();
  assert.equal(connected.nodes['connection-status'].textContent,'Data connected');
  assert.match(connected.nodes['connection-description'].textContent,/freshness, liquidity and today’s price-basis reviews/);
  assert.match(connected.nodes['connection-next'].textContent,/connected socket alone does not make a quote usable/);
  assert.equal(connected.nodes['feed-connection'].open,true);
  const failed=setup(async()=>ok(status({stream_requested:true,feed_diagnostics:{state:'failed',failures:10,last_failure:'secret-server-error'}})));await failed.unlock();
  assert.equal(failed.nodes['connection-status'].textContent,'Connection needs attention');
  assert.match(failed.nodes['connection-next'].textContent,/retries are exhausted/);
  assert.doesNotMatch(failed.nodes['connection-next'].textContent,/secret-server-error/);
  assert.equal(failed.calls.length,1);assert.equal(failed.nodes.confirm.open,false);
});
test('connection guide uses keyboard-accessible native disclosure and preserves direct feed anchors',()=>{
  const html=readFileSync('src/trading_agent/api/static/setup.html','utf8');
  assert.equal((html.match(/class="panel setup-step"/g)||[]).length,6);
  assert.equal((html.match(/name="broker-setup"/g)||[]).length,6);
  assert.equal((html.match(/<summary id="setup-step-title-/g)||[]).length,6);
  assert.match(html,/<details id="feed-connection"[^>]+tabindex="-1"/);
  assert.match(html,/id="setup-next-action" type="button" aria-describedby="connection-next"/);
  assert.match(html,/id="setup-progress"[^>]+role="status"[^>]+aria-live="polite"/);
  assert.ok(html.indexOf('id="connection-title"')<html.indexOf('id="setup-step-1"'));
  assert.ok(html.indexOf('id="setup-step-1"')<html.indexOf('Help: which credential'));
  assert.match(html,/Moving between steps does not save settings or approve a trading date/);
});
test('session hours default on unlock without saving or attesting and preserve edits across refresh',async()=>{
  const s=setup();await s.unlock();
  assert.equal(s.nodes['session-open'].value,'09:15');assert.equal(s.nodes['session-close'].value,'15:30');
  assert.equal(s.nodes['session-source'].value,'');assert.equal(s.nodes['session-reviewed'].checked,false);
  assert.equal(s.calls.length,1);assert.equal(s.calls[0].options.method,'GET');
  s.nodes['session-open'].value='09:30';s.nodes['session-close'].value='14:00';
  s.nodes['refresh-status'].fire('click');await flush();
  assert.equal(s.nodes['session-open'].value,'09:30');assert.equal(s.nodes['session-close'].value,'14:00');
  s.nodes['session-open'].value='';s.nodes['refresh-status'].fire('click');await flush();
  assert.equal(s.nodes['session-open'].value,'');
  s.nodes.lock.fire('click');assert.equal(s.nodes['session-close'].value,'');
  await s.unlock();assert.equal(s.nodes['session-open'].value,'09:15');assert.equal(s.nodes['session-close'].value,'15:30');
  assert.equal(s.nodes['session-reviewed'].checked,false);
});
test('default session hours appear in the confirmation and only post after explicit review',async()=>{
  const s=setup();await s.unlock();
  s.nodes['session-source'].value='invented NSE notice';s.nodes['session-reviewed'].checked=true;
  s.nodes.calendar.fire('submit');assert.ok(s.nodes.confirm.open);
  assert.match(s.nodes['confirm-text'].textContent,/09:15–15:30 IST/);assert.equal(s.calls.length,1);
  s.nodes['cancel-confirm'].fire('click');assert.equal(s.calls.length,1);
  s.nodes.calendar.fire('submit');s.nodes['confirm-action'].fire('click');await flush();
  assert.deepEqual(JSON.parse(s.calls.at(-1).options.body),{date:'2026-10-21',open:'09:15',close:'15:30',source:'invented NSE notice',reviewed:true});
  assert.equal(s.nodes['session-reviewed'].checked,false);
});
test('saved feed list stays distinct from unsaved edits and explains catalog versus streaming',async()=>{
  const s=setup();await s.unlock();
  assert.equal(s.nodes['selected-title'].textContent,'Saved feed subscriptions (1 of 10)');
  s.nodes['symbol-list'].value='SECOND';
  assert.match(s.nodes.selected.textContent,/NSE:DEMO/);assert.doesNotMatch(s.nodes.selected.textContent,/SECOND/);
  assert.equal(s.calls.length,1);s.nodes.lock.fire('click');
  assert.equal(s.nodes['selected-title'].textContent,'Saved feed subscriptions');
  const html=readFileSync('src/trading_agent/api/static/setup.html','utf8');
  assert.match(html,/aria-describedby="selection-help selection-save-help"/);
  assert.match(html,/catalog is a symbol\/token lookup/);assert.match(html,/Editing the field does not change subscriptions/);
  assert.match(html,/defaults do not approve a trading date/);
});
test('configured stream capacity updates accessible selection guidance and supports reviewed larger lists',async()=>{
  const symbols=Array.from({length:50},(_,i)=>'NSE:SYMBOL'+i);
  const s=setup(async(url,options)=>ok(status({stream_limit:50,profile_verified_this_run:true,selected:url.endsWith('/symbols')?JSON.parse(options.body).symbols.map((symbol,i)=>({symbol,token:i+1,tick:'0.05'})):[]})));
  await s.unlock();
  assert.equal(s.nodes['overview-symbols'].textContent,'0 of 50 stocks');
  assert.equal(s.nodes['selected-title'].textContent,'Saved feed subscriptions (0 of 50)');
  assert.equal(s.nodes['symbol-list-label'].textContent,'One to 50 symbols, comma separated');
  assert.equal(s.nodes['symbol-list'].maxLength,1800);
  assert.match(s.nodes['selection-help'].textContent,/up to 50 saved symbols/);
  assert.match(s.nodes['connection-next'].textContent,/up to 50 saved stock subscriptions/);
  s.nodes['symbol-list'].value=symbols.join(', ');assert.ok(s.nodes['symbol-list'].value.length>400);
  s.nodes.symbols.fire('submit');assert.equal(s.calls.length,1);assert.ok(s.nodes.confirm.open);
  s.nodes['cancel-confirm'].fire('click');assert.equal(s.calls.length,1);
  s.nodes.symbols.fire('submit');s.nodes['confirm-action'].fire('click');await flush();
  assert.deepEqual(JSON.parse(s.calls.at(-1).options.body),{symbols});
  assert.equal(s.nodes['selected-title'].textContent,'Saved feed subscriptions (50 of 50)');
  assert.equal(s.nodes['overview-symbols'].textContent,'50 of 50 stocks');
  s.nodes['symbol-list'].value=symbols.concat('NSE:EXTRA').join(', ');s.nodes.symbols.fire('submit');
  assert.match(s.nodes.message.textContent,/one to 50 catalog symbols/);assert.equal(s.nodes.confirm.open,false);assert.equal(s.calls.length,2);
  s.nodes.lock.fire('click');assert.equal(s.nodes['symbol-list-label'].textContent,'One to 10 symbols, comma separated');assert.equal(s.nodes['symbol-list'].maxLength,360);
  const html=readFileSync('src/trading_agent/api/static/setup.html','utf8');
  assert.match(html,/<label><span id="symbol-list-label">[^<]+<\/span><input id="symbol-list"/);
});
test('stream capacity display has bounded defaults for older or malformed status payloads',async()=>{
  for(const stream_limit of [undefined,0,3001,50.5,'50',true]){
    const s=setup(async()=>ok(status({stream_limit})));await s.unlock();
    assert.equal(s.nodes['symbol-list'].maxLength,360);assert.equal(s.nodes['overview-symbols'].textContent,'1 of 10 stocks');
  }
  const s=setup(async()=>ok(status({stream_limit:3000})));await s.unlock();
  assert.equal(s.nodes['symbol-list'].maxLength,108000);assert.match(s.nodes['symbol-list-label'].textContent,/3000/);
});
test('auth failure distinguishes local operator token from Zerodha and clears private state',async()=>{
  const s=setup(async()=>({ok:false,status:401,json:async()=>({detail:'Unauthorized'})}));
  await s.unlock();assert.ok(s.nodes.private.hidden);assert.match(s.nodes.message.textContent,/TRADING_OPERATOR_TOKEN/);
  assert.match(s.nodes.message.textContent,/Zerodha/);assert.equal(s.nodes.token.value,'');
});
test('saved-session check shows inline progress, prevents duplicate requests and reports profile-only success',async()=>{
  let finish;
  const s=setup(async url=>url.endsWith('/profile')?new Promise(r=>{finish=r;}):ok(status()));await s.unlock();
  s.nodes.profile.fire('click');s.nodes.profile.fire('click');
  assert.match(s.nodes['session-feedback'].textContent,/Checking saved broker session/);
  assert.match(s.nodes.profile.textContent,/Checking/);assert.equal(s.nodes.profile.disabled,true);
  assert.equal(s.instance.canNavigate(),false);
  const calls=s.calls.filter(c=>c.url.endsWith('/profile'));assert.equal(calls.length,1);
  assert.equal(calls[0].options.method,'POST');assert.deepEqual(JSON.parse(calls[0].options.body),{});
  finish(ok(status({profile_verified_this_run:true})));await flush();
  assert.match(s.nodes['session-state'].textContent,/Profile verified/);
  assert.match(s.nodes['session-feedback'].textContent,/verified successfully/);
  assert.match(s.nodes['session-feedback'].textContent,/profile access only/);
  assert.equal(s.nodes.profile.disabled,false);assert.equal(s.nodes.profile.textContent,'Check saved broker session');
  assert.equal(s.instance.canNavigate(),true);
});
test('failed recheck clears stale verification locally and gives inline login recovery, then allows retry',async()=>{
  let failed=true;
  const s=setup(async url=>url.endsWith('/profile')&&failed?{ok:false,status:409,json:async()=>({detail:'Kite profile check failed.'})}:ok(status({profile_verified_this_run:true})));
  await s.unlock();s.nodes.profile.fire('click');await flush();
  assert.match(s.nodes['session-state'].textContent,/have not been verified/);
  assert.match(s.nodes['session-feedback'].textContent,/Kite profile check failed/);
  assert.match(s.nodes['session-feedback'].textContent,/disconnect any requested feed in step 6/);
  assert.match(s.nodes['session-feedback'].textContent,/exchange a fresh request token/);
  assert.equal(s.nodes['session-feedback'].className,'error');assert.equal(s.nodes.profile.disabled,false);
  failed=false;s.nodes.profile.fire('click');await flush();
  assert.match(s.nodes['session-feedback'].textContent,/verified successfully/);
  assert.equal(s.nodes['session-feedback'].className,'');
});
test('session-check timeout offers retry without replaying or consuming a login token',async()=>{
  const s=setup(async(url,options)=>url.endsWith('/profile')?new Promise((_,reject)=>options.signal.addEventListener('abort',()=>reject(Object.assign(Error('aborted'),{name:'AbortError'})))):ok(status()));
  await s.unlock();s.nodes.profile.fire('click');
  for(const timeout of s.timeouts.values())timeout();await flush();
  assert.match(s.nodes['session-feedback'].textContent,/check timed out/);
  assert.match(s.nodes['session-feedback'].textContent,/connection and retry/);
  assert.doesNotMatch(s.nodes['session-feedback'].textContent,/consumed login token/);
  assert.equal(s.nodes.profile.disabled,false);assert.equal(s.calls.length,2);assert.equal(s.timeouts.size,0);
});
test('lock and authentication failure clear inline session feedback and ignore late results',async()=>{
  let finish;
  const s=setup(async url=>url.endsWith('/profile')?new Promise(r=>{finish=r;}):ok(status()));await s.unlock();
  s.nodes.profile.fire('click');s.nodes.lock.fire('click');finish(ok(status({profile_verified_this_run:true})));await flush();
  assert.equal(s.nodes['session-feedback'].textContent,'');assert.equal(s.nodes['session-state'].textContent,'');assert.ok(s.nodes.private.hidden);
  const auth=setup(async url=>url.endsWith('/profile')?{ok:false,status:401,json:async()=>({detail:'Unauthorized'})}:ok(status()));
  await auth.unlock();auth.nodes.profile.fire('click');await flush();
  assert.ok(auth.nodes.private.hidden);assert.equal(auth.nodes['session-feedback'].textContent,'');
  assert.match(auth.nodes.message.textContent,/TRADING_OPERATOR_TOKEN/);
});
test('session result is an atomic live status beside the check control',()=>{
  const html=readFileSync('src/trading_agent/api/static/setup.html','utf8');
  assert.match(html,/<p id="session-feedback" role="status" aria-live="polite" aria-atomic="true">/);
  assert.ok(html.indexOf('id="profile"')<html.indexOf('id="session-feedback"'));
  assert.ok(html.indexOf('id="session-feedback"')<html.indexOf('id="exchange"'));
});
test('secrets clear before network settles and lock discards late setup responses',async()=>{
  let hold=false,finish;
  const s=setup(async()=>hold?new Promise(r=>{finish=r;}):ok(status()));await s.unlock();hold=true;
  s.nodes['api-key'].value='privatekey';s.nodes['api-secret'].value='privatesecret';s.nodes.credentials.fire('submit');
  assert.equal(s.nodes['api-key'].value,'');assert.equal(s.nodes['api-secret'].value,'');
  assert.deepEqual(JSON.parse(s.calls.at(-1).options.body),{api_key:'privatekey',api_secret:'privatesecret'});
  s.nodes.lock.fire('click');finish(ok(status()));await flush();assert.ok(s.nodes.private.hidden);
  assert.equal(s.nodes.selected.textContent,'');assert.equal(s.calls.length,2);
});
test('callback requires matching origin, popup window and login attempt; exchange posts only once',async()=>{
  const s=setup(async url=>ok(url.endsWith('/login')?{login_url:'https://kite.zerodha.com/connect/login?api_key=unitkey',state:'nonce'}:status()));
  await s.unlock();s.nodes.login.fire('click');await flush();assert.match(s.popup.location,/^https:\/\/kite\.zerodha\.com/);
  const event={origin:'http://127.0.0.1:8004',source:s.popup,data:{type:'kite-request-token',state:'nonce',request_token:'onetime'}};
  for(const bad of [{origin:'https://evil.test'},{source:{}},{data:{...event.data,state:'wrong'}}])s.events.message({...event,...bad});
  assert.equal(s.nodes['request-token'].value,'');
  s.events.message(event);assert.equal(s.nodes['request-token'].value,'onetime');
  s.nodes.exchange.fire('submit');s.nodes.exchange.fire('submit');await flush();
  const posts=s.calls.filter(c=>c.url.endsWith('/exchange'));assert.equal(posts.length,1);
  assert.deepEqual(JSON.parse(posts[0].options.body),{request_token:'onetime',state:'nonce'});
  assert.equal(s.nodes['request-token'].value,'');
});
test('selection/calendar/disconnect require explicit review and cancel submits nothing',async()=>{
  const s=setup();await s.unlock();s.nodes['symbol-list'].value='DEMO, SECOND';s.nodes.symbols.fire('submit');
  assert.ok(s.nodes.confirm.open);assert.match(s.nodes['confirm-text'].textContent,/DEMO, SECOND/);
  assert.equal(s.calls.length,1);s.nodes['cancel-confirm'].fire('click');assert.equal(s.calls.length,1);
  s.nodes.symbols.fire('submit');s.nodes['confirm-action'].fire('click');await flush();
  assert.deepEqual(JSON.parse(s.calls.at(-1).options.body),{symbols:['DEMO','SECOND']});
  s.nodes['session-date'].value='2026-10-21';s.nodes['session-open'].value='09:15';s.nodes['session-close'].value='15:30';s.nodes['session-source'].value='reviewed source';s.nodes['session-reviewed'].checked=true;s.nodes.calendar.fire('submit');
  assert.match(s.nodes['confirm-text'].textContent,/2026-10-21, 09:15–15:30/);
  s.nodes.lock.fire('click');s.nodes['confirm-action'].fire('click');await flush();assert.equal(s.calls.length,2);
});
test('streaming prevents credential/selection replacement and connecting twice',async()=>{
  const s=setup(async()=>ok(status({stream_requested:true,feed_connected:true})));await s.unlock();
  for(const id of ['save-credentials','login','exchange-button','catalog','save-symbols','connect'])assert.ok(s.nodes[id].disabled,id);
  assert.equal(s.nodes.disconnect.disabled,false);s.nodes.disconnect.fire('click');assert.ok(s.nodes.confirm.open);
  assert.match(s.nodes['confirm-text'].textContent,/Holdings stay open/);
});
test('connected empty books explain missing usable quotes without presenting them as tradable',async()=>{
  const s=setup(async()=>ok(status({stream_requested:true,feed_connected:true,feed_diagnostics:{state:'connected',failures:0,unusable_quotes:5}})));await s.unlock();
  assert.match(s.nodes['feed-state'].textContent,/WebSocket connected/);
  assert.match(s.nodes['feed-state'].textContent,/not proof of fresh usable quotes/);
  assert.match(s.nodes['feed-state'].textContent,/ignored: 5/);
  assert.match(s.nodes['feed-state'].textContent,/cannot fill orders/);
});
test('exhausted feed retries give recovery steps and fixed credential-free failure descriptions',async()=>{
  const s=setup(async()=>ok(status({stream_requested:true,feed_diagnostics:{state:'failed',failures:10,last_failure:'timeout',unusable_quotes:0}})));await s.unlock();
  assert.match(s.nodes['feed-state'].textContent,/retries exhausted/);
  assert.match(s.nodes['feed-state'].textContent,/Disconnect market data, then Connect/);
  assert.match(s.nodes['feed-state'].textContent,/timed out/);
  assert.equal(s.nodes.disconnect.disabled,false);assert.equal(s.nodes.connect.disabled,true);
  const other=setup(async()=>ok(status({stream_requested:true,feed_diagnostics:{state:'retrying',failures:2,last_failure:'sensitive-broker-error',unusable_quotes:0}})));await other.unlock();
  assert.match(other.nodes['feed-state'].textContent,/failure 2 of 10/);
  assert.doesNotMatch(other.nodes['feed-state'].textContent,/sensitive/);
});
test('callback removes sensitive query before posting only to its own origin',()=>{
  const messages=[],history=[];
  const window={location:{search:'?request_token=onetime&setup_state=nonce',pathname:'/',origin:'http://127.0.0.1:8004'},history:{replaceState:(...a)=>history.push(a)},opener:{postMessage:(...a)=>messages.push(a)}};
  vm.runInNewContext(readFileSync('src/trading_agent/api/static/kite-callback.js','utf8'),{window,URLSearchParams});
  assert.equal(history[0][2],'/');assert.equal(messages[0][1],'http://127.0.0.1:8004');
  assert.equal(messages[0][0].request_token,'onetime');
});
test('legacy CLI redirect remains available for manual token capture',()=>{
  const window={location:{search:'?request_token=onetime',pathname:'/',origin:'http://127.0.0.1:8004'},history:{replaceState(){throw Error('legacy token removed');}},opener:null};
  vm.runInNewContext(readFileSync('src/trading_agent/api/static/kite-callback.js','utf8'),{window,URLSearchParams});
});
test('connecting repeats selected symbols and warns about resumed pending fills before explicit confirmation',async()=>{
  const s=setup();await s.unlock();s.nodes.connect.fire('click');
  assert.ok(s.nodes.confirm.open);assert.equal(s.calls.length,1);
  assert.match(s.nodes['confirm-text'].textContent,/NSE:DEMO/);
  assert.match(s.nodes['confirm-text'].textContent,/resume pending fills/);
  s.nodes['confirm-action'].fire('click');s.nodes['confirm-action'].fire('click');await flush();
  assert.equal(s.calls.filter(c=>c.url.endsWith('/connect')).length,1);
});
test('Escape and pagehide revoke connect confirmation so delayed or duplicate clicks submit nothing',async()=>{
  for(const close of ['escape','pagehide']){
    const s=setup();await s.unlock();s.nodes.connect.fire('click');assert.equal(s.nodes.confirm.open,true);
    if(close==='escape')s.nodes.confirm.fire('cancel');else s.events.pagehide();
    assert.equal(s.nodes.confirm.open,false);s.nodes['confirm-action'].fire('click');s.nodes['confirm-action'].fire('click');await flush();
    assert.equal(s.calls.length,1);assert.equal(s.calls[0].options.method,'GET');
  }
});
test('pagehide while checking a saved session clears credentials and ignores the late result',async()=>{
  let finish;const s=setup(async url=>url.endsWith('/profile')?new Promise(resolve=>{finish=resolve;}):ok(status()));
  await s.unlock();s.nodes.profile.fire('click');assert.match(s.nodes['session-feedback'].textContent,/Checking/);
  s.events.pagehide();finish(ok(status({profile_verified_this_run:true})));await flush();
  assert.equal(s.nodes.private.hidden,true);assert.equal(s.nodes['session-feedback'].textContent,'');assert.equal(s.nodes['session-state'].textContent,'');
  assert.equal(s.calls.length,2);assert.equal(s.calls[1].options.signal.aborted,true);
});
