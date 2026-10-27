'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const vm = require('node:vm');
const {readFileSync} = require('node:fs');

const code = execFileSync('.venv/bin/python', ['-c',
  'from importlib.resources import files; from trading_agent.api.public_path import PublicAssets; print(PublicAssets(files("trading_agent.api").joinpath("static"), "/agentic-trader").joinpath("workspace.js").read_text())'
], {encoding:'utf8'});
const moduleBox = {exports:{}};
vm.runInNewContext(code, {module:moduleBox, AbortController, Intl, Date, Set, Map, URL, URLSearchParams});
const {createWorkspace} = moduleBox.exports;

class Element {
  constructor(){this.events={};this.value='';this.style={};this.attributes={};this.children=[];this.open=false;}
  set textContent(value){this.text=String(value);this.children=[];}
  get textContent(){return (this.text||'')+this.children.map(n=>n.textContent).join('');}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;this.text='';}
  addEventListener(name, fn){(this.events[name]||=[]).push(fn);}
  fire(name){for(const fn of this.events[name]||[])fn({preventDefault(){}});}
  setAttribute(name,value){this.attributes[name]=value;}
  getAttribute(name){return this.attributes[name];}
  removeAttribute(name){delete this.attributes[name];}
}

test('published HTTPS workspace keeps API, iframe, navigation and credential handoff within its prefix', async()=>{
  const nodes=Object.fromEntries([...readFileSync('src/trading_agent/api/static/workspace.html','utf8').matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
  const events={}, calls=[], posts=[];
  const child={postMessage:(...args)=>posts.push(args),AgenticNavigation:{canNavigate:()=>true}};
  nodes['workspace-frame'].contentWindow=child;
  const win={location:{origin:'https://shanmukhan.com',hash:'#risk'},history:{replaceState(...args){win.location.hash=args[2];}},
    addEventListener:(name,fn)=>{events[name]=fn;},setTimeout:()=>1,clearTimeout(){},setInterval:()=>1};
  createWorkspace({getElementById:id=>nodes[id]},win,async(url,options)=>{
    calls.push({url,options});return {ok:true,status:200,json:async()=>({mode:'paper',investment_horizon:'intraday',observed_at:'2026-10-25T12:00:00Z',feed_requested:false,feed_connected:false})};
  });
  assert.equal(calls.length,0);
  nodes['workspace-token'].value='synthetic-test-operator-token';nodes['workspace-unlock'].fire('submit');
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(calls[0].url,'/agentic-trader/api/workspace');
  assert.equal(calls[0].options.headers.Authorization,'Bearer synthetic-test-operator-token');
  assert.equal(nodes['workspace-frame'].src,'/agentic-trader/console');
  events.message({origin:win.location.origin,source:child,data:{type:'workspace-ready',view:'risk',path:'/agentic-trader/console'}});
  assert.ok(posts.some(([message,origin])=>message.type==='workspace-unlock'&&origin==='https://shanmukhan.com'));
  const count=posts.length;
  events.message({origin:'https://evil.example',source:child,data:{type:'workspace-ready',view:'risk',path:'/agentic-trader/console'}});
  assert.equal(posts.length,count);
  win.location.hash='#analysis';events.hashchange();
  assert.equal(nodes['workspace-frame'].src,'/agentic-trader/analysis');
});
