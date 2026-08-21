# 🧠 Memora — Your Memory, Outside Your Head

<p align="center">
  <img src="static/logo.svg" alt="Memora Logo" width="100" height="100">
</p>

<p align="center">
  <strong>Memora</strong> is a cross-device personal external memory system built for zero-friction capture.<br>
  Capture quotes, ideas, links, tasks, code snippets, movies, places, people, and thoughts in seconds.<br>
  Everything goes into one beautiful dark-aurora vault — organized effortlessly, found instantly.
</p>

<p align="center">
  <a href="https://github.com/omtiwari17/Memora/actions"><img src="https://img.shields.io/badge/CI%2FCD-4--Stage%20Pipeline-emerald?style=flat-square&logo=githubactions" alt="CI/CD"></a>
  <a href="https://github.com/omtiwari17/Memora"><img src="https://img.shields.io/badge/Tests-115%20Passed-purple?style=flat-square&logo=django" alt="Tests"></a>
  <a href="https://omtiwari.tech/"><img src="https://img.shields.io/badge/Author-Om%20Tiwari-blue?style=flat-square" alt="Author"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-amber?style=flat-square" alt="License"></a>
</p>

---

## ✨ Key Features

### 🎬 Interactive Cinema & Movie Watch Ratings
- **Cinema Category**: Consolidated visual media workspace for movies, TV series, anime, and documentaries.
- **SVG Watch Status Pills**: Instant 0ms status toggles directly on memory cards:
  - 🔖 **`Want to Watch`** (Plan to watch)
  - 🍿 **`Watching`** (Currently watching)
  - 📸 **`Watched`** (Completed)
- **⭐ 5-Star Rating System**: Interactive star rating bar (**`⭐⭐⭐⭐★ 4/5`**) with smooth glowing CSS hover fill animation and instant HTMX save.

### 🔐 Private Vault Security & Niche Authentication
- **Vault Handle + 6-Digit PIN**: Zero email or password friction. Unlock your personal private memory vault using your unique handle (e.g. `@om`) and secure 6-digit PIN.
- **Unlock Vault / Create New Vault**: Seamless mode toggle on login screen for new and returning users.

### 🛡️ Custom Admin Command Console (`/ctrl/`)
- Dedicated glassmorphic Admin Command Console at hidden route `/ctrl/`.
- Amber Gold Command Console theme with session key isolation (`request.session["admin_unlocked"] = True`).
- Dynamic HTMX handle filtering to inspect user activity feeds in real time.
- Management CLI tool: `python manage.py create_admin --handle <handle> --pin <pin>`.

### ⚡ Zero-Friction Capture & Smart Auto-Categorization
- **High-Confidence Auto-Categorization (200ms)**: Real-time pattern & keyword engine automatically classifies notes into **Code**, **Quotes**, **Links**, **Cinema**, **Tasks**, **Read**, **Buy**, **Places**, etc.
- **Smart Auto-Titling**: Client & server title extraction for quotes (`"Phrase..." — Author`), HTML snippets (`<title>`), and URLs.
- **Clean Quick Capture**: Lightning-fast capture modal focused purely on content and title.

### 🎨 Type-Aware Glassmorphic Card Engine
Custom visual card layouts rendered per category:
- **🎬 Cinema / Watch**: SVG Watch Status Pills & 5-Star Rating selector with glowing hover fill animation.
- **💬 Quotes & 🧠 Thoughts**: Warm golden serif quotation typography with author attribution line.
- **💻 Code**: Monospace syntax blocks with horizontal scroll.
- **✅ Tasks**: Interactive checkboxes with strike-through styling.
- **🔗 Links**: Clickable URL previews.
- **✈️ Places**: Location marker styling.

### 🚀 Productivity Workspaces & Memory Resurfacing
- **Productivity**: Dedicated workspaces for **Tasks** (`/tasks/`), **Reminders** (`/reminders/`), and **Priority Levels** (`/priority/`).
- **Resurfacing**: **Remember This** random memory resurfacing (`/random/`), **On This Day** historical resurfacing (`/on-this-day/`), and **Recently Viewed** history (`/recently-viewed/`).

---

## 🛠️ Tech Stack & Architecture

| Layer | Technology | Why |
|---|---|---|
| **Backend** | Python 3.11 / Django 5 | Fast, batteries-included, stable |
| **Interactivity** | HTMX 1.9 | Dynamic search, filtering, and 0ms inline DOM swaps without JS framework overhead |
| **Styling** | Tailwind CSS + DaisyUI | Dark Aurora background blobs & glassmorphism theme via CDN |
| **Typography** | Space Grotesk | Modern geometric Google Font |
| **Database** | SQLite (Dev) / Neon PostgreSQL (Prod) | 100% Free forever PostgreSQL via `dj-database-url` |
| **Hosting & Ping** | Render + cron-job.org | 100% Free production hosting with 24/7 zero cold-start keep-alive |
| **Testing & CI/CD** | Django TestCase (115 tests) + GitHub Actions | 4-stage automated pipeline: Lint → System Check → 115 Tests → Deploy Gate |

---

## 📁 Repository Structure

```
Memora/
├── manage.py
├── requirements.txt
├── README.md
├── AGENTS.md
├── .github/
│   └── workflows/
│       └── ci.yml           # 4-stage GitHub Actions CI/CD pipeline (115 tests)
├── quotevault/              # Django project core
│   ├── settings.py          # Production security: HSTS, SSL redirect, secure cookies
│   ├── urls.py
│   └── wsgi.py
├── quotes/                  # Main memory application
│   ├── models.py            # Memory, Category, Tag, Collection
│   ├── views.py             # Dashboard, search, capture, API, category CRUD, custom admin
│   ├── tests.py             # 115 automated tests (models, auth, views, CRUD, APIs, admin)
│   ├── urls.py
│   ├── management/
│   │   └── commands/
│   │       ├── seed_categories.py
│   │       └── create_admin.py
│   └── templates/
│       └── quotes/
│           ├── dashboard.html       # Dashboard with sidebar & developer footer
│           ├── login.html           # Vault login screen with Unlock/Create toggle
│           ├── memory_list.html     # Filtered list view (category, tag, tasks, etc.)
│           ├── admin_dashboard.html # Custom Admin Console at /ctrl/
│           ├── admin_login.html     # Dedicated Admin Login Portal at /ctrl/login/
│           └── partials/
│               ├── memory_card.html      # Type-aware memory card partial (Watch & Ratings)
│               └── memory_edit_modal.html# HTMX edit modal partial
└── static/
    ├── manifest.json        # PWA Web Share Target manifest
    ├── bookmarklet.js       # Desktop browser bookmarklet script
    └── logo.svg             # Handcrafted Synapse Infinity M SVG logo
```

---

## 💻 Local Development Setup

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

# 5. Create your admin superuser account
python manage.py create_admin --handle om --pin 123456

# 6. Start development server (sets DEBUG=True)
$env:DEBUG="True"             # PowerShell
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser!

---

## 🌐 100% Free Forever Production Deployment Guide

Memora is configured to run **100% free forever** on Render and Neon PostgreSQL without cold starts:

### Step 1: Database Setup (Neon — Free PostgreSQL)
1. Sign up at **[Neon.tech](https://neon.tech)** (100% free PostgreSQL, no credit card required).
2. Create a project `memora-db` and copy the connection string (`postgres://...`).

### Step 2: Web Hosting (Render — Free Web Service)
1. Create a new **Web Service** on **[Render.com](https://render.com)** connected to `omtiwari17/Memora`.
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
   - `SECRET_KEY` = *(Random secret key)*
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `*`
   - `ADMIN_HANDLE` = `admin`
   - `ADMIN_PIN` = `123456`

### Step 3: Prevent Render Sleep (cron-job.org Keep-Alive)
Render free services sleep after 15 minutes of inactivity. To keep your app **online 24/7 with zero cold-start delays**:
1. Register at **[cron-job.org](https://cron-job.org)** (100% free).
2. Create a Cronjob pointing to `https://your-app.onrender.com` every **10 minutes**.
3. Save the job. Your app will stay awake 24/7 for $0/month!

---

## 👨‍💻 Created By

**Om Tiwari**  
- 🌐 **Portfolio**: [omtiwari.tech](https://omtiwari.tech/)  
- 🐙 **GitHub**: [@omtiwari17](https://github.com/omtiwari17)  
- 💼 **LinkedIn**: [in/tiwariom](https://www.linkedin.com/in/tiwariom/)  

---

## 📜 License

MIT License © 2026 Om Tiwari