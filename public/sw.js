// Service worker: ontvangt push-notificaties en opent de app bij een tik.
// Bewust géén caching: de app moet altijd verse leaddata tonen.

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('push', event => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = {}; }
  const titel = data.titel || 'Leadgenerator Felison';
  const opties = {
    body: data.tekst || 'Er staat een actie voor je klaar.',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    tag: data.tag || 'leadgenerator',
    data: { url: data.url || '/' },
  };
  event.waitUntil(self.registration.showNotification(titel, opties));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const doel = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(vensters => {
      // Al open? Dan dat venster naar voren halen in plaats van een tweede te openen.
      for (const v of vensters) {
        if ('focus' in v) { v.navigate(doel); return v.focus(); }
      }
      return self.clients.openWindow(doel);
    })
  );
});
