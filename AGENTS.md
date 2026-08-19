# AGENTS.md — Memora

> This file is the single source of truth for any AI coding agent (or human) picking up this project. It contains full project context, architecture decisions, and the current codebase state.

---

## 1. Project Purpose

**Memora** — "Your memory, outside your head."

A cross-device personal external memory system. Zero-friction capture for anything worth remembering — quotes, ideas, links, tasks, code snippets, purchase lists, places, people, and more. Everything goes into one app, organized later, found instantly.

**Core philosophy:**
1. **Capture first** — saving takes seconds, no mandatory metadata
2. **Organize later** — categories, tags, collections available but never forced
3. **Find anything** — universal search across all memory fields

Not a notes app, not a to-do app, not a bookmark manager. It's a **personal second brain / memory inbox**.

## 2. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3 / Django 5 | Familiar, batteries-included, fast to ship |
| Interactivity | HTMX | Dynamic search/filter without a JS framework |
| Styling | Tailwind CSS + DaisyUI (CDN) | Premium look without a build step |
| Font | Space Grotesk (Google Fonts) | Modern, geometric, pairs well with glassmorphism |
| DB | PostgreSQL (prod) / SQLite (local dev) | Free-tier Render Postgres |
| Hosting | Render (Web Service + Postgres) | Free tier friendly |
| Static files | WhiteNoise | No CDN/S3 needed for a small personal app |

**Explicitly excluded:** React, Node.js, any heavy frontend JS framework or build pipeline. Tailwind and DaisyUI are loaded via CDN — no npm build step.

## 3. Architecture Decisions

- **Aesthetic: Dark Aurora + Glassmorphism** — aurora blur backgrounds (`filter: blur(120px)` + absolute positioned divs), glass cards with `backdrop-filter: blur(16px)`, gradient accents.
- **Data model evolved** from Quote → Memory with Category, Tag, and Collection models for flexible organization.
- **Smart Capture** uses keyword-based category suggestion (server-side, no ML) — matches content against keyword dictionaries per category and returns the highest-scoring match via a JSON API.
- **Type-aware cards** — memory cards render differently based on category slug: tasks get checkboxes, code gets monospace, links show URLs, thoughts get quote marks, etc.
- **HTMX for all dynamic interactions** — search, pin/archive/status toggling, capture feedback, random memory surfacing.
- **Capture API is CSRF-exempt** by design (external bookmarklet/PWA can't carry a Django CSRF token). Known gap for single-user use.
- **PWA share target** uses `GET` with query params per the Web Share Target API spec.
- **DB config** uses `dj-database-url` — same `settings.py` works on Render and locally.

## 4. File Structure

```
Memora/
├── manage.py
├── requirements.txt
├── .gitignore
├── AGENTS.md
├── quotevault/              # Django project config (kept as quotevault internally)
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── quotes/                  # Main app (kept as quotes internally)
│   ├── __init__.py
│   ├── admin.py
│   ├── models.py            # Memory, Category, Tag, Collection
│   ├── views.py             # Dashboard, capture, search, memory actions, API
│   ├── urls.py
│   ├── management/
│   │   └── commands/
│   │       └── seed_categories.py
│   └── templates/
│       └── quotes/
│           ├── dashboard.html       # Main dashboard with sidebar + capture modal
│           ├── memory_list.html     # Filtered list view (inbox, category, tag, etc.)
│           ├── memory_detail.html   # Single memory detail page
│           ├── capture_form.html    # Full-page capture form
│           ├── random_memory.html   # Random memory page
│           └── partials/
│               ├── memory_card.html      # Type-aware memory card
│               ├── memory_grid.html      # Shared grid of memory cards
│               ├── capture_feedback.html  # Capture success/error feedback
│               └── random_memory.html     # Random memory card partial
├── static/
│   ├── manifest.json
│   ├── bookmarklet.js
│   ├── icon-192.png   (not yet created)
│   └── icon-512.png   (not yet created)
└── venv/                    # Virtual environment (gitignored)
```

## 5. Data Models

### Memory (core model)
- `title` (CharField, optional)
- `content` (TextField, required)
- `category` (FK → Category, optional)
- `tags` (M2M → Tag)
- `collections` (M2M → Collection)
- `source_url`, `source_title`, `author`
- `created_at`, `updated_at`, `due_date`, `reminder_at`
- `status` (inbox/active/done/archived)
- `priority` (none/low/medium/high/urgent)
- `is_pinned`, `is_archived`

### Category
- `name`, `slug`, `emoji`, `color`, `is_default`, `order`
- 15 default categories seeded via management command

### Tag
- `name`, `slug`

### Collection
- `name`, `description`, `created_at`, `updated_at`

## 6. Default Categories

🧠 Thoughts, 💡 Ideas, 📚 Learn, 🔖 Save, 🔗 Links, 🎬 Watch, 📖 Read, 🛒 Buy, ✅ Tasks, 📅 Reminders, ✈️ Places, 💻 Code, 👤 People, 🚀 Projects, ❤️ Important

## 7. URL Routes

| Path | Name | Purpose |
|---|---|---|
| `/` | dashboard | Main dashboard |
| `/search/` | search_memories | HTMX search endpoint |
| `/capture/` | capture | Web capture form (GET/POST) |
| `/api/capture/` | capture_api | JSON capture API (CSRF-exempt) |
| `/api/suggest-category/` | suggest_category | Category suggestion API |
| `/memory/<id>/` | memory_detail | Single memory detail |
| `/memory/<id>/pin/` | memory_pin | Toggle pin |
| `/memory/<id>/archive/` | memory_archive | Toggle archive |
| `/memory/<id>/status/` | memory_status | Update status |
| `/memory/<id>/delete/` | memory_delete | Delete memory |
| `/inbox/` | inbox | Inbox view |
| `/important/` | important | Pinned items |
| `/archive/` | archive | Archived items |
| `/today/` | today | Today's captures |
| `/week/` | week | This week's captures |
| `/category/<slug>/` | category_filter | Filter by category |
| `/tag/<slug>/` | tag_filter | Filter by tag |
| `/random/` | random_memory | Random memory surfacing |
| `/share/` | share_target | PWA Web Share Target |

## 8. Completed Work (Phase 1 — Foundation)

- [x] Memory model with full field set
- [x] Category, Tag, Collection models
- [x] 15 default categories with seed command
- [x] Dashboard with sidebar navigation
- [x] Universal capture modal with smart category suggestion
- [x] HTMX-powered search across all fields
- [x] Type-aware memory cards (different visual per category)
- [x] Filtered views (inbox, category, tag, today, important, archive)
- [x] Memory actions (pin, archive, status change, delete)
- [x] Random memory "Remember This" feature
- [x] Capture API (CSRF-exempt, JSON)
- [x] PWA Web Share Target
- [x] Desktop bookmarklet
- [x] Dark Aurora + Glassmorphism visual design
- [x] Mobile responsive bottom navigation
- [x] Keyboard shortcut (Ctrl+K for capture)

## 9. Pending Tasks

### Phase 2 — Organization
- [ ] Tag management UI (view all tags, rename, merge)
- [ ] Collection management (create, edit, add/remove memories)
- [ ] Bulk actions (select multiple → archive, tag, categorize)
- [ ] Drag-and-drop reordering within collections
- [ ] Edit memory form (inline or modal)

### Phase 3 — Productivity
- [ ] Task completion tracking with statistics
- [ ] Reminder notifications (if possible in PWA)
- [ ] Due date calendar view
- [ ] Status workflow per category type

### Phase 4 — Smart Capture
- [ ] URL metadata extraction (title, description, favicon)
- [ ] Image/screenshot attachment support
- [ ] Automatic title extraction improvements
- [ ] Better bookmarklet with floating UI

### Phase 5 — Memory Features
- [ ] "On this day" — memories from the same date in previous years
- [ ] Recently viewed tracking
- [ ] Smart suggestions based on usage patterns
- [ ] Export (JSON, Markdown)

### Infrastructure
- [ ] Generate real PWA icons (icon-192.png, icon-512.png)
- [ ] Replace bookmarklet domain placeholder
- [ ] Add shared-secret header to capture API
- [ ] Pagination / infinite scroll for large archives
- [ ] Deploy to Render

## 10. Known Gaps

- `/api/capture/` has **no authentication** — acceptable for single-user use.
- Free-tier Render Postgres **expires after 90 days**.
- Dashboard loads all recent memories with no pagination.
- PWA icons not yet generated.
- No edit form for existing memories (must use Django admin).
- Reminder notifications not implemented (model field exists but no scheduling).

## 11. Local Development

```bash
# Setup
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_categories
python manage.py runserver    # Set DEBUG=True env var

# Create superuser for admin
python manage.py createsuperuser
```

## 12. Deployment (Render)

1. Create Postgres instance, copy Internal Database URL.
2. Create Web Service:
   - Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_categories`
   - Start: `gunicorn quotevault.wsgi:application`
3. Env vars: `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL`, `ALLOWED_HOSTS`
