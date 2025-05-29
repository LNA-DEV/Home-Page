// self.addEventListener('push', event => {
//   const data = event.data ? event.data.json() : {};
//   const title = data.title || "New Notification";
//   const options = {
//     body: data.body || "",
//     icon: "/icon.png",
//   };
//   event.waitUntil(
//     self.registration.showNotification(title, options)
//   );
// });
self.addEventListener('push', event => {
  console.log('[Service Worker] Push Received.');
  console.log(`[Service Worker] Push had this data: "${event.data.text()}"`);

  const title = 'Test Webpush';
  const options = {
    body: event.data.text(),
  };

  event.waitUntil(self.registration.showNotification(title, options));
});