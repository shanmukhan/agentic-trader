'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const {createWorkspace}=require('../../src/trading_agent/api/static/workspace.js');
class Element {
 constructor(){this.events={};this.value='';this.style={};this.attributes={};this.children=[];this.open=false;}
 set textContent(v){this.text=String(v);this.children=[];}
 get textContent(){return (this.text||'')+this.children.map(n=>n.textContent).join('');}
 append(...n){this.children.push(...n);}
 replaceChildren(...n){this.text='';this.children=n;}
 showModal(){this.open=true;}
 close(){this.open=false;}
 addEventListener(n,f){(this.events[n]||=[]).push(f);}
 fire(n){if(!this.disabled)for(const f of this.events[n]||[])f({preventDefault(){}});}
 dispatchEvent(event){for(const f of this.events[event.type]||[])f(event);}
 setAttribute(n,v){this.attributes[n]=v;}
 getAttribute(n){return this.attributes[n];}
 removeAttribute(n){delete this.attributes[n];}
}
const flush=()=>new Promise(r=>setImmediate(r));
const info=()=>({mode:'paper',investment_horizon:'long_term',observed_at:'2026-10-21T12:30:00+00:00',automation_enabled:false,automation_armed:false,feed_requested:false,feed_connected:false,entry_start:'09:30',entry_end:'14:30',flatten_at:'15:15',max_quote_age_seconds:5,calendar_open:false});
const ok=data=>({ok:true,status:200,json:async()=>data});
function setup(fetcher=async()=>ok(info())){
 const nodes=Object.fromEntries([...readFileSync('src/trading_agent/api/static/workspace.html','utf8').matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const events={},posts=[],calls=[];
 const child={postMessage:(...a)=>posts.push(a),AgenticNavigation:{canNavigate:()=>true}};
 nodes['workspace-frame'].contentWindow=child;
 const win={location:{origin:'http://127.0.0.1:8004',hash:'#console'},history:{replaceState(...a){win.location.hash=a[2];}},addEventListener:(n,f)=>{events[n]=f;},setTimeout:()=>1,clearTimeout(){}};
 const doc={getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];}};
 const instance=createWorkspace(doc,win,async(url,options)=>{calls.push({url,options});return fetcher(url,options);});
 async function unlock(){nodes['workspace-token'].value='valid-test-operator-token-1234567890';nodes['workspace-unlock'].fire('submit');await flush();}
 function ready(view='risk',extra={}){events.message({origin:win.location.origin,source:child,data:{type:'workspace-ready',view,path:nodes['workspace-frame'].src.split('#')[0]},...extra});}
 function navigate(view){win.location.hash='#'+view;events.hashchange();}
 return {nodes,events,win,child,posts,calls,instance,unlock,ready,navigate};
}
test('workspace loads no private API before unlocking and explains manual trading/feed startup',async()=>{
 const s=setup();assert.equal(s.calls.length,0);assert.ok(s.nodes['workspace-frame'].hidden);
 await s.unlock();assert.equal(s.calls.length,1);assert.equal(s.calls[0].url,'/api/workspace');
 assert.equal(s.calls[0].options.credentials,'omit');assert.equal(s.nodes['workspace-token'].value,'');
 assert.match(s.nodes['workspace-mode'].textContent,/manual/);assert.match(s.nodes['workspace-feed'].textContent,/Feed not started/);
 assert.match(s.nodes['workspace-hours'].textContent,/09:30–14:30/);
});
test('one unlock survives menu changes and sends credentials only to the current matching-origin frame',async()=>{
 const s=setup();await s.unlock();s.posts.length=0;
 s.ready('risk',{origin:'https://evil.test'});s.ready('risk',{source:{}});s.ready('broker');assert.equal(s.posts.length,0);
 s.ready();assert.equal(s.posts.length,1);assert.equal(s.posts[0][1],s.win.location.origin);
 assert.equal(s.posts[0][0].type,'workspace-unlock');
 s.navigate('setup');s.ready('broker');assert.equal(s.nodes['workspace-frame'].src,'/setup');
 assert.equal(s.posts.filter(p=>p[0].type==='workspace-unlock').length,2);
 assert.equal(s.calls.length,1);assert.ok(s.nodes['workspace-access'].hidden);
 s.navigate('__proto__');assert.equal(s.nodes['nav-dashboard'].attributes['aria-current'],'page');
});
test('lock destroys the active private view and late readiness cannot recover the token',async()=>{
 const s=setup();await s.unlock();s.nodes['workspace-lock'].fire('click');s.posts.length=0;s.ready();
 assert.equal(s.posts.length,0);assert.equal(s.nodes['workspace-frame'].src,'about:blank');
 assert.ok(s.nodes['workspace-frame'].hidden);assert.equal(s.nodes['workspace-mode'].textContent,'Unlock to inspect the current account and its actual settings.');
});
test('pending confirmation/request prevents navigation and authorization failure locks the whole workspace',async()=>{
 const s=setup();await s.unlock();s.child.AgenticNavigation.canNavigate=()=>false;s.navigate('portfolio');
 assert.equal(s.win.location.hash,'#risk');assert.match(s.nodes['workspace-message'].textContent,/Finish or cancel/);
 s.events.message({origin:s.win.location.origin,source:s.child,data:{type:'workspace-locked'}});
 assert.ok(!s.nodes['workspace-access'].hidden);assert.ok(s.nodes['workspace-frame'].hidden);
});
test('pagehide clears memory and late authorization response cannot unlock again',async()=>{
 let finish;const s=setup(()=>new Promise(r=>{finish=r;}));await s.unlock();s.events.pagehide();finish(ok(info()));await flush();
 assert.ok(s.nodes['workspace-frame'].hidden);assert.equal(s.nodes['workspace-state'].textContent,'Locked');
});
test('section bridge redirects standalone pages but preserves legacy CLI and handled Kite callbacks',()=>{
 const source=readFileSync('src/trading_agent/api/static/workspace-bridge.js','utf8');
 for(const [search,handled,expected] of [['',false,'/workspace#broker'],['?request_token=manual',false,null],['',true,null]]){
  let redirected=null;const win={location:{search,pathname:'/setup',replace:v=>{redirected=v;}},__kiteCallbackHandled:handled};win.parent=win;
  vm.runInNewContext(source,{window:win,document:{},URLSearchParams});assert.equal(redirected,expected);
 }
});
test('section bridge verifies parent identity and suppresses a false lock during shared-token handoff',()=>{
 const events={},posts=[];const parent={postMessage:(...a)=>posts.push(a)};
 const win={parent,location:{origin:'http://127.0.0.1:8004',pathname:'/portfolio'},addEventListener:(n,f)=>{events[n]=f;}};
 const input={value:''};let submissions=0,locks=0;
 const form={dispatchEvent(){submissions++;win.AgenticNavigation.locked();input.value='';}};
 const doc={body:{classList:{add(){}}},getElementById:id=>id==='token'?input:form,addEventListener(){}};
 vm.runInNewContext(readFileSync('src/trading_agent/api/static/workspace-bridge.js','utf8'),{window:win,document:doc,URLSearchParams,Event:class{},URL});
 win.AgenticNavigation.connect({lock(){locks++;win.AgenticNavigation.locked();},canNavigate:()=>true},'access');
 const event={origin:win.location.origin,source:parent,data:{type:'workspace-unlock',token:'test-operator-token-long-enough-123456789'}};
 events.message({...event,origin:'https://evil.test'});events.message({...event,source:{}});assert.equal(submissions,0);
 events.message(event);assert.equal(submissions,1);assert.equal(posts.filter(p=>p[0].type==='workspace-locked').length,0);
 win.AgenticNavigation.locked();assert.equal(posts.at(-1)[0].type,'workspace-locked');
 events.message({...event,data:{type:'workspace-lock'}});assert.equal(locks,1);
});
test('real setup controller accepts workspace handoff without a second unlock and propagates its lock',async()=>{
 const {createSetup}=require('../../src/trading_agent/api/static/setup.js');
 const s=setup();await s.unlock();s.navigate('setup');
 const nodes=Object.fromEntries([...readFileSync('src/trading_agent/api/static/setup.html','utf8').matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const childEvents={},childCalls=[];
 const parent={postMessage(data,origin){s.events.message({data,origin,source:child});}};
 const child={parent,location:{origin:s.win.location.origin,pathname:'/setup'},addEventListener:(n,f)=>{childEvents[n]=f;},setTimeout:()=>1,clearTimeout(){},postMessage(data,origin){childEvents.message({data,origin,source:parent});}};
 s.nodes['workspace-frame'].contentWindow=child;
 const doc={body:{classList:{add(){}}},getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:()=>new Element(),addEventListener(){}};
 class SubmitEvent {constructor(type){this.type=type;}preventDefault(){}}
 vm.runInNewContext(readFileSync('src/trading_agent/api/static/workspace-bridge.js','utf8'),{window:child,document:doc,URLSearchParams,Event:SubmitEvent,URL});
 const view=createSetup(doc,child,async(url,options)=>{childCalls.push({url,options});return ok({manual:true,credentials_configured:true,access_token_available:true,profile_verified_this_run:false,stream_requested:false,feed_connected:false,catalog_count:3,selected:[],sessions:[],today:'2026-10-21',calendar_today:false});});
 child.AgenticNavigation.connect(view,'access');await flush();
 assert.equal(childCalls.length,1);assert.equal(childCalls[0].url,'/api/setup');
 assert.equal(childCalls[0].options.headers.Authorization,'Bearer valid-test-operator-token-1234567890');
 assert.equal(nodes.token.value,'');assert.equal(nodes.private.hidden,false);
 assert.equal(s.nodes['workspace-access'].hidden,true);
 view.lock();assert.equal(s.nodes['workspace-access'].hidden,false);assert.equal(s.nodes['workspace-frame'].src,'about:blank');
});
test('returning to Dashboard refreshes feed state without losing the workspace unlock',async()=>{
 let connected=false;const s=setup(async()=>ok({...info(),feed_requested:connected,feed_connected:connected}));
 await s.unlock();s.navigate('setup');connected=true;s.navigate('dashboard');await flush();
 assert.equal(s.calls.length,2);assert.match(s.nodes['workspace-feed'].textContent,/connection established/);
 assert.equal(s.nodes['workspace-access'].hidden,true);
});
test('direct desk fragment survives redirect into a bookmarkable workspace route',()=>{
 let redirected;
 const win={location:{search:'',pathname:'/desk',hash:'#apply-shortlist',replace:v=>{redirected=v;}}};win.parent=win;
 vm.runInNewContext(readFileSync('src/trading_agent/api/static/workspace-bridge.js','utf8'),{window:win,document:{},URLSearchParams});
 assert.equal(redirected,'/workspace#strategies/execution-shortlist');
});
test('workspace retains destination fragments, guards section changes and scrolls below sticky navigation',async()=>{
 const s=setup();await s.unlock();s.navigate('desk/apply-shortlist');
 assert.equal(s.nodes['workspace-frame'].src,'/strategies#execution-shortlist');
 assert.equal(s.win.location.hash,'#strategies/execution-shortlist');
 s.ready('strategies');assert.equal(s.posts.at(-1)[0].type,'workspace-unlock');
 s.navigate('desk/execution-shortlist');assert.equal(s.posts.at(-1)[0].type,'workspace-anchor');
 assert.equal(s.posts.at(-1)[0].anchor,'execution-shortlist');
 s.child.AgenticNavigation.canNavigate=()=>false;s.navigate('setup/feed-connection');
 assert.equal(s.win.location.hash,'#strategies/execution-shortlist');
 s.win.scrollY=500;s.win.scrollTo=value=>{s.scrolled=value;};
 s.nodes['workspace-frame'].getBoundingClientRect=()=>({top:-100});
 s.nodes['workspace-nav'].getBoundingClientRect=()=>({height:70});
 s.win.getComputedStyle=()=>({position:'sticky'});
 const event={origin:s.win.location.origin,source:s.child,data:{type:'workspace-scroll-target',top:1300}};
 s.events.message({...event,origin:'https://evil.test'});assert.equal(s.scrolled,undefined);
 s.events.message({...event,source:{}});assert.equal(s.scrolled,undefined);
 s.events.message({...event,data:{type:'workspace-scroll-target',top:Infinity}});assert.equal(s.scrolled,undefined);
 s.events.message(event);assert.equal(s.scrolled.top,1614);
 s.win.getComputedStyle=()=>({position:'static'});s.events.message(event);assert.equal(s.scrolled.top,1684);
 assert.equal(s.calls.length,1); // Navigation and reveal never submit an action.
});
test('embedded links preserve fragments and reveal legacy shortlist after unlock without applying it',()=>{
 const events={},posts=[],clicks={};let hidden=true,focused=0;
 const details={tagName:'DETAILS',open:false,parentElement:null};
 const target={parentElement:details,tabIndex:-1,closest:()=>hidden?{}:null,getClientRects:()=>[{}],getBoundingClientRect:()=>({top:1500}),focus:()=>{focused++;}};
 const win={parent:{postMessage:(...a)=>posts.push(a)},location:{origin:'http://127.0.0.1:8004',pathname:'/desk',hash:'#apply-shortlist'},scrollY:0,addEventListener:(n,f)=>{events[n]=f;}};
 const doc={body:{classList:{add(){}},getBoundingClientRect:()=>({height:3000})},getElementById:id=>id==='execution-shortlist'?target:null,addEventListener:(n,f)=>{clicks[n]=f;}};
 vm.runInNewContext(readFileSync('src/trading_agent/api/static/workspace-bridge.js','utf8'),{window:win,document:doc,URLSearchParams,URL});
 win.AgenticNavigation.connect({canNavigate:()=>true},'access');assert.equal(focused,0);
 hidden=false;win.AgenticNavigation.updated();assert.equal(focused,1);assert.equal(details.open,true);
 assert.equal(posts.at(-1)[0].type,'workspace-scroll-target');assert.equal(posts.at(-1)[0].top,1500);
 assert.equal(posts.at(-2)[0].type,'workspace-height');assert.equal(posts.at(-2)[0].height,3032);
 win.AgenticNavigation.updated();assert.equal(focused,1); // Polling does not keep jumping.
 let prevented=false;
 const anchor={href:win.location.origin+'/desk#execution-shortlist'};
 clicks.click({target:{closest:()=>anchor},preventDefault(){prevented=true;}});
 assert.equal(prevented,true);assert.equal(posts.at(-1)[0].view,'strategies');assert.equal(posts.at(-1)[0].anchor,'execution-shortlist');
 const count=posts.length;clicks.click({target:{closest:()=>anchor},ctrlKey:true});assert.equal(posts.length,count);
 events.message({origin:'https://evil.test',source:win.parent,data:{type:'workspace-anchor',anchor:'execution-shortlist'}});assert.equal(focused,1);
 events.message({origin:win.location.origin,source:win.parent,data:{type:'workspace-anchor',anchor:'execution-shortlist'}});assert.equal(focused,2);
});

test('new sidebar sections preserve the same private handoff and ordinary navigation is read-only',async()=>{
 const s=setup(); await s.unlock();
 for(const [view,path] of Object.entries({discovery:'/discovery',analysis:'/analysis',strategies:'/strategies',backtesting:'/backtesting',paper:'/paper',portfolio:'/holdings',history:'/activity',risk:'/console',broker:'/setup',settings:'/settings',learn:'/learn'})) {
  s.navigate(view); s.ready(view);
  assert.equal(s.nodes['workspace-frame'].src,path);
  assert.equal(s.nodes['nav-'+view].attributes['aria-current'],'page');
  assert.equal(s.posts.at(-1)[0].type,'workspace-unlock');
 }
 assert.equal(s.calls.length,1);
 assert.equal(s.nodes['workspace-title'].textContent,'Learning Center');
 s.nodes['workspace-lock'].fire('click');
 assert.equal(s.nodes['workspace-onboarding'].hidden,true);
});
test('contextual onboarding reflects missing setup and clears on lock without activating anything',async()=>{
 const s=setup(async()=>ok({...info(),analysis_configured:true,calendar_today:true,feed_requested:true}));
 await s.unlock(); assert.equal(s.nodes['workspace-onboarding'].hidden,true);
 assert.equal(s.calls.length,1);
 const t=setup();await t.unlock();
 assert.equal(t.nodes['workspace-onboarding'].hidden,false);
 assert.equal(t.nodes['onboarding-action'].href,'#strategies');
 t.nodes['workspace-lock'].fire('click');assert.equal(t.nodes['workspace-onboarding'].hidden,true);
});

test('same-screen anchors and purchase subviews remain guarded; handshake checks the actual child path',async()=>{
 const s=setup();await s.unlock();s.navigate('portfolio');s.posts.length=0;
 s.events.message({origin:s.win.location.origin,source:s.child,data:{type:'workspace-ready',view:'portfolio'}});assert.equal(s.posts.length,0);
 s.events.message({origin:s.win.location.origin,source:s.child,data:{type:'workspace-ready',view:'portfolio',path:'/portfolio'}});assert.equal(s.posts.length,0);
 s.events.message({origin:s.win.location.origin,source:s.child,data:{type:'workspace-ready',view:'portfolio',path:'/holdings'}});assert.equal(s.posts.length,1);
 let focused=0;s.nodes['workspace-main'].focus=()=>{focused++;};s.navigate('workspace-main');assert.equal(s.win.location.hash,'#portfolio');assert.equal(focused,1);assert.equal(s.nodes['workspace-frame'].src,'/holdings');
 s.child.AgenticNavigation.canNavigate=()=>false;s.navigate('portfolio/purchases');assert.equal(s.win.location.hash,'#portfolio');
 s.child.AgenticNavigation.canNavigate=()=>true;s.navigate('portfolio/purchases');assert.equal(s.nodes['workspace-frame'].src,'/portfolio#buy-heading');
 s.navigate('portfolio/holdings-heading');assert.equal(s.posts.at(-1)[0].type,'workspace-anchor');assert.equal(s.posts.at(-1)[0].anchor,'holdings-heading');
 s.child.AgenticNavigation.canNavigate=()=>false;s.navigate('portfolio/plans-heading');assert.equal(s.win.location.hash,'#portfolio/holdings-heading');
});
test('narrow menu exposes every destination, closes on navigation, and stays inert during a child confirmation',async()=>{
 const s=setup();s.win.matchMedia=()=>({matches:true});s.events.resize();assert.equal(s.nodes['workspace-nav'].hidden,true);
 s.nodes['workspace-menu-toggle'].fire('click');assert.equal(s.nodes['workspace-nav'].hidden,false);assert.equal(s.nodes['workspace-menu-toggle'].getAttribute('aria-expanded'),'true');
 await s.unlock();assert.equal(s.nodes['workspace-nav'].hidden,true);
 const event={origin:s.win.location.origin,source:s.child,data:{type:'workspace-dialog',open:true}};
 s.events.message({...event,origin:'https://evil.test'});assert.equal(s.nodes['workspace-nav'].inert,false);
 s.events.message(event);assert.equal(s.nodes['workspace-nav'].inert,true);assert.equal(s.nodes['workspace-sidebar'].inert,true);assert.equal(s.nodes['workspace-footer'].inert,true);assert.equal(s.nodes['workspace-menu-toggle'].disabled,true);
 s.navigate('risk/long-term');assert.equal(s.win.location.hash,'#risk');
 s.events.message({...event,data:{type:'workspace-dialog',open:false}});assert.equal(s.nodes['workspace-nav'].inert,false);
 s.nodes['workspace-menu-toggle'].fire('click');s.navigate('learn');assert.equal(s.nodes['workspace-nav'].hidden,true);assert.equal(s.nodes['workspace-frame'].src,'/learn');
 s.win.matchMedia=()=>({matches:false});s.events.resize();assert.equal(s.nodes['workspace-nav'].hidden,false);
});
test('legacy aliases and all purchase links retain their destination without applying an action',()=>{
 const source=readFileSync('src/trading_agent/api/static/workspace-bridge.js','utf8');
 for(const [pathname,hash,expected] of [['/desk','','dashboard'],['/setup','#feed-connection','broker/feed-connection'],['/console','#long-term','risk/long-term'],['/activity','','history'],['/portfolio','','portfolio/purchases'],['/portfolio','#holdings-heading','portfolio/holdings-heading'],['/holdings','#holdings','portfolio/holdings']]){
  let redirect;const win={location:{pathname,hash,search:'',replace:value=>{redirect=value;}}};win.parent=win;vm.runInNewContext(source,{window:win,document:{},URLSearchParams});assert.equal(redirect,'/workspace#'+expected);
 }
});

test('investment-policy is a guarded Strategies subview with matching path handoff and preserved legacy setup anchors',async()=>{
 const s=setup();await s.unlock();s.navigate('strategies/investment-policy');assert.equal(s.nodes['workspace-frame'].src,'/investment-policy#investment-policy');assert.equal(s.nodes['nav-strategies'].attributes['aria-current'],'page');s.ready('strategies');assert.equal(s.posts.at(-1)[0].type,'workspace-unlock');s.child.AgenticNavigation.canNavigate=()=>false;s.navigate('strategies/strategy-setup');assert.equal(s.win.location.hash,'#strategies/investment-policy');assert.equal(s.nodes['workspace-frame'].src,'/investment-policy#investment-policy');s.child.AgenticNavigation.canNavigate=()=>true;s.navigate('strategies/strategy-setup');assert.equal(s.nodes['workspace-frame'].src,'/strategies#strategy-setup');
});

test('menu and onboarding update their text spans, preserving decorative icons and collapsed guidance',async()=>{
 const s=setup();const menuIcon=new Element(),actionIcon=new Element();s.nodes['workspace-menu-toggle'].append(menuIcon);s.nodes['onboarding-action'].append(actionIcon);await s.unlock();s.navigate('analysis');assert.equal(s.nodes['workspace-menu-label'].textContent,'Menu · Stock Analysis');assert.equal(s.nodes['onboarding-action-label'].textContent,'Set up a strategy');assert.ok(s.nodes['workspace-menu-toggle'].children.includes(menuIcon));assert.ok(s.nodes['onboarding-action'].children.includes(actionIcon));assert.equal(s.nodes['workspace-onboarding'].open,false);assert.equal(s.nodes['workspace-section-note'].hidden,true);s.nodes['workspace-onboarding'].open=true;s.instance.lock();assert.equal(s.nodes['workspace-onboarding'].open,false);assert.equal(s.nodes['workspace-onboarding'].hidden,true);
});
