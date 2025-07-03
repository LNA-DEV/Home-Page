if ("serviceWorker" in navigator) {
  navigator.serviceWorker
    .register("/service-worker.js")
    .then((reg) => console.log("Service Worker registered", reg))
    .catch((err) => console.error("Service Worker registration failed", err));
}

document.addEventListener("DOMContentLoaded", () => {
  const notifyLink = document.getElementById("enable-notifications-link");

  if (notifyLink) {
    notifyLink.addEventListener("click", async (event) => {
      event.preventDefault(); // Prevent link navigation

      try {
        const permission = await Notification.requestPermission();
        if (permission === "granted") {
          await subscribeUser();
        } else {
          console.log("Notification permission denied or dismissed.");
        }
      } catch (err) {
        console.error("Error during subscription:", err);
      }
    });
  }
});

async function subscribeUser() {
  const reg = await navigator.serviceWorker.ready;

  const response = await fetch("{{ .Site.Params.CompanionUrl }}/api/webpush/vapidkey");
  const key = await response.text();

  const subscription = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(key),
  });

  await fetch("{{ .Site.Params.CompanionUrl }}/api/webpush/subscribe", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      expirationTime: subscription.expirationTime,
      keys: subscription.toJSON().keys,
    }),
  });

  console.log("Push subscription sent to server.");
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, "+")
    .replace(/_/g, "/");
  const raw = window.atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; ++i) {
    output[i] = raw.charCodeAt(i);
  }
  return output;
}
