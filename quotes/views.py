import json
import re
from datetime import timedelta

from django.http import JsonResponse, HttpResponseBadRequest, FileResponse
from django.conf import settings
from django.urls import reverse
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Memory, Category, Tag, Collection, PushSubscription


# ── Category suggestion (pattern + keyword matching) ──────────────────────
CODE_PATTERNS = [
    r"<[a-zA-Z0-9]+[^>]*>",           # HTML/XML opening tags (<meta, <div, <head)
    r"</[a-zA-Z0-9]+>",              # HTML closing tags (</div>, </head>)
    r"<!DOCTYPE\s+html>",            # HTML doctype
    r"\b(const|let|var|function|async|await)\b",  # JavaScript / JS keywords
    r"\b(def|import|from|self|elif)\b",           # Python keywords
    r"\b(public|private|protected|class|void|int|string|boolean)\b", # Java/C#/C++
    r"(console\.log|print\(|System\.out\.println)", # Print statements
    r"(git\s+commit|git\s+push|git\s+checkout|npm\s+install|pip\s+install|docker\s+run|sudo\s+apt)", # CLI
    r"[\{\}\[\];]\s*$",              # Code lines ending with semicolon or brackets
    r"=>|\$env:|\$\(document\)"      # Arrow functions & shell variables
]

CATEGORY_KEYWORDS = {
    "cinema": ["movie", "film", "cinema", "show", "series", "tv show", "web series", "netflix", "imdb", "boxoffice", "season", "episode", "anime"],
    "watch": ["watch", "youtube", "video", "documentary", "stream"],
    "read": ["read", "book", "article", "paper", "blog", "novel", "manga", "ebook"],
    "buy": ["buy", "purchase", "order", "price", "cost", "shopping", "amazon", "flipkart", "deal"],
    "tasks": ["todo", "to-do", "task", "need to", "should", "must", "finish", "complete", "submit", "deadline"],
    "reminders": ["remind", "remember to", "don't forget", "dont forget", "appointment", "meeting", "schedule"],
    "learn": ["learn", "study", "understand", "how to", "tutorial", "course", "lesson", "concept", "explain"],
    "ideas": ["idea", "what if", "build", "create", "make a", "app that", "website that", "project", "startup"],
    "code": ["code", "command", "snippet", "function", "script", "api", "git", "npm", "pip", "sudo", "terminal", "debug", "html", "css", "js", "sql"],
    "links": ["http://", "https://", "www.", "website", "link", "url", "resource"],
    "places": ["visit", "travel", "restaurant", "hotel", "cafe", "place", "destination", "trip", "location"],
    "people": ["person", "contact", "met", "talked to", "called", "phone number", "email"],
    "projects": ["project", "roadmap", "milestone", "sprint", "feature", "requirement"],
    "thoughts": ["thinking", "thought", "feel", "feeling", "wonder", "maybe", "perhaps", "opinion"],
    "important": ["important", "critical", "urgent", "crucial", "vital", "essential", "never forget"],
}


QUOTE_PATTERNS = [
    r'^["“].+["”]\s*([\n\r]|\s+[-—–~])',
    r'[\n\r]\s*[-—–~]\s*[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}',
    r'\b(famous quote|quote by|quote of the day)\b',
]


def suggest_category(text):
    """High-confidence smart category suggestion."""
    if not text or len(text.strip()) < 5:
        return None

    clean = text.strip()
    lower_text = clean.lower()

    for pattern in CODE_PATTERNS:
        if re.search(pattern, clean, re.MULTILINE):
            return "code"

    for pattern in QUOTE_PATTERNS:
        if re.search(pattern, clean, re.MULTILINE):
            return "quotes"

    if re.search(r"https?://", lower_text):
        return "links"

    for slug, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', lower_text):
                return slug

    return "inbox"


def extract_title(text):
    """Auto-generate a title from memory content."""
    clean = text.strip()
    author_match = re.search(r'[\n\r\s]+[-—–~]\s*([A-Z][a-zA-Z\s\.]+)', clean)
    quote_text = re.sub(r'[\n\r\s]+[-—–~].*$', '', clean).strip()
    quote_text = re.sub(r'^[“"\'\`\s]+|[”"\'\`\s]+$', '', quote_text)

    if author_match and quote_text:
        author_name = author_match.group(1).strip()
        words = quote_text.split()
        short_quote = " ".join(words[:5]) + "..." if len(words) > 5 else quote_text
        return f'"{short_quote}" — {author_name}'

    if clean.startswith("<") and ">" in clean:
        tag_title = re.search(r'<title[^>]*>(.*?)</title>', clean, re.IGNORECASE)
        if tag_title:
            return tag_title.group(1).strip()

    if clean.startswith("http://") or clean.startswith("https://"):
        parts = clean.split("/")
        domain = parts[2] if len(parts) > 2 else clean
        return domain.replace("www.", "")

    first_line = clean.split("\n")[0].strip()
    first_line = re.sub(r'^[“"\'\`\s\-*\d\.]+', '', first_line)
    first_line = re.sub(r'[”"\'\`\s]+$', '', first_line).strip()

    if not first_line:
        first_line = clean[:80]

    words = first_line.split()
    if len(words) > 8:
        return " ".join(words[:8]) + "..."
    return first_line


def get_user_categories(user):
    """Return categories accessible by user."""
    return Category.objects.filter(Q(is_default=True) | Q(user=user)).order_by("order", "name")


# ── Custom Error Handlers ─────────────────────────────────────────────
def custom_404_view(request, exception=None, *args, **kwargs):
    """Custom glassmorphic 404 Page Not Found error view."""
    return render(request, "404.html", status=404)


def custom_500_view(request):
    """Custom glassmorphic 500 Internal Server Error view."""
    return render(request, "500.html", status=500)


def custom_403_view(request, exception=None):
    """Custom glassmorphic 403 Permission Denied error view."""
    return render(request, "403.html", status=403)


def custom_400_view(request, exception=None):
    """Custom glassmorphic 400 Bad Request error view."""
    return render(request, "400.html", status=400)


# ── Authentication (Vault Handle + 6-Digit PIN) ──────────────────────
def home_root(request):
    """Home Root / handler — Serves the Product Landing Page for unauthenticated visitors, or redirects authenticated users to their Vault Dashboard."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "quotes/landing.html")


def landing_page(request):
    """Product Landing Page for Memora — Showcase features, design, and vault entry."""
    return render(request, "quotes/landing.html")


def health_check(request):
    """Health check endpoint — returns JSON for API/cron pings or a glassmorphic UI for browser visits."""
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({"status": "ok", "app": "Memora", "service": "awake"}, status=200)
    
    return render(request, "quotes/health_check.html", {
        "status": "operational",
        "app_name": "Memora",
    }, status=200)


def vault_login(request):
    """Unlock or create a personal memory vault with Vault Handle + 6-Digit PIN."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    error = None
    handle = ""

    if request.method == "POST":
        raw_handle = request.POST.get("handle", "").strip().lower().replace("@", "")
        pin = request.POST.get("pin", "").strip()

        handle = re.sub(r'[^a-z0-9_]', '', raw_handle)

        if not handle or len(handle) < 2:
            error = "Vault handle must be at least 2 characters long (letters/numbers)."
        elif not pin.isdigit() or len(pin) != 6:
            error = "PIN must be exactly a 6-digit number (e.g. 123456)."
        else:
            user = User.objects.filter(username=handle).first()
            if user:
                authenticated_user = authenticate(request, username=handle, password=pin)
                if authenticated_user:
                    login(request, authenticated_user)
                    return redirect("dashboard")
                else:
                    error = f"Incorrect 6-digit PIN for @{handle}. Please try again."
            else:
                user = User.objects.create_user(username=handle, password=pin)
                # Claim unassigned memories in fresh DB if any
                Memory.objects.filter(user=None).update(user=user)
                Category.objects.filter(user=None, is_default=False).update(user=user)
                Collection.objects.filter(user=None).update(user=user)
                
                login(request, user)
                return redirect("dashboard")

    return render(request, "quotes/login.html", {"error": error, "handle": handle})


def vault_logout(request):
    """Lock current memory vault."""
    logout(request)
    return redirect("login")


# ── Dashboard ──────────────────────────────────────────────────────────
@login_required(login_url="login")
def dashboard(request):
    """Main dashboard — shows recent memories, pinned items, upcoming."""
    categories = get_user_categories(request.user)
    user_memories = Memory.objects.filter(user=request.user, is_archived=False)

    total_count = user_memories.count()
    inbox_count = user_memories.filter(status=Memory.Status.INBOX).count()
    tasks_done = user_memories.filter(status=Memory.Status.DONE).count()
    due_soon = user_memories.filter(due_date__isnull=False, due_date__gte=timezone.now()).count()

    pinned = user_memories.filter(is_pinned=True)[:6]
    recent = user_memories[:12]
    
    upcoming = user_memories.filter(
        due_date__isnull=False,
        due_date__gte=timezone.now()
    ).order_by("due_date")[:5]

    all_tags = Tag.objects.filter(memories__user=request.user).distinct().order_by("name")

    return render(request, "quotes/dashboard.html", {
        "categories": categories,
        "all_tags": all_tags,
        "total_count": total_count,
        "inbox_count": inbox_count,
        "tasks_done": tasks_done,
        "due_soon": due_soon,
        "pinned": pinned,
        "recent": recent,
        "upcoming": upcoming,
    })


# ── Memory list (filtered by category, tag, collection, status) ───────
@login_required(login_url="login")
def memory_list(request, filter_type=None, filter_value=None):
    """Filtered memory list view."""
    memories = Memory.objects.filter(user=request.user, is_archived=False)
    title = "All Memories"
    active_filter = filter_type

    if filter_type == "category":
        category = get_object_or_404(Category, slug=filter_value)
        memories = memories.filter(category=category)
        title = category.name
    elif filter_type == "tag":
        tag = get_object_or_404(Tag, slug=filter_value)
        memories = memories.filter(tags=tag)
        title = f"#{tag.name}"
    elif filter_type == "collection":
        collection = get_object_or_404(Collection, pk=filter_value, user=request.user)
        memories = memories.filter(collections=collection)
        title = collection.name
    elif filter_type == "inbox":
        memories = memories.filter(status=Memory.Status.INBOX)
        title = "Inbox"
    elif filter_type == "important":
        memories = memories.filter(is_pinned=True)
        title = "Important"
    elif filter_type == "archive":
        memories = Memory.objects.filter(user=request.user, is_archived=True)
        title = "Archive"
    elif filter_type == "today":
        today = timezone.now().date()
        memories = memories.filter(created_at__date=today)
        title = "Today"
    elif filter_type == "week":
        week_ago = timezone.now() - timedelta(days=7)
        memories = memories.filter(created_at__gte=week_ago)
        title = "This Week"
    elif filter_type == "tasks":
        category = Category.objects.filter(slug="tasks").first()
        if category:
            memories = memories.filter(category=category)
        title = "Tasks Workspace"
    elif filter_type == "reminders":
        memories = memories.filter(due_date__isnull=False).order_by("due_date")
        title = "Reminders & Timeline"
    elif filter_type == "priority":
        memories = memories.filter(priority=filter_value)
        title = f"Priority: {filter_value.capitalize()}"
    elif filter_type == "on_this_day":
        today = timezone.now()
        memories = memories.filter(
            created_at__month=today.month,
            created_at__day=today.day
        ).exclude(created_at__year=today.year)
        title = "On This Day"

    categories = get_user_categories(request.user)
    inbox_count = Memory.objects.filter(user=request.user, status=Memory.Status.INBOX, is_archived=False).count()
    all_tags = Tag.objects.filter(memories__user=request.user).distinct().order_by("name")

    return render(request, "quotes/memory_list.html", {
        "memories": memories,
        "title": title,
        "categories": categories,
        "all_tags": all_tags,
        "inbox_count": inbox_count,
        "active_filter": active_filter,
        "filter_value": filter_value,
    })


# ── Search ─────────────────────────────────────────────────────────────
@login_required(login_url="login")
def search_memories(request):
    """HTMX search handler."""
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()

    memories = Memory.objects.filter(user=request.user, is_archived=False)

    if category_slug:
        memories = memories.filter(category__slug=category_slug)

    if query:
        memories = memories.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(author__icontains=query) |
            Q(tags__name__icontains=query) |
            Q(source_url__icontains=query)
        ).distinct()

    return render(request, "quotes/partials/memory_grid.html", {
        "memories": memories[:30],
        "query": query,
    })


# ── Memory Detail ──────────────────────────────────────────────────────
@login_required(login_url="login")
def memory_detail(request, pk):
    """Individual memory detail view with smart related suggestions."""
    memory = get_object_or_404(Memory, pk=pk, user=request.user)

    viewed_ids = request.session.get("recently_viewed", [])
    if pk in viewed_ids:
        viewed_ids.remove(pk)
    viewed_ids.insert(0, pk)
    request.session["recently_viewed"] = viewed_ids[:20]

    suggestions = Memory.objects.filter(
        user=request.user,
        is_archived=False
    ).exclude(pk=memory.pk)

    if memory.category:
        suggestions = suggestions.filter(category=memory.category)

    suggestions = suggestions[:3]

    return render(request, "quotes/memory_detail.html", {
        "memory": memory,
        "suggestions": suggestions,
    })


# ── Memory Edit Modal & Save ───────────────────────────────────────────
@login_required(login_url="login")
def memory_edit(request, pk):
    """HTMX endpoint to render edit modal (GET) or update memory (POST)."""
    memory = get_object_or_404(Memory, pk=pk, user=request.user)

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if not content:
            return HttpResponseBadRequest("Content cannot be empty.")

        title = request.POST.get("title", "").strip()
        category_slug = request.POST.get("category", "").strip()
        tags_str = request.POST.get("tags", "").strip()
        source_url = request.POST.get("source_url", "").strip()
        author = request.POST.get("author", "").strip()
        priority = request.POST.get("priority", "none").strip()
        status = request.POST.get("status", "inbox").strip()
        due_date_str = request.POST.get("due_date", "").strip()

        memory.content = content
        watch_status = request.POST.get("watch_status", "want_to_watch").strip()
        rating_val = request.POST.get("rating", "").strip()
        rating = int(rating_val) if rating_val.isdigit() and 1 <= int(rating_val) <= 5 else None

        memory.title = title or extract_title(content)
        memory.source_url = source_url
        memory.author = author
        memory.priority = priority
        memory.status = status
        if watch_status in Memory.WatchStatus.values:
            memory.watch_status = watch_status
        memory.rating = rating

        if category_slug:
            category = Category.objects.filter(slug=category_slug).first()
            memory.category = category
        else:
            memory.category = None

        if due_date_str:
            try:
                memory.due_date = timezone.datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                pass
        else:
            memory.due_date = None

        memory.save()

        memory.tags.clear()
        if tags_str:
            tag_names = [t.strip() for t in tags_str.split(",") if t.strip()]
            for name in tag_names:
                slug = name.lower().replace(" ", "-")
                tag, _ = Tag.objects.get_or_create(slug=slug, defaults={"name": name})
                memory.tags.add(tag)

        return render(request, "quotes/partials/memory_card.html", {"memory": memory})

    categories = get_user_categories(request.user)
    tags_str = ", ".join(t.name for t in memory.tags.all())
    all_tags = Tag.objects.filter(memories__user=request.user).distinct().order_by("name")

    return render(request, "quotes/partials/memory_edit_modal.html", {
        "memory": memory,
        "categories": categories,
        "tags_str": tags_str,
        "all_tags": all_tags,
    })


# ── Quick Capture ──────────────────────────────────────────────────────
@login_required(login_url="login")
def capture(request):
    """Handle memory creation (from modal or standalone capture page)."""
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if not content:
            return render(request, "quotes/partials/capture_feedback.html", {
                "success": False,
                "error": "Content cannot be empty."
            })

        title = request.POST.get("title", "").strip()
        category_slug = request.POST.get("category", "").strip()
        tags_str = request.POST.get("tags", "").strip()
        source_url = request.POST.get("source_url", "").strip()
        author = request.POST.get("author", "").strip()
        priority = request.POST.get("priority", "none").strip()
        due_date_str = request.POST.get("due_date", "").strip()
        watch_status = request.POST.get("watch_status", "want_to_watch").strip()
        rating_val = request.POST.get("rating", "").strip()
        rating = int(rating_val) if rating_val.isdigit() and 1 <= int(rating_val) <= 5 else None

        if not category_slug:
            category_slug = suggest_category(content) or "inbox"

        category = None
        if category_slug:
            category = Category.objects.filter(slug=category_slug).first()

        if not title:
            title = extract_title(content)

        due_date = None
        if due_date_str:
            try:
                due_date = timezone.datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                pass

        memory = Memory.objects.create(
            user=request.user,
            title=title,
            content=content,
            category=category,
            source_url=source_url,
            author=author,
            priority=priority,
            due_date=due_date,
            watch_status=watch_status if watch_status in Memory.WatchStatus.values else Memory.WatchStatus.WANT_TO_WATCH,
            rating=rating,
            status=Memory.Status.INBOX if not category or category.slug == "inbox" else Memory.Status.ACTIVE
        )

        if tags_str:
            tag_names = [t.strip() for t in tags_str.split(",") if t.strip()]
            for name in tag_names:
                slug = name.lower().replace(" ", "-")
                tag, _ = Tag.objects.get_or_create(slug=slug, defaults={"name": name})
                memory.tags.add(tag)

        if request.headers.get("HX-Request"):
            return render(request, "quotes/partials/capture_feedback.html", {
                "success": True,
                "memory": memory,
            })

        return redirect("dashboard")

    categories = get_user_categories(request.user)
    return render(request, "quotes/capture_form.html", {"categories": categories})


@login_required(login_url="login")
@require_http_methods(["POST"])
def memory_watch_status(request, pk):
    """HTMX endpoint to update movie watch_status and rating."""
    memory = get_object_or_404(Memory, pk=pk, user=request.user)

    new_watch_status = request.POST.get("watch_status", "").strip()
    if new_watch_status in Memory.WatchStatus.values:
        memory.watch_status = new_watch_status

    rating_str = request.POST.get("rating", "").strip()
    if rating_str.isdigit():
        r = int(rating_str)
        if 1 <= r <= 5:
            memory.rating = r

    memory.save()
    return render(request, "quotes/partials/memory_card.html", {"memory": memory})


# ── Universal Capture API (for extension/bookmarklet) ──────────────────
@csrf_exempt
def capture_api(request):
    """CSRF-exempt JSON endpoint for browser extensions and bookmarklets."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    content = data.get("content", "").strip()
    if not content:
        return JsonResponse({"error": "Content is required"}, status=400)

    user = request.user if request.user.is_authenticated else User.objects.first()

    title = data.get("title", "").strip() or extract_title(content)
    source_url = data.get("url", "").strip() or data.get("source_url", "").strip()
    category_slug = data.get("category", "").strip() or suggest_category(content)

    category = None
    if category_slug:
        category = Category.objects.filter(slug=category_slug).first()

    memory = Memory.objects.create(
        user=user,
        title=title,
        content=content,
        category=category,
        source_url=source_url,
        status=Memory.Status.INBOX
    )

    tags_str = data.get("tags", "")
    if tags_str:
        tag_names = [t.strip() for t in tags_str.split(",") if t.strip()]
        for name in tag_names:
            slug = name.lower().replace(" ", "-")
            tag, _ = Tag.objects.get_or_create(slug=slug, defaults={"name": name})
            memory.tags.add(tag)

    return JsonResponse({
        "success": True,
        "memory_id": memory.id,
        "title": memory.title,
        "category": category.name if category else "Inbox",
    }, status=201)


def suggest_category_api(request):
    """Return a category suggestion based on content text."""
    content = request.GET.get("content", "").strip()
    if not content:
        return JsonResponse({"suggestion": None})

    slug = suggest_category(content)
    if slug:
        category = Category.objects.filter(slug=slug).first()
        if category:
            return JsonResponse({
                "suggestion": {
                    "slug": category.slug,
                    "name": category.name,
                    "color": category.color,
                }
            })
    return JsonResponse({"suggestion": None})


# ── HTMX Toggle Pin / Archive / Status / Delete ───────────────────────
@login_required(login_url="login")
@require_http_methods(["POST"])
def memory_pin(request, pk):
    """Toggle memory pinned state."""
    memory = get_object_or_404(Memory, pk=pk, user=request.user)
    memory.is_pinned = not memory.is_pinned
    memory.save()
    return render(request, "quotes/partials/memory_card.html", {"memory": memory})


@login_required(login_url="login")
@require_http_methods(["POST"])
def memory_archive(request, pk):
    """Toggle memory archived state with instant HTMX removal."""
    memory = get_object_or_404(Memory, pk=pk, user=request.user)
    memory.is_archived = not memory.is_archived
    memory.save()

    if request.headers.get("HX-Request"):
        from django.http import HttpResponse
        return HttpResponse("")

    return render(request, "quotes/partials/memory_card.html", {"memory": memory})


@login_required(login_url="login")
@require_http_methods(["POST"])
def memory_status(request, pk):
    """Update memory status (e.g., done/active)."""
    memory = get_object_or_404(Memory, pk=pk, user=request.user)
    new_status = request.POST.get("status", "")
    if new_status in Memory.Status.values:
        memory.status = new_status
        memory.save()
    return render(request, "quotes/partials/memory_card.html", {"memory": memory})


@login_required(login_url="login")
@require_http_methods(["POST"])
def memory_delete(request, pk):
    """Delete a memory with instant HTMX removal."""
    memory = get_object_or_404(Memory, pk=pk, user=request.user)
    memory.delete()

    if request.headers.get("HX-Request"):
        from django.http import HttpResponse
        return HttpResponse("")

    return redirect("dashboard")


# ── Memory Resurfacing ────────────────────────────────────────────────
@login_required(login_url="login")
def random_memory(request):
    """Resurface a random past memory."""
    memories = list(Memory.objects.filter(user=request.user, is_archived=False))
    chosen = None
    if memories:
        import random as rnd
        chosen = rnd.choice(memories)

    if request.headers.get("HX-Request"):
        return render(request, "quotes/partials/random_memory.html", {"memory": chosen})

    return render(request, "quotes/random_memory.html", {"memory": chosen})


@login_required(login_url="login")
def recently_viewed(request):
    """Show memories recently viewed in this session."""
    viewed_ids = request.session.get("recently_viewed", [])
    memories = Memory.objects.filter(user=request.user, pk__in=viewed_ids)

    memories_dict = {m.pk: m for m in memories}
    ordered = [memories_dict[pk] for pk in viewed_ids if pk in memories_dict]

    categories = get_user_categories(request.user)
    inbox_count = Memory.objects.filter(user=request.user, status=Memory.Status.INBOX, is_archived=False).count()

    return render(request, "quotes/memory_list.html", {
        "memories": ordered,
        "title": "Recently Viewed",
        "categories": categories,
        "inbox_count": inbox_count,
        "active_filter": "recently_viewed",
    })


# ── Category Management ───────────────────────────────────────────────
PRESET_PALETTE = [
    ("#a78bfa", "Purple"),
    ("#818cf8", "Indigo"),
    ("#38bdf8", "Sky Blue"),
    ("#34d399", "Emerald"),
    ("#fbbf24", "Amber"),
    ("#f87171", "Rose Red"),
    ("#f472b6", "Pink"),
    ("#e879f9", "Fuchsia"),
    ("#2dd4bf", "Teal"),
    ("#60a5fa", "Blue"),
    ("#a3e635", "Lime"),
    ("#fb923c", "Orange"),
    ("#c084fc", "Violet"),
    ("#4ade80", "Green"),
    ("#f43f5e", "Crimson"),
    ("#06b6d4", "Cyan"),
    ("#ec4899", "Hot Pink"),
    ("#8b5cf6", "Deep Purple"),
    ("#14b8a6", "Mint Teal"),
    ("#f59e0b", "Gold"),
    ("#ff6b6b", "Coral Red"),
    ("#48dbfb", "Bright Cyan"),
    ("#1dd1a1", "Jade Green"),
    ("#fabca1", "Peach"),
    ("#ff9ff3", "Soft Lavender"),
    ("#54a0ff", "Cerulean Blue"),
    ("#5f27cd", "Electric Violet"),
    ("#c8d6e5", "Cool Silver"),
    ("#576574", "Slate Gray"),
    ("#ee5253", "Sunset Red"),
    ("#00d2d3", "Aquamarine"),
    ("#ff9f43", "Tangerine"),
    ("#10b981", "Emerald Green"),
    ("#6366f1", "Indigo Blue"),
    ("#d946ef", "Magenta"),
    ("#f97316", "Vibrant Orange"),
]


@login_required(login_url="login")
def category_manage(request):
    """Category manager view."""
    categories = get_user_categories(request.user)
    color_map = {c.color.lower(): c.name for c in categories if c.color}
    used_colors = list(color_map.keys())
    suggested_colors = [p for p in PRESET_PALETTE if p[0].lower() not in used_colors]
    return render(request, "quotes/category_manage.html", {
        "categories": categories,
        "used_colors": used_colors,
        "color_map": color_map,
        "preset_palette": PRESET_PALETTE,
        "suggested_colors": suggested_colors,
    })


@login_required(login_url="login")
@require_http_methods(["POST"])
def category_create(request):
    """Create a new category."""
    name = request.POST.get("name", "").strip()
    color = request.POST.get("color", "#a78bfa").strip()

    if not name:
        return redirect("category_manage")

    slug = name.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    max_order = Category.objects.filter(Q(is_default=True) | Q(user=request.user)).count()

    Category.objects.create(
        user=request.user,
        name=name,
        slug=slug,
        emoji="",
        color=color,
        is_default=False,
        order=max_order + 1
    )

    return redirect("category_manage")


@login_required(login_url="login")
@require_http_methods(["POST"])
def category_edit(request, pk):
    """Edit an existing category."""
    category = get_object_or_404(Category, pk=pk)
    name = request.POST.get("name", "").strip()
    color = request.POST.get("color", category.color).strip()

    if name:
        category.name = name
        category.slug = re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))
    category.color = color
    category.save()

    return redirect("category_manage")


@login_required(login_url="login")
@require_http_methods(["POST"])
def category_delete(request, pk):
    """Delete a category; associated memories default to Inbox."""
    category = get_object_or_404(Category, pk=pk)
    Memory.objects.filter(category=category).update(category=None, status=Memory.Status.INBOX)
    category.delete()
    return redirect("category_manage")


@login_required(login_url="login")
@require_http_methods(["POST"])
def category_reorder(request, pk, direction):
    """Swap category order value with adjacent category."""
    cat = get_object_or_404(Category, pk=pk)
    categories = list(get_user_categories(request.user))

    try:
        idx = categories.index(cat)
    except ValueError:
        return redirect("category_manage")

    target_idx = idx - 1 if direction == "up" else idx + 1

    if 0 <= target_idx < len(categories):
        target = categories[target_idx]
        cat.order, target.order = target.order, cat.order
        cat.save()
        target.save()

    return redirect("category_manage")


# ── PWA Share Target Handler ──────────────────────────────────────────
@login_required(login_url="login")
def share_target(request):
    """Accept PWA Web Share Target POST payload."""
    title = request.GET.get("title") or request.POST.get("title", "")
    text = request.GET.get("text") or request.POST.get("text", "")
    url = request.GET.get("url") or request.POST.get("url", "")

    content_parts = []
    if text:
        content_parts.append(text)
    if url:
        content_parts.append(url)

    content = "\n".join(content_parts).strip()
    if not content and title:
        content = title

    if content:
        category_slug = suggest_category(content)
        category = Category.objects.filter(slug=category_slug).first() if category_slug else None

        Memory.objects.create(
            user=request.user,
            title=title or extract_title(content),
            content=content,
            category=category,
            source_url=url,
            status=Memory.Status.INBOX
        )

    return redirect("dashboard")


# ── Seed default categories ───────────────────────────────────────────
def seed_categories():
    """Create default categories if they don't exist."""
    Category.objects.all().update(emoji="")

    shows_cat = Category.objects.filter(slug="shows", is_default=True).first()
    cinema_cat = Category.objects.filter(slug="cinema", is_default=True).first()
    if shows_cat:
        if cinema_cat:
            Memory.objects.filter(category=shows_cat).update(category=cinema_cat)
        shows_cat.delete()

    defaults = [
        {"name": "Quotes", "slug": "quotes", "emoji": "", "color": "#f59e0b", "order": 1},
        {"name": "Thoughts", "slug": "thoughts", "emoji": "", "color": "#a78bfa", "order": 2},
        {"name": "Ideas", "slug": "ideas", "emoji": "", "color": "#fbbf24", "order": 3},
        {"name": "Learn", "slug": "learn", "emoji": "", "color": "#34d399", "order": 4},
        {"name": "Save", "slug": "save", "emoji": "", "color": "#60a5fa", "order": 5},
        {"name": "Links", "slug": "links", "emoji": "", "color": "#38bdf8", "order": 6},
        {"name": "Watch", "slug": "watch", "emoji": "", "color": "#f87171", "order": 7},
        {"name": "Cinema", "slug": "cinema", "emoji": "", "color": "#e11d48", "order": 8},
        {"name": "Read", "slug": "read", "emoji": "", "color": "#fb923c", "order": 9},
        {"name": "Buy", "slug": "buy", "emoji": "", "color": "#4ade80", "order": 10},
        {"name": "Tasks", "slug": "tasks", "emoji": "", "color": "#22d3ee", "order": 11},
        {"name": "Reminders", "slug": "reminders", "emoji": "", "color": "#e879f9", "order": 12},
        {"name": "Places", "slug": "places", "emoji": "", "color": "#2dd4bf", "order": 13},
        {"name": "Code", "slug": "code", "emoji": "", "color": "#a3e635", "order": 14},
        {"name": "People", "slug": "people", "emoji": "", "color": "#f472b6", "order": 15},
        {"name": "Projects", "slug": "projects", "emoji": "", "color": "#818cf8", "order": 16},
        {"name": "Important", "slug": "important", "emoji": "", "color": "#ef4444", "order": 17},
    ]
    for cat_data in defaults:
        Category.objects.get_or_create(
            slug=cat_data["slug"],
            defaults={**cat_data, "is_default": True}
        )


def favicon_view(request):
    """Serve logo.svg directly for /favicon.ico requests."""
    logo_path = os.path.join(settings.BASE_DIR, "static", "logo.svg")
    return FileResponse(open(logo_path, "rb"), content_type="image/svg+xml")


# ── Custom Glassmorphic Admin Console ──────────────────────────────────
def admin_vault_login(request):
    """Dedicated login portal for Admin Control Console (/ctrl/)."""
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser) and request.session.get("admin_unlocked") == True:
        return redirect("custom_admin_panel")

    error = None
    handle = ""

    if request.method == "POST":
        raw_handle = request.POST.get("handle", "").strip().lower().replace("@", "")
        pin = request.POST.get("pin", "").strip()

        handle = re.sub(r'[^a-z0-9_]', '', raw_handle)

        if not handle or len(handle) < 2:
            error = "Admin Handle must be at least 2 characters long."
        elif not pin:
            error = "Admin Key / PIN is required."
        else:
            user = User.objects.filter(username=handle).first()
            if user:
                if not (user.is_staff or user.is_superuser):
                    error = f"Access Denied: @{handle} does not have Admin Control privileges."
                else:
                    authenticated_user = authenticate(request, username=handle, password=pin)
                    if authenticated_user:
                        login(request, authenticated_user)
                        request.session["admin_unlocked"] = True
                        return redirect("custom_admin_panel")
                    else:
                        error = f"Incorrect Admin Key / PIN for @{handle}."
            else:
                error = f"Admin Handle @{handle} does not exist."

    return render(request, "quotes/admin_login.html", {"error": error, "handle": handle})


def admin_vault_logout(request):
    """Logout from Admin Control Console."""
    request.session["admin_unlocked"] = False
    logout(request)
    return redirect("admin_vault_login")


def custom_admin_panel(request):
    """Custom glassmorphic admin dashboard for system administration with user filtering."""
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser) and request.session.get("admin_unlocked") == True):
        return redirect("admin_vault_login")

    selected_user_id = request.GET.get("user_id", "").strip()
    selected_user = None

    users = User.objects.all().order_by("-date_joined")
    user_data = []
    for u in users:
        mem_count = Memory.objects.filter(user=u).count()
        user_data.append({
            "user": u,
            "memory_count": mem_count,
        })

    recent_memories = Memory.objects.select_related("user", "category").all()

    if selected_user_id.isdigit():
        selected_user = User.objects.filter(pk=int(selected_user_id)).first()
        if selected_user:
            recent_memories = recent_memories.filter(user=selected_user)

    recent_memories = recent_memories.order_by("-created_at")[:50]

    # HTMX Partial swap for live feed filtering
    if request.headers.get("HX-Request") and "user_id" in request.GET:
        return render(request, "quotes/partials/admin_memory_feed.html", {
            "recent_memories": recent_memories,
            "selected_user": selected_user,
        })

    total_memories = Memory.objects.count()
    total_users = User.objects.count()
    total_categories = Category.objects.count()
    total_tags = Tag.objects.count()

    db_url = os.environ.get("DATABASE_URL", "")
    if "postgres" in db_url or "neon" in db_url:
        db_name = "Neon PostgreSQL (Production)"
    else:
        db_name = "SQLite (Local Dev)"

    return render(request, "quotes/admin_dashboard.html", {
        "user_data": user_data,
        "recent_memories": recent_memories,
        "selected_user": selected_user,
        "total_memories": total_memories,
        "total_users": total_users,
        "total_categories": total_categories,
        "total_tags": total_tags,
        "db_name": db_name,
        "debug_mode": settings.DEBUG,
    })


@login_required(login_url="login")
@require_http_methods(["POST"])
def admin_toggle_staff(request, user_id):
    """Toggle staff permission for a user (admin only)."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseBadRequest("Unauthorized")

    target_user = get_object_or_404(User, pk=user_id)
    if target_user != request.user:
        target_user.is_staff = not target_user.is_staff
        target_user.save()

    return redirect("custom_admin_panel")


# ── Web Push & Native Reminder Notifications ─────────────────────────
def vapid_public_key_view(request):
    """Return VAPID Public Key for client Service Worker subscription."""
    return JsonResponse({"public_key": getattr(settings, "VAPID_PUBLIC_KEY", "")})


@csrf_exempt
@login_required(login_url="login")
@require_http_methods(["POST"])
def push_subscribe_view(request):
    """Register or update Web Push subscription for current user."""
    try:
        data = json.loads(request.body.decode("utf-8"))
        endpoint = data.get("endpoint")
        keys = data.get("keys", {})
        p256dh = keys.get("p256dh")
        auth = keys.get("auth")

        if not (endpoint and p256dh and auth):
            return HttpResponseBadRequest("Missing subscription parameters")

        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

        sub, _ = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user,
                "p256dh": p256dh,
                "auth": auth,
                "user_agent": user_agent,
            }
        )
        return JsonResponse({"status": "subscribed", "subscription_id": sub.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@login_required(login_url="login")
@require_http_methods(["POST"])
def push_unsubscribe_view(request):
    """Remove Web Push subscription."""
    try:
        data = json.loads(request.body.decode("utf-8"))
        endpoint = data.get("endpoint")
        if endpoint:
            PushSubscription.objects.filter(endpoint=endpoint, user=request.user).delete()
        return JsonResponse({"status": "unsubscribed"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required(login_url="login")
def due_reminders_api(request):
    """Return due memories & reminders for active tab native/toast notifications."""
    now = timezone.now()
    memories = Memory.objects.filter(
        user=request.user,
        is_archived=False
    ).filter(
        Q(reminder_at__lte=now) | Q(due_date__lte=now)
    ).exclude(status=Memory.Status.DONE).order_by("-reminder_at", "-due_date")[:10]

    due_list = []
    for m in memories:
        due_list.append({
            "id": m.id,
            "title": m.title or (m.content[:40] + "..."),
            "content": m.content[:120],
            "category": m.category.name if m.category else "Reminder",
            "url": reverse("memory_detail", args=[m.id]),
        })

    return JsonResponse({"due_reminders": due_list, "count": len(due_list)})


@csrf_exempt
def trigger_due_reminders_view(request):
    """Trigger Web Push notifications for due memories across registered subscriptions."""
    now = timezone.now()
    due_memories = Memory.objects.filter(
        is_archived=False
    ).filter(
        Q(reminder_at__lte=now) | Q(due_date__lte=now)
    ).exclude(status=Memory.Status.DONE).select_related("user", "category")

    sent_count = 0
    errors = 0

    if not due_memories.exists():
        return JsonResponse({"status": "ok", "sent": 0, "message": "No due reminders"})

    try:
        from pywebpush import webpush, WebPushException
        vapid_private_key = getattr(settings, "VAPID_PRIVATE_KEY", "")
        vapid_claims = {"sub": f"mailto:{getattr(settings, 'VAPID_CLAIM_EMAIL', 'admin@memora.vault')}"}

        for memory in due_memories:
            subscriptions = PushSubscription.objects.filter(user=memory.user)
            payload = json.dumps({
                "title": f"🔔 Memora Reminder: {memory.title or 'Memory Reminder'}",
                "body": memory.content[:140],
                "url": reverse("memory_detail", args=[memory.id]),
                "memory_id": memory.id,
            })

            for sub in subscriptions:
                try:
                    webpush(
                        subscription_info={
                            "endpoint": sub.endpoint,
                            "keys": {
                                "p256dh": sub.p256dh,
                                "auth": sub.auth,
                            }
                        },
                        data=payload,
                        vapid_private_key=vapid_private_key,
                        vapid_claims=vapid_claims,
                        timeout=5
                    )
                    sent_count += 1
                except WebPushException as ex:
                    errors += 1
                    if ex.response and ex.response.status_code in [404, 410]:
                        sub.delete()
                except Exception:
                    errors += 1

    except ImportError:
        return JsonResponse({"error": "pywebpush not installed"}, status=500)

    return JsonResponse({
        "status": "ok",
        "due_memories": due_memories.count(),
        "sent_notifications": sent_count,
        "errors": errors
    })



