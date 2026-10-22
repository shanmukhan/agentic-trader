'use strict';
const {test}=require('node:test'), assert=require('node:assert/strict'),{readFileSync}=require('node:fs');
const {createPreparation}=require('../../src/trading_agent/api/static/preparation.js');
class Element{
 constructor(){this.events={};this.children=[];this.value='';this.disabled=false;this.checked=false;this.style={};}
 set textContent(v){this.text=String(v);this.children=[];}get textContent(){return(this.text||'')+this.children.map(n=>n.textContent).join('');}
 set innerHTML(_){throw Error('unsafe HTML');}append(...items){this.children.push(...items);}replaceChildren(...items){this.text='';this.children=items;}
 addEventListener(name,fn){this.events[name]=fn;}fire(name){if(!this.disabled&&this.events[name])this.events[name]({preventDefault(){}});}
 showModal(){this.open=true;}close(){this.open=false;}focus(){this.focused=true;}
}
const flush=()=>new Promise(r=>setImmediate(r));
const job=(extra={})=>({job_id:'a'.repeat(32),state:'ready_for_review',stage:'review',total:98,completed:98,eligible:97,completed_sessions:60,symbols:['NSE:A000'],calendar_csv:'date,open,close\n2026-10-21,09:15,15:30\n',preview_sha256:'b'.repeat(64),excluded:[{symbol:'NSE:DIV',reason:'CORPORATE_ACTION_IN_HISTORY'}],...extra});
function setup(response,windowOptions={}){
 const nodes=Object.fromEntries([...readFileSync('src/trading_agent/api/static/desk.html','utf8').matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const calls=[],dialogs=[];let refreshes=0;
 const data={mode:'manual',revision:'c'.repeat(32)},doc={getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:()=>new Element()};
 const ui=createPreparation(doc,{crypto:{getRandomValues:a=>a.fill(9)},...windowOptions},async(path,body)=>{calls.push({path,body});return response?await response(path,body):{available:true,ml_configured:false,job:job({state:'installed'})};},async()=>{refreshes++;},(title,text,action)=>dialogs.push({title,text,action}),()=>data);
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
const guided=()=>({preview_sha256:'e'.repeat(64),state:'review',plan:{horizon:'long_term',cash:'25000.00',strategy_mode:'rules',eligible:65,completed_sessions:60,history_start:'2026-07-27',history_end:'2026-10-20',symbols:['NSE:EXAMPLE'],held_symbols:[],basis_reviews:['NSE:EXAMPLE'],manual_basis_reviews:[],session_date:'2026-10-21',calendar_conflicts:[{date:'2026-10-21',existing:'09:15–15:15',proposed:'09:15–15:30'}],calendar_csv:'date,open,close\n2026-10-21,09:15,15:30',entry_start:'09:30',entry_end:'14:30',sources:{calendar:'https://www.nseindia.com/'}}});
test('guided path hides advanced forms by default and requires an explicit policy and one unchecked review',async()=>{
 const s=setup(()=>guided());s.ui.render(s.view,null);
 const html=readFileSync('src/trading_agent/api/static/desk.html','utf8');assert.match(html,/<details id="prep-advanced">/);assert.doesNotMatch(html,/<details id="prep-advanced"[^>]*open/);
 s.nodes['guided-review'].fire('click');assert.equal(s.calls.length,0);assert.match(s.nodes['guided-result'].textContent,/Choose a decision policy/);
 s.nodes['prep-policy'].value='rules';s.nodes['guided-review'].fire('click');await flush();
 assert.equal(s.calls[0].path,'/api/desk/preparation/guided/preview');assert.equal(s.nodes['guided-dialog'].open,true);assert.equal(s.ui.canNavigate(),false);
 assert.equal(s.nodes['guided-ack'].checked,false);assert.equal(s.nodes['guided-confirm'].disabled,true);
 assert.match(s.nodes['guided-summary'].textContent,/NSE:EXAMPLE/);assert.match(s.nodes['guided-summary'].textContent,/09:15–15:15 → 09:15–15:30/);assert.match(s.nodes['guided-summary'].textContent,/No mode is activated/);
 s.nodes['guided-cancel'].fire('click');assert.equal(s.ui.canNavigate(),true);assert.equal(s.calls.length,1);
});
test('one acknowledgement submits only the server preview identity, then refreshes completion status',async()=>{
 const s=setup(path=>path.endsWith('preview')?guided():{state:'complete',message:'Setup complete; Manual stays selected.'});s.ui.render(s.view,null);s.nodes['prep-policy'].value='rules';
 s.nodes['guided-review'].fire('click');await flush();s.nodes['guided-ack'].checked=true;s.nodes['guided-ack'].fire('change');assert.equal(s.nodes['guided-confirm'].disabled,false);
 s.nodes['guided-confirm'].fire('click');s.nodes['guided-confirm'].fire('click');await flush();
 assert.equal(s.calls.length,2);assert.deepEqual(s.calls[1],{path:'/api/desk/preparation/guided/confirm',body:{preview_sha256:'e'.repeat(64),acknowledged:true}});
 assert.equal(s.refreshes,1);assert.match(s.nodes['guided-result'].textContent,/Manual stays selected/);
});
test('locking during a guided preview discards late private data and clears an open review',async()=>{
 let finish;const s=setup(()=>new Promise(resolve=>{finish=resolve;}));s.ui.render(s.view,null);s.nodes['prep-policy'].value='rules';s.nodes['guided-review'].fire('click');s.ui.clear();finish(guided());await flush();
 assert.notEqual(s.nodes['guided-dialog'].open,true);assert.equal(s.nodes['guided-summary'].textContent,'');assert.equal(s.nodes['guided-review'].disabled,true);
});
test('saved guided completion or partial failure tells the operator the outcome after refresh',()=>{
 const s=setup();s.ui.render(s.view,{state:'stopped',message:'Setup stopped during connection. Saved steps remain.'});assert.match(s.nodes['guided-result'].textContent,/Saved steps remain/);
 s.ui.render(s.view,{state:'complete',message:'Setup complete. Waiting for market hours; Manual.'});assert.match(s.nodes['guided-result'].textContent,/Waiting for market hours/);
 s.ui.clear();assert.equal(s.nodes['guided-result'].textContent,'');
});
test('embedded review fits the visible parent viewport and removes parent listeners when closed',async()=>{
 const listeners=new Map(),parent={innerHeight:844,addEventListener:(type,fn)=>listeners.set(type,fn),removeEventListener:type=>listeners.delete(type)};
 const s=setup(()=>guided(),{parent,frameElement:{getBoundingClientRect:()=>({top:-2900})}});s.ui.render(s.view,null);s.nodes['prep-policy'].value='rules';s.nodes['guided-review'].fire('click');await flush();
 assert.equal(s.nodes['guided-dialog'].style.maxHeight,'692px');assert.equal(s.nodes['guided-dialog'].style.top,'2976px');assert.equal(listeners.size,2);
 parent.innerHeight=1100;listeners.get('resize')();assert.equal(s.nodes['guided-dialog'].style.maxHeight,'902px');
 s.nodes['guided-cancel'].fire('click');assert.equal(listeners.size,0);
});
function readyDailyReview(s){
 Object.assign(s.data,{strategy_mode:'rules',observed_at:'2026-10-22T05:10:00Z',blockers:['LONG_TERM_REVIEW_REQUIRED']});
 s.ui.render({...s.view,job:job({snapshot_at:'2026-10-22T05:07:28Z'})},null);
}
test('daily-review shortcut beside the warning opens a preview using the existing policy without approving',async()=>{
 const s=setup(()=>guided());readyDailyReview(s);
 assert.equal(s.nodes['daily-review'].hidden,false);assert.equal(s.nodes['daily-review-button'].disabled,false);
 assert.equal(s.nodes['quote-review-button'].hidden,false);assert.equal(s.nodes['daily-review-download'].hidden,true);
 assert.match(s.nodes['daily-review-message'].textContent,/Restarting or opening the summary does not approve/);
 assert.equal(s.nodes['prep-policy'].value,'');assert.equal(s.calls.length,0);
 s.nodes['daily-review-button'].fire('click');await flush();
 assert.equal(s.calls.length,1);assert.deepEqual(s.calls[0],{path:'/api/desk/preparation/guided/preview',body:{revision:s.data.revision,strategy_mode:'rules'}});
 assert.equal(s.nodes['guided-dialog'].open,true);assert.equal(s.nodes['guided-ack'].checked,false);
 assert.equal(s.nodes['guided-confirm'].disabled,true);
 s.nodes['guided-cancel'].fire('click');assert.equal(s.calls.length,1);
 assert.equal(s.nodes['daily-review'].hidden,false);
});
test('quote-row shortcut still requires acknowledgement before exactly one confirmation',async()=>{
 const s=setup(path=>path.endsWith('preview')?guided():{state:'complete',message:'Manual stays selected.'});readyDailyReview(s);
 s.nodes['quote-review-button'].fire('click');await flush();
 s.nodes['guided-confirm'].fire('click');assert.equal(s.calls.length,1);
 s.nodes['guided-ack'].checked=true;s.nodes['guided-ack'].fire('change');
 s.nodes['guided-confirm'].fire('click');s.nodes['guided-confirm'].fire('click');await flush();
 assert.equal(s.calls.length,2);assert.equal(s.calls[1].path,'/api/desk/preparation/guided/confirm');
 assert.deepEqual(s.calls[1].body,{preview_sha256:'e'.repeat(64),acknowledged:true});
});
test('daily-review shortcut refuses stale sources, non-manual mode and unavailable combined setup',()=>{
 const s=setup();readyDailyReview(s);
 s.ui.render({...s.view,job:job({snapshot_at:'2026-10-21T05:07:28Z'})},null);
 assert.equal(s.nodes['daily-review-button'].disabled,true);assert.equal(s.nodes['daily-review-download'].hidden,false);
 assert.match(s.nodes['daily-review-message'].textContent,/Yesterday’s download\/review/);
 s.nodes['daily-review-button'].fire('click');assert.equal(s.calls.length,0);
 s.data.mode='automatic';readyDailyReview(s);assert.equal(s.nodes['daily-review-button'].disabled,true);
 assert.match(s.nodes['daily-review-message'].textContent,/Choose Manual/);
 s.data.mode='manual';s.ui.render({...s.view,profile_override:true,job:job({snapshot_at:'2026-10-22T05:07:28Z'})},null);
 assert.equal(s.nodes['daily-review-button'].disabled,true);assert.match(s.nodes['daily-review-message'].textContent,/Advanced controls/);
});
test('first-time policy stays explicit and existing ML policy is never downgraded by the daily shortcut',async()=>{
 const s=setup(()=>guided());readyDailyReview(s);s.data.strategy_mode='unconfigured';s.ui.controls();
 assert.equal(s.nodes['daily-review-button'].disabled,true);
 s.nodes['prep-policy'].value='rules';s.nodes['prep-policy'].fire('change');assert.equal(s.nodes['daily-review-button'].disabled,false);
 s.nodes['prep-policy'].value='';s.data.strategy_mode='rules_ml';s.ui.controls();
 s.nodes['daily-review-button'].fire('click');await flush();assert.equal(s.calls[0].body.strategy_mode,'rules_ml');
});
test('locking hides the shortcut and discards a late review; polling does not approve anything',async()=>{
 let finish;const s=setup(()=>new Promise(r=>{finish=r;}));readyDailyReview(s);
 s.nodes['daily-review-button'].fire('click');s.ui.clear();finish(guided());await flush();
 assert.equal(s.nodes['daily-review'].hidden,true);assert.equal(s.nodes['quote-review-button'].hidden,true);
 assert.equal(s.nodes['daily-review-message'].textContent,'');assert.notEqual(s.nodes['guided-dialog'].open,true);
 assert.equal(s.calls.length,1);
});
test('completed daily review hides both shortcut locations instead of leaving the warning visible',()=>{
 const s=setup();readyDailyReview(s);s.data.blockers=[];
 s.ui.render({...s.view,job:job({state:'installed',strategy_mode:'rules',snapshot_at:'2026-10-22T05:07:28Z'})},{state:'complete'});
 assert.equal(s.nodes['daily-review'].hidden,true);assert.equal(s.nodes['quote-review-button'].hidden,true);
 assert.equal(s.nodes['daily-review-button'].disabled,true);assert.equal(s.nodes['daily-review-message'].textContent,'');
 assert.equal(s.ui.currentReviewReady(),false);assert.equal(s.calls.length,0);
});
