self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || "New Notification";
  const options = {
    body: data.body || "",
    icon: "/assets/Pingüino.png",
  };
  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});