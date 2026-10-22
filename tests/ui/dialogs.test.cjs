'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {createDialogs}=require('../../src/trading_agent/api/static/dialogs.js');
class Events{
 constructor(){this.events=new Map();}
 addEventListener(name,fn){if(!this.events.has(name))this.events.set(name,new Set());this.events.get(name).add(fn);}
 removeEventListener(name,fn){this.events.get(name)?.delete(fn);if(!this.events.get(name)?.size)this.events.delete(name);}
 fire(name){let prevented=false;for(const fn of [...(this.events.get(name)||[])])fn({preventDefault(){prevented=true;}});return prevented;}
 get count(){return [...this.events.values()].reduce((sum,set)=>sum+set.size,0);}
}
function fixture({embedded=true,rect={top:-2900,bottom:1600,left:240,right:1400,width:1160,height:4500},visual=null}={}){
 const events=[],trigger={isConnected:true,focus(options){events.push(['restore',options]);}},doc={activeElement:trigger};
 const win=Object.assign(new Events(),{innerWidth:1440,innerHeight:844,location:{origin:'http://127.0.0.1:8004'}});
 const parent=Object.assign(new Events(),{innerWidth:1440,innerHeight:844,postMessage(message,origin){events.push(['message',message,origin]);}});
 if(visual)parent.visualViewport=Object.assign(new Events(),visual);
 let currentRect=rect,reveals=0,observer;
 const frame={getBoundingClientRect:()=>currentRect,scrollIntoView(options){reveals++;events.push(['reveal',options]);}};
 if(embedded){win.parent=parent;win.frameElement=frame;}else win.parent=win;
 win.ResizeObserver=class{constructor(fn){this.fn=fn;observer=this;}observe(element){this.element=element;}disconnect(){this.disconnected=true;}};
 const dialog=Object.assign(new Events(),{style:{maxWidth:'720px'},open:false,
  showModal(){events.push(['show',Object.assign({},this.style)]);this.open=true;},close(){this.open=false;this.fire('close');}});
 const cancel={focus(options){events.push(['focus',options]);}};
 const api=createDialogs(doc,win);
 return{api,doc,win,parent,dialog,cancel,events,frame,trigger,get observer(){return observer;},get reveals(){return reveals;},move:value=>{currentRect=value;}};
}
function inBounds(s,area){
 const style=s.dialog.style,height=parseFloat(style.maxHeight),width=parseFloat(style.maxWidth),top=parseFloat(style.top),left=parseFloat(style.left);
 assert.ok(Number.isFinite(height)&&height>0);assert.ok(Number.isFinite(width)&&width>0);
 assert.ok(top-height/2>=area.top-.001);assert.ok(top+height/2<=area.bottom+.001);
 assert.ok(left-width/2>=area.left-.001);assert.ok(left+width/2<=area.right+.001);
}
test('deep-scroll frame is positioned before native autofocus with no parent scroll or data disclosure',()=>{
 const s=fixture();let cancels=0;s.api.open(s.dialog,{cancel:()=>cancels++,focus:s.cancel});
 const shown=s.events.find(e=>e[0]==='show')[1];
 assert.equal(shown.top,'3322px');assert.equal(shown.left,'580px');assert.equal(shown.maxHeight,'812px');assert.equal(shown.maxWidth,'1128px');
 assert.equal(shown.position,'fixed');assert.equal(shown.transform,'translate(-50%, -50%)');assert.equal(shown.margin,'0');
 assert.equal(s.reveals,0);assert.deepEqual(s.events.find(e=>e[0]==='focus'),['focus',{preventScroll:true}]);
 assert.deepEqual(s.events.find(e=>e[0]==='message'),['message',{type:'workspace-dialog',open:true},'http://127.0.0.1:8004']);
 s.api.close(s.dialog);assert.equal(cancels,0);assert.equal(s.dialog.style.maxWidth,'720px');assert.equal(s.parent.count,0);assert.equal(s.win.count,0);assert.ok(s.observer.disconnected);
 assert.deepEqual(s.events.at(-1),['restore',{preventScroll:true}]);
 assert.equal(s.events.filter(e=>e[0]==='message').at(-1)[1].open,false);
});
test('top, middle and deep frames fit 320/360/768/1440px visible intersections before show',()=>{
 for(const width of [320,360,768,1440])for(const top of [90,-400,-2900]){
  const s=fixture({rect:{left:0,right:width,width,top,bottom:top+4500,height:4500}});s.parent.innerWidth=width;
  assert.equal(s.api.open(s.dialog,{focus:s.cancel}),true);
  inBounds(s,{left:16,right:width-16,top:Math.max(0,top)+16-top,bottom:844-16-top});s.api.close(s.dialog);
 }
});
test('visual viewport zoom and keyboard offsets update both axes and survive long content resizing',()=>{
 const s=fixture({rect:{left:-80,right:720,width:800,top:-1800,bottom:2200,height:4000},visual:{offsetTop:80,offsetLeft:40,width:360,height:500}});
 s.api.open(s.dialog,{focus:s.cancel});
 inBounds(s,{left:136,right:464,top:1896,bottom:2364});
 assert.equal(s.dialog.style.overflow,'auto');assert.equal(s.dialog.style.boxSizing,'border-box');
 assert.equal(s.dialog.style.minWidth,'0');assert.equal(s.dialog.style.minHeight,'0');
 s.parent.visualViewport.height=250;s.parent.visualViewport.fire('resize');
 assert.equal(s.dialog.style.maxHeight,'218px');
 s.observer.fn();assert.equal(s.dialog.style.maxHeight,'218px');assert.equal(s.dialog.open,true);
 s.api.cancel(s.dialog);assert.equal(s.parent.visualViewport.count,0);
});
test('scaled bordered frames translate parent coordinates into child content coordinates',()=>{
 const s=fixture({rect:{left:20,right:620,width:600,top:40,bottom:940,height:900}});
 Object.assign(s.frame,{offsetWidth:1200,offsetHeight:1800,clientLeft:4,clientTop:6,clientWidth:1192,clientHeight:1788});
 s.api.open(s.dialog,{focus:s.cancel});
 // The 0.5 scale applies to border offsets and all parent-space padding.
 assert.equal(s.dialog.style.maxWidth,'1128px');assert.equal(s.dialog.style.maxHeight,'1538px');
 assert.equal(s.dialog.style.left,'596px');assert.equal(s.dialog.style.top,'801px');s.api.destroy();
});
test('no intersection safely reveals and remeasures the section before opening',()=>{
 const s=fixture({rect:{left:240,right:1400,width:1160,top:2000,bottom:6500,height:4500}});
 s.frame.scrollIntoView=options=>{s.events.push(['reveal',options]);s.move({left:240,right:1400,width:1160,top:100,bottom:4600,height:4500});};
 assert.equal(s.api.open(s.dialog,{focus:s.cancel}),true);
 assert.equal(s.events[0][0],'reveal');assert.equal(s.events[1][0],'show');assert.equal(s.dialog.style.maxHeight,'712px');s.api.close();
});
test('a still hidden or zero-size frame cancels authority instead of opening a zero-height confirmation',()=>{
 const s=fixture({rect:{left:0,right:0,width:0,top:2000,bottom:2000,height:0}});let pending=true;
 assert.equal(s.api.open(s.dialog,{cancel:()=>{pending=false;},focus:s.cancel}),false);
 assert.equal(pending,false);assert.equal(s.dialog.open,false);assert.equal(s.reveals,1);assert.equal(s.events.filter(e=>e[0]==='show').length,0);assert.equal(s.win.count,0);assert.equal(s.parent.count,0);
});
test('Escape, direct native close, pagehide and destroy revoke review once and remove every listener',()=>{
 for(const method of ['escape','native','pagehide','destroy']){
  const s=fixture();let pending=true,cancels=0;s.api.open(s.dialog,{cancel:()=>{pending=false;cancels++;},focus:s.cancel});
  if(method==='escape')assert.equal(s.dialog.fire('cancel'),true);
  if(method==='native')s.dialog.close();if(method==='pagehide')s.win.fire('pagehide');if(method==='destroy')s.api.destroy();
  s.api.cancel();s.win.fire('pagehide');s.dialog.fire('cancel');
  assert.equal(pending,false);assert.equal(cancels,1);assert.equal(s.dialog.open,false);assert.equal(s.dialog.count,0);assert.equal(s.win.count,0);assert.equal(s.parent.count,0);assert.ok(s.observer.disconnected);
 }
});
test('parent scroll follows current intersection and loss of all visibility closes instead of clipping',()=>{
 const s=fixture();let cancels=0;s.api.open(s.dialog,{cancel:()=>cancels++,focus:s.cancel});
 s.move({left:240,right:1400,width:1160,top:-3000,bottom:1500,height:4500});s.parent.fire('scroll');assert.equal(s.dialog.style.top,'3422px');
 s.move({left:0,right:0,width:0,top:2000,bottom:2000,height:0});s.parent.fire('scroll');assert.equal(s.dialog.open,false);assert.equal(cancels,1);assert.equal(s.parent.count,0);
});
test('standalone native dialog remains centered, bounded and reacts to its visual viewport',()=>{
 const s=fixture({embedded:false});s.win.innerWidth=360;s.win.innerHeight=640;
 s.api.open(s.dialog,{focus:s.cancel});assert.equal(s.dialog.style.top,'320px');assert.equal(s.dialog.style.left,'180px');assert.equal(s.dialog.style.maxWidth,'328px');assert.equal(s.dialog.style.maxHeight,'608px');
 assert.equal(s.events.filter(e=>e[0]==='message').length,0);s.api.cancel();
});
test('all controllers in one document share one lifecycle; an overlapping request grants no pending authority',()=>{
 const s=fixture(),same=createDialogs(s.doc,s.win),other=Object.assign(new Events(),{open:false,style:{},showModal(){throw Error('must not open');}});let rejected=false;
 assert.equal(same,s.api);s.api.open(s.dialog,{focus:s.cancel});
 assert.equal(same.open(other,{cancel:()=>{rejected=true;}}),false);assert.equal(rejected,true);assert.equal(s.dialog.open,true);
 s.api.cancel(other);assert.equal(s.dialog.open,true);s.api.destroy();
});
test('a delayed close event from the previous review cannot dismiss a newly opened confirmation',()=>{
 const s=fixture();s.api.open(s.dialog,{focus:s.cancel});s.api.close();s.api.open(s.dialog,{focus:s.cancel});s.dialog.fire('close');assert.equal(s.dialog.open,true);s.api.destroy();
});
