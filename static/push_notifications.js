/* ==========================================================================
   Memora PWA Native Web Push & Reminder Notification Controller
   ========================================================================== */

(function() {
    'use strict';
    console.log('[Memora Push] Script loaded and executing...');

    // Helper function to decode VAPID public key
    function urlB64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    // CSRF token helper
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    let vapidPublicKey = null;
    let swRegistration = null;
    // In-Memory Notification Tracker (prevents spam from 60s interval, but resets on reload so uncompleted reminders show again)
    let notifiedMemoryIds = new Set();
    
    function addNotifiedId(id) {
        notifiedMemoryIds.add(id);
    }

    async function registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                swRegistration = await navigator.serviceWorker.register('/static/sw.js');
                console.log('[Memora Push] Service Worker registered successfully.');
                
                // Fetch VAPID Key for subscription
                const response = await fetch('/api/vapid-public-key/');
                if (response.ok) {
                    const data = await response.json();
                    vapidPublicKey = data.public_key;
                }
            } catch (error) {
                console.warn('[Memora Push] Service Worker registration failed:', error);
            }
        }
    }

    // Mark Memory Done directly from Toast Notification
    window.markMemoryDoneFromToast = async function(memoryId, btnElement) {
        if (memoryId === 'test') {
            const toast = btnElement.closest('#memora-toast-container > div');
            if (toast) {
                toast.classList.add('opacity-0', 'translate-y-4');
                setTimeout(() => toast.remove(), 300);
            }
            setTimeout(() => {
                showMemoraToast('🎉 Test Completed', 'Your reminder system and Mark Done actions are working perfectly!');
            }, 350);
            return;
        }

        try {
            const params = new URLSearchParams();
            params.append('status', 'done');
            
            let csrfToken = getCookie('csrftoken');
            if (!csrfToken) {
                console.warn('[Memora Push] CSRF token not found, request might fail.');
                csrfToken = ''; // Fallback
            }

            const resp = await fetch(`/memory/${memoryId}/status/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: params
            });

            if (resp.ok) {
                addNotifiedId(memoryId);
                const toast = btnElement.closest('#memora-toast-container > div');
                if (toast) {
                    toast.classList.add('opacity-0', '-translate-y-4');
                    setTimeout(() => toast.remove(), 300);
                }

                // HTMX or DOM card update if present on page
                const card = document.getElementById(`memory-card-${memoryId}`);
                if (card) {
                    card.classList.add('opacity-40', 'line-through');
                }
                
                showMemoraToast('✅ Marked as Done', 'Memory successfully completed.');
            } else {
                console.error('[Memora Push] Server returned status:', resp.status);
                showMemoraToast('❌ Error', 'Failed to mark done. Server returned ' + resp.status);
            }
        } catch (err) {
            console.error('[Memora Push] Failed to mark memory done:', err);
            showMemoraToast('❌ Error', 'Network error while marking done.');
        }
    };

    // Request Push Notification Permission
    window.subscribePushReminders = async function() {
        if (!('Notification' in window)) return;
        
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
            document.querySelectorAll('.memora-push-toggle-container').forEach(el => el.remove());
            
            if ('serviceWorker' in navigator && vapidPublicKey) {
                try {
                    const swReg = await navigator.serviceWorker.ready;
                    const subscription = await swReg.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: urlB64ToUint8Array(vapidPublicKey)
                    });
                    
                    await fetch('/api/push-subscribe/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify(subscription)
                    });
                } catch (e) {
                    console.warn('[Memora Push] Push subscription failed:', e);
                }
            }
            
            showMemoraToast('🔔 Notifications Enabled', 'You will now receive native OS push notifications for due reminders.');
        } else {
            showMemoraToast('🔕 Notifications Blocked', 'You denied push notifications. To enable them, change your browser settings.');
        }
    };

    // Check Due Reminders for Active Tab (Instant Browser Notification + Toast)
    async function checkDueReminders() {
        try {
            const resp = await fetch('/api/due-reminders/');
            if (!resp.ok) return;
            const data = await resp.json();

            if (data.due_reminders && data.due_reminders.length > 0) {
                data.due_reminders.forEach(async (item) => {
                    if (!notifiedMemoryIds.has(item.id)) {
                        addNotifiedId(item.id);
                        notifiedMemoryIds.add(item.id);

                        // Trigger native OS notification if permission granted
                        if ('Notification' in window && Notification.permission === 'granted') {
                            if ('serviceWorker' in navigator) {
                                navigator.serviceWorker.ready.then(swReg => {
                                    if (swReg && typeof swReg.showNotification === 'function') {
                                        swReg.showNotification(`🔔 Reminder: ${item.title}`, {
                                            body: item.content,
                                            icon: '/static/icon-192.png',
                                            badge: '/static/icon-192.png',
                                            requireInteraction: true,
                                            data: { url: item.url }
                                        }).catch(e => {
                                            console.warn('[Memora Push] SW showNotification error:', e);
                                            try { new Notification(`🔔 Reminder: ${item.title}`, { body: item.content, icon: '/static/icon-192.png' }); } catch(err) {}
                                        });
                                    }
                                });
                            } else if (typeof Notification === 'function') {
                                try {
                                    new Notification(`🔔 Reminder: ${item.title}`, {
                                        body: item.content,
                                        icon: '/static/icon-192.png',
                                        badge: '/static/icon-192.png',
                                        requireInteraction: true
                                    });
                                } catch (e) {
                                    console.warn('[Memora Push] Native notification error:', e);
                                }
                            }
                        }

                        // Trigger in-app glassmorphic toast with Mark Done button
                        showMemoraToast(`🔔 Due Reminder: ${item.title}`, item.content, item.url, item.id);
                    }
                });
            }
        } catch (err) {
            console.error('[Memora Push] Due reminders check failed:', err);
        }
    }

    // Floating Glassmorphic In-App Toast Container
    function showMemoraToast(title, body, url = null, memoryId = null) {
        let container = document.getElementById('memora-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'memora-toast-container';
            container.className = 'fixed top-24 right-5 z-[9999] flex flex-col gap-3 max-w-sm w-full pointer-events-none px-2 max-h-[calc(100vh-7rem)] overflow-y-auto pb-4';
            
            // Custom scrollbar styling inline for the container
            const style = document.createElement('style');
            style.textContent = `
                #memora-toast-container::-webkit-scrollbar { width: 4px; }
                #memora-toast-container::-webkit-scrollbar-track { background: transparent; }
                #memora-toast-container::-webkit-scrollbar-thumb { background: rgba(168, 85, 247, 0.2); border-radius: 4px; }
                #memora-toast-container::-webkit-scrollbar-thumb:hover { background: rgba(168, 85, 247, 0.4); }
            `;
            document.head.appendChild(style);
            
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = 'pointer-events-auto shrink-0 bg-[#141226]/95 backdrop-blur-2xl border border-purple-500/30 rounded-2xl p-4 shadow-2xl shadow-purple-950/50 flex flex-col gap-2 transform transition-all duration-300 -translate-y-4 opacity-0';

        const showEnablePermissionPrompt = ('Notification' in window && Notification.permission !== 'granted');

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
            <div class="flex items-center justify-between gap-2 mt-1">
                <div class="flex items-center gap-2">
                    ${url ? `<a href="${url}" class="inline-flex items-center gap-1 text-[11px] font-bold text-purple-400 hover:text-purple-300">View Memory &rarr;</a>` : ''}
                    ${memoryId ? `<button onclick="window.markMemoryDoneFromToast('${memoryId}', this)" class="text-[11px] font-bold text-emerald-400 hover:text-emerald-300 px-2 py-0.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all">✓ Mark Done</button>` : ''}
                </div>
                ${showEnablePermissionPrompt ? `<button onclick="window.subscribePushReminders()" class="text-[10px] font-bold px-2 py-1 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/30 transition-all">🔔 Enable OS Banners</button>` : ''}
            </div>
        `;

        if (container.firstChild) {
            container.insertBefore(toast, container.firstChild);
        } else {
            container.appendChild(toast);
        }

        // Animate toast entry
        setTimeout(() => {
            toast.classList.remove('-translate-y-4', 'opacity-0');
        }, 50);

        // Auto remove toast after 10 seconds
        setTimeout(() => {
            if (document.body.contains(toast)) {
                toast.classList.add('opacity-0', 'translate-y-4');
                setTimeout(() => toast.remove(), 300);
            }
        }, 10000);
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', () => {
        if ('Notification' in window && Notification.permission === 'granted') {
            document.querySelectorAll('.memora-push-toggle-container').forEach(el => el.remove());
        }
        
        registerServiceWorker();
        checkDueReminders();
        setInterval(checkDueReminders, 60000); // Check every 60 seconds
    });

})();
