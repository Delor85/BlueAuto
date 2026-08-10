var CACHE = 'blue-magic-v2-3-1-regression-guard';
var SHELL = ['./index.html', './style.css', './app.js', './manifest.json'];

self.addEventListener('install', function (event) {
    event.waitUntil(caches.open(CACHE).then(function (cache) {
        return cache.addAll(SHELL);
    }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (event) {
    event.waitUntil(caches.keys().then(function (keys) {
        return Promise.all(keys.filter(function (key) {
            return key !== CACHE;
        }).map(function (key) { return caches.delete(key); }));
    }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (event) {
    if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) return;
    event.respondWith(fetch(event.request).then(function (response) {
        var copy = response.clone();
        caches.open(CACHE).then(function (cache) { return cache.put(event.request, copy); });
        return response;
    }).catch(function () { return caches.match(event.request); }));
});
