(function () {
  'use strict';
  const win = window, doc = document;
  const embedded = win.parent !== win;
  const views = {'/':'desk','/desk':'desk','/activity':'activity','/console':'console','/setup':'setup','/portfolio':'portfolio'};
  const cleanAnchor = value => typeof value === 'string' && /^[A-Za-z][A-Za-z0-9_-]{0,99}$/.test(value) ? value : '';
  if (!embedded) {
    if (!win.__kiteCallbackHandled && !new URLSearchParams(win.location.search).has('request_token'))
      win.location.replace('/workspace#'+(views[win.location.pathname] || 'overview')+(cleanAnchor((win.location.hash||'').slice(1))?'/'+cleanAnchor(win.location.hash.slice(1)):''));
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
        if (url.origin === win.location.origin && views[url.pathname]) { event.preventDefault(); send('workspace-navigate', {view:views[url.pathname],anchor:cleanAnchor(url.hash.slice(1))}); }
      });
      if (win.ResizeObserver) new win.ResizeObserver(() => send('workspace-height', {height:Math.ceil(doc.body.getBoundingClientRect().height)+32})).observe(doc.body);
      send('workspace-ready', {view:views[win.location.pathname]});
      revealAnchor();
    },
    canNavigate() { return !instance || !instance.canNavigate || instance.canNavigate(); },
    locked() { if (instance && !receiving) send('workspace-locked'); }
  };
})();
