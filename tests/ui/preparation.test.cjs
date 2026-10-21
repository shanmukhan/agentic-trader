'use strict';
const {test}=require('node:test'), assert=require('node:assert/strict'),{readFileSync}=require('node:fs');
const {createPreparation}=require('../../src/trading_agent/api/static/preparation.js');
class Element{
 constructor(){this.events={};this.children=[];this.value='';this.disabled=false;this.checked=false;}
 set textContent(v){this.text=String(v);this.children=[];}get textContent(){return(this.text||'')+this.children.map(n=>n.textContent).join('');}
 set innerHTML(_){throw Error('unsafe HTML');}append(...items){this.children.push(...items);}replaceChildren(...items){this.text='';this.children=items;}
 addEventListener(name,fn){this.events[name]=fn;}fire(name){if(!this.disabled&&this.events[name])this.events[name]({preventDefault(){}});}
}
const flush=()=>new Promise(r=>setImmediate(r));
const job=(extra={})=>({job_id:'a'.repeat(32),state:'ready_for_review',stage:'review',total:98,completed:98,eligible:97,completed_sessions:60,symbols:['NSE:A000'],calendar_csv:'date,open,close\n2026-10-21,09:15,15:30\n',preview_sha256:'b'.repeat(64),excluded:[{symbol:'NSE:DIV',reason:'CORPORATE_ACTION_IN_HISTORY'}],...extra});
function setup(){
 const nodes=Object.fromEntries([...readFileSync('src/trading_agent/api/static/desk.html','utf8').matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const calls=[],dialogs=[];let refreshes=0;
 const data={mode:'manual',revision:'c'.repeat(32)},doc={getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:()=>new Element()};
 const ui=createPreparation(doc,{crypto:{getRandomValues:a=>a.fill(9)}},async(path,body)=>{calls.push({path,body});return{available:true,ml_configured:false,job:job({state:'installed'})};},async()=>{refreshes++;},(title,text,action)=>dialogs.push({title,text,action}),()=>data);
 const view={available:true,ml_configured:false,job:job(),sources:{actions:'https://www.nseindia.com/companies-listing/corporate-filings-actions'}};
 return{nodes,ui,calls,dialogs,data,view,get refreshes(){return refreshes;}};
}
test('no automatic download, no prechecked reviews, explicit rules selection and truthful ML explanation',()=>{
 const s=setup();s.ui.render(s.view);
 assert.equal(s.calls.length,0);assert.equal(s.nodes['prep-policy'].value,'');
 for(const id of ['prep-calendar-reviewed','prep-basis-reviewed','prep-policy-reviewed'])assert.equal(s.nodes[id].checked,false);
 assert.equal(s.nodes['prep-ml-option'].disabled,true);assert.match(s.nodes['prep-model-help'].textContent,/cannot validate ML/);
 assert.match(s.nodes['prep-exclusions'].textContent,/corporate action/);assert.match(s.nodes['prep-result'].textContent,/prospective/);
});
test('periodic refresh preserves edited calendar, selected policy and review inputs',()=>{
 const s=setup();s.ui.render(s.view);s.nodes['prep-calendar'].value='edited dates';s.nodes['prep-policy'].value='rules';s.nodes['prep-reference'].value='Reviewed actual notices';s.nodes['prep-calendar-reviewed'].checked=true;
 s.ui.render(s.view);assert.equal(s.nodes['prep-calendar'].value,'edited dates');assert.equal(s.nodes['prep-policy'].value,'rules');assert.equal(s.nodes['prep-calendar-reviewed'].checked,true);
 s.ui.clear();assert.equal(s.nodes['prep-calendar'].value,'');assert.equal(s.nodes['prep-reference'].value,'');assert.equal(s.nodes['prep-calendar-reviewed'].checked,false);
});
test('download requires confirmation, only uses server-selected universe and cannot submit an order',async()=>{
 const s=setup();s.ui.render({...s.view,job:null});s.nodes['prep-universe'].value='nifty500';s.nodes['prep-download'].fire('click');
 assert.equal(s.calls.length,0);assert.match(s.dialogs[0].text,/does not change your mode/);await s.dialogs[0].action();
 assert.equal(s.calls[0].path,'/api/desk/preparation/download');assert.equal(s.calls[0].body.universe,'nifty500');assert.equal(s.calls[0].body.revision,s.data.revision);assert.match(s.calls[0].body.request_id,/^[a-f0-9]{32}$/);
 assert.equal(s.calls.length,1);assert.equal(s.refreshes,1);
});
test('installation confirmation binds edited review, selected policy and current source hash',async()=>{
 const s=setup();s.ui.render(s.view);s.nodes['prep-policy'].value='rules';s.nodes['prep-reference'].value='Genuine operator review';
 s.nodes['prep-form'].fire('submit');assert.equal(s.dialogs.length,0);
 for(const id of ['prep-calendar-reviewed','prep-basis-reviewed','prep-policy-reviewed'])s.nodes[id].checked=true;
 s.nodes['prep-form'].fire('submit');assert.equal(s.calls.length,0);assert.match(s.dialogs[0].text,/EXPERIMENTAL RULES ONLY/);assert.match(s.dialogs[0].text,/Manual stays selected/);await s.dialogs[0].action();
 const call=s.calls[0];assert.equal(call.path,'/api/desk/preparation/install');assert.equal(call.body.preview_sha256,s.view.job.preview_sha256);assert.equal(call.body.strategy_mode,'rules');assert.equal(call.body.calendar_reviewed,true);assert.equal(call.body.calendar_csv,s.nodes['prep-calendar'].value);
});
test('download failures explain concrete recovery and disabled controls remain independent of connected feed',()=>{
 const s=setup();s.ui.render({...s.view,job:job({state:'failed',error:'BROKER_DAILY_HISTORY_UNAVAILABLE'})});assert.match(s.nodes['prep-error'].textContent,/WebSocket does not prove history access/);
 s.data.mode='automatic';s.ui.render(s.view);assert.equal(s.nodes['prep-install'].disabled,true);assert.equal(s.nodes['prep-download'].disabled,true);
 s.data.mode='manual';s.ui.render({...s.view,job:job({state:'downloading',completed:3})});assert.equal(s.nodes['prep-download'].disabled,true);assert.equal(s.nodes['prep-cancel'].disabled,false);assert.equal(s.nodes['prep-progress-bar'].value,3);
 s.ui.controls(true,true);assert.equal(s.nodes['prep-cancel'].disabled,true);
});
test('locking clears private history, source references and controls',()=>{
 const s=setup();s.ui.render(s.view);s.ui.clear();assert.equal(s.nodes['prep-sources'].children.length,0);assert.equal(s.nodes['prep-exclusions'].children.length,0);assert.equal(s.nodes['prep-install'].disabled,true);assert.equal(s.nodes['prep-progress'].textContent,'');
});
test('custom profile override and older server routes give recovery instead of an inert installation form',()=>{
 const s=setup();s.ui.render({...s.view,profile_override:true});assert.equal(s.nodes['prep-install'].disabled,true);assert.match(s.nodes['prep-availability'].textContent,/Clear it and restart/);
 s.ui.render(undefined);assert.equal(s.nodes['prep-install'].disabled,true);assert.match(s.nodes['prep-state'].textContent,/restart required/);
});
test('calendar conflicts show old/proposed hours and never pre-approve empty-account correction',()=>{
 const s=setup();s.ui.render({...s.view,calendar_conflicts:[{date:'2026-10-21',existing:'09:15–15:15',proposed:'09:15–15:30'}],can_correct_unused_calendar:true});
 assert.match(s.nodes['prep-calendar-conflicts'].textContent,/saved 09:15–15:15/);assert.equal(s.nodes['prep-correction-label'].hidden,false);assert.equal(s.nodes['prep-calendar-correction'].checked,false);
 s.ui.render({...s.view,can_correct_unused_calendar:false});assert.equal(s.nodes['prep-calendar-correction'].disabled,true);assert.equal(s.nodes['prep-correction-label'].hidden,true);
});
