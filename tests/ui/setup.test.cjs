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
}
const flush=()=>new Promise(r=>setImmediate(r));
const status=(extra={})=>({manual:true,credentials_configured:true,access_token_available:true,profile_verified_this_run:false,stream_requested:false,feed_connected:false,catalog_count:3,selected:[{symbol:'NSE:DEMO',token:1,tick:'0.05'}],sessions:[],today:'2026-10-21',calendar_today:false,...extra});
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
test('auth failure distinguishes local operator token from Zerodha and clears private state',async()=>{
  const s=setup(async()=>({ok:false,status:401,json:async()=>({detail:'Unauthorized'})}));
  await s.unlock();assert.ok(s.nodes.private.hidden);assert.match(s.nodes.message.textContent,/TRADING_OPERATOR_TOKEN/);
  assert.match(s.nodes.message.textContent,/Zerodha/);assert.equal(s.nodes.token.value,'');
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
