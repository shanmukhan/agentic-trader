/* The server has already consumed the nonce-bound callback. Never retain its query. */
(function () {
  'use strict';
  if (window.location.search) window.history.replaceState(null, '', window.location.pathname);
})();
