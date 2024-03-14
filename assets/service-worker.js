const APP_PREFIX = '{{ .Site.Params.ShortTitle }}_';
const VERSION = 'version_02';

// Define the base URLs for different languages
const BASE_URLS = [
  '/',
  '/en/',
  '/de/',
];

// Array to store generated URLs
let URLS = [
  {{ range (readDir "public") }}
    '{{ .Name }}',
    {{ if .IsDir }}
      {{ $dir := .Name }}
      {{ $baseDir := print "public/" $dir }}
      {{ range $file := readDir $baseDir }}
        {{ if $file.IsDir }}
          {{ range (readDir (print $baseDir "/" $file.Name)) }}
            '{{ print $dir "/" $file.Name "/" .Name }}',
          {{ end }}
        {{ else }}
          '{{ print $dir "/" $file.Name }}',
        {{ end }}
      {{ end }}
    {{ end }}
  {{ end }}
];

URLS.forEach(element => {
  console.log(element)
});

const CACHE_NAME = APP_PREFIX + VERSION;

self.addEventListener('fetch', function (e) {
  console.log('Fetch request : ' + e.request.url);
  e.respondWith(
    caches.match(e.request).then(function (request) {
      if (request) {
        console.log('Responding with cache : ' + e.request.url);
        return request;
      } else {
        console.log('File is not cached, fetching : ' + e.request.url);
        return fetch(e.request);
      }
    })
  );
});

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      console.log('Installing cache : ' + CACHE_NAME);
      return cache.addAll(URLS);
    })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keyList) {
      var cacheWhitelist = keyList.filter(function (key) {
        return key.indexOf(APP_PREFIX);
      });
      cacheWhitelist.push(CACHE_NAME);
      return Promise.all(keyList.map(function (key, i) {
        if (cacheWhitelist.indexOf(key) === -1) {
          console.log('Deleting cache : ' + keyList[i]);
          return caches.delete(keyList[i]);
        }
      }));
    })
  );
});
