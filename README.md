# 🧠 Memora — Your Memory, Outside Your Head

<p align="center">
  <img src="static/logo.svg" alt="Memora Logo" width="96" height="96">
</p>

<p align="center">
  <strong>Memora</strong> is a cross-device personal external memory system engineered for zero-friction capture.<br>
  Save quotes, ideas, links, tasks, code snippets, cinema lists, places, people, and thoughts in seconds.<br>
  Everything flows into one private glassmorphic vault — effortlessly categorized, instantly resurfaced.
</p>

<p align="center">
  <a href="https://github.com/omtiwari17/Memora/actions"><img src="https://img.shields.io/badge/CI%2FCD-4--Stage%20Pipeline-emerald?style=flat-square&logo=githubactions" alt="CI/CD"></a>
  <a href="https://github.com/omtiwari17/Memora"><img src="https://img.shields.io/badge/Tests-115%20Passed-purple?style=flat-square&logo=django" alt="Tests"></a>
  <a href="https://omtiwari.tech/"><img src="https://img.shields.io/badge/Author-Om%20Tiwari-blue?style=flat-square" alt="Author"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-amber?style=flat-square" alt="License"></a>
</p>

---

## ✨ Core Feature System

### ⚡ Universal Zero-Friction Capture
- **Instant Memory Logging**: Capture thoughts, links, quotes, or code in seconds via top-header capture buttons or quick capture modal.
- **Smart Auto-Categorization (200ms)**: High-confidence regex and keyword matching automatically routes memories to **Code**, **Quotes**, **Links**, **Cinema**, **Tasks**, **Read**, **Buy**, **Places**, and more.
- **Intelligent Auto-Titling**: Client & server title formatting for quotes (`"Phrase..." — Author`), HTML snippets (`<title>` tag extraction), and URLs (domain/path parsing).

### 🎨 Type-Aware Visual Card Layouts
Custom visual rendering engine designed per category:
- **💬 Quotes & 🧠 Thoughts**: Golden serif quotation typography with author attribution.
- **💻 Code Snippets**: Monospace syntax blocks with horizontal scroll.
- **🎬 Cinema & Watch**: Interactive SVG Watch Status pills (*Want to Watch*, *Watching*, *Watched*) and 5-Star Rating bar with glowing CSS hover fill animation.
- **✅ Tasks**: Interactive checkboxes with strike-through completion styling.
- **🔗 Links**: Clickable URL previews with domain icons.
- **✈️ Places**: Location marker formatting.

### 🔐 Niche Vault Security & Private Handles
- **Vault Handle + 6-Digit PIN**: Lightweight, secure authentication without email friction. Users unlock their private vault with a unique handle (e.g. `@om`) and encrypted 6-digit PIN.
- **Unlock / Create Toggle**: Smooth dual-mode login interface for instant registration or vault entry.

### 🛡️ Custom Admin Command Console (`/ctrl/`)
- Dedicated glassmorphic Admin Command Console at hidden route `/ctrl/`.
- Distinct Amber Gold theme with session key protection (`request.session["admin_unlocked"] = True`).
- Dynamic HTMX handle filtering to audit memory feeds across accounts in real time.
- Management CLI integration: `python manage.py create_admin --handle <handle> --pin <pin>`.

### 🚀 Productivity Workspaces & Memory Resurfacing Engine
- **Productivity Workspaces**: Dedicated portals for **Tasks** (`/tasks/`), **Reminders** (`/reminders/`), and **Priority Filtering** (`/priority/`).
- **Memory Resurfacing**: **Remember This** random memory resurfacing (`/random/`), **On This Day** historical memory engine (`/on-this-day/`), and **Recently Viewed** history (`/recently-viewed/`).
- **Universal Capture Everywhere**: Desktop bookmarklet script, PWA Web Share Target (`/share/`), and CSRF-exempt JSON API (`/api/capture/`).

---

## 🛠️ Tech Stack & Architecture

| Layer | Technology | Function |
|---|---|---|
| **Backend** | Python 3.11 / Django 5 | Secure, batteries-included web foundation |
| **Interactivity** | HTMX 1.9 | Dynamic universal search, modal editing, and 0ms inline DOM updates |
| **Styling** | Tailwind CSS + DaisyUI | Dark Aurora ambient background blobs and glassmorphism styling |
| **Typography** | Space Grotesk | Modern geometric Google Font |
| **Database** | SQLite (Dev) / Neon PostgreSQL (Prod) | Scalable PostgreSQL database via `dj-database-url` |
| **Hosting & Asset Handling** | Render + WhiteNoise + cron-job.org | Production WSGI deployment with automated keep-alive orchestration |
| **Testing & CI/CD** | Django TestCase + GitHub Actions | 4-stage pipeline verifying linting, Django checks, 115 unit tests, and deploy readiness |

---

## 📁 Codebase Architecture

```
Memora/
├── manage.py
├── requirements.txt
├── README.md
├── AGENTS.md
├── .github/
│   └── workflows/
│       └── ci.yml           # 4-stage GitHub Actions CI/CD pipeline (115 tests)
├── quotevault/              # Core Django package
│   ├── settings.py          # Production security: HSTS, SSL redirect, secure cookies
│   ├── urls.py
│   └── wsgi.py
├── quotes/                  # Main application package
│   ├── models.py            # Memory, Category, Tag, Collection
│   ├── views.py             # Dashboard, search, capture, API, category CRUD, custom admin
│   ├── tests.py             # 115 automated unit tests
│   ├── urls.py
│   ├── management/
│   │   └── commands/
│   │       ├── seed_categories.py
│   │       └── create_admin.py
│   └── templates/
│       └── quotes/
│           ├── dashboard.html       # Main dashboard with sidebar & developer footer
│           ├── login.html           # Vault login screen with Unlock/Create toggle
│           ├── memory_list.html     # Filtered list view (category, tag, tasks, etc.)
│           ├── admin_dashboard.html # Custom Admin Console at /ctrl/
│           └── partials/
│               ├── memory_card.html # Type-aware memory card partial
│               └── memory_edit_modal.html
└── static/
    ├── manifest.json        # PWA Web Share Target manifest
    ├── bookmarklet.js       # Desktop browser bookmarklet script
    └── logo.svg             # Handcrafted Synapse Infinity M SVG logo
```

---

## 💻 Local Setup Guide

```bash
# 1. Clone repository
git clone https://github.com/omtiwari17/Memora.git
cd Memora

# 2. Configure virtual environment
python -m venv venv
venv\Scripts\activate        # On Windows (or source venv/bin/activate on Linux/Mac)

# 3. Install requirements
pip install -r requirements.txt

# 4. Execute database migrations & seed default categories
python manage.py migrate
python manage.py seed_categories

# 5. Provision admin user account
python manage.py create_admin --handle om --pin 123456

# 6. Launch local server
$env:DEBUG="True"             # PowerShell
python manage.py runserver
```

Access the application at `http://127.0.0.1:8000/`.

---

## 🌐 Production Deployment Guide

Memora is configured for production hosting on Render backed by Neon PostgreSQL:

### Step 1: Database Provisioning (Neon PostgreSQL)
1. Provision a PostgreSQL database instance on **[Neon.tech](https://neon.tech)**.
2. Retrieve the PostgreSQL connection string (`postgres://...`).

### Step 2: Web Service Deployment (Render)
1. Create a new **Web Service** on **[Render.com](https://render.com)** linked to `omtiwari17/Memora`.
2. Set configuration:
   - **Environment**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_categories && python manage.py create_admin
     ```
   - **Start Command**:
     ```bash
     gunicorn quotevault.wsgi:application
     ```
3. Configure environment variables:
   - `DATABASE_URL` = *(Your Neon PostgreSQL connection string)*
   - `SECRET_KEY` = *(Secure secret key string)*
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `*`
   - `ADMIN_HANDLE` = `admin`
   - `ADMIN_PIN` = `123456`

### Step 3: Uptime & Keep-Alive Monitoring (cron-job.org)
To keep the application awake 24/7 without cold starts or redirect errors:
1. Register a ping job on **[cron-job.org](https://cron-job.org)**.
2. Set Target URL to **`https://your-app.onrender.com/healthz/`** *(Note: include `https://` and `/healthz/` to get direct `HTTP 200 OK` with 0 redirects)*.
3. Schedule for **every 10 minutes**.

---

## 👨‍💻 Author & Developer Credits

**Om Tiwari**  
- 🌐 **Portfolio**: [omtiwari.tech](https://omtiwari.tech/)  
- 🐙 **GitHub**: [@omtiwari17](https://github.com/omtiwari17)  
- 💼 **LinkedIn**: [in/tiwariom](https://www.linkedin.com/in/tiwariom/)  

---

## 📜 License

MIT License © 2026 Om Tiwari