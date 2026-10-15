/* superHuy service worker: mở app nhanh (vỏ app được lưu sẵn), không bao giờ lưu dữ liệu riêng tư (API, media). */
const SHELL = 'superhuy-shell-v2';
const ASSETS = ['/app', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-180.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(SHELL).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== SHELL).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;
  if (u.pathname.startsWith('/api/') || u.pathname === '/media' || u.pathname === '/dl' || u.pathname.startsWith('/s/')) return;
  if (e.request.mode === 'navigate') {  // luôn lấy bản mới nhất; mất mạng thì dùng bản đã lưu
    e.respondWith(fetch(e.request).then(r => { const cp = r.clone(); caches.open(SHELL).then(c => c.put('/app', cp)); return r; })
      .catch(() => caches.match('/app')));
    return;
  }
  if (u.pathname.startsWith('/icons/') || u.pathname === '/manifest.webmanifest') {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
  }
});
