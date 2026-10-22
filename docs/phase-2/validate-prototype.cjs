'use strict';
// Design-only DOM checks. No browser rendering, application import, network or account.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'prototype.html'),'utf8');
const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'navigation.json'),'utf8'));
class Element{
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.attributes={};this.events={};this.open=false;this.value='';this.classes=new Set();this.classList={add:x=>this.classes.add(x),remove:x=>this.classes.delete(x),toggle:x=>{if(this.classes.has(x)){this.classes.delete(x);return false;}this.classes.add(x);return true;}};}
 set className(value){this.classes=new Set(String(value).split(/\s+/).filter(Boolean));}
 get className(){return [...this.classes].join(' ');}
 set textContent(value){this.text=String(value);this.children=[];}
 get textContent(){return (this.text||'')+this.children.map(n=>n.textContent).join('');}
 append(...nodes){this.children.push(...nodes);if(this.tagName==='SELECT'&&!this.value&&nodes.length)this.value=nodes[0].value||nodes[0].textContent;}
 replaceChildren(...nodes){this.text='';this.children=[...nodes];}
 setAttribute(name,value){this.attributes[name]=String(value);}
 removeAttribute(name){delete this.attributes[name];}
 addEventListener(name,callback){(this.events[name]||=[]).push(callback);}
 fire(name){if(this.disabled)return;for(const cb of this.events[name]||[])cb({preventDefault(){}});}
 querySelectorAll(selector){const all=[];for(const n of this.children){if(selector==='[data-screen]'&&n.dataset.screen)all.push(n);all.push(...n.querySelectorAll(selector));}return all;}
 focus(){this.focused=true;}
 showModal(){this.open=true;}
 close(){this.open=false;}
}
function create(){
 const nodes={};for(const match of html.matchAll(/\bid="([^"]+)"/g))nodes[match[1]]=new Element();
 nodes['navigation-data'].textContent=JSON.stringify(manifest);nodes['preview-state'].value='setup';
 const doc={getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:tag=>new Element(tag)};
 const scripts=[...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)].filter(m=>!m[1].includes('application/json'));
 assert.equal(scripts.length,1);const blocked=()=>{throw Error('A design preview must not access network or account APIs');};
 vm.runInNewContext(scripts[0][2],{document:doc,fetch:blocked,XMLHttpRequest:blocked,WebSocket:blocked,localStorage:{setItem:blocked,getItem:blocked},sessionStorage:{setItem:blocked,getItem:blocked}},{filename:'phase2-prototype.js',timeout:1000});
 const visit=id=>{const link=nodes['preview-nav'].querySelectorAll('[data-screen]').find(n=>n.dataset.screen===id);assert.ok(link,id);link.fire('click');};
 return {nodes,visit};
}
function find(root,tag,text){if(root.tagName===tag.toUpperCase()&&root.textContent.includes(text))return root;for(const child of root.children){const result=find(child,tag,text);if(result)return result;}return null;}
test('prototype embeds the exact navigation contract and no duplicate static identifiers',()=>{
 const embedded=html.match(/<script id="navigation-data" type="application\/json">([\s\S]*?)<\/script>/);
 assert.deepEqual(JSON.parse(embedded[1]),manifest);assert.equal(manifest.screens.length,12);
 const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);
 for(const reference of html.matchAll(/(?:aria-controls|aria-labelledby|aria-describedby|for)="([^"]+)"/g))for(const id of reference[1].split(' '))assert.ok(ids.includes(id),id);
});
test('all twelve destinations render through local navigation without account access',()=>{
 const s=create();for(const screen of manifest.screens){s.visit(screen.id);assert.equal(s.nodes['screen-title'].textContent,screen.title);const current=s.nodes['preview-nav'].querySelectorAll('[data-screen]').filter(n=>n.attributes['aria-current']==='page');assert.equal(current.length,1);assert.equal(current[0].dataset.screen,screen.id);assert.ok(s.nodes['screen-content'].children.length>0);}
 assert.match(html,/DESIGN PREVIEW · Not connected to an account/);assert.doesNotMatch(html,/<input[^>]+type="password"/);
});
test('all example state and destination combinations render without invented balances',()=>{
 const s=create();for(const state of ['setup','waiting','stale','missing'])for(const screen of manifest.screens){s.visit(screen.id);s.nodes['preview-state'].value=state;s.nodes['preview-state'].fire('change');assert.equal(s.nodes['screen-title'].textContent,screen.title);assert.doesNotMatch(s.nodes['screen-content'].textContent,/₹[1-9][0-9,]*\.\d\d/);}
 s.visit('dashboard');s.nodes['preview-state'].value='stale';s.nodes['preview-state'].fire('change');assert.match(s.nodes['screen-content'].textContent,/Valuation needs fresh data/);
});
test('analysis interval selection changes only a missing-history message',()=>{
 const s=create();s.visit('analysis');const select=find(s.nodes['screen-content'],'select','Daily');assert.ok(select);select.value='Monthly';select.fire('change');assert.match(s.nodes['screen-content'].textContent,/Monthly history is not loaded/);assert.match(s.nodes['screen-content'].textContent,/No candles or indicator values are inferred/);
});
test('connection preview cancel and confirm close locally with no real action',()=>{
 const s=create();s.visit('broker');const opener=find(s.nodes['screen-content'],'button','Preview connection confirmation');assert.ok(opener);opener.fire('click');assert.equal(s.nodes['connection-preview'].open,true);assert.equal(s.nodes['preview-cancel'].focused,true);s.nodes['preview-cancel'].fire('click');assert.equal(s.nodes['connection-preview'].open,false);assert.match(s.nodes['preview-feedback'].textContent,/No connection was requested/);opener.fire('click');s.nodes['preview-confirm'].fire('click');assert.equal(s.nodes['connection-preview'].open,false);assert.match(s.nodes['preview-feedback'].textContent,/No connection or financial action was requested/);
});
test('mobile menu exposes expanded state and closes after navigation',()=>{
 const s=create();s.nodes['menu-toggle'].fire('click');assert.equal(s.nodes['menu-toggle'].attributes['aria-expanded'],'true');s.visit('learn');assert.equal(s.nodes['menu-toggle'].attributes['aria-expanded'],'false');assert.match(s.nodes['menu-toggle'].textContent,/Learning Center/);
});
