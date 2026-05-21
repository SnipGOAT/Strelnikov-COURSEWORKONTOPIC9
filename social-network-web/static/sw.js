const CACHE_NAME = 'socialnet-v1';

// Список ресурсов, которые нужно кэшировать сразу при установке
const PRECACHE_URLS = [
  '/',
  '/static/style.css',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/manifest.json'
];

// Установка: кэшируем основные ресурсы
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

// Активация: удаляем старые кэши
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME)
            .map(key => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

// Перехват запросов: пытаемся загрузить из сети, если не получается — из кэша
self.addEventListener('fetch', event => {
  // Не кэшируем POST-запросы и другие методы
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then(cached => {
      // Возвращаем из кэша мгновенно, а в фоне обновляем кэш из сети
      const fetched = fetch(event.request).then(response => {
        // Кэшируем только успешные ответы
        if (response && response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      }).catch(() => cached); // если сеть недоступна, используем кэш

      return cached || fetched;
    })
  );
});
