/* JP Croco — Service Worker: entrega a notificação no aparelho do admin
   (push do backend), mesmo com o site fechado. Exige contexto seguro
   (HTTPS ou localhost). */

self.addEventListener('push', (event) => {
  let data = { title: '🐊 JP Croco', body: 'Atualização de pedido' };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch (_) {
    try {
      if (event.data) data = { ...data, body: event.data.text() };
    } catch (_) { /* mantém padrão */ }
  }
  event.waitUntil(
    self.registration.showNotification(data.title || '🐊 JP Croco', {
      body: data.body || 'Atualização de pedido',
      tag: 'jpcroco-pedido',
      renotify: true,
      vibrate: [200, 100, 200],
      data: { url: '/admin' },
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/admin';
  event.waitUntil(
    (async () => {
      const wins = await clients.matchAll({ type: 'window', includeUncontrolled: true });
      for (const w of wins) {
        try {
          if (new URL(w.url).pathname.startsWith(url) && 'focus' in w) return w.focus();
        } catch (_) { /* ignora URLs inválidas */ }
      }
      if (clients.openWindow) return clients.openWindow(url);
    })(),
  );
});
