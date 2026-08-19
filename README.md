# 🧠 Memora — Your Memory, Outside Your Head

> A cross-device personal external memory system. Zero-friction capture for anything worth remembering — quotes, ideas, links, tasks, code snippets, purchase lists, places, people, and more. Everything goes into one app, organized later, found instantly.

---

## ✨ Features

- **⚡ Zero-Friction Universal Capture**: Capture anything in seconds with `Ctrl+K` keyboard shortcut or top-header capture button. No mandatory metadata required.
- **🤖 Real-Time Smart Auto-Categorization (200ms)**: High-confidence regex matching automatically categorizes your entries into **💻 Code**, **💬 Quotes**, **🔗 Links**, or **📥 Inbox** in real time as you type.
- **✍️ Intelligent Live Auto-Titling**: Automatically formats titles as you type. Quotes automatically extract core phrases with author attribution (e.g. `"`I didn't fail the test..." — Benjamin Franklin`), web links extract domain paths, and code snippets extract HTML `<title>` tags.
- **🎨 Type-Aware Glassmorphic Card Engine**: Beautiful custom visual layouts rendered per category:
  - **💬 Quotes & 🧠 Thoughts**: Warm golden serif quotation typography with author attribution line and decorative quote mark icon.
  - **💻 Code**: Monospace syntax blocks with horizontal scroll.
  - **✅ Tasks**: Interactive completion checkboxes with strike-through styling.
  - **🔗 Links**: Clickable URL previews.
  - **🎬 Watch / 📖 Read / 🛒 Buy**: Status indicators and purchase/watched badges.
  - **✈️ Places**: Map marker location styling.
- **⚡ Instant 0ms HTMX Actions**: Delete, archive, and update status instantly without full page reloads or UI lag.
- **⚙️ Complete Category Manager**:
  - 16 seeded default categories.
  - Create, edit, and delete any category with automatic memory fallback to Inbox.
  - 20-color dark-mode preset palette with used-color checkmark indicators (`✓`).
  - 32-emoji quick selector bar.
  - **⬆️ / ⬇️ Category Reordering System** to customize sidebar and dropdown ordering.
- **🚀 Dedicated Productivity Workspaces**:
  - **`✅ Tasks`**: Filter and manage pending and completed task items.
  - **`📅 Reminders`**: Chronological timeline of upcoming due dates and reminders.
  - **`🔴 Priority Levels`**: Filter memories by Urgent, High, Medium, Low, or None.
- **🧠 Memory Resurfacing & Nostalgia**:
  - **`🎲 Random Memory`**: "Remember This" resurfacing engine.
  - **`✨ On This Day`**: Historical memory resurfacing engine.
  - **`🕒 Recently Viewed`**: Session-based history of inspected memories.
  - **`💡 Smart Related Suggestions`**: Automatically suggests related memories on detail view.
- **📱 Cross-Device Capture Everywhere**:
  - **Desktop Bookmarklet**: Drag-and-drop 1-click browser capture button.
  - **PWA Web Share Target**: Accept text, links, and titles directly from Android/iOS Chrome & Safari share menus via `/share/`.
  - **Universal JSON API**: CSRF-exempt `/api/capture/` endpoint for integrations.

---

## 🛠️ Tech Stack

| Layer | Technology | Description |
|---|---|---|
| **Backend** | Python 3.11 / Django 5 | Fast, stable, batteries-included web framework |
| **Frontend Interactivity** | HTMX 1.9 | Dynamic live search, modal edits, and 0ms DOM swaps without SPA overhead |
| **Styling & Aesthetics** | Tailwind CSS + DaisyUI | Dark Aurora background blobs & glassmorphism theme |
| **Typography** | Space Grotesk | Modern geometric Google Font |
| **Database** | SQLite (Local) / Neon PostgreSQL (Prod) | 100% Free forever PostgreSQL via `dj-database-url` |
| **Hosting & Keep-Alive** | Render + cron-job.org | 100% Free production hosting with 24/7 zero cold-start keep-alive |
| **Static Assets** | WhiteNoise | Compressed static asset handling |

---

## 📁 File Structure

```
Memora/
├── manage.py
├── requirements.txt
├── README.md
├── AGENTS.md
├── quotevault/              # Django project package
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── quotes/                  # Main memory application
│   ├── models.py            # Memory, Category, Tag, Collection
│   ├── views.py             # Dashboard, search, capture, API, category CRUD, reorder
│   ├── urls.py
│   ├── management/
│   │   └── commands/
│   │       └── seed_categories.py
│   └── templates/
│       └── quotes/
│           ├── dashboard.html       # Main dashboard with sidebar + header capture button
│           ├── memory_list.html     # Filtered list view (inbox, category, tag, tasks, etc.)
│           ├── memory_detail.html   # Single memory detail page with related suggestions
│           ├── category_manage.html # Category manager with CRUD, palette, emoji suggest, reorder
│           ├── capture_form.html    # Full-page capture form
│           ├── random_memory.html   # Random memory page
│           └── partials/
│               ├── memory_card.html       # Type-aware memory card partial
│               ├── memory_grid.html       # Shared grid of memory cards with empty state
│               ├── memory_edit_modal.html # Pre-filled edit modal partial with HTMX swap
│               ├── capture_modal.html     # Quick capture modal with live title & auto-category
│               └── capture_feedback.html  # Capture success/error feedback partial
└── static/
    ├── manifest.json        # PWA Web Share Target manifest
    └── bookmarklet.js       # Desktop browser bookmarklet script
```

---

## 💻 Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/omtiwari17/Memora.git
cd Memora

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # On Windows (or source venv/bin/activate on Linux/Mac)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run database migrations & seed default categories
python manage.py migrate
python manage.py seed_categories

# 5. Start development server (sets DEBUG=True)
$env:DEBUG="True"             # PowerShell
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser!

---

## 🌐 100% Free Forever Production Deployment Guide

Memora is configured to run **100% free forever** on Render and Neon PostgreSQL without cold starts:

### Step 1: Database Setup (Neon — Free PostgreSQL)
1. Sign up at **[Neon.tech](https://neon.tech)** (100% free PostgreSQL, no credit card required).
2. Create a database `memora-db` and copy the connection string (`postgres://...`).

### Step 2: Web Hosting (Render — Free Web Service)
1. Go to **[Render.com](https://render.com)** and create a new **Web Service** connected to `omtiwari17/Memora`.
2. Configure settings:
   - **Environment**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_categories
     ```
   - **Start Command**:
     ```bash
     gunicorn quotevault.wsgi:application
     ```
3. Set **Environment Variables** in Render dashboard:
   - `DATABASE_URL` = *(Your Neon PostgreSQL connection string)*
   - `SECRET_KEY` = *(Random secret key)*
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `*`

### Step 3: Prevent Render Sleep (cron-job.org Keep-Alive)
Render free services sleep after 15 minutes of inactivity. To keep your app **online 24/7 with zero cold-start delays**:
1. Register at **[cron-job.org](https://cron-job.org)** (100% free).
2. Create a Cronjob pointing to `https://your-app.onrender.com` every **10 minutes**.
3. Save the job. Your app will stay awake 24/7 for $0/month!

---

## 🗺️ Implementation Roadmap

- [x] **Phase 1 — Foundation**: Generic Memory model, zero-friction capture, inbox, categories, universal HTMX search, recent memories feed.
- [x] **Phase 2 — Organization**: Tags, collections, pinning, archive with 0ms DOM removal, category CRUD & palette.
- [x] **Phase 3 — Productivity**: Tasks workspace, reminders timeline, due dates, priority levels.
- [x] **Phase 4 — Smart Capture**: 200ms high-confidence auto-categorization, smart quote author titling, PWA share target, bookmarklet.
- [x] **Phase 5 — Memory Features**: Random memory, "On This Day" resurfacing, Recently Viewed history, Smart Related Suggestions.

---

## 📜 License

MIT License © 2026 Om Tiwari