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
| **CI/CD** | GitHub Actions | 4-stage pipeline: Lint → Django Checks → 115 Tests → Deploy Readiness |
| **Testing** | Django TestCase (115 tests) | Models, auth, views, URLs, CRUD, APIs, custom admin, movie watch ratings, data isolation |

**Explicitly Excluded:** React, Node.js, npm build pipelines, heavy SPA frameworks. Tailwind and DaisyUI are loaded directly via CDN.

---

## 3. Architecture Decisions

- **Visual Theme: Dark Aurora + Glassmorphism + Crisp SVG Icons** — Absolute animated aurora background blobs (`filter: blur(120px)`), glass cards with category left-border accents (`border-l-4`), CSS gradient accents, Space Grotesk font, and vector SVG iconography replacing raw OS emojis for a high-end application aesthetic.
- **Handcrafted Vector SVG Branding: Synapse Infinity M Logo & Favicon** — Pin-sharp, handcrafted vector SVG logo mark (`logo.svg`) featuring an interlocking gradient memory ribbon ('M'), an infinity retention arch, and a central synapse pulse node (`#e879f9`). Served directly for all favicons (`/favicon.ico`), browser tabs, desktop/mobile headers, and login screens with 0ms load time.
- **Niche Authentication: Vault Handle + 6-Digit PIN** — Zero email or password friction. Users register and unlock their personal private memory vault using a unique **Vault Handle** (e.g. `@om`) and a secure **6-Digit PIN** (hashed via Django's PBKDF2). All memories, categories, and collections are strictly user-scoped (`user=request.user`). Login page features a clear **Unlock Vault / Create New Vault** toggle so new users immediately see the registration option.
- **Custom Admin Console (`/ctrl/`)** — Dedicated glassmorphic Admin Command Console at route `/ctrl/` with dedicated login portal (`/ctrl/login/`), session isolation (`request.session["admin_unlocked"] = True`), Amber Gold Command Console visual theme, dynamic HTMX handle filtering, rich empty state card, and management command `create_admin --handle <handle> --pin <pin>`.
- **Interactive Movie / Cinema Watch Status & 5-Star Rating System** — `Memory.watch_status` (`want_to_watch`, `watching`, `watched`) and `Memory.rating` (1-5 stars) with SVG icon watch status pills (`Want to Watch`, `Watching`, `Watched`) and interactive CSS hover fill with glowing spring scale animation (`drop-shadow(0 0 8px rgba(251,191,36,0.9))`) directly on memory cards.
- **Unified Cinema Category & Tag-Based Media** — Consolidated media categories under **Cinema** 🎬 (`slug: cinema`), organizing movies vs TV series via tags (`#movie`, `#series`, `#anime`, `#documentary`).
- **Developer Profile Links Footer** — Glassmorphic **Created by Om Tiwari** developer badge in left navigation sidebar (`dashboard.html`, `memory_list.html`) and login screen (`login.html`) linking to Portfolio (`https://omtiwari.tech/`), GitHub (`https://github.com/omtiwari17`), and LinkedIn (`https://www.linkedin.com/in/tiwariom/`).
- **Production Security Hardening** — When `DEBUG=False`, Django enforces: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS=31536000` (1 year with preload), `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and `SECURE_PROXY_SSL_HEADER` for Render's reverse proxy. All 6 Django `--deploy` security warnings resolved to zero.
- **CI/CD Safety Net (GitHub Actions)** — 4-stage pipeline runs on every push/PR to `main`: (1) Lint & syntax compile, (2) Django system check + migration integrity, (3) 115-test suite covering models, auth, views, URLs, CRUD, APIs, favicon, admin console, and user data isolation, (4) Production deploy readiness with Gunicorn startup verification.
- **Sidebar & Header Layout Rules** — Persistent **`+ New Category`** button in the left sidebar on all pages (`dashboard.html`, `memory_list.html`). The primary **`+ Capture New Memory`** header button is exclusively displayed on the "All Memories" dashboard page (`dashboard.html`). Filtered out `reminders` and `tasks` from the categories loop in the sidebar so Reminders appears exactly once under Productivity.
- **Full-Width Aligned Layout** — Search bar containers span 100% full-width (`w-full`) across dashboard and filtered list views, aligning flush with header statistics cards and memory grid cards.
- **Generic Memory Model** — Replaced legacy Quote model with `Memory` (supports content, title, category, tags, collections, URLs, author, priority, status, due dates, watch_status, rating).
- **Type-Aware Card Rendering** — Cards render custom visual layouts per category slug:
  - `tasks`: Interactive checkbox with strike-through styling
  - `code`: Monospace syntax block
  - `links`: Clickable URL preview
  - `cinema` / `watch`: SVG Watch Status Pills (`Want to Watch`, `Watching`, `Watched`) & 5-Star Rating selector with glowing hover fill animation
  - `read` / `buy`: Status badges & purchase/read indicators
  - `quotes` / `thoughts`: Warm golden serif quotation typography with author attribution & decorative quotation mark
  - `places`: Map marker styling
- **High-Confidence Auto-Categorization** — Real-time 200ms auto-categorization algorithm in `quotes/views.py` using strict regex pattern matching AND keyword-based dictionary matching:
  - `Code`: HTML tags (`<div`, `<meta`), JS/Python/SQL keywords, CLI commands (regex)
  - `Quotes`: Explicit author attributions on new lines (e.g. `- Benjamin Franklin`) or quoted text with named author (regex)
  - `Links`: HTTP/HTTPS URL detection (regex)
  - `Cinema`, `Watch`, `Read`, `Buy`, `Places`, `Ideas`, `Learn`, `Reminders`, `People`, `Projects`, `Thoughts`, `Important`: Keyword dictionary matching via `CATEGORY_KEYWORDS`
  - `Inbox`: Plain text notes default to Inbox cleanly when no patterns match
- **Smart Auto-Titling** — Automatically formats titles on client & server:
  - Quotes: `"`Short phrase..." — Author Name`
  - HTML Snippets: `<title>` tag content extraction
  - URLs: Domain and path extraction
- **Full Capture Form** — Clean quick capture modal (content, title, category, tags, author, priority, due date, source URL) kept lightning fast for all categories.
- **Full Edit Modal** — Edit modal includes: content, title, category, tags, author, priority, due date, status, watch_status, rating, and source URL with HTMX live DOM swap.
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
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI/CD pipeline (4-stage, 115 tests)
├── quotevault/              # Django project package (quotevault internally)
│   ├── __init__.py
│   ├── settings.py          # Production security: HSTS, SSL redirect, secure cookies
│   ├── urls.py
│   └── wsgi.py
├── quotes/                  # Main memory app (quotes internally)
│   ├── __init__.py
│   ├── admin.py
│   ├── models.py            # Memory, Category, Tag, Collection
│   ├── views.py             # Dashboard, search, capture, API, category CRUD, custom admin
│   ├── tests.py             # 115 automated tests (models, auth, views, URLs, CRUD, APIs, admin)
│   ├── urls.py
│   ├── management/
│   │   └── commands/
│   │       ├── seed_categories.py
│   │       └── create_admin.py  # Management command to create/promote admin accounts (--handle, --pin)
│   └── templates/
│       └── quotes/
│           ├── dashboard.html       # Main dashboard with sidebar + header capture button
│           ├── login.html           # Vault login with Unlock/Create toggle + Developer footer
│           ├── memory_list.html     # Filtered list view (inbox, category, tag, tasks, etc.)
│           ├── memory_detail.html   # Single memory detail page with related suggestions
│           ├── category_manage.html # Category manager with CRUD, palette, emoji suggest, reorder
│           ├── admin_dashboard.html # Custom Admin Console with Amber Gold theme & handle filter
│           ├── admin_login.html     # Dedicated Admin Login Portal
│           ├── admin_denied.html    # Custom Admin Access Denied screen
│           ├── capture_form.html    # Full-page capture form
│           ├── random_memory.html   # Random memory page
│           └── partials/
│               ├── memory_card.html      # Type-aware memory card partial (with Watch & Ratings)
│               ├── memory_grid.html      # Shared grid of memory cards with empty state
│               ├── memory_edit_modal.html# Pre-filled edit modal partial with HTMX swap
│               ├── capture_modal.html   # Quick capture modal with live title & auto-category
│               ├── capture_feedback.html # Capture success/error feedback partial
│               ├── admin_memory_feed.html# HTMX admin feed partial with filter & empty state
│               └── random_memory.html    # Random memory card partial
├── static/
│   ├── manifest.json        # PWA Web Share Target manifest
│   ├── bookmarklet.js       # Desktop browser bookmarklet script
│   ├── logo.svg             # Handcrafted Synapse Infinity M vector SVG logo
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
- `watch_status` (`want_to_watch`, `watching`, `watched`)
- `rating` (IntegerField 1 to 5 stars, optional)
- `is_pinned`, `is_archived`

### Category
- `name`, `slug`, `emoji`, `color`, `is_default`, `order`
- 17 default system categories seeded via `python manage.py seed_categories`

### Tag
- `name`, `slug`

### Collection
- `name`, `description`, `created_at`, `updated_at`

---

## 6. Default Categories

💬 **Quotes** • 🧠 **Thoughts** • 💡 **Ideas** • 📚 **Learn** • 🔖 **Save** • 🔗 **Links** • 🎬 **Watch** • 🎬 **Cinema** • 📖 **Read** • 🛒 **Buy** • ✅ **Tasks** • 📅 **Reminders** • ✈️ **Places** • 💻 **Code** • 👤 **People** • 🚀 **Projects** • ❤️ **Important**

---

## 7. URL Routes

| Path | Name | Purpose |
|---|---|---|
| `/login/` | `login` | Vault Handle + 6-Digit PIN unlock and registration screen |
| `/logout/` | `logout` | Lock memory vault session |
| `/favicon.ico` | `favicon` | Vector SVG favicon endpoint serving `logo.svg` directly |
| `/ctrl/` | `custom_admin_panel` | Custom Admin Command Console with handle filtering |
| `/ctrl/login/` | `admin_vault_login` | Dedicated Admin Vault Login Portal |
| `/ctrl/logout/` | `admin_vault_logout` | Admin Logout & session lock |
| `/ctrl/user/<id>/toggle-staff/` | `admin_toggle_staff` | Admin toggle staff status endpoint |
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
| `/memory/<id>/watch-status/` | `memory_watch_status` | HTMX update movie watch status and star rating |
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
| `/categories/` | `category_manage` | Full category management dashboard (36-color palette + Suggest Unused Color) |
| `/categories/create/` | `category_create` | Create new category endpoint |
| `/categories/<id>/edit/` | `category_edit` | Edit category endpoint |
| `/categories/<id>/delete/` | `category_delete` | Delete category with Inbox fallback |
| `/categories/<id>/reorder/<dir>/` | `category_reorder` | Swap category order (up/down) |
| `/share/` | `share_target` | Mobile PWA Web Share Target handler |
| `/api/vapid-public-key/` | `vapid_public_key` | JSON VAPID Public Key endpoint for Service Worker |
| `/api/push-subscribe/` | `push_subscribe` | Save browser Web Push subscription |
| `/api/push-unsubscribe/` | `push_unsubscribe` | Delete browser Web Push subscription |
| `/api/due-reminders/` | `due_reminders_api` | Active tab due reminders API |
| `/api/trigger-due-reminders/` | `trigger_due_reminders` | Cron / push notification dispatch endpoint |
| `/healthz/` | `health_check` | Direct HTTP 200 OK uptime ping & Glassmorphic System Health Dashboard |
| `/ping/` | `health_check` | Alias for health check uptime endpoint |

---

## 8. Completed Work (Phase 1 — Phase 7 Complete)

- [x] Native PWA Web Push & Service Worker Notification System (`sw.js`, `push_notifications.js`, VAPID key pair generation, `PushSubscription` model)
- [x] In-App Glassmorphic Toast Notifications & 60s Due Reminder Poll Checker
- [x] `static/logo.svg` standardized as 100% single source of truth global logo across all headers, sidebars, footers, login screens, and error pages
- [x] Username profile badge cleaned (no `@` prefix, uppercase initial avatar) with vector Sign Out exit icon (`🚪`)
- [x] Memory, Category, Tag, Collection models implemented
- [x] 17 default categories seeded with custom colors
- [x] Niche Vault Handle + 6-Digit PIN authentication system (`login.html`, `vault_login`, `vault_logout`, user-scoped data filtering)
- [x] Login page **Unlock Vault / Create New Vault** toggle UX (clear registration path for new users)
- [x] Handcrafted Synapse Infinity M vector SVG branding & favicon system (`logo.svg`, `/favicon.ico` endpoint)
- [x] Custom Admin Console at `/ctrl/` with dedicated login portal `/ctrl/login/`, Amber Gold theme, handle filter & empty state
- [x] Management command `python manage.py create_admin --handle <handle> --pin <pin>`
- [x] Interactive Movie / Cinema Watch Status pills (`Want to Watch`, `Watching`, `Watched`) & 5-Star Rating selector with glowing CSS hover fill animation
- [x] Developer Profile Links Footer ("Created by Om Tiwari" linking to Portfolio `https://omtiwari.tech/`, GitHub `https://github.com/omtiwari17`, LinkedIn `https://www.linkedin.com/in/tiwariom/`)
- [x] 100% Emoji Purge across entire database & templates replaced with crisp Heroicons SVG icons
- [x] Full Category Management suite (Create, Edit, Delete with Inbox fallback, 36-color preset palette, in-use `✓` checkmark swatches, Up/Down reordering, and **`Suggest Unused Color`** generator)
- [x] User-scoped tag autocomplete & click-to-add suggestion chips (`Tag.objects.filter(memories__user=request.user)`)
- [x] Mobile view user profile badge (`@username`), direct sign-out button, and developer footer card
- [x] Dedicated unauthenticated `/healthz/` and `/ping/` uptime monitoring endpoints returning direct `HTTP 200 OK` (0 redirects)
- [x] Glassmorphic System Health & Uptime Dashboard front-end page (`health_check.html`)
- [x] Dashboard with sidebar navigation & category chips
- [x] Persistent sidebar **`+ New Category`** button across all views
- [x] Header **`+ Capture New Memory`** button scoped exclusively to the "All Memories" dashboard page
- [x] 100% full-width aligned search bar (`w-full`) flush with statistics cards and memory cards
- [x] Real-time 200ms high-confidence auto-categorization engine
- [x] Real-time live auto-title preview on client & smart quote author titling on server
- [x] Type-aware memory cards (Tasks, Code, Links, Cinema/Watch, Golden Serif Quotes, Places)
- [x] Full Memory Editing system (`memory_edit_modal.html` with HTMX live DOM swap)
- [x] Instant 0ms DOM removal for Delete and Archive actions
- [x] Dedicated Productivity workspaces (`/tasks/`, `/reminders/`, `/priority/`)
- [x] Memory Resurfacing ("Remember This" random memory & "On This Day" historical resurfacing)
- [x] Recently Viewed session history (`/recently-viewed/`)
- [x] Smart Related Memory suggestions on memory detail page
- [x] Desktop bookmarklet script & PWA Web Share Target with auto-categorization
- [x] Environment-aware sidebar version badge (Dev milestone vs Production branding)
- [x] GitHub Actions CI/CD pipeline (4-stage, 118 tests, deploy readiness gatekeeper)
- [x] Production security hardening (HSTS, SSL redirect, secure cookies, CSRF — 0 deploy warnings)
- [x] Full secret audit — zero sensitive data in Git history or tracked files
- [x] GitHub repository setup and initial commit pushes (`omtiwari17/Memora`)
- [x] Production deployment on **100% Free Forever Hosting** (Neon Postgres + Render + cron-job.org keep-alive via `/healthz/`)

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
python manage.py create_admin --handle om --pin 123456

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
     pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_categories && python manage.py create_admin
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
   - `ADMIN_HANDLE` = `admin` *(Optional: your preferred admin handle, default: admin)*
   - `ADMIN_PIN` = `123456` *(Optional: your 6-digit admin PIN, default: 000000)*

### Step 3: Prevent Render Sleep (cron-job.org — Free 24/7 Keep-Alive)
Render's free tier puts web services to sleep after 15 minutes of inactivity. To keep your app **awake 24/7 with zero loading delays**:
1. Register at **[cron-job.org](https://cron-job.org)** (100% free).
2. Click **+ CREATE CRONJOB**:
   - **Title**: `Memora Keep Alive`
   - **URL**: `https://your-app.onrender.com/healthz/` *(Must include `https://` and `/healthz/` to return HTTP 200 OK directly with 0 redirects)*
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

### Phase 6 — Production & CI/CD
- [x] Custom Admin Console at `/ctrl/`
- [x] Interactive Movie Watch Status & 5-Star Rating System
- [x] Developer Profile Links Footer
- [x] GitHub Actions CI/CD pipeline (118 tests)
- [x] Production security hardening (0 deploy warnings)
- [x] Secret audit (0 leaks in Git history)
- [x] Live deployment (Neon + Render + cron-job.org)
- [x] Login UX toggle (Unlock / Create New Vault)

---

## 12. Git Branching & Deployment Workflow

> ⛔ **STRICT DIRECTIVE FOR ALL AI AGENTS & CONTRIBUTORS:**
> **NEVER execute `git commit` or direct pushes on the `main` branch under ANY circumstance.**
> All commits, feature work, bug fixes, and edits MUST be committed exclusively to the **`dev`** branch.
> Merging from `dev` to `main` is performed ONLY when the user explicitly instructs to merge or deploy.

```
dev branch  ──→  User tests locally  ──→  User says "merge"  ──→  main branch  ──→  Render auto-deploys
```

### Strict Operating Rules:
1. **NEVER commit on `main`** — switch to `dev` before creating any commit (`git checkout dev`).
2. **All new features, fixes, and changes** → commit exclusively to `dev` branch.
3. **User tests locally** on `dev` branch (`python manage.py runserver`).
4. **Only merge `dev` → `main`** when the user explicitly gives instructions to merge or deploy.
5. **Render auto-deploys** from `main` — merging `dev` → `main` triggers production release.
6. **GitHub Actions CI** runs 118 unit tests on both `push` and `pull_request` to `main`.

### Exact Command Sequence:
```bash
# 1. ALWAYS verify you are on dev before working/committing
git checkout dev

# 2. Make changes and commit to dev
git add .
git commit -m "feat(...): ..."
git push origin dev

# 3. ONLY when the user explicitly instructs to merge/deploy to main:
git checkout main
git merge dev
git push origin main
git checkout dev
```
