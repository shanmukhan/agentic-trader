/* Shared native confirmation geometry and lifecycle; never grants action authority. */
(function () {
  'use strict';
  const instances = new WeakMap();
  function createDialogs(doc, win) {
    if (instances.has(doc)) return instances.get(doc);
    let active = null;
    const properties = ['position', 'top', 'bottom', 'left', 'right', 'margin', 'transform', 'maxHeight', 'maxWidth', 'minHeight', 'minWidth', 'boxSizing', 'overflow', 'overscrollBehavior'];
    const listen = (record, target, type, handler) => {
      if (!target?.addEventListener) return;
      target.addEventListener(type, handler);
      record.listeners.push(() => target.removeEventListener?.(type, handler));
    };
    function embedded() {
      try { return win.parent && win.parent !== win && win.frameElement ? { parent: win.parent, frame: win.frameElement } : null; }
      catch (_) { return null; }
    }
    function notify(open) {
      const host = embedded();
      if (host && win.location?.origin) host.parent.postMessage?.({ type: 'workspace-dialog', open }, win.location.origin);
    }
    function viewport(target) {
      const visual = target.visualViewport;
      return { top: visual?.offsetTop || 0, left: visual?.offsetLeft || 0,
        width: visual?.width || target.innerWidth, height: visual?.height || target.innerHeight };
    }
    function bounds(host) {
      const visible = viewport(host.parent), rect = host.frame.getBoundingClientRect();
      const scaleX = rect.width > 0 && host.frame.offsetWidth > 0 ? rect.width / host.frame.offsetWidth : 1;
      const scaleY = rect.height > 0 && host.frame.offsetHeight > 0 ? rect.height / host.frame.offsetHeight : 1;
      const left = rect.left + (host.frame.clientLeft || 0) * scaleX;
      const top = rect.top + (host.frame.clientTop || 0) * scaleY;
      const right = host.frame.clientWidth > 0 ? left + host.frame.clientWidth * scaleX : rect.right;
      const bottom = host.frame.clientHeight > 0 ? top + host.frame.clientHeight * scaleY : rect.bottom;
      const intersection = { left: Math.max(visible.left, left) + 16, top: Math.max(visible.top, top) + 16,
        right: Math.min(visible.left + visible.width, right) - 16, bottom: Math.min(visible.top + visible.height, bottom) - 16 };
      if (!Object.values(intersection).every(Number.isFinite) || intersection.right <= intersection.left || intersection.bottom <= intersection.top) return null;
      return { left: (intersection.left - left) / scaleX, top: (intersection.top - top) / scaleY,
        width: (intersection.right - intersection.left) / scaleX, height: (intersection.bottom - intersection.top) / scaleY };
    }
    function position(record, reveal = false) {
      if (active !== record) return false;
      const host = embedded();
      let area;
      if (host) {
        area = bounds(host);
        if (!area && reveal) {
          // A collapsed/off-screen section must be revealed before native focus.
          // If the host remains hidden, cancel the review without opening.
          host.frame.scrollIntoView?.({ block: 'center', inline: 'nearest', behavior: 'instant' });
          area = bounds(host);
        }
        if (!area) return false;
      } else {
        const view = viewport(win);
        if (Number.isFinite(view.width) && Number.isFinite(view.height)) area = { left: view.left + 16, top: view.top + 16, width: Math.max(1, view.width - 32), height: Math.max(1, view.height - 32) };
      }
      const style = record.dialog.style;
      if (!style) return true;
      style.boxSizing = 'border-box'; style.minHeight = '0'; style.minWidth = '0';
      style.overflow = 'auto'; style.overscrollBehavior = 'contain';
      if (area) {
        style.maxHeight = area.height + 'px'; style.maxWidth = area.width + 'px';
        // Native centering is against the expanded iframe. Place its top layer
        // in the parent's currently visible portion before showModal autofocus.
        style.position = 'fixed'; style.top = (area.top + area.height / 2) + 'px';
        style.left = (area.left + area.width / 2) + 'px'; style.bottom = 'auto'; style.right = 'auto';
        style.margin = '0'; style.transform = 'translate(-50%, -50%)';
      }
      return true;
    }
    function finish(record, cancelled) {
      if (active !== record) return;
      active = null;
      record.listeners.splice(0).forEach(remove => remove());
      record.observer?.disconnect();
      if (record.dialog.open) record.dialog.close();
      if (record.dialog.style) for (const name of properties) record.dialog.style[name] = record.styles[name];
      notify(false);
      if (cancelled) record.cancel?.();
      if (record.trigger?.isConnected !== false && !record.trigger?.disabled) record.trigger?.focus?.({ preventScroll: true });
    }
    function open(dialog, options = {}) {
      if (active || dialog.open) { options.cancel?.(); return false; }
      const record = { dialog, cancel: options.cancel, trigger: doc.activeElement, listeners: [], styles: {} };
      if (dialog.style) for (const name of properties) record.styles[name] = dialog.style[name] || '';
      active = record;
      if (!position(record, true)) { finish(record, true); return false; }
      const reposition = () => { if (!position(record, true)) finish(record, true); };
      const host = embedded();
      for (const target of [win, win.visualViewport, host?.parent, host?.parent.visualViewport]) {
        listen(record, target, 'resize', reposition); listen(record, target, 'scroll', reposition);
      }
      listen(record, dialog, 'cancel', event => { event.preventDefault(); finish(record, true); });
      // Native form method=dialog or an external close also revokes pending UI.
      listen(record, dialog, 'close', () => { if (!dialog.open) finish(record, true); });
      listen(record, win, 'pagehide', () => finish(record, true));
      if (win.ResizeObserver) { record.observer = new win.ResizeObserver(reposition); record.observer.observe(dialog); }
      try { dialog.showModal(); }
      catch (_) { finish(record, true); return false; }
      notify(true);
      const focus = options.focus || dialog.querySelector?.('button:not(:disabled)');
      focus?.focus?.({ preventScroll: true });
      return true;
    }
    const api = { open, close: dialog => { if (active && (!dialog || active.dialog === dialog)) finish(active, false); },
      cancel: dialog => { if (active && (!dialog || active.dialog === dialog)) finish(active, true); },
      destroy: () => { if (active) finish(active, true); } };
    instances.set(doc, api);
    return api;
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { createDialogs };
  if (typeof window !== 'undefined') window.AgenticDialogs = createDialogs;
})();
