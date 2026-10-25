'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');
const {createFeedback}=require('../../src/trading_agent/api/static/workspace-bridge.js');
function setup(){const nodes=Object.fromEntries(['message','error-alert','loading-state','main'].map(id=>[id,{textContent:'',hidden:true,setAttribute(n,v){this[n]=v;}}]));let error=false;nodes.message.classList={contains:()=>error};const posts=[];const win={parent:{postMessage:(...a)=>posts.push(a)},location:{origin:'http://127.0.0.1:8879',pathname:'/paper'}};const feedback=createFeedback({getElementById:id=>nodes[id]},win);return {nodes,posts,feedback,error:value=>{error=value;}};}
test('shared errors use separate assertive region, deduplicate unchanged polls and clear on recovery',()=>{
 const s=setup();s.nodes.message.textContent='Outcome unknown. Read recorded orders before retrying.';s.error(true);s.feedback.update();s.feedback.update();assert.equal(s.posts.length,1);assert.equal(s.nodes['error-alert'].textContent,s.nodes.message.textContent);
 assert.equal(s.posts[0][0].type,'workspace-feedback');assert.equal(s.posts[0][0].path,'/paper');assert.equal(s.posts[0][1],'http://127.0.0.1:8879');
 s.error(false);s.nodes.message.textContent='Account refreshed';s.feedback.update();assert.equal(s.posts.length,1);assert.equal(s.nodes['error-alert'].textContent,'');
});
test('busy state exposes loading and aria-busy; explicit outcomes are bounded literal text',()=>{
 const s=setup();s.feedback.setBusy(true);assert.equal(s.nodes['loading-state'].hidden,false);assert.equal(s.nodes.main['aria-busy'],'true');s.feedback.setBusy(false);assert.equal(s.nodes['loading-state'].hidden,true);
 s.feedback.notify('<script>literal text</script>');assert.equal(s.posts[0][0].text,'<script>literal text</script>');s.feedback.notify('a'.repeat(2000),true);assert.equal(s.posts[1][0].text.length,1000);s.feedback.notify('');assert.equal(s.posts.length,2);
});
