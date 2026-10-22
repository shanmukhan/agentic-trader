(function () {
'use strict';
const errors={
 BROKER_SESSION_UNAVAILABLE:'The saved Kite session could not be verified. Check it in Broker & data; complete a fresh login if expired.',
 OFFICIAL_SOURCE_UNAVAILABLE:'An official source could not be read. Keep the existing account unchanged; retry later. No fallback data or calendar was assumed.',
 UNIVERSE_RESPONSE_INVALID:'The constituent file failed the expected equity-share/ISIN/size checks. No universe was installed.',
 CALENDAR_RESPONSE_INVALID_OR_TOO_SHORT:'The current-year holiday source is invalid or does not cover enough completed sessions. A reviewed cross-year bundle is required early in the year.',
 ACTION_RESPONSE_INVALID_OR_EMPTY:'The corporate-action response is missing or invalid. An empty response is not proof that there were no actions.',
 BROKER_DAILY_HISTORY_UNAVAILABLE:'Kite daily history failed. Check the saved broker session and historical-data subscription in Broker & data, then retry. A working WebSocket does not prove history access.',
 HISTORY_OR_PREPARATION_FAILED:'Data preparation failed. No strategy was installed. Check broker entitlement, source coverage and the local preparation files before retrying.',
 NO_ELIGIBLE_HISTORY:'No stocks have complete history with supported action-free basis. Inspect exclusions; no prices or actions were invented.',
 DOWNLOAD_INTERRUPTED:'The server stopped during the download. Start a new download; an incomplete run is never installed.',
 DOWNLOAD_DATE_CHANGED:'The IST date changed during download. Start a new run so the calendar/action sources and history period share the same reviewed date.',
 SAVED_PREPARATION_INVALID:'Saved preparation status is invalid. Inspect the local preparation files before retrying.'
};
const createDialogs=typeof module!=='undefined'&&module.exports?require('./dialogs.js').createDialogs:window.AgenticDialogs;
function createPreparation(doc,win,api,refresh,confirm,getLatest){
 const dialogs=createDialogs(doc,win);
 const el=id=>doc.getElementById(id),node=(tag,text)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=String(text);return n;};
 let latest=null,jobId=null,downloadId=null,busy=false,unlocked=false,guidedSupported=false,review=null,generation=0;
 const istDay=value=>{const parsed=new Date(value);return value&&Number.isFinite(parsed.getTime())?new Date(parsed.getTime()+19800000).toISOString().slice(0,10):'';};
 function currentReviewReady(ignoreBusy=false){const data=getLatest(),job=latest?.job;
  return Boolean(unlocked&&(ignoreBusy||!busy)&&guidedSupported&&latest?.available&&!latest.profile_override&&data?.mode==='manual'&&data.blockers?.includes('LONG_TERM_REVIEW_REQUIRED')&&['ready_for_review','installed'].includes(job?.state)&&istDay(job.snapshot_at)&&istDay(job.snapshot_at)===istDay(data.observed_at)&&(['rules','rules_ml'].includes(el('prep-policy').value)||['rules','rules_ml'].includes(data.strategy_mode)));
 }
 function controls(isBusy=busy,isUnlocked=unlocked){busy=isBusy;unlocked=isUnlocked;const data=getLatest(),job=latest?.job;
  const available=unlocked&&latest?.available&&data?.mode==='manual';
  el('prep-download').disabled=busy||!available||job?.state==='downloading';
  el('prep-cancel').disabled=busy||!unlocked||job?.state!=='downloading'||Boolean(job?.cancel_requested);
  el('prep-install').disabled=busy||!available||latest?.profile_override||job?.state!=='ready_for_review';
  for(const id of ['prep-calendar','prep-reference','prep-calendar-reviewed','prep-basis-reviewed','prep-policy-reviewed'])el(id).disabled=busy||!available||latest?.profile_override||job?.state!=='ready_for_review';
  el('prep-policy').disabled=busy||!available||latest?.profile_override||!['ready_for_review','installed'].includes(job?.state);
  el('guided-review').disabled=busy||!available||!guidedSupported||latest?.profile_override||!['ready_for_review','installed'].includes(job?.state);
  el('guided-confirm').disabled=busy||!unlocked||!review||!el('guided-ack').checked;
  el('prep-calendar-correction').disabled=busy||!available||!latest?.can_correct_unused_calendar||job?.state!=='ready_for_review';
  el('prep-ml-option').disabled=!latest?.ml_configured;
  const needsReview=unlocked&&Boolean(data?.blockers?.includes('LONG_TERM_REVIEW_REQUIRED'));
  el('daily-review').hidden=!needsReview;el('quote-review-button').hidden=!needsReview;
  for(const id of ['daily-review-button','quote-review-button'])el(id).disabled=!currentReviewReady();
  el('daily-review-download').hidden=currentReviewReady(true);
  el('daily-review-message').textContent=!needsReview?'':data.mode!=='manual'?'Choose Manual before reviewing today’s setup.':latest?.profile_override||!guidedSupported||!latest?.available?'Use Advanced controls for today’s price-basis reviews; the combined review is unavailable for this account.':currentReviewReady(true)?'Today’s data is ready. Open the setup summary, inspect the sources/calendar/stocks, then acknowledge and select Confirm and prepare. This applies the displayed shortlist and eligible daily reviews and requests reconnection; Manual stays selected. Restarting or opening the summary does not approve the review.':'Today’s price-basis approval is still missing. Open data preparation below and download current-day sources/history if needed, then choose a policy. Yesterday’s download/review and a restart cannot approve today’s prices.';
 }
 function clear(){generation++;latest=null;jobId=null;downloadId=null;unlocked=false;review=null;guidedSupported=false;
  dialogs.cancel(el('guided-dialog'));el('guided-ack').checked=false;el('guided-summary').replaceChildren();el('guided-sources').replaceChildren();el('guided-calendar').textContent='';el('guided-result').textContent='';
  for(const id of ['prep-progress','prep-error','prep-result','prep-availability','prep-model-help','prep-calendar-conflicts'])el(id).textContent='';
  for(const id of ['prep-sources','prep-exclusions'])el(id).replaceChildren();
  for(const id of ['prep-calendar','prep-policy','prep-reference'])el(id).value='';
  for(const id of ['prep-calendar-reviewed','prep-basis-reviewed','prep-policy-reviewed'])el(id).checked=false;
  el('prep-calendar-correction').checked=false;el('prep-correction-label').hidden=true;
  el('prep-progress-bar').value=0;el('prep-state').textContent='Not prepared';controls(false,false);
 }
 function render(value,guided){latest=value||null;unlocked=true;guidedSupported=guided!==undefined;const data=getLatest(),job=value?.job;
  if(!value){el('prep-state').textContent='Server restart required';el('prep-availability').textContent='Stop the older server in its owning terminal with Ctrl+C, run ./scripts/start_ui.sh and unlock again. Reloading a page cannot update Python routes.';controls();return;}
  el('prep-availability').textContent=!value?.available?'Preparation is available on the manual account with Broker & data setup. Bound legacy controllers keep their existing workflow.':value?.profile_override?'A custom TRADING_ANALYSIS_PROFILE is set. Clear it and restart before installing a UI-managed strategy; it would otherwise override the saved selection.':data?.mode!=='manual'?'Choose Manual before preparing or replacing a strategy.':'Begin with a verified broker session and imported NSE catalog. Download once, choose a policy and review the combined setup. The confirmed flow handles disconnection and reconnection.';
  el('prep-model-help').textContent=value?.ml_configured?'A server-selected model directory is configured. Installation must still pass horizon, policy, integrity and chronological validation; there is no rules fallback.':'No validated ML model is configured. Choose Rules only explicitly to paper-test the declared hypothesis, or have a matching validated model installed with TRADING_PREPARATION_MODEL. Downloading daily history alone cannot validate ML.';
  el('prep-state').textContent=({downloading:'Downloading',ready_for_review:'Review required',installed:'Strategy installed',failed:'Download failed',cancelled:'Cancelled',interrupted:'Interrupted'})[job?.state]||'Not prepared';
  el('prep-error').textContent=job?.error?(errors[job.error]||'Preparation is unavailable. Review the local data and retry.') : '';
  el('prep-progress').textContent=job?((job.cancel_requested&&job.state==='downloading'?'Cancellation requested; waiting for the current bounded network read. ':'')+(job.stage==='official_sources'?'Reading official constituent, holiday and action sources. ': '')+(job.total?job.completed+' / '+job.total+' stocks downloaded; '+job.eligible+' with complete eligible history. ':'')+(job.history_start?'History '+job.history_start+' to '+job.history_end+'. ':'')+(job.elapsed_seconds!==undefined?'Elapsed '+Math.round(job.elapsed_seconds)+' seconds. ':'')+(job.state==='ready_for_review'?'Ready for your source/calendar/policy review.':'')):'No download started. Your current watchlist and account remain in place.';
  el('prep-progress-bar').max=job?.total||100;el('prep-progress-bar').value=job?.completed||0;
  const conflicts=value.calendar_conflicts||[];el('prep-calendar-conflicts').textContent=conflicts.length?'Saved account hours differ from the proposal: '+conflicts.map(c=>c.date+' saved '+c.existing+' / proposed '+c.proposed+' IST').join('; ')+'. '+(value.can_correct_unused_calendar?'This account has no quote/review/execution usage. Review and explicitly approve any correction below.':'This account already has usage evidence; preserve its session definitions and review locally.') : '';
  el('prep-correction-label').hidden=!conflicts.length||!value.can_correct_unused_calendar;
  if(job?.job_id!==jobId){jobId=job?.job_id||null;if(job?.universe)el('prep-universe').value=job.universe;for(const id of ['prep-calendar','prep-policy','prep-reference'])el(id).value='';for(const id of ['prep-calendar-reviewed','prep-basis-reviewed','prep-policy-reviewed','prep-calendar-correction'])el(id).checked=false;}
  // Preserve edits and reviews during periodic status refreshes.
  if(job?.calendar_csv&&!el('prep-calendar').value)el('prep-calendar').value=job.calendar_csv;
  if(job?.state==='installed'){el('prep-policy').value=job.strategy_mode||'';el('prep-reference').value=job.review_reference||'';}
  el('prep-result').textContent=job?.state==='installed'?'Strategy installed; Manual remains selected. Review/apply the ranked shortlist below, complete today’s basis reviews in Advanced controls, reconnect market data, then wait for fresh quotes in an open entry session.':job?.state==='ready_for_review'?job.symbols.length+' eligible equity shares · '+job.completed_sessions+' completed daily sessions. This is a current constituent snapshot for prospective paper screening. Disconnect the feed before installation.':'';
  if(guidedSupported){el('prep-result').textContent=job?.state==='ready_for_review'?job.symbols.length+' eligible equity shares · '+job.completed_sessions+' completed daily sessions · prospective screening. Choose a policy and select Review and finish setup.':job?.state==='installed'?'Strategy installed. Use the guided review to finish or refresh the shortlist and today’s eligible reviews. Manual remains selected.':'';el('guided-result').textContent=guided?.message||(guided?.state==='review'?'Setup review prepared; no changes have been applied.':'');}
  else el('guided-result').textContent='Restart the server with ./scripts/start_ui.sh to use the simplified setup.';
  el('prep-sources').replaceChildren();for(const [name,url]of Object.entries(value?.sources||{})){const link=node('a','Open '+name+' source');link.href=url;link.target='_blank';link.rel='noopener noreferrer';el('prep-sources').append(link);}
  el('prep-exclusions').replaceChildren();for(const item of job?.excluded||[]){const why={CORPORATE_ACTION_IN_HISTORY:'Excluded: corporate action in the history interval; adjustment is not guessed.',CATALOG_MATCH_MISSING:'Excluded: no supported NSE token in the imported broker catalog.',INCOMPLETE_DAILY_HISTORY:'Excluded: missing or unexpected daily sessions.',UNSUPPORTED_SHARE_SERIES:'Excluded: unsupported series/class, including REIT or trade-to-trade entries.',UNSUPPORTED_SHARE_IDENTIFIER:'Excluded: no supported equity-share ISIN; dummy/other instruments cannot execute.'}[item.reason]||item.reason;el('prep-exclusions').append(node('p',item.symbol+' · '+why));}
  controls();
 }
 async function openReview(useCurrentPolicy=false){const data=getLatest();let mode=el('prep-policy').value;if(!data||busy||!unlocked||el('guided-dialog').open)return;
  if(useCurrentPolicy&&!mode&&['rules','rules_ml'].includes(data.strategy_mode)){mode=data.strategy_mode;el('prep-policy').value=mode;}
  if(!mode){el('guided-result').textContent='Choose a decision policy above first.';el('prep-policy').focus();return;}
  const version=generation;const result=await api('/api/desk/preparation/guided/preview',{revision:data.revision,strategy_mode:mode});if(!result||!unlocked||version!==generation)return;
  review=result;const p=result.plan;el('guided-ack').checked=false;el('guided-summary').replaceChildren();
  for(const text of [
   (p.horizon==='long_term'?'Long-term':'Intraday')+' paper account · virtual cash INR '+p.cash,
   'Policy: '+(p.strategy_mode==='rules'?'Experimental rules only; no ML filter.':'Rules + independently validated matching ML.'),
   'Screen: positive 20-session momentum, 50-session trend, average turnover at least INR 1 crore and daily volatility at most 5%. A screen is not a buy signal or profit forecast.',
   p.eligible+' eligible equity shares; '+p.completed_sessions+' completed sessions ('+p.history_start+' to '+p.history_end+'). Stocks with returned corporate actions or incomplete history stay excluded.',
   'Execution shortlist: '+p.symbols.join(', '),
   'Held symbols retained: '+(p.held_symbols.join(', ')||'none'),
   'Today’s price-basis reviews included ('+p.session_date+'): '+(p.basis_reviews.join(', ')||'none'),
   'Separate manual basis review still required: '+(p.manual_basis_reviews.join(', ')||'none')+'. Existing holdings, quarantines and uncovered price histories are never auto-cleared.',
   'Saved calendar corrections: '+(p.calendar_conflicts.map(c=>c.date+' '+c.existing+' → '+c.proposed+' IST').join('; ')||'none')+'. Used account session history is preserved.',
   'Entry window: '+p.entry_start+'–'+p.entry_end+' IST, inside a reviewed open session. After-hours setup does not enable trading.',
   'This review expires in two minutes. No mode is activated by this confirmation.'
  ])el('guided-summary').append(node('p',text));
  el('guided-calendar').textContent=p.calendar_csv;el('guided-sources').replaceChildren();for(const [name,url]of Object.entries(p.sources)){const link=node('a','Review '+name+' source');link.href=url;link.target='_blank';link.rel='noopener noreferrer';el('guided-sources').append(link);}
  controls();if(!dialogs.open(el('guided-dialog'),{cancel:()=>{review=null;el('guided-ack').checked=false;controls();},focus:el('guided-cancel')}))el('guided-result').textContent='The review could not be displayed. Reopen Strategies and review the setup again. Nothing was applied.';
 }
 el('guided-review').addEventListener('click',()=>openReview());
 const reviewCurrent=()=>{if(currentReviewReady())return openReview(true);};
 for(const id of ['daily-review-button','quote-review-button'])el(id).addEventListener('click',reviewCurrent);
 el('prep-policy').addEventListener('change',()=>controls());
 el('guided-ack').addEventListener('change',()=>controls());
 const closeReview=()=>{review=null;el('guided-ack').checked=false;dialogs.close(el('guided-dialog'));controls();};
 el('guided-cancel').addEventListener('click',()=>dialogs.cancel(el('guided-dialog')));
 el('guided-confirm').addEventListener('click',async()=>{if(!review||!unlocked||busy||!el('guided-ack').checked)return;const body={preview_sha256:review.preview_sha256,acknowledged:true};closeReview();el('guided-result').textContent='Preparing the confirmed setup. Keep this tab open; no trading mode is being activated.';const result=await api('/api/desk/preparation/guided/confirm',body);if(result&&unlocked)el('guided-result').textContent=result.message;await refresh();});
 el('prep-download').addEventListener('click',()=>{const data=getLatest();if(!data||busy)return;const universe=el('prep-universe').value;
  if(!downloadId||latest?.job?.state!=='downloading')downloadId=Array.from(win.crypto.getRandomValues(new Uint8Array(16)),v=>v.toString(16).padStart(2,'0')).join('');
  const body={universe,request_id:downloadId,revision:data.revision,acknowledged:true};
  confirm('Download genuine strategy data?',universe+' constituents, official holiday/action sources and completed daily Kite history will be read. This may take several minutes. It does not change your mode, feed selection or virtual cash. No orders are submitted.',async()=>{const result=await api('/api/desk/preparation/download',body);if(result){render(result);await refresh();}});
 });
 el('prep-cancel').addEventListener('click',async()=>{const result=await api('/api/desk/preparation/cancel',{});if(result){render(result);await refresh();}});
 el('prep-form').addEventListener('submit',event=>{event.preventDefault();const data=getLatest(),job=latest?.job;if(!data||busy||job?.state!=='ready_for_review')return;
  const body={preview_sha256:job.preview_sha256,revision:data.revision,strategy_mode:el('prep-policy').value,calendar_csv:el('prep-calendar').value,reference:el('prep-reference').value.trim(),calendar_reviewed:el('prep-calendar-reviewed').checked,basis_reviewed:el('prep-basis-reviewed').checked,policy_reviewed:el('prep-policy-reviewed').checked,correct_unused_calendar:!el('prep-calendar-correction').disabled&&el('prep-calendar-correction').checked};
  if(!body.strategy_mode||!body.reference||!body.calendar_reviewed||!body.basis_reviewed||!body.policy_reviewed)return;
  confirm('Install this reviewed paper strategy?',job.symbols.length+' equity shares; '+job.completed_sessions+' completed sessions; '+(body.strategy_mode==='rules'?'EXPERIMENTAL RULES ONLY, without an ML filter.':'rules + the matching validated ML model, subject to validation. ')+' Your edited session calendar and source reviews will be saved.'+(body.correct_unused_calendar?' You also approve correcting the displayed saved hours; the server will recheck that no account history has used them.':'')+' Review reference: '+body.reference+'. Manual stays selected. The feed must be disconnected and pending orders resolved; current holdings are retained. Today’s execution-basis reviews remain separate.',async()=>{const result=await api('/api/desk/preparation/install',body);if(result){render(result);await refresh();}});
 });
 win.addEventListener?.('pagehide',clear);
 clear();return{render,controls,clear,reviewCurrent,currentReviewReady,canNavigate:()=>!el('guided-dialog').open};
}
if(typeof module!=='undefined'&&module.exports)module.exports={createPreparation};
if(typeof window!=='undefined')window.AgenticPreparation=createPreparation;
})();
