/* ==========================================================================
   Memora PWA Service Worker — Native Web Push Notifications & Offline Cache
   ========================================================================== */

const CACHE_NAME = 'memora-v1.0';
const ASSETS_TO_CACHE = [
  '/',
  '/static/logo.svg',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/manifest.json'
];

// Install Event — Cache essential PWA assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

// Activate Event — Clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event — Network-first strategy with cache fallback
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});

// Push Event — Handle incoming Web Push Notifications from server
self.addEventListener('push', (event) => {
  let data = {
    title: 'Memora Vault Notification',
    body: 'You have a memory reminder waiting.',
    icon: '/static/icon-192.png',
    badge: '/static/icon-192.png',
    url: '/app/'
  };

  if (event.data) {
    try {
      data = Object.assign(data, event.data.json());
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: data.icon || '/static/icon-192.png',
    badge: data.badge || '/static/icon-192.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/app/'
    },
    actions: [
      { action: 'open', title: 'Open Vault' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Notification Click Event — Open target memory or vault page
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) ? event.notification.data.url : '/app/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (let client of windowClients) {
        if (client.url.includes(targetUrl) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});
