(function () {
  'use strict';
  const win = window, doc = document;
  const embedded = win.parent !== win;
  const views = {'/':'dashboard','/desk':'dashboard','/dashboard':'dashboard','/discovery':'discovery','/analysis':'analysis','/strategies':'strategies','/investment-policy':'strategies','/backtesting':'backtesting','/paper':'paper','/holdings':'portfolio','/portfolio':'portfolio','/activity':'history','/console':'risk','/setup':'broker','/settings':'settings','/learn':'learn'};
  const cleanAnchor = value => typeof value === 'string' && /^[A-Za-z][A-Za-z0-9_-]{0,99}$/.test(value) ? value : '';
  function destination(path, hash) {
    let view=views[path],anchor=cleanAnchor((hash||'').slice(1));
    if(view==='dashboard'&&['strategy-setup','execution-shortlist','apply-shortlist'].includes(anchor)){view='strategies';if(anchor==='apply-shortlist')anchor='execution-shortlist';}
    if(path==='/portfolio'&&!anchor)anchor='purchases';
    if(path==='/investment-policy')anchor='investment-policy';

    return {view,anchor};
  }
  if (!embedded) {
    if (!win.__kiteCallbackHandled && !new URLSearchParams(win.location.search).has('request_token')) {
      const target=destination(win.location.pathname,win.location.hash);
      win.location.replace('/workspace#'+(target.view||'learn')+(target.anchor?'/'+target.anchor:''));
    }
    return;
  }
  doc.body.classList.add('workspace-child');
  let instance = null, receiving = false, requestedAnchor = cleanAnchor((win.location.hash||'').slice(1));
  const send = (type, extra = {}) => win.parent.postMessage({type,...extra}, win.location.origin);
  function revealAnchor() {
    if (!requestedAnchor) return;
    const target = doc.getElementById(requestedAnchor === 'apply-shortlist' ? 'execution-shortlist' : requestedAnchor);
    if (!target || target.closest('[hidden]')) return;
    for (let parent = target; parent; parent = parent.parentElement) if (parent.tagName === 'DETAILS') parent.open = true;
    if (!target.getClientRects().length) return;
    requestedAnchor = '';
    // The frame is expanded to its full document height. Scroll its parent viewport,
    // rather than a frame viewport that already considers the target visible.
    send('workspace-height', {height:Math.ceil(doc.body.getBoundingClientRect().height)+32});
    send('workspace-scroll-target', {top:target.getBoundingClientRect().top + win.scrollY});
    if (target.tabIndex < 0) target.tabIndex = -1;
    target.focus({preventScroll:true});
  }
  win.AgenticNavigation = {
    updated: revealAnchor,
    connect(view, formId) {
      instance = view;
      win.addEventListener('message', event => {
        if (event.origin !== win.location.origin || event.source !== win.parent || !event.data) return;
        if (event.data.type === 'workspace-lock') { receiving = true; view.lock(); receiving = false; }
        if (event.data.type === 'workspace-anchor') { requestedAnchor = cleanAnchor(event.data.anchor); revealAnchor(); }
        if (event.data.type === 'workspace-unlock' && typeof event.data.token === 'string' && event.data.token.length >= 32 && event.data.token.length <= 4096) {
          receiving = true;
          doc.getElementById('token').value = event.data.token;
          doc.getElementById(formId).dispatchEvent(new Event('submit', {bubbles:true,cancelable:true}));
          receiving = false;
        }
      });
      doc.addEventListener('click', event => {
        const anchor = event.target.closest && event.target.closest('a[href]');
        if (!anchor || event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        if (event.button !== undefined && event.button !== 0) return;
        const url = new URL(anchor.href, win.location.origin);
        if (url.origin === win.location.origin && Object.hasOwn(views,url.pathname)) { event.preventDefault(); send('workspace-navigate', destination(url.pathname,url.hash)); }
      });
      if (win.ResizeObserver) new win.ResizeObserver(() => send('workspace-height', {height:Math.ceil(doc.body.getBoundingClientRect().height)+32})).observe(doc.body);
      send('workspace-ready', {view:views[win.location.pathname],path:win.location.pathname});
      revealAnchor();
    },
    canNavigate() { return !instance || !instance.canNavigate || instance.canNavigate(); },
    locked() { if (instance && !receiving) send('workspace-locked'); }
  };
})();
