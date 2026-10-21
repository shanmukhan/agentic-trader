(function () {
  'use strict';
  const win = window, doc = document;
  const embedded = win.parent !== win;
  const views = {'/':'desk','/desk':'desk','/activity':'activity','/console':'console','/setup':'setup','/portfolio':'portfolio'};
  if (!embedded) {
    if (!win.__kiteCallbackHandled && !new URLSearchParams(win.location.search).has('request_token'))
      win.location.replace('/workspace#'+(views[win.location.pathname] || 'overview'));
    return;
  }
  doc.body.classList.add('workspace-child');
  let instance = null, receiving = false;
  const send = (type, extra = {}) => win.parent.postMessage({type,...extra}, win.location.origin);
  win.AgenticNavigation = {
    connect(view, formId) {
      instance = view;
      win.addEventListener('message', event => {
        if (event.origin !== win.location.origin || event.source !== win.parent || !event.data) return;
        if (event.data.type === 'workspace-lock') { receiving = true; view.lock(); receiving = false; }
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
        if (anchor.getAttribute('href').startsWith('#')) return;
        const url = new URL(anchor.href, win.location.origin);
        if (url.origin === win.location.origin && views[url.pathname]) { event.preventDefault(); send('workspace-navigate', {view:views[url.pathname]}); }
      });
      if (win.ResizeObserver) new win.ResizeObserver(() => send('workspace-height', {height:Math.ceil(doc.body.getBoundingClientRect().height)+32})).observe(doc.body);
      send('workspace-ready', {view:views[win.location.pathname]});
    },
    canNavigate() { return !instance || !instance.canNavigate || instance.canNavigate(); },
    locked() { if (instance && !receiving) send('workspace-locked'); }
  };
})();
