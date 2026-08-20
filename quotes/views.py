import json
import re
from datetime import timedelta

from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q

from .models import Memory, Category, Tag, Collection


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
    "watch": ["watch", "movie", "film", "show", "series", "episode", "netflix", "youtube", "video", "documentary", "anime"],
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
    # Explicit quote with double quotes AND an author attribution
    r'^["“].+["”]\s*([\n\r]|\s+[-—–~])',
    # Author attribution on a new line: - Firstname Lastname (at least 2 capitalized name words)
    r'[\n\r]\s*[-—–~]\s*[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}',
    # Explicit quote keywords
    r'\b(famous quote|quote by|quote of the day)\b',
]


def suggest_category(text):
    """High-confidence smart category suggestion."""
    if not text or len(text.strip()) < 5:
        return None

    # 1. High-confidence Code syntax & HTML structure
    for pattern in CODE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "code"

    # 2. High-confidence Quote attributions
    for pattern in QUOTE_PATTERNS:
        if re.search(pattern, text):
            if Category.objects.filter(slug="quotes").exists():
                return "quotes"
            if Category.objects.filter(slug="thoughts").exists():
                return "thoughts"

    # 3. High-confidence Link detection
    if re.search(r'\b(https?://|www\.)\S+', text, re.IGNORECASE):
        return "links"

    # 4. Keyword matching
    text_lower = text.lower()
    for slug, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                return slug

    return None


def auto_title(content):
    """Generate a clean, smart title from content."""
    if not content:
        return "Untitled Memory"

    clean = content.strip()

    # 1. Author quote extraction (e.g. - Benjamin Franklin)
    author_match = re.search(r'[\n\r\s]+[-—–~]\s*([A-Z][a-zA-Z\s\.]+)', clean)
    if author_match and author_match.group(1).strip():
        author = author_match.group(1).strip()
        quote_text = clean.replace(author_match.group(0), '').split('\n')[0].replace('"', '').replace('“', '').replace('”', '').strip()
        words = quote_text.split()
        short_quote = " ".join(words[:5]) + "..." if len(words) > 5 else quote_text
        return f'"{short_quote}" — {author}'

    # 2. HTML title tag extraction
    title_match = re.search(r"<title>(.*?)</title>", clean, re.IGNORECASE)
    if title_match and title_match.group(1).strip():
        return title_match.group(1).strip()[:80]

    # 3. URL title extraction
    if clean.startswith("http://") or clean.startswith("https://"):
        from urllib.parse import urlparse
        parsed = urlparse(clean.split()[0])
        path = parsed.path.rstrip("/")
        if path:
            return f"{parsed.netloc}{path}"
        return parsed.netloc or "Saved Link"

    # 4. Clean first line summary
    first_line = clean.split("\n")[0].strip()
    first_line = re.sub(r'^[“"\'\`\s\-*\d\.]+', '', first_line)
    first_line = re.sub(r'[”"\'\`\s]+$', '', first_line).strip()

    if not first_line:
        first_line = clean[:80]

    words = first_line.split()
    if len(words) > 8:
        return " ".join(words[:8]) + "..."
    return first_line


# ── Dashboard ──────────────────────────────────────────────────────────
def dashboard(request):
    """Main dashboard — shows recent memories, pinned items, upcoming."""
    categories = Category.objects.all().order_by("order", "name")
    total_count = Memory.objects.filter(is_archived=False).count()
    inbox_count = Memory.objects.filter(status=Memory.Status.INBOX, is_archived=False).count()
    tasks_done = Memory.objects.filter(status=Memory.Status.DONE, is_archived=False).count()
    due_soon = Memory.objects.filter(is_archived=False, due_date__isnull=False, due_date__gte=timezone.now()).count()

    pinned = Memory.objects.filter(is_pinned=True, is_archived=False)[:6]
    recent = Memory.objects.filter(is_archived=False)[:12]
    
    # Upcoming: tasks/reminders with due dates in the future
    upcoming = Memory.objects.filter(
        is_archived=False,
        due_date__isnull=False,
        due_date__gte=timezone.now()
    ).order_by("due_date")[:5]

    return render(request, "quotes/dashboard.html", {
        "categories": categories,
        "total_count": total_count,
        "inbox_count": inbox_count,
        "tasks_done": tasks_done,
        "due_soon": due_soon,
        "pinned": pinned,
        "recent": recent,
        "upcoming": upcoming,
    })


# ── Memory list (filtered by category, tag, collection, status) ───────
def memory_list(request, filter_type=None, filter_value=None):
    """Filtered memory list view."""
    memories = Memory.objects.filter(is_archived=False)
    title = "All Memories"
    active_filter = filter_type

    if filter_type == "category":
        category = get_object_or_404(Category, slug=filter_value)
        memories = memories.filter(category=category)
        title = str(category)
    elif filter_type == "tag":
        tag = get_object_or_404(Tag, slug=filter_value)
        memories = memories.filter(tags=tag)
        title = f"#{tag.name}"
    elif filter_type == "collection":
        collection = get_object_or_404(Collection, pk=filter_value)
        memories = memories.filter(collections=collection)
        title = collection.name
    elif filter_type == "inbox":
        memories = memories.filter(status=Memory.Status.INBOX)
        title = "📥 Inbox"
    elif filter_type == "important":
        memories = memories.filter(is_pinned=True)
        title = "❤️ Important"
    elif filter_type == "archive":
        memories = Memory.objects.filter(is_archived=True)
        title = "🗄️ Archive"
    elif filter_type == "today":
        today = timezone.now().date()
        memories = memories.filter(created_at__date=today)
        title = "📅 Today"
    elif filter_type == "week":
        week_ago = timezone.now() - timedelta(days=7)
        memories = memories.filter(created_at__gte=week_ago)
        title = "📅 This Week"
    elif filter_type == "tasks":
        memories = memories.filter(category__slug="tasks")
        title = "✅ Tasks"
    elif filter_type == "reminders":
        memories = memories.filter(Q(due_date__isnull=False) | Q(reminder_at__isnull=False)).order_by('due_date')
        title = "📅 Reminders & Due Dates"
    elif filter_type == "priority":
        memories = memories.filter(priority=filter_value)
        title = f"Priority: {filter_value.capitalize()}"
    elif filter_type == "on_this_day":
        today = timezone.now()
        memories = memories.filter(
            created_at__month=today.month,
            created_at__day=today.day
        )
        if not memories.exists():
            memories = Memory.objects.filter(is_archived=False).order_by("created_at")[:12]
        title = "✨ On This Day"

    categories = Category.objects.all().order_by("order", "name")
    
    if request.headers.get("HX-Request"):
        return render(request, "quotes/partials/memory_grid.html", {
            "memories": memories,
            "title": title,
        })

    inbox_count = Memory.objects.filter(status=Memory.Status.INBOX, is_archived=False).count()

    return render(request, "quotes/memory_list.html", {
        "memories": memories,
        "title": title,
        "categories": categories,
        "active_filter": active_filter,
        "filter_value": filter_value,
        "inbox_count": inbox_count,
    })


# ── Recently Viewed View ──────────────────────────────────────────────
def recently_viewed(request):
    """View list of recently viewed memories."""
    recent_ids = request.session.get("recently_viewed", [])
    memories = []
    if recent_ids:
        memory_map = {m.id: m for m in Memory.objects.filter(id__in=recent_ids, is_archived=False)}
        memories = [memory_map[m_id] for m_id in recent_ids if m_id in memory_map]
    
    categories = Category.objects.all().order_by("order", "name")
    return render(request, "quotes/memory_list.html", {
        "memories": memories,
        "title": "🕒 Recently Viewed",
        "categories": categories,
        "active_filter": "recently_viewed",
    })


# ── Search ─────────────────────────────────────────────────────────────
def search_memories(request):
    """Universal search across all memory fields."""
    query = request.GET.get("q", "").strip()
    category_filter = request.GET.get("category", "").strip()
    
    memories = Memory.objects.filter(is_archived=False)
    
    if query:
        memories = memories.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(author__icontains=query)
            | Q(source_url__icontains=query)
            | Q(source_title__icontains=query)
            | Q(tags__name__icontains=query)
            | Q(category__name__icontains=query)
        ).distinct()
    
    if category_filter:
        memories = memories.filter(category__slug=category_filter)
    
    return render(request, "quotes/partials/memory_grid.html", {
        "memories": memories,
        "query": query,
    })


# ── Capture (web form) ─────────────────────────────────────────────────
def capture(request):
    """Handle the universal capture form submission."""
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if not content:
            if request.headers.get("HX-Request"):
                return render(request, "quotes/partials/capture_feedback.html", {
                    "error": "Content is required."
                })
            return redirect("dashboard")

        title = request.POST.get("title", "").strip() or auto_title(content)
        category_slug = request.POST.get("category", "").strip()
        tags_str = request.POST.get("tags", "").strip()
        source_url = request.POST.get("source_url", "").strip()
        priority = request.POST.get("priority", Memory.Priority.NONE)
        author = request.POST.get("author", "").strip()

        due_date = None
        due_date_str = request.POST.get("due_date", "").strip()
        if due_date_str:
            from datetime import datetime
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()

        category = None
        if category_slug:
            category = Category.objects.filter(slug=category_slug).first()

        status = Memory.Status.INBOX
        if category:
            status = Memory.Status.ACTIVE

        memory = Memory.objects.create(
            title=title,
            content=content,
            category=category,
            source_url=source_url,
            author=author,
            priority=priority,
            status=status,
            due_date=due_date,
        )

        # Handle tags
        if tags_str:
            tag_names = [t.strip().lower() for t in tags_str.split(",") if t.strip()]
            for tag_name in tag_names:
                from django.utils.text import slugify
                tag, _ = Tag.objects.get_or_create(
                    slug=slugify(tag_name),
                    defaults={"name": tag_name}
                )
                memory.tags.add(tag)

        if request.headers.get("HX-Request"):
            return render(request, "quotes/partials/capture_feedback.html", {
                "success": True, "memory": memory
            })
        return redirect("dashboard")

    # GET — show capture form (for direct navigation)
    categories = Category.objects.all().order_by("order", "name")
    return render(request, "quotes/capture_form.html", {"categories": categories})


# ── Category suggestion API (for smart capture) ───────────────────────
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
                    "emoji": category.emoji,
                }
            })
    return JsonResponse({"suggestion": None})


# ── Memory detail & actions ────────────────────────────────────────────
def memory_detail(request, pk):
    """View a single memory detail page + track recently viewed + smart suggestions."""
    memory = get_object_or_404(Memory, pk=pk)
    
    # Track in session
    recent_ids = request.session.get("recently_viewed", [])
    if memory.id in recent_ids:
        recent_ids.remove(memory.id)
    recent_ids.insert(0, memory.id)
    request.session["recently_viewed"] = recent_ids[:20]

    # Smart suggestions (related memories sharing category or tags)
    suggestions = Memory.objects.filter(is_archived=False).exclude(id=memory.id)
    if memory.category:
        suggestions = suggestions.filter(category=memory.category)
    suggestions = suggestions[:3]

    categories = Category.objects.all().order_by("order", "name")
    return render(request, "quotes/memory_detail.html", {
        "memory": memory,
        "categories": categories,
        "suggestions": suggestions,
    })


def memory_edit(request, pk):
    """Edit memory view (handles GET form modal and POST update)."""
    memory = get_object_or_404(Memory, pk=pk)

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            memory.content = content
            memory.title = request.POST.get("title", "").strip() or auto_title(content)
            
            cat_slug = request.POST.get("category", "").strip()
            if cat_slug:
                memory.category = Category.objects.filter(slug=cat_slug).first()
                if memory.status == Memory.Status.INBOX:
                    memory.status = Memory.Status.ACTIVE
            else:
                memory.category = None

            memory.source_url = request.POST.get("source_url", "").strip()
            memory.priority = request.POST.get("priority", Memory.Priority.NONE)
            memory.author = request.POST.get("author", "").strip()
            
            status = request.POST.get("status", "").strip()
            if status:
                memory.status = status

            due_date_str = request.POST.get("due_date", "").strip()
            if due_date_str:
                from datetime import datetime
                memory.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            else:
                memory.due_date = None
            
            # Tags
            tags_str = request.POST.get("tags", "").strip()
            memory.tags.clear()
            if tags_str:
                tag_names = [t.strip().lower() for t in tags_str.split(",") if t.strip()]
                for tag_name in tag_names:
                    from django.utils.text import slugify
                    tag, _ = Tag.objects.get_or_create(
                        slug=slugify(tag_name),
                        defaults={"name": tag_name}
                    )
                    memory.tags.add(tag)

            memory.save()

        if request.headers.get("HX-Request"):
            return render(request, "quotes/partials/memory_card.html", {"memory": memory})
        return redirect("dashboard")

    # GET request - return edit modal HTML
    categories = Category.objects.all()
    tags_str = ", ".join([t.name for t in memory.tags.all()])
    if request.headers.get("HX-Request"):
        return render(request, "quotes/partials/memory_edit_modal.html", {
            "memory": memory,
            "categories": categories,
            "tags_str": tags_str,
        })

    return render(request, "quotes/memory_detail.html", {
        "memory": memory,
        "categories": categories,
        "editing": True,
        "tags_str": tags_str,
    })


@require_http_methods(["POST"])
def memory_pin(request, pk):
    """Toggle pin status."""
    memory = get_object_or_404(Memory, pk=pk)
    memory.is_pinned = not memory.is_pinned
    memory.save(update_fields=["is_pinned"])
    if request.headers.get("HX-Request"):
        return render(request, "quotes/partials/memory_card.html", {"memory": memory})
    return redirect("dashboard")


@require_http_methods(["POST"])
def memory_archive(request, pk):
    """Toggle archive status."""
    memory = get_object_or_404(Memory, pk=pk)
    memory.is_archived = not memory.is_archived
    if memory.is_archived:
        memory.status = Memory.Status.ARCHIVED
    else:
        memory.status = Memory.Status.ACTIVE
    memory.save(update_fields=["is_archived", "status"])
    
    if request.headers.get("HX-Request"):
        from django.http import HttpResponse
        current_url = request.headers.get("HX-Current-URL", "")

        # If on single memory detail page, re-render card
        if f"/memory/{pk}" in current_url:
            return render(request, "quotes/partials/memory_card.html", {"memory": memory})

        # If on /archive/ view and item was unarchived, remove from archive list
        if "/archive/" in current_url and not memory.is_archived:
            return HttpResponse("", status=200)

        # If on active list view and item was archived, remove from active list
        if "/archive/" not in current_url and memory.is_archived:
            return HttpResponse("", status=200)

        return render(request, "quotes/partials/memory_card.html", {"memory": memory})

    return redirect("dashboard")


@require_http_methods(["POST"])
def memory_status(request, pk):
    """Update memory status (e.g. mark task as done)."""
    memory = get_object_or_404(Memory, pk=pk)
    new_status = request.POST.get("status", "").strip()
    if new_status in dict(Memory.Status.choices):
        memory.status = new_status
        if new_status == Memory.Status.ARCHIVED:
            memory.is_archived = True
        memory.save(update_fields=["status", "is_archived"])
    if request.headers.get("HX-Request"):
        return render(request, "quotes/partials/memory_card.html", {"memory": memory})
    return redirect("dashboard")


@require_http_methods(["POST", "DELETE"])
def memory_delete(request, pk):
    """Permanently delete a memory."""
    memory = get_object_or_404(Memory, pk=pk)
    memory.delete()
    if request.headers.get("HX-Request"):
        from django.http import HttpResponse
        response = HttpResponse("", status=200)
        current_url = request.headers.get("HX-Current-URL", "")
        if f"/memory/{pk}" in current_url or "/memory/" in current_url:
            response["HX-Redirect"] = "/"
        return response
    return redirect("dashboard")


# ── Random memory ("Remember This") ───────────────────────────────────
def random_memory(request):
    """Return a random memory for the 'Remember This' feature."""
    memory = Memory.random_memory()
    if request.headers.get("HX-Request"):
        return render(request, "quotes/partials/random_memory.html", {"memory": memory})
    return render(request, "quotes/random_memory.html", {"memory": memory})


# ── Capture API (bookmarklet / external) ──────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def capture_api(request):
    """Bookmarklet / generic capture endpoint. Accepts JSON body."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponseBadRequest(
            json.dumps({"error": "Invalid JSON"}), content_type="application/json"
        )

    content = (payload.get("text") or payload.get("content") or "").strip()
    if not content:
        return JsonResponse({"error": "Content is required."}, status=400)

    title = (payload.get("title") or "").strip() or auto_title(content)
    
    # Try to auto-suggest category
    category = None
    cat_slug = suggest_category(content)
    if cat_slug:
        category = Category.objects.filter(slug=cat_slug).first()

    memory = Memory.objects.create(
        title=title,
        content=content,
        category=category,
        author=(payload.get("author") or "").strip(),
        source_url=(payload.get("source_url") or payload.get("url") or "").strip(),
        source_title=(payload.get("source_title") or "").strip(),
        status=Memory.Status.ACTIVE if category else Memory.Status.INBOX,
    )
    return JsonResponse({"success": True, "id": memory.id})


# ── PWA Web Share Target ──────────────────────────────────────────────
@require_http_methods(["GET"])
def share_target(request):
    """PWA Web Share Target endpoint."""
    shared_text = request.GET.get("text", "").strip()
    shared_title = request.GET.get("title", "").strip()
    shared_url = request.GET.get("url", "").strip()

    body = shared_text or shared_title or shared_url
    if body:
        cat_slug = suggest_category(body)
        category = Category.objects.filter(slug=cat_slug).first() if cat_slug else None
        status = Memory.Status.ACTIVE if category else Memory.Status.INBOX

        Memory.objects.create(
            title=shared_title or auto_title(body),
            content=body,
            category=category,
            source_url=shared_url,
            status=status,
        )
    return redirect("dashboard")


# ── Category Management ────────────────────────────────────────────────
def category_manage(request):
    """View to list, create, edit, and delete categories."""
    categories = Category.objects.all().order_by("order", "name")
    return render(request, "quotes/category_manage.html", {"categories": categories})


@require_http_methods(["POST"])
def category_create(request):
    """Create a new category."""
    name = request.POST.get("name", "").strip()
    emoji = request.POST.get("emoji", "📌").strip() or "📌"
    color = request.POST.get("color", "#a78bfa").strip() or "#a78bfa"
    
    if not name:
        return redirect("category_manage")
    
    from django.utils.text import slugify
    slug = slugify(name)
    
    base_slug = slug
    counter = 1
    while Category.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    Category.objects.create(
        name=name,
        slug=slug,
        emoji=emoji,
        color=color,
        is_default=False,
        order=Category.objects.count() + 1
    )
    return redirect("category_manage")


@require_http_methods(["POST"])
def category_edit(request, pk):
    """Edit an existing category."""
    category = get_object_or_404(Category, pk=pk)
    name = request.POST.get("name", "").strip()
    emoji = request.POST.get("emoji", "").strip()
    color = request.POST.get("color", "").strip()

    if name:
        category.name = name
        from django.utils.text import slugify
        category.slug = slugify(name)
    if emoji:
        category.emoji = emoji
    if color:
        category.color = color
    category.save()
    return redirect("category_manage")


@require_http_methods(["POST"])
def category_delete(request, pk):
    """Delete a category (reassign memories to Inbox)."""
    category = get_object_or_404(Category, pk=pk)
    # Reassign memories to Inbox before deleting
    Memory.objects.filter(category=category).update(category=None, status=Memory.Status.INBOX)
    category.delete()
    return redirect("category_manage")


@require_http_methods(["POST"])
def category_reorder(request, pk, direction):
    """Reorder category up or down."""
    category = get_object_or_404(Category, pk=pk)
    cats = list(Category.objects.all().order_by("order", "name"))
    
    # Ensure clean 1..N order
    for idx, c in enumerate(cats, start=1):
        if c.order != idx:
            c.order = idx
            c.save()

    curr_idx = cats.index(category)
    if direction == "up" and curr_idx > 0:
        other = cats[curr_idx - 1]
        category.order, other.order = other.order, category.order
        category.save()
        other.save()
    elif direction == "down" and curr_idx < len(cats) - 1:
        other = cats[curr_idx + 1]
        category.order, other.order = other.order, category.order
        category.save()
        other.save()

    return redirect("category_manage")


# ── Seed default categories ───────────────────────────────────────────
def seed_categories():
    """Create default categories if they don't exist."""
    Category.objects.all().update(emoji="")
    defaults = [
        {"name": "Quotes", "slug": "quotes", "emoji": "", "color": "#f59e0b", "order": 1},
        {"name": "Thoughts", "slug": "thoughts", "emoji": "", "color": "#a78bfa", "order": 2},
        {"name": "Ideas", "slug": "ideas", "emoji": "", "color": "#fbbf24", "order": 3},
        {"name": "Learn", "slug": "learn", "emoji": "", "color": "#34d399", "order": 4},
        {"name": "Save", "slug": "save", "emoji": "", "color": "#60a5fa", "order": 5},
        {"name": "Links", "slug": "links", "emoji": "", "color": "#38bdf8", "order": 6},
        {"name": "Watch", "slug": "watch", "emoji": "", "color": "#f87171", "order": 7},
        {"name": "Read", "slug": "read", "emoji": "", "color": "#fb923c", "order": 8},
        {"name": "Buy", "slug": "buy", "emoji": "", "color": "#4ade80", "order": 9},
        {"name": "Tasks", "slug": "tasks", "emoji": "", "color": "#22d3ee", "order": 10},
        {"name": "Reminders", "slug": "reminders", "emoji": "", "color": "#e879f9", "order": 11},
        {"name": "Places", "slug": "places", "emoji": "", "color": "#2dd4bf", "order": 12},
        {"name": "Code", "slug": "code", "emoji": "", "color": "#a3e635", "order": 13},
        {"name": "People", "slug": "people", "emoji": "", "color": "#f472b6", "order": 14},
        {"name": "Projects", "slug": "projects", "emoji": "", "color": "#818cf8", "order": 15},
        {"name": "Important", "slug": "important", "emoji": "", "color": "#ef4444", "order": 16},
    ]
    for cat_data in defaults:
        Category.objects.get_or_create(
            slug=cat_data["slug"],
            defaults={**cat_data, "is_default": True}
        )
