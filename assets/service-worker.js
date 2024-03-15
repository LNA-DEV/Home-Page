const APP_PREFIX = '{{- .Site.Params.ShortTitle -}}_';
const VERSION = 'version_{{ now.Unix }}'; // Use Hugo's date format to get the build timestamp

// Array to store generated URLs
let URLS = [
  {{- $publicDir := readDir "public" -}}
  {{- range $i, $dir := $publicDir -}}
    {{- if $dir.IsDir -}}
      {{- $files := readDir (printf "public/%s" $dir.Name) -}}
      {{- range $j, $file := $files -}}
        '{{- printf "%s/%s" $dir.Name $file.Name -}}',
      {{- end -}}
      {{- template "listSubDirectories" (slice $dir.Name) -}}
    {{- else -}}
      '{{- printf "%s" $dir.Name -}}',
    {{- end -}}
  {{- end -}}
];

{{- define "listSubDirectories" -}}
  {{- $dirName := index . 0 -}}
  '{{- print $dirName -}}',
  {{- $subDirs := readDir (printf "public/%s" $dirName) -}}
  {{- range $subDir := $subDirs -}}
    {{- if $subDir.IsDir -}}
      {{- $subDirName := $subDir.Name -}}
      {{- $subFiles := readDir (printf "public/%s/%s" $dirName $subDirName) -}}
      '{{- printf "%s/%s" $dirName $subDirName -}}',
      {{- range $k, $subFile := $subFiles -}}
        {{- if not $subFile.IsDir -}}
          '{{- printf "%s/%s/%s" $dirName $subDirName $subFile.Name -}}',
        {{- end -}}
      {{- end -}}
      {{- template "listSubDirectories" (slice (printf "%s/%s" $dirName $subDirName)) -}}
    {{- else -}}
      '{{- printf "%s/%s" $dirName $subDir.Name -}}',
    {{- end -}}
  {{- end -}}
{{ end }}

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
