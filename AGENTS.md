# AGENTS.md — Memora

> This file is the single source of truth for any AI coding agent (or human) picking up this project. It contains full project context, architecture decisions, database configurations, deployment instructions, and current codebase state.

---

## 1. Project Purpose

**Memora** — "Your memory, outside your head."

A cross-device personal external memory system. Zero-friction capture for anything worth remembering — quotes, ideas, links, tasks, code snippets, purchase lists, places, people, and more. Everything goes into one app, organized later, found instantly.

**Core Philosophy:**
1. **Capture first** — saving takes seconds, no mandatory metadata
2. **Organize later** — categories, tags, collections available but never forced
3. **Find anything** — universal search across all memory fields

Not a notes app, not a to-do app, not a bookmark manager. It's a **personal second brain / memory inbox**.

---

## 2. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| **Backend** | Python 3.11 / Django 5 | Fast, batteries-included, stable |
| **Interactivity** | HTMX 1.9 | Dynamic search, filtering, inline actions without JS framework overhead |
| **Styling** | Tailwind CSS + DaisyUI (CDN) | Modern glassmorphism UI with zero build step |
| **Typography** | Space Grotesk (Google Fonts) | Modern, geometric, suits dark glassmorphic UI |
| **Database** | **SQLite** (local dev) / **Neon PostgreSQL** (production) | 100% Free forever PostgreSQL via `dj-database-url` |
| **Hosting** | **Render** (Free Web Service) + **cron-job.org** (Keep-Alive Ping) | 100% Free production hosting, stays awake 24/7 without cold starts |
| **Static Files** | WhiteNoise | Compressed static assets served directly by Django WSGI |

**Explicitly Excluded:** React, Node.js, npm build pipelines, heavy SPA frameworks. Tailwind and DaisyUI are loaded directly via CDN.

---

## 3. Architecture Decisions

- **Visual Theme: Dark Aurora + Glassmorphism** — Absolute animated aurora background blobs (`filter: blur(120px)`), glass cards (`backdrop-filter: blur(16px)`), CSS gradient accents, and Space Grotesk font.
- **Generic Memory Model** — Replaced legacy Quote model with `Memory` (supports content, title, category, tags, collections, URLs, author, priority, status, due dates).
- **Type-Aware Card Rendering** — Cards render custom visual layouts per category slug:
  - `tasks`: Interactive checkbox with strike-through styling
  - `code`: Monospace syntax block
  - `links`: Clickable URL preview
  - `watch` / `read` / `buy`: Status badges & purchase/watched indicators
  - `quotes` / `thoughts`: Warm golden serif quotation typography with author attribution & decorative quotation mark
  - `places`: Map marker styling
- **High-Confidence Auto-Categorization** — Real-time 200ms auto-categorization algorithm in `quotes/views.py` using strict regex pattern matching AND keyword-based dictionary matching:
  - `Code`: HTML tags (`<div`, `<meta`), JS/Python/SQL keywords, CLI commands (regex)
  - `Quotes`: Explicit author attributions on new lines (e.g. `- Benjamin Franklin`) or quoted text with named author (regex)
  - `Links`: HTTP/HTTPS URL detection (regex)
  - `Tasks`, `Watch`, `Read`, `Buy`, `Places`, `Ideas`, `Learn`, `Reminders`, `People`, `Projects`, `Thoughts`, `Important`: Keyword dictionary matching via `CATEGORY_KEYWORDS`
  - `Inbox`: Plain text notes default to Inbox cleanly when no patterns match
- **Smart Auto-Titling** — Automatically formats titles on client & server:
  - Quotes: `"`Short phrase..." — Author Name`
  - HTML Snippets: `<title>` tag content extraction
  - URLs: Domain and path extraction
- **Full Capture Form** — Capture modal includes: content, title, category (auto-suggested), tags, author, priority, due date, and source URL.
- **Full Edit Modal** — Edit modal includes: content, title, category, tags, author, priority, due date, status, and source URL with HTMX live DOM swap.
- **Instant HTMX Actions** — Returning `HttpResponse("")` for delete and archive requests with `hx-swap="outerHTML"` causes HTMX to remove cards instantly (0ms delay) without page reloads.
- **Form Edit Lifecycle Safety** — Uses `hx-on::after-request="closeEditModal('...')"` to ensure HTMX completes the POST submission and DOM swap before removing modal elements.
- **Category Reordering System** — Custom ordering endpoint (`/categories/<id>/reorder/<direction>/`) swaps integer sequence values between adjacent categories with live sidebar & dropdown updates.
- **Environment-Aware Sidebar Branding** — Conditionally renders `Memora v5.0 — All 5 Phases Complete 🎉` in development (`DEBUG=True` + `INTERNAL_IPS`) and clean product branding `Memora v5.0 — Personal Vault` in production (`DEBUG=False`).
- **Universal Capture API** — CSRF-exempt JSON endpoint (`/api/capture/`) enabling 1-click capture from desktop bookmarklets and browser extensions.
- **PWA Web Share Target** — Accepts shared links, text, and titles from Android/iOS Web Share API via `/share/` with server-side auto-categorization.

---

## 4. File Structure

```
Memora/
├── manage.py
├── requirements.txt
├── .gitignore
├── AGENTS.md
├── quotevault/              # Django project package (quotevault internally)
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── quotes/                  # Main memory app (quotes internally)
│   ├── __init__.py
│   ├── admin.py
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
│               ├── memory_card.html      # Type-aware memory card partial
│               ├── memory_grid.html      # Shared grid of memory cards with empty state
│               ├── memory_edit_modal.html# Pre-filled edit modal partial with HTMX swap
│               ├── capture_modal.html   # Quick capture modal with live title & auto-category
│               ├── capture_feedback.html # Capture success/error feedback partial
│               └── random_memory.html    # Random memory card partial
├── static/
│   ├── manifest.json        # PWA Web Share Target manifest
│   ├── bookmarklet.js       # Desktop browser bookmarklet script
│   ├── icon-192.png
│   └── icon-512.png
└── venv/                    # Virtual environment (gitignored)
```

---

## 5. Data Models

### Memory
- `title` (CharField, optional)
- `content` (TextField, required)
- `category` (FK → Category, optional)
- `tags` (M2M → Tag)
- `collections` (M2M → Collection)
- `source_url`, `source_title`, `author`
- `created_at`, `updated_at`, `due_date`, `reminder_at`
- `status` (`inbox`, `active`, `done`, `archived`)
- `priority` (`none`, `low`, `medium`, `high`, `urgent`)
- `is_pinned`, `is_archived`

### Category
- `name`, `slug`, `emoji`, `color`, `is_default`, `order`
- 16 default system categories seeded via `python manage.py seed_categories`

### Tag
- `name`, `slug`

### Collection
- `name`, `description`, `created_at`, `updated_at`

---

## 6. Default Categories

💬 **Quotes** • 🧠 **Thoughts** • 💡 **Ideas** • 📚 **Learn** • 🔖 **Save** • 🔗 **Links** • 🎬 **Watch** • 📖 **Read** • 🛒 **Buy** • ✅ **Tasks** • 📅 **Reminders** • ✈️ **Places** • 💻 **Code** • 👤 **People** • 🚀 **Projects** • ❤️ **Important**

---

## 7. URL Routes

| Path | Name | Purpose |
|---|---|---|
| `/` | `dashboard` | Main dashboard with recent memories, pinned items & sidebar |
| `/search/` | `search_memories` | HTMX real-time universal search endpoint |
| `/capture/` | `capture` | Quick capture form handler |
| `/api/capture/` | `capture_api` | CSRF-exempt JSON API endpoint for bookmarklet/share |
| `/api/suggest-category/` | `suggest_category` | Category suggestion JSON API |
| `/memory/<id>/` | `memory_detail` | Detailed view for a single memory + smart suggestions |
| `/memory/<id>/edit/` | `memory_edit` | HTMX memory edit modal & POST handler |
| `/memory/<id>/pin/` | `memory_pin` | HTMX toggle pin |
| `/memory/<id>/archive/` | `memory_archive` | HTMX toggle archive (0ms DOM swap) |
| `/memory/<id>/status/` | `memory_status` | HTMX update memory status (e.g. mark done) |
| `/memory/<id>/delete/` | `memory_delete` | HTMX delete memory (0ms DOM swap) |
| `/inbox/` | `inbox` | Unclassified Inbox view |
| `/important/` | `important` | Pinned / Important memories |
| `/tasks/` | `tasks` | Dedicated Tasks productivity workspace |
| `/reminders/` | `reminders` | Chronological Reminders & Due Dates timeline |
| `/priority/<level>/` | `priority_filter` | Filter memories by priority level |
| `/archive/` | `archive` | Archived memories view |
| `/today/` | `today` | Memories captured today |
| `/week/` | `week` | Memories captured this week |
| `/category/<slug>/` | `category_filter` | Filter memories by category |
| `/tag/<slug>/` | `tag_filter` | Filter memories by tag |
| `/random/` | `random_memory` | "Remember This" random memory resurfacing |
| `/on-this-day/` | `on_this_day` | Historical memory resurfacing engine |
| `/recently-viewed/` | `recently_viewed` | Session-based recently viewed history |
| `/categories/` | `category_manage` | Full category management dashboard |
| `/categories/create/` | `category_create` | Create new category endpoint |
| `/categories/<id>/edit/` | `category_edit` | Edit category endpoint |
| `/categories/<id>/delete/` | `category_delete` | Delete category with Inbox fallback |
| `/categories/<id>/reorder/<dir>/` | `category_reorder` | Swap category order (up/down) |
| `/share/` | `share_target` | Mobile PWA Web Share Target handler |

---

## 8. Completed Work (Phase 1 — Phase 5 Complete)

- [x] Memory, Category, Tag, Collection models implemented
- [x] 16 default categories seeded with custom colors and emojis
- [x] Full Category Management suite (Create, Edit, Delete with Inbox fallback, 20-color preset palette, 32-emoji quick picker, Up/Down reordering)
- [x] Dashboard with sidebar navigation & category chips
- [x] Persistent top-right **`+ Capture New Memory`** header button (`Ctrl+K` shortcut indicator)
- [x] Real-time 200ms high-confidence auto-categorization engine
- [x] Real-time live auto-title preview on client & smart quote author titling on server
- [x] Type-aware memory cards (Tasks, Code, Links, Watch/Read/Buy, Golden Serif Quotes, Places)
- [x] Full Memory Editing system (`memory_edit_modal.html` with HTMX live DOM swap)
- [x] Instant 0ms DOM removal for Delete and Archive actions
- [x] Dedicated Productivity workspaces (`/tasks/`, `/reminders/`, `/priority/`)
- [x] Memory Resurfacing ("Remember This" random memory & "On This Day" historical resurfacing)
- [x] Recently Viewed session history (`/recently-viewed/`)
- [x] Smart Related Memory suggestions on memory detail page
- [x] Desktop bookmarklet script & PWA Web Share Target with auto-categorization
- [x] Environment-aware sidebar version badge (Dev milestone vs Production branding)
- [x] GitHub repository setup and initial commit pushes (`omtiwari17/Memora`)
- [x] Production deployment configuration for **100% Free Forever Hosting** (Neon Postgres + Render + cron-job.org keep-alive)

---

## 9. Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/omtiwari17/Memora.git
cd Memora

# 2. Setup virtual environment
python -m venv venv
venv\Scripts\activate        # On Windows (or source venv/bin/activate on Linux/Mac)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run database migrations & seed default categories
python manage.py migrate
python manage.py seed_categories

# 5. Start dev server (sets DEBUG=True)
$env:DEBUG="True"             # PowerShell
python manage.py runserver
```

---

## 10. 100% Free Forever Production Deployment Guide

Memora is configured to run **100% free forever** without paying for database or hosting subscriptions, and without Render going to sleep:

### Step 1: Database Setup (Neon — Free PostgreSQL)
1. Register at **[Neon.tech](https://neon.tech)** (100% free PostgreSQL, no credit card required).
2. Create a project `memora-db` and copy the **Connection String** (`postgres://...`).

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
   - `SECRET_KEY` = *(Random secret string)*
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `*`

### Step 3: Prevent Render Sleep (cron-job.org — Free 24/7 Keep-Alive)
Render's free tier puts web services to sleep after 15 minutes of inactivity. To keep your app **awake 24/7 with zero loading delays**:
1. Register at **[cron-job.org](https://cron-job.org)** (100% free).
2. Click **+ CREATE CRONJOB**:
   - **Title**: `Memora Keep Alive`
   - **URL**: `https://your-app.onrender.com`
   - **Schedule**: `Every 10 minutes`
3. Save the job. Your app will now stay online 24/7 with **0-second cold starts** for $0/month!

---

## 11. Implementation Roadmap & Milestones

### Phase 1 — Foundation
- [x] Rename Quote → Memory
- [x] Generic capture
- [x] Inbox
- [x] Categories
- [x] Universal search
- [x] Recent memories

### Phase 2 — Organization
- [x] Tags
- [x] Collections
- [x] Pinning
- [x] Archive
- [x] Filters

### Phase 3 — Productivity
- [x] Tasks
- [x] Reminders
- [x] Due dates
- [x] Statuses

### Phase 4 — Smart Capture
- [x] Automatic category suggestions
- [x] Automatic title extraction
- [x] URL metadata
- [x] Better browser/mobile capture

### Phase 5 — Memory Features
- [x] Random memory
- [x] Resurfacing
- [x] Recently viewed
- [x] "On this day"
- [x] Smart suggestions
