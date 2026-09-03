# AGENTS.md - Memora

> This file is the single source of truth for any AI coding agent (or human) picking up this project. It contains full project context, architecture decisions, database configurations, deployment instructions, and current codebase state.

---

## 1. Project Purpose

**Memora** - "Your memory, outside your head."

A cross-device personal external memory system. Zero-friction capture for anything worth remembering - quotes, ideas, links, tasks, code snippets, purchase lists, places, people, and more. Everything goes into one app, organized later, found instantly.

**Core Philosophy:**
1. **Capture first** - saving takes seconds, no mandatory metadata
2. **Organize later** - categories, tags, collections available but never forced
3. **Find anything** - universal search across all memory fields

Not a notes app, not a to-do app, not a bookmark manager. It's a **personal second brain / memory inbox**.

---

## 2. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| **Backend** | Python 3.11 / Django 5 | Fast, batteries-included, stable |
| **Interactivity** | HTMX 1.9.12 (Local bundle + CDN fallback) | Dynamic search, filtering, inline actions without JS framework overhead |
| **Styling** | Tailwind CSS + DaisyUI (CDN) | Modern glassmorphism UI with zero build step |
| **Typography** | Space Grotesk (Google Fonts) | Modern, geometric, suits dark glassmorphic UI |
| **Database** | **SQLite** (local dev) / **Neon PostgreSQL** (production) | 100% Free forever PostgreSQL via `dj-database-url` |
| **Hosting** | **Render** (Free Web Service) + **cron-job.org** (Keep-Alive Ping) | 100% Free production hosting, stays awake 24/7 without cold starts |
| **Static Files** | WhiteNoise | Compressed static assets served directly by Django WSGI |
| **CI/CD** | GitHub Actions | 4-stage pipeline: Lint → Django Checks → 135 Tests → Deploy Readiness |
| **Testing** | Django TestCase (135 tests) | Models, auth, views, URLs, CRUD, APIs, custom admin, movie watch ratings, HTMX in-place updates, category uniqueness, data isolation |

**Explicitly Excluded:** React, Node.js, npm build pipelines, heavy SPA frameworks. Tailwind and DaisyUI are loaded directly via CDN.

---

## 3. Architecture Decisions

- **Visual Theme: Dark Aurora + Dot-Grid Canvas + Glassmorphism** - Architectural radial dot-grid canvas (`bg-grid-pattern`), multi-stop animated aurora lighting blobs (`filter: blur(120px)`), frosted glass cards with ambient category glow accents, Space Grotesk typography, and clean vector SVG iconography.
- **Handcrafted Vector SVG Branding: Synapse Infinity M Logo & Favicon** - Pin-sharp, handcrafted vector SVG logo mark (`logo.svg`) featuring an interlocking gradient memory ribbon ('M'), an infinity retention arch, and a central synapse pulse node (`#e879f9`). Served directly for all favicons (`/favicon.ico`), browser tabs, desktop/mobile headers, and login screens with 0ms load time.
- **Niche Authentication: Vault Handle + 6-Digit PIN** - Zero email or password friction. Users register and unlock their personal private memory vault using a unique **Vault Handle** (e.g. `@om`) and a secure **6-Digit PIN** (hashed via Django's PBKDF2). All memories, categories, and collections are strictly user-scoped (`user=request.user`). Login page features a clear **Unlock Vault / Create New Vault** toggle so new users immediately see the registration option.
- **Custom Admin Console (`/ctrl/`)** - Dedicated glassmorphic Admin Command Console at route `/ctrl/` with dedicated login portal (`/ctrl/login/`), session isolation (`request.session["admin_unlocked"] = True`), Amber Gold Command Console visual theme, dynamic HTMX handle filtering, rich empty state card, and management command `create_admin --handle <handle> --pin <pin>`.
- **Interactive Movie / Cinema Watch Status & 5-Star Rating System** - `Memory.watch_status` (`want_to_watch`, `watching`, `watched`) and `Memory.rating` (1-5 stars) with SVG icon watch status pills (`Want to Watch`, `Watching`, `Watched`) and interactive CSS hover fill with glowing spring scale animation (`drop-shadow(0 0 8px rgba(251,191,36,0.9))`) directly on memory cards.
- **Unified Cinema Category & Tag-Based Media** - Consolidated media categories under **Cinema** (`slug: cinema`), organizing movies vs TV series via tags (`#movie`, `#series`, `#anime`, `#documentary`).
- **Developer Profile Links Footer** - Glassmorphic **Created by Om Tiwari** developer badge in left navigation sidebar (`dashboard.html`, `memory_list.html`) and login screen (`login.html`) linking to Portfolio (`https://omtiwari.tech/`), GitHub (`https://github.com/omtiwari17`), and LinkedIn (`https://www.linkedin.com/in/tiwariom/`).
- **Production Security Hardening & CI Guard** - In `quotevault/settings.py`, security flags (`SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS=31536000`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`) activate when `not DEBUG and "test" not in sys.argv:`. This prevents local port redirects during development while ensuring GitHub Actions `--deploy` checks and live production deployments enforce strict HTTPS with zero warnings.
- **CI/CD Safety Net (GitHub Actions)** - 4-stage pipeline runs on every push/PR to `main`: (1) Lint & syntax compile, (2) Django system check + migration integrity, (3) 135-test suite covering models, auth, views, URLs, CRUD, APIs, favicon, admin console, category uniqueness, and user data isolation, (4) Production deploy readiness with Gunicorn startup verification.
- **Executive Header Bar & Compact Metrics** - Eliminated tall marketing hero banners. Dashboard features a streamlined executive top bar with memory total pill (`{{ total_count }}`), live vault status indicator (`@username`), inline stat counters (Inbox, Done, Due Soon), and primary `+ Capture Memory` button (`Ctrl+K`).
- **Fluid Horizontal Navigation Rail with Triple-Action Scroll** - Unified filter tabs and 17 categories into a single, space-efficient horizontal carousel across both `dashboard.html` and `memory_list.html`. Solved the desktop mouse horizontal scrolling limitation with:
  1. **Chevron Arrows**: Floating frosted left (`‹`) and right (`›`) navigation arrows with dynamic boundary detection and gradient edge masks.
  2. **Mouse Wheel Translation**: Standard mouse wheel scrolling over the rail translates vertical wheel motion directly into smooth horizontal scrolling.
  3. **Drag-to-Scroll (Fling)**: Click and drag with grab-hand cursor across the rail.
  4. **Touch & Trackpad**: Full support for native gestures on mobile and laptop trackpads.
- **Refined Borderless Ambient Memory Cards** - Replaced dated `border-l-4` vertical left bars with a modern 1px glass border (`border border-white/[0.08] hover:border-white/[0.18]`) and a delicate 2px top category gradient line matching each category's exact accent color, accompanied by a soft radial top-left aura. Body text contrast upgraded to crisp `white/[0.88]`. Floating action toolbar is accessible on touch/mobile (`opacity-90`) and smoothly transitions on desktop hover.
- **Strict Category Uniqueness & Seeding Integrity** -
  - `category_create`: Validates case-insensitively against all system defaults and the current user's categories (`Q(name__iexact=name) | Q(slug=slug)`). Rejects duplicates with a clear message: `"A category named '<name>' already exists. Category names must be unique."`
  - `category_edit`: Enforces the same uniqueness check, excluding the current category ID.
  - `category_manage.html`: Real-time client-side name check while typing that highlights the input red and disables the Create button if a duplicate name is entered. Also renders dismissible Django `messages` banners.
  - `seed_categories`: Explicitly seeds default categories with `is_default=True` in lookup keys, safely merges memories from any conflicting custom categories into canonical defaults, and deletes redundant duplicate rows.
- **Standardized Typography: En Dash / Hyphen (`-`)** - All instances of the long Em dash (`—`) across page titles, branding footers, quote attributions, and auto-generated titles have been replaced with a clean hyphen / En dash (`-`), while retaining regex pattern support (`[-—–~]`) for pasted quote content.
- **Type-Aware Card Rendering** - Cards render custom visual layouts per category slug:
  - `tasks`: Interactive checkbox with spring scale and strike-through styling
  - `code`: Mac developer terminal window styling (traffic light dots 🔴 🟡 🟢, dark syntax container, dedicated "Copy Code" button)
  - `links`: Clickable URL preview with source link
  - `cinema` / `watch`: SVG Watch Status Pills (`Want to Watch`, `Watching`, `Watched`) & 5-Star Rating selector with glowing hover fill animation
  - `read` / `buy`: Status badges & purchase/read indicators
  - `quotes` / `thoughts`: Warm golden serif quotation typography with author attribution & decorative quotation mark
  - `places`: Map marker styling
- **High-Confidence Auto-Categorization** - Real-time 200ms auto-categorization algorithm in `quotes/views.py` using strict regex pattern matching AND keyword-based dictionary matching:
  - `Code`: HTML tags (`<div`, `<meta`), JS/Python/SQL keywords, CLI commands (regex)
  - `Quotes`: Explicit author attributions on new lines (e.g. `- Benjamin Franklin`) or quoted text with named author (regex)
  - `Links`: HTTP/HTTPS URL detection (regex)
  - `Cinema`, `Watch`, `Read`, `Buy`, `Places`, `Ideas`, `Learn`, `Reminders`, `People`, `Projects`, `Thoughts`, `Important`: Keyword dictionary matching via `CATEGORY_KEYWORDS`
  - `Inbox`: Plain text notes default to Inbox cleanly when no patterns match
- **Smart Auto-Titling (Top-Positioned Inputs)** - Placed Title at the very top above Content in Quick Capture (`capture_modal.html`), Edit Modal (`memory_edit_modal.html`), and Full Capture (`capture_form.html`). Title extraction formats automatically:
  - Quotes: `"`Short phrase..." - Author Name`
  - HTML Snippets: `<title>` tag content extraction
  - URLs: Domain and path extraction
- **Instant HTMX Zero-Reload Architecture** - Native `<form>` reloads eliminated from card actions. Card Pin, Archive, Delete, Task complete, Cinema Watch Status, and 5-Star Ratings execute in-place with `hx-post` and `hx-swap="outerHTML"`. Quick Capture uses Out-of-Band (`hx-swap-oob="afterbegin"`) stream insertion and live stat updates without full-page refreshes.
- **Local HTMX 1.9.12 Bundle with CDN Fallback** - Bundled in `static/htmx.min.js` to guarantee instant script execution without CDN blocking or network delays.
- **Category Reordering System** - Custom ordering endpoint (`/categories/<id>/reorder/<direction>/`) swaps integer sequence values between adjacent categories with live sidebar & dropdown updates.
- **Environment-Aware Sidebar Branding** - Conditionally renders `Memora v5.0 - All 5 Phases Complete 🎉` in development (`DEBUG=True` + `INTERNAL_IPS`) and clean product branding `Memora v5.0 - Personal Vault` in production (`DEBUG=False`).
- **Universal Capture API** - CSRF-exempt JSON endpoint (`/api/capture/`) enabling 1-click capture from desktop bookmarklets and browser extensions.
- **PWA Web Share Target** - Accepts shared links, text, and titles from Android/iOS Web Share API via `/share/` with server-side auto-categorization.

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
│       └── ci.yml           # GitHub Actions CI/CD pipeline (4-stage, 135 tests)
├── quotevault/              # Django project package (quotevault internally)
│   ├── __init__.py
│   ├── settings.py          # Production security: HSTS, SSL redirect, secure cookies
│   ├── urls.py
│   └── wsgi.py
├── quotes/                  # Main memory app (quotes internally)
│   ├── __init__.py
│   ├── admin.py
│   ├── models.py            # Memory, Category, Tag, Collection, PushSubscription
│   ├── views.py             # Dashboard, search, capture, API, category CRUD, custom admin
│   ├── tests.py             # 135 automated tests (models, auth, views, URLs, CRUD, APIs, admin, category uniqueness)
│   ├── urls.py
│   ├── management/
│   │   └── commands/
│   │       ├── seed_categories.py
│   │       └── create_admin.py  # Management command to create/promote admin accounts (--handle, --pin)
│   └── templates/
│       ├── 400.html         # Custom 400 Bad Request error page
│       ├── 403.html         # Custom 403 Permission Denied error page
│       ├── 404.html         # Custom 404 Page Not Found error page
│       ├── 500.html         # Custom 500 Server Error error page
│       └── quotes/
│           ├── landing.html         # Product landing page for unauthenticated visitors
│           ├── dashboard.html       # Main dashboard with executive header, rail, search & memory stream
│           ├── login.html           # Vault login with Unlock/Create toggle + Developer footer
│           ├── memory_list.html     # Filtered list view with navigation rail (inbox, category, tag, tasks, etc.)
│           ├── memory_detail.html   # Single memory detail page with related suggestions
│           ├── category_manage.html # Category manager with CRUD, palette, uniqueness check, reorder
│           ├── admin_dashboard.html # Custom Admin Console with Amber Gold theme & handle filter
│           ├── admin_login.html     # Dedicated Admin Login Portal
│           ├── admin_denied.html    # Custom Admin Access Denied screen
│           ├── capture_form.html    # Full-page capture form
│           ├── health_check.html    # Glassmorphic System Health & Uptime Dashboard
│           ├── random_memory.html   # Random memory page
│           └── partials/
│               ├── memory_card.html      # Type-aware memory card partial (with Watch & Ratings)
│               ├── memory_grid.html      # Shared grid of memory cards with empty state
│               ├── memory_edit_modal.html# Pre-filled edit modal partial with HTMX swap
│               ├── capture_modal.html   # Quick capture modal with live title & auto-category
│               ├── capture_feedback.html # Capture success/error feedback partial with OOB updates
│               ├── admin_memory_feed.html# HTMX admin feed partial with filter & empty state
│               └── random_memory.html    # Random memory card partial
├── static/
│   ├── htmx.min.js          # Vendor-bundled HTMX 1.9.12
│   ├── manifest.json        # PWA Web Share Target manifest
│   ├── bookmarklet.js       # Desktop browser bookmarklet script
│   ├── sw.js                # Service Worker for Web Push & PWA offline caching
│   ├── push_notifications.js# Client Web Push subscription & toast alert engine
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
- `name` (CharField, max_length=100)
- `slug` (SlugField, max_length=100)
- `emoji` (CharField, empty default, vector SVGs used in UI)
- `color` (CharField, hex color for UI)
- `is_default` (BooleanField, default=False)
- `order` (IntegerField, default=0)
- 17 default system categories seeded via `python manage.py seed_categories`
- Strict uniqueness enforced per user across custom and system categories

### Tag
- `name`, `slug`

### Collection
- `name`, `description`, `created_at`, `updated_at`

### PushSubscription
- `user` (FK → User)
- `endpoint` (TextField, unique)
- `p256dh` (TextField)
- `auth` (TextField)
- `created_at` (DateTimeField)

---

## 6. Default Categories

Quotes • Thoughts • Ideas • Learn • Save • Links • Watch • Cinema • Read • Buy • Tasks • Reminders • Places • Code • People • Projects • Important

---

## 7. URL Routes

| Path | Name | Purpose |
|---|---|---|
| `/` | `home_root` / `dashboard` | Product Landing for guests, Vault Dashboard for logged-in users |
| `/login/` | `login` | Vault Handle + 6-Digit PIN unlock and registration screen |
| `/logout/` | `logout` | Lock memory vault session |
| `/favicon.ico` | `favicon` | Vector SVG favicon endpoint serving `logo.svg` directly |
| `/ctrl/` | `custom_admin_panel` | Custom Admin Command Console with handle filtering |
| `/ctrl/login/` | `admin_vault_login` | Dedicated Admin Vault Login Portal |
| `/ctrl/logout/` | `admin_vault_logout` | Admin Logout & session lock |
| `/ctrl/user/<id>/toggle-staff/` | `admin_toggle_staff` | Admin toggle staff status endpoint |
| `/search/` | `search_memories` | HTMX real-time universal search endpoint |
| `/capture/` | `capture` | Quick capture form handler |
| `/api/capture/` | `capture_api` | CSRF-exempt JSON API endpoint for bookmarklet/share |
| `/api/suggest-category/` | `suggest_category` | Category suggestion JSON API |
| `/memory/<id>/` | `memory_detail` | Detailed view for a single memory + smart suggestions |
| `/memory/<id>/edit/` | `memory_edit` | HTMX memory edit modal & POST handler |
| `/memory/<id>/pin/` | `memory_pin` | HTMX toggle pin (in-place) |
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
| `/categories/` | `category_manage` | Full category management dashboard (36-color palette + Suggest Unused Color + Duplicate Warning) |
| `/categories/create/` | `category_create` | Create new category endpoint (strict uniqueness check) |
| `/categories/<id>/edit/` | `category_edit` | Edit category endpoint (strict uniqueness check) |
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

## 8. Completed Work (Phases 1 to 9 Complete)

### Phase 9 - Modern Executive UI, Fluid Category Rail, Strict Uniqueness & Typographic Consistency
- [x] **Executive Header Bar**: Replaced tall marketing hero with an executive top bar featuring live vault status node (`@username`), memory counter pill (`{{ total_count }}`), compact metrics strip (Inbox, Done, Due Soon), and primary `+ Capture Memory` button (`Ctrl+K`).
- [x] **Fluid Horizontal Navigation Rail**: Consolidated multi-tiered filter rows into a single, cohesive horizontal carousel across `dashboard.html` and `memory_list.html`.
- [x] **Triple-Action Horizontal Scrolling Engine**:
  - Floating chevron arrow controls (`‹` and `›`) with edge masks.
  - Automatic mouse wheel translation (vertical scroll rotates horizontal rail smoothly).
  - Mouse click-and-drag (grab/fling) functionality.
  - Native touch/trackpad swipe support.
- [x] **Refined Borderless Ambient Memory Cards**: Replaced thick `border-l-4` with 1px border (`border-white/[0.08]`) and top glowing category color line (`2px`). Typography upgraded to `text-white/[0.88]`. Floating action toolbar accessible on mobile and animated on desktop hover.
- [x] **Strict Category Name & Slug Uniqueness**:
  - Server-side case-insensitive validation against system defaults and user categories on creation and edit.
  - Client-side real-time duplicate check with red border alert and disabled submit button.
  - Dismissible glassmorphic Django `messages` alert banners on `category_manage.html`.
  - Deduplicated `seed_categories` logic with explicit `is_default=True` lookup, merging colliding custom categories into canonical defaults.
- [x] **Top-Positioned Modal Form Titles**: Relocated Title input to the top above Content in Quick Capture, Edit Modal, and Full Capture.
- [x] **Deploy Readiness CI Guard (`quotevault/settings.py`)**: Configured security checks to activate when `not DEBUG and "test" not in sys.argv:`, resolving all 4 CI deploy warnings to zero.
- [x] **Typographic Polish (Em Dash Purge)**: Replaced all occurrences of long Em dashes (`—`) with clean En dashes / hyphens (`-`) across page titles, author attributions, branding text, and auto-titling, while preserving regex matcher sets `[-—–~]` for pasted quote content.
- [x] **Automated Test Suite Expansion**: Expanded suite to **135 tests** covering category uniqueness, edit collision, duplicate prevention, and OOB swaps.

### Phase 8 - Zero-Reload In-Place HTMX Architecture & Performance
- [x] **Zero Full-Page Reloads**: Purged native `<form>` tags from card actions (Pin/Heart, Archive, Delete, Task complete, Cinema Watch Status, and 5-Star Ratings). Converted all to `<button type="button">` with `hx-post`, `hx-vals`, and `hx-target="closest .memory-card"` with `hx-swap="outerHTML"`.
- [x] **Eliminated Modal Capture Reload**: Removed explicit `window.location.reload()` from `capture_modal.html` and implemented Out-of-Band (OOB) insertion (`hx-swap-oob="afterbegin"`) in `capture_feedback.html` targeting `#memory-stream` and `#memory-grid`, accompanied by real-time stat counter updates (`#stat-total-count`, `#stat-inbox-count`, etc.) without page refresh.
- [x] **Local HTMX 1.9.12 Bundle**: Downloaded and vendor-bundled `static/htmx.min.js` with automatic CDN fallback across all templates, guaranteeing HTMX executes reliably without third-party network blocking.
- [x] **Global CSRF Security Headers**: Applied `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` and `htmx:configRequest` token listeners across all templates.
- [x] **Smooth HTMX Micro-Animations**: Injected `.htmx-swapping` and `.htmx-settling` CSS transitions for seamless card exit and entry animations.
- [x] **Elevated Glassmorphic UI & Micro-Interactions**:
  - Ambient radial category top glow on each memory card.
  - 1-Click Clipboard Copy button (`copyCardContent`, `copyDetailText`) with live green checkmark micro-feedback.
  - Redesigned search bar with glowing group focus (`shadow-[0_0_25px_rgba(168,85,247,0.18)]`), quick clear (`×`) button, and keyboard shortcut indicators (`/` to focus).
  - Quick Capture modal with deep frosted backdrop (`backdrop-blur-xl bg-black/80`), `Ctrl+Enter` keyboard submit shortcut, and refined textarea focus styling.

### Phase 7 - Native Web Push & Real-Time Reminders
- [x] Native PWA Web Push & Service Worker Notification System (`sw.js`, `push_notifications.js`, VAPID key pair generation, `PushSubscription` model).
- [x] In-App Glassmorphic Toast Notifications & 60s Due Reminder Poll Checker (`/api/due-reminders/`).
- [x] `static/logo.svg` standardized as 100% single source of truth global logo across all headers, sidebars, footers, login screens, and error pages.
- [x] Username profile badge cleaned (no `@` prefix, uppercase initial avatar) with vector Sign Out exit icon.
- [x] Toast banner with direct "✓ Mark Done" action and live test notification utility in sidebar.

### Phases 1 to 6 - Core Capabilities
- [x] Memory, Category, Tag, Collection models implemented
- [x] 17 default categories seeded with custom colors
- [x] Niche Vault Handle + 6-Digit PIN authentication system (`login.html`, `vault_login`, `vault_logout`, user-scoped data filtering)
- [x] Login page **Unlock Vault / Create New Vault** toggle UX
- [x] Handcrafted Synapse Infinity M vector SVG branding & favicon system (`logo.svg`, `/favicon.ico` endpoint)
- [x] Custom Admin Console at `/ctrl/` with dedicated login portal `/ctrl/login/`, Amber Gold theme, handle filter & empty state
- [x] Management command `python manage.py create_admin --handle <handle> --pin <pin>`
- [x] Interactive Movie / Cinema Watch Status pills & 5-Star Rating selector with glowing CSS hover fill animation
- [x] Developer Profile Links Footer ("Created by Om Tiwari" linking to Portfolio, GitHub, and LinkedIn)
- [x] 100% Emoji Purge across entire database & templates replaced with crisp Heroicons SVG icons
- [x] Full Category Management suite (Create, Edit, Delete with Inbox fallback, 36-color preset palette, in-use `✓` checkmark swatches, Up/Down reordering, and **`Suggest Unused Color`** generator)
- [x] User-scoped tag autocomplete & click-to-add suggestion chips
- [x] Dedicated unauthenticated `/healthz/` and `/ping/` uptime monitoring endpoints returning direct `HTTP 200 OK` (0 redirects)
- [x] Glassmorphic System Health & Uptime Dashboard front-end page (`health_check.html`)
- [x] 100% full-width aligned search bar flush with statistics cards and memory cards
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
- [x] GitHub Actions CI/CD pipeline (4-stage, 135 tests, deploy readiness gatekeeper)
- [x] Production security hardening (HSTS, SSL redirect, secure cookies, CSRF - 0 deploy warnings)
- [x] Full secret audit - zero sensitive data in Git history or tracked files
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

# 5. Start dev server (sets DEBUG=True by default locally)
python manage.py runserver 8001
```

---

## 10. 100% Free Forever Production Deployment Guide

Memora is configured to run **100% free forever** without paying for database or hosting subscriptions, and without Render going to sleep:

### Step 1: Database Setup (Neon - Free PostgreSQL)
1. Register at **[Neon.tech](https://neon.tech)** (100% free PostgreSQL, no credit card required).
2. Create a project `memora-db` and copy the **Connection String** (`postgres://...`).

### Step 2: Web Hosting (Render - Free Web Service)
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

### Step 3: Prevent Render Sleep (cron-job.org - Free 24/7 Keep-Alive)
Render's free tier puts web services to sleep after 15 minutes of inactivity. To keep your app **awake 24/7 with zero loading delays**:
1. Register at **[cron-job.org](https://cron-job.org)** (100% free).
2. Click **+ CREATE CRONJOB**:
   - **Title**: `Memora Keep Alive`
   - **URL**: `https://your-app.onrender.com/healthz/` *(Must include `https://` and `/healthz/` to return HTTP 200 OK directly with 0 redirects)*
   - **Schedule**: `Every 10 minutes`
3. Save the job. Your app will now stay online 24/7 with **0-second cold starts** for $0/month!

---

## 11. Implementation Roadmap & Milestones

### Phase 1 - Foundation
- [x] Rename Quote → Memory
- [x] Generic capture
- [x] Inbox
- [x] Categories
- [x] Universal search
- [x] Recent memories

### Phase 2 - Organization
- [x] Tags
- [x] Collections
- [x] Pinning
- [x] Archive
- [x] Filters

### Phase 3 - Productivity
- [x] Tasks
- [x] Reminders
- [x] Due dates
- [x] Statuses

### Phase 4 - Smart Capture
- [x] Automatic category suggestions
- [x] Automatic title extraction
- [x] URL metadata
- [x] Better browser/mobile capture

### Phase 5 - Memory Features
- [x] Random memory
- [x] Resurfacing
- [x] Recently viewed
- [x] "On this day"
- [x] Smart suggestions

### Phase 6 - Production & CI/CD
- [x] Custom Admin Console at `/ctrl/`
- [x] Interactive Movie Watch Status & 5-Star Rating System
- [x] Developer Profile Links Footer
- [x] GitHub Actions CI/CD pipeline (135 tests)
- [x] Production security hardening (0 deploy warnings)
- [x] Secret audit (0 leaks in Git history)
- [x] Live deployment (Neon + Render + cron-job.org)
- [x] Login UX toggle (Unlock / Create New Vault)

### Phase 7 - Native Web Push & Notifications
- [x] Service Worker setup (`sw.js`) and PWA integration
- [x] VAPID Key Generation & PushManager Subscription
- [x] In-App Glassmorphic Toast Alerts with "✓ Mark Done" action
- [x] Due reminder API & 60s polling check
- [x] OS System Push Notifications via `navigator.serviceWorker.ready`
- [x] `sessionStorage` notification spam protection
- [x] 1-Click OS Banner Permission Trigger
- [x] Dedicated "Test Notification Live ⚡" sidebar utility

### Phase 8 - Zero-Reload In-Place HTMX Architecture & Performance
- [x] In-place card actions with 0 full-page reloads
- [x] Quick Capture modal OOB stream insertion with live stat badges
- [x] Local vendor HTMX 1.9.12 bundle with automatic CDN fallback
- [x] Global CSRF request interception and security headers
- [x] Elevated glassmorphic UI, copy buttons, and micro-animations

### Phase 9 - Modern Executive UI, Fluid Category Rail, Strict Uniqueness & Typographic Consistency
- [x] Compact executive header bar and inline metrics strip
- [x] Fluid horizontal navigation rail across dashboard and list views
- [x] Triple-action category rail scroll: chevron buttons, mouse wheel translation, and drag-to-scroll
- [x] Refined borderless ambient cards with 2px category top glow
- [x] Strict category name & slug uniqueness on client and server
- [x] Deduplicated seed_categories with canonical default category recovery
- [x] Repositioned title input to the top in all capture and edit modals
- [x] Resolved CI deployment warnings in `quotevault/settings.py` (0 warnings)
- [x] Universal typographic standardization from Em dashes (`—`) to En dashes / hyphens (`-`)
- [x] 135 automated unit and integration tests passing cleanly

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
1. **NEVER commit on `main`** - switch to `dev` before creating any commit (`git checkout dev`).
2. **All new features, fixes, and changes** → commit exclusively to `dev` branch.
3. **User tests locally** on `dev` branch (`python manage.py runserver 8001`).
4. **Only merge `dev` → `main`** when the user explicitly gives instructions to merge or deploy.
5. **Render auto-deploys** from `main` - merging `dev` → `main` triggers production release.
6. **GitHub Actions CI** runs 135 unit tests on both `push` and `pull_request` to `main`.

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
