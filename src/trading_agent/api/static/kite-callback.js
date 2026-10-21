(function () {
  'use strict';
  const query = new URLSearchParams(window.location.search);
  const requestToken = query.get('request_token'), state = query.get('setup_state');
  if (!requestToken || !state || !window.opener) return;
  window.__kiteCallbackHandled = true;
  // UI popup handoff only. Leave the legacy CLI redirect available for manual capture.
  window.history.replaceState(null, '', window.location.pathname);
  window.opener.postMessage({ type: 'kite-request-token', request_token: requestToken, state }, window.location.origin);
})();
