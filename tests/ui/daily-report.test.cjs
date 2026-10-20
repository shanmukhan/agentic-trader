'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
const root = 'src/trading_agent/daily_research/static/';
class Element {
  constructor() { this.children=[];this.listeners={};this.value=''; }
  set textContent(value){this.text=String(value);this.children=[];}
  get textContent(){return (this.text||'')+this.children.map(node=>node.textContent).join('');}
  set innerHTML(_){throw Error('unsafe HTML sink');}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.text='';this.children=children;}
  addEventListener(name,handler){this.listeners[name]=handler;}
  fire(name){this.listeners[name]?.();}
  focus(){this.focused=true;}
}
function setup(rows){
  const nodes=Object.fromEntries([...readFileSync(root+'template.html','utf8').matchAll(/\bid="([^"]+)"/g)].map(match=>[match[1],new Element()]));
  const report={as_of:'2026-09-04T10:30:00Z',latest_reviewed_completed_session:'2026-09-04',synthetic:true,candidate_count:rows.filter(row=>row.rank).length,rows,dataset:{source:'</script><img onerror=attack()>',notes:'invented'},policy:{momentum_sessions:20},quality:{},limitations:['No executable orders.']};
  nodes['report-data'].textContent=JSON.stringify(report);
  nodes.status.value='all';nodes.sort.value='rank';
  const document={getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},createElement:()=>new Element()};
  vm.runInNewContext(readFileSync(root+'dashboard.js','utf8'),{document});
  return nodes;
}
const rows=[{symbol:'NSE:B',status:'research_candidate',rank:1,reasons:[],gross_total_return_pct:'8.25',daily_volatility_pct:'1.2',average_turnover:'12345678',last_session:'2026-09-04',observations:90},{symbol:'NSE:A',status:'needs_data',rank:null,reasons:['LATEST_SESSION_UNAVAILABLE_OR_MISSING']}];

test('daily report clearly labels synthetic research, values and unavailable observations',()=>{
 const n=setup(rows);
 assert.match(n.provenance.textContent,/Invented dataset/);
 assert.match(n.rows.children[0].textContent,/NSE:B/);
 assert.match(n.rows.children[0].textContent,/8.25%/);
 assert.match(n.rows.children[1].textContent,/not yet knowable/);
 assert.match(n.source.textContent,/<img onerror/);
 assert.match(n['result-count'].textContent,/2 of 2/);
});
test('daily report filters, sorts and restores results without network or mutation',()=>{
 const n=setup(rows);n.sort.value='symbol';n.sort.fire('input');
 assert.match(n.rows.children[0].textContent,/NSE:A/);
 n.status.value='needs_data';n.status.fire('input');assert.equal(n.rows.children.length,1);
 n.search.value='unknown';n.search.fire('input');assert.equal(n.rows.children.length,0);
 assert.equal(n.empty.hidden,false);assert.match(n.empty.textContent,/No symbols match/);
 n.clear.fire('click');assert.equal(n.rows.children.length,2);assert.ok(n.search.focused);
});
test('daily report provides a useful empty state before any reviewed session completes',()=>{
 const n=setup([]);assert.match(n.empty.textContent,/No universe members/);
 assert.match(n['candidate-count'].textContent,/0/);
});
test('daily report retains out-of-display-range metrics without showing Infinity',()=>{
 const n=setup([{...rows[0],gross_total_return_pct:'1E+1000'}]);
 assert.match(n.rows.textContent,/1E\+1000%/);assert.doesNotMatch(n.rows.textContent,/Infinity/);
});
