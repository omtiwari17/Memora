/* ==========================================================================
   Memora PWA Native Web Push & Reminder Notification Controller
   ========================================================================== */

(function() {
    'use strict';

    let vapidPublicKey = null;
    let swRegistration = null;
    let notifiedMemoryIds = new Set();

    // Utility: Convert base64 string to Uint8Array for PushManager
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    // Register Service Worker
    async function registerServiceWorker() {
        if ('serviceWorker' in navigator && 'PushManager' in window) {
            try {
                swRegistration = await navigator.serviceWorker.register('/static/sw.js');
                console.log('[Memora SW] Service Worker registered successfully:', swRegistration);
                updateNotificationUI();
            } catch (err) {
                console.error('[Memora SW] Service Worker registration failed:', err);
            }
        }
    }

    // Fetch VAPID Key from Django backend
    async function getVapidPublicKey() {
        if (vapidPublicKey) return vapidPublicKey;
        try {
            const resp = await fetch('/api/vapid-public-key/');
            const data = await resp.json();
            vapidPublicKey = data.public_key;
            return vapidPublicKey;
        } catch (err) {
            console.error('[Memora Push] Failed to fetch VAPID key:', err);
            return null;
        }
    }

    // Subscribe to Web Push
    window.subscribePushReminders = async function() {
        if (!('Notification' in window)) {
            alert('Notifications are not supported by your browser.');
            return;
        }

        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            alert('Notification permission was denied. Please allow notifications in browser settings.');
            updateNotificationUI();
            return;
        }

        if (!swRegistration) {
            await registerServiceWorker();
        }

        const pubKey = await getVapidPublicKey();
        if (!pubKey) {
            console.warn('[Memora Push] No VAPID public key available.');
            return;
        }

        try {
            const subscription = await swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(pubKey)
            });

            // Send subscription to server
            const res = await fetch('/api/push-subscribe/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subscription)
            });

            if (res.ok) {
                showMemoraToast('🔔 Reminders Activated', 'Native push notifications are now active on this device!');
                updateNotificationUI();
            }
        } catch (err) {
            console.error('[Memora Push] Subscription error:', err);
        }
    };

    // Unsubscribe from Web Push
    window.unsubscribePushReminders = async function() {
        if (!swRegistration) return;
        try {
            const subscription = await swRegistration.pushManager.getSubscription();
            if (subscription) {
                await fetch('/api/push-unsubscribe/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ endpoint: subscription.endpoint })
                });
                await subscription.unsubscribe();
                showMemoraToast('🔔 Reminders Paused', 'Native push notifications turned off on this device.');
                updateNotificationUI();
            }
        } catch (err) {
            console.error('[Memora Push] Unsubscribe error:', err);
        }
    };

    // Update Notification Toggle UI Elements
    async function updateNotificationUI() {
        const toggleBtns = document.querySelectorAll('.memora-push-toggle');
        const badges = document.querySelectorAll('.memora-push-status');

        if (!('Notification' in window)) {
            toggleBtns.forEach(btn => btn.classList.add('hidden'));
            return;
        }

        let isSubscribed = false;
        if (swRegistration) {
            const subscription = await swRegistration.pushManager.getSubscription();
            isSubscribed = !!subscription;
        }

        toggleBtns.forEach(btn => {
            if (isSubscribed) {
                btn.innerHTML = `<span class="flex items-center gap-1.5 text-emerald-400 font-bold"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"/></svg> Reminders Active</span>`;
                btn.onclick = window.unsubscribePushReminders;
            } else {
                btn.innerHTML = `<span class="flex items-center gap-1.5 text-purple-300 font-semibold hover:text-white"><svg class="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"/></svg> Enable Push Reminders</span>`;
                btn.onclick = window.subscribePushReminders;
            }
        });

        badges.forEach(badge => {
            if (isSubscribed) {
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        });
    }

    // Check Due Reminders for Active Tab (Instant Browser Notification + Toast)
    async function checkDueReminders() {
        try {
            const resp = await fetch('/api/due-reminders/');
            if (!resp.ok) return;
            const data = await resp.json();

            if (data.due_reminders && data.due_reminders.length > 0) {
                data.due_reminders.forEach(item => {
                    if (!notifiedMemoryIds.has(item.id)) {
                        notifiedMemoryIds.add(item.id);

                        // Trigger native browser notification if allowed
                        if (Notification.permission === 'granted') {
                            new Notification(`🔔 Reminder: ${item.title}`, {
                                body: item.content,
                                icon: '/static/icon-192.png',
                                badge: '/static/icon-192.png'
                            });
                        }

                        // Trigger in-app glassmorphic toast
                        showMemoraToast(`🔔 Due Reminder: ${item.title}`, item.content, item.url);
                    }
                });
            }
        } catch (err) {
            console.error('[Memora Push] Due reminders check failed:', err);
        }
    }

    // Floating Glassmorphic In-App Toast Container
    function showMemoraToast(title, body, url = null) {
        let container = document.getElementById('memora-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'memora-toast-container';
            container.className = 'fixed bottom-5 right-5 z-[9999] flex flex-col gap-3 max-w-sm w-full pointer-events-none px-4';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = 'pointer-events-auto bg-[#141226]/95 backdrop-blur-2xl border border-purple-500/30 rounded-2xl p-4 shadow-2xl shadow-purple-950/50 flex flex-col gap-2 transform transition-all duration-300 translate-y-4 opacity-0';

        toast.innerHTML = `
            <div class="flex items-start justify-between gap-3">
                <div class="flex items-center gap-2">
                    <div class="w-8 h-8 rounded-xl bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-purple-300 shrink-0">
                        <svg class="w-4 h-4 animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"/></svg>
                    </div>
                    <h4 class="text-xs font-bold text-white leading-snug">${title}</h4>
                </div>
                <button onclick="this.closest('#memora-toast-container > div').remove()" class="text-white/40 hover:text-white p-1">
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
            </div>
            <p class="text-xs text-white/70 line-clamp-2">${body}</p>
            ${url ? `<a href="${url}" class="inline-flex items-center gap-1 text-[11px] font-bold text-purple-400 hover:text-purple-300 mt-1">View Memory &rarr;</a>` : ''}
        `;

        container.appendChild(toast);

        // Animate toast entry
        setTimeout(() => {
            toast.classList.remove('translate-y-4', 'opacity-0');
        }, 50);

        // Auto remove toast after 8 seconds
        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-y-4');
            setTimeout(() => toast.remove(), 300);
        }, 8000);
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', () => {
        registerServiceWorker();
        checkDueReminders();
        setInterval(checkDueReminders, 60000); // Check every 60 seconds
    });

})();
