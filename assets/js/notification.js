if ("serviceWorker" in navigator) {
  navigator.serviceWorker
    .register("/service-worker.js")
    .then((reg) => console.log("Service Worker registered", reg))
    .catch((err) => console.error("Service Worker registration failed", err));
}

askPermission();

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const permission = await Notification.requestPermission();
    if (permission === "granted") {
      await subscribeUser();
    } else {
      console.log("Notification permission denied or dismissed.");
    }
  } catch (err) {
    console.error("Subscription failed:", err);
  }
});

async function askPermission() {
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Permission not granted");
  }
}

async function subscribeUser() {
  const reg = await navigator.serviceWorker.ready;

  let response = await fetch("http://localhost:8080/api/webpush/vapidkey");
  let key = await response.text();

  const subscription = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(key),
  });

  const userId = "test"; // getUserId(); // Get from auth or localStorage

  await fetch("http://localhost:8080/api/webpush/subscribe", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      expirationTime: subscription.expirationTime,
      keys: subscription.toJSON().keys,
      userId: userId,
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
