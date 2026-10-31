(function(){
'use strict';
function reusable(report,job){return Boolean(job&&/^[a-f0-9]{32}$/.test(job.job_id||'')&&report?.preparation?.job_id===job.job_id&&report.preparation.universe==='nifty50'&&job.universe==='nifty50'&&['ready_for_review','installed'].includes(job.state)&&['ready_for_review','installed'].includes(report.preparation.state)&&['hashes_valid','same_ist_date','coverage_valid'].every(k=>report?.source_validation?.[k]===true));}
const day=value=>{const n=Date.parse(value);return Number.isFinite(n)?new Date(n+19800000).toISOString().slice(0,10):'';};
function auditKey(data,setup){const job=data?.preparation?.job||{},date=day(data?.observed_at),now=Date.parse(data?.observed_at);
 const proposed=(job.calendar_csv||'').split(/\r?\n/).map(r=>r.split(',')).find(r=>r[0]===date)?.[2];
 const closes=[setup?.sessions?.find(s=>s.date===date)?.close,proposed].filter(Boolean).sort();
 return JSON.stringify([date,job.job_id,job.state,job.preview_sha256,data?.strategy_mode,closes.length?closes.map(c=>[c,now>=Date.parse(date+'T'+c+(c.length===5?':00':'')+'+05:30')]):Math.floor(now/300000)]);
}
function createDaily(doc,win,api,refresh,confirm,getLatest,preparation){
 const el=id=>doc.getElementById(id),text=(id,value)=>{if(el(id).textContent!==value)el(id).textContent=value;};
 let unlocked=false,busy=false,checking=false,setup=null,audit=null,key='',profileDay='',following=false,chosen='',jobId='',generation=0,error='',inspect=false,stale=false;
 const current=()=>getLatest()||{},job=()=>current().preparation?.job;
 function installed(){const j=job(),receipt=current().guided_setup;return j?.state==='installed'&&current().readiness?.checks?.some(c=>c.key==='strategy'&&c.ready===true)&&!(receipt?.plan?.job_id===j.job_id&&['applying','stopped','interrupted'].includes(receipt.state));}
 function verified(){return current().preparation?.download_prerequisites?.session_verified===true;}
 function ready(){return key===auditKey(current(),setup)&&reusable(audit,job());}
 function stage(){return !verified()?0:!ready()?1:!installed()?2:3;}
 function render(data){unlocked=true;if(jobId!==(data.preparation?.job?.job_id||'')){jobId=data.preparation?.job?.job_id||'';chosen='';}draw();if(!checking&&!busy&&!inspect&&!stale&&typeof win.setTimeout==='function')win.setTimeout(()=>check(),0);}
 function draw(){const step=stage(),data=current(),j=job(),policy=chosen||(['rules','rules_ml'].includes(data.strategy_mode)?data.strategy_mode:'');
  text('day-step','Step '+(step+1)+' of 4 · '+['Access','Data','Review','Trade'][step]);
  for(let n=0;n<4;n++){el('day-step-'+n).className=n<step?'day-done':n===step?'day-current':'';el('day-step-'+n).setAttribute('aria-current',n===step?'step':'false');}
  const guide=data.readiness?.mode_guidance||{},running=j?.state==='downloading',failed=setup?.feed_diagnostics?.state==='failed';
  const summary=inspect?'The previous instruction may have completed. Inspect saved setup and activity before continuing.':stale?'Waiting for fresh server status. Retrying automatically.':checking?'Checking saved access and data automatically…':error||[
   'We check saved Kite access first. Sign in only if verification is still needed.',
   running?(j.total?j.completed+' / '+j.total+' stocks read. ':'Preparing sources and stock coverage. ')+(following?'The setup review opens when ready.':'Progress updates automatically.'):'Current Nifty 50 sources and completed history are needed. A valid download is reused.',
   'One review covers stocks, sources, exchange sessions, eligible basis reviews and the market-data connection.',
   failed?'Market-data connection failed after its retry limit. Resolve the cause in Broker & data; no retry was sent.':setup?.stream_requested&&!setup.feed_connected?'Connecting to Zerodha… success or failure appears automatically.':(guide.title||'Review paper trading readiness')+'. '+(guide.summary||data.readiness?.next_action||'Fresh quotes and session safeguards still apply.')+(guide.next_entry_at?' Next reviewed entry: '+new Date(guide.next_entry_at).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})+' IST.':'')
  ][step];text('day-summary',summary);
  el('day-policy-wrap').hidden=step!==2;el('day-policy').value=policy;el('day-ml').disabled=!data.preparation?.ml_configured;
  el('day-broker').hidden=(step!==0&&!(step===3&&failed))||checking;text('day-broker',failed?'Resolve connection in Broker & data →':'Complete Kite sign-in →');el('day-trade').hidden=step!==3||failed;el('day-inspect').hidden=!inspect;
  el('day-continue').hidden=step===0||step===3&&(setup?.stream_requested||data.account?.feed_connected);
  text('day-continue',step===1?(running?'Continue this preparation':data.mode!=='manual'?'Choose Manual in Paper Trading':'Prepare & continue'):step===2?'Review & continue':'Review market-data connection');
  el('day-continue').disabled=!unlocked||busy||checking||inspect||stale||(step<3&&data.mode!=='manual')||step===2&&!policy||running&&following;
  text('day-checks',(verified()?'Access verified today':'Access needs verification')+' · '+(ready()?'Current data verified':'Data check needed')+' · '+(installed()?'Setup installed':'Setup review needed')+' · '+(data.mode||'unknown')+' mode');
 }
 function controls(value){busy=value;draw();}
 async function check(force=false,advance=true){if(!unlocked||checking||busy||inspect||stale)return;checking=true;draw();const version=generation,valid=()=>unlocked&&generation===version;
  try{const s=await api('/api/setup',undefined,true);if(!valid())return;if(!s){error='Could not check saved access. Retrying automatically.';return;}setup=s;
   const date=day(current().observed_at);if(!verified()&&s.credentials_configured&&s.access_token_available&&(profileDay!==date||force)){profileDay=date;const result=await api('/api/setup/profile',{},true);if(!valid())return;if(result){setup=result;await refresh(true);}else{error='Saved Kite access could not be verified. Check connectivity or complete broker sign-in.';return;}}
   if(!valid())return;const k=auditKey(current(),setup);if(['ready_for_review','installed'].includes(job()?.state)&&k!==key){const result=await api('/api/desk/preparation/audit',undefined,true);if(!valid())return;if(!result){error='Saved data could not be checked. Retrying automatically; no download was started.';return;}audit=result;key=k;}
   error='';
  }finally{if(valid()){checking=false;draw();}}
  if(advance&&valid()&&following&&stage()===2){const policy=chosen||current().strategy_mode;if(['rules','rules_ml'].includes(policy)){following=false;await preparation.openDailyReview(policy);}}
 }
 async function next(){if(!unlocked||busy||checking||inspect||stale)return;const version=generation,valid=()=>unlocked&&version===generation;error='';
  if(stage()===3){confirm('Connect market data?','Fresh quotes can resume pending paper fills and protective exits. This keeps your trading mode unchanged.',async()=>{const result=await api('/api/setup/connect',{});if(valid()){if(result)setup=result;else inspect=true;await refresh();draw();}});return;}
  if(current().mode!=='manual')return;following=true;await check(true,false);if(!valid()||error)return;
  if(stage()===2){following=false;const policy=chosen||current().strategy_mode;if(['rules','rules_ml'].includes(policy))await preparation.openDailyReview(policy);return;}
  if(stage()!==1)return;if(job()?.state==='downloading'){draw();return;}
  if(!verified()){draw();return;}
  if(!(current().preparation?.download_prerequisites?.catalog_count>0)){const result=await api('/api/setup/catalog',{});if(!valid()||!result){inspect=valid();draw();return;}await refresh();}
  const fresh=await api('/api/desk');if(!valid()||!fresh)return;if(fresh.mode!=='manual'){await refresh();return;}
  if(fresh.preparation?.job?.state==='downloading'){await refresh();return;}
  const identity=Array.from(win.crypto.getRandomValues(new Uint8Array(16)),v=>v.toString(16).padStart(2,'0')).join('');
  const result=await api('/api/desk/preparation/download',{universe:'nifty50',request_id:identity,revision:fresh.revision,acknowledged:true});if(!valid())return;
  if(!result){inspect=true;following=false;}await refresh();draw();
 }
 function clear(){generation++;unlocked=false;busy=false;checking=false;setup=null;audit=null;key='';profileDay='';following=false;chosen='';jobId='';error='';inspect=false;stale=false;
  for(const id of ['day-step','day-summary','day-checks'])text(id,'');el('day-policy').value='';el('day-continue').disabled=true;
 }
 el('day-policy').addEventListener('change',()=>{chosen=el('day-policy').value;draw();});el('day-continue').addEventListener('click',next);
 el('day-inspect').addEventListener('click',()=>{el('prep-controls').open=true;});
 clear();return{render,controls,clear,check,next,stale:()=>{stale=true;key='';draw();},fresh:()=>{stale=false;},stop:()=>{following=false;}};
}
if(typeof module!=='undefined'&&module.exports)module.exports={createDaily,reusable,auditKey};
if(typeof window!=='undefined')window.AgenticDaily=createDaily;
})();
