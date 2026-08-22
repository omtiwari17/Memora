/* ==========================================================================
   Memora PWA Native Web Push & Reminder Notification Controller
   ========================================================================== */

(function() {
    'use strict';

    let vapidPublicKey = null;
    let swRegistration = null;
    // LocalStorage Persistent Notification Tracker
    function getNotifiedIds() {
        try {
            const raw = localStorage.getItem('memora_notified_memory_ids');
            return raw ? new Set(JSON.parse(raw)) : new Set();
        } catch (e) {
            return new Set();
        }
    }

    function addNotifiedId(id) {
        const ids = getNotifiedIds();
        ids.add(id);
        try {
            localStorage.setItem('memora_notified_memory_ids', JSON.stringify(Array.from(ids)));
        } catch (e) {}
    }

    let notifiedMemoryIds = getNotifiedIds();

    // Mark Memory Done directly from Toast Notification
    window.markMemoryDoneFromToast = async function(memoryId, btnElement) {
        try {
            const formData = new FormData();
            formData.append('status', 'done');

            const resp = await fetch(`/memory/${memoryId}/status/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                },
                body: formData
            });

            if (resp.ok) {
                addNotifiedId(memoryId);
                const toast = btnElement.closest('#memora-toast-container > div');
                if (toast) {
                    toast.classList.add('opacity-0', 'translate-y-4');
                    setTimeout(() => toast.remove(), 300);
                }

                // HTMX or DOM card update if present on page
                const card = document.getElementById(`memory-card-${memoryId}`);
                if (card) {
                    card.classList.add('opacity-40', 'line-through');
                }
            }
        } catch (err) {
            console.error('[Memora Push] Failed to mark memory done:', err);
        }
    };

    // Check Due Reminders for Active Tab (Instant Browser Notification + Toast)
    async function checkDueReminders() {
        try {
            const resp = await fetch('/api/due-reminders/');
            if (!resp.ok) return;
            const data = await resp.json();

            if (data.due_reminders && data.due_reminders.length > 0) {
                data.due_reminders.forEach(item => {
                    if (!notifiedMemoryIds.has(item.id)) {
                        addNotifiedId(item.id);
                        notifiedMemoryIds.add(item.id);

                        // Trigger native OS notification if permission granted
                        if ('Notification' in window && Notification.permission === 'granted') {
                            try {
                                if (swRegistration && swRegistration.showNotification) {
                                    swRegistration.showNotification(`🔔 Reminder: ${item.title}`, {
                                        body: item.content,
                                        icon: '/static/icon-192.png',
                                        badge: '/static/icon-192.png',
                                        data: { url: item.url }
                                    });
                                } else {
                                    new Notification(`🔔 Reminder: ${item.title}`, {
                                        body: item.content,
                                        icon: '/static/icon-192.png',
                                        badge: '/static/icon-192.png'
                                    });
                                }
                            } catch (e) {
                                console.warn('[Memora Push] Native notification error:', e);
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
            container.className = 'fixed bottom-5 right-5 z-[9999] flex flex-col gap-3 max-w-sm w-full pointer-events-none px-4';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = 'pointer-events-auto bg-[#141226]/95 backdrop-blur-2xl border border-purple-500/30 rounded-2xl p-4 shadow-2xl shadow-purple-950/50 flex flex-col gap-2 transform transition-all duration-300 translate-y-4 opacity-0';

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
                    ${memoryId ? `<button onclick="window.markMemoryDoneFromToast(${memoryId}, this)" class="text-[11px] font-bold text-emerald-400 hover:text-emerald-300 px-2 py-0.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all">✓ Mark Done</button>` : ''}
                </div>
                ${showEnablePermissionPrompt ? `<button onclick="window.subscribePushReminders()" class="text-[10px] font-bold px-2 py-1 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/30 transition-all">🔔 Enable OS Banners</button>` : ''}
            </div>
        `;

        container.appendChild(toast);

        // Animate toast entry
        setTimeout(() => {
            toast.classList.remove('translate-y-4', 'opacity-0');
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
        registerServiceWorker();
        checkDueReminders();
        setInterval(checkDueReminders, 60000); // Check every 60 seconds
    });

})();
