// TVHub service worker: makes the app installable. It deliberately caches nothing (every page and API call is
// authenticated and live); it only shows a friendly page when the server cannot be reached.
const OFFLINE = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
  '<title>TVHub</title><body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#000;color:#f5f5f7;' +
  'font:16px -apple-system,system-ui,sans-serif;text-align:center"><div><h1 style="font-size:22px;margin:0 0 8px">TVHub</h1>' +
  '<p style="color:#98989d;margin:0 0 18px">The server is not reachable.<br>Check that TVHub is running and you are on the same network.</p>' +
  '<button onclick="location.reload()" style="background:#f5654a;color:#fff;border:0;border-radius:12px;padding:12px 22px;font:600 16px inherit">Retry</button></div>';
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", (e) => {
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).catch(() => new Response(OFFLINE, { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } })));
  }
});
