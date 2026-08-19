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


# ── Category suggestion (simple keyword matching) ──────────────────────
CATEGORY_KEYWORDS = {
    "watch": ["watch", "movie", "film", "show", "series", "episode", "netflix", "youtube", "video", "documentary", "anime"],
    "read": ["read", "book", "article", "paper", "blog", "novel", "manga", "ebook"],
    "buy": ["buy", "purchase", "order", "price", "cost", "shopping", "amazon", "flipkart", "deal"],
    "tasks": ["todo", "to-do", "task", "need to", "should", "must", "finish", "complete", "submit", "deadline"],
    "reminders": ["remind", "remember to", "don't forget", "dont forget", "appointment", "meeting", "schedule"],
    "learn": ["learn", "study", "understand", "how to", "tutorial", "course", "lesson", "concept", "explain"],
    "ideas": ["idea", "what if", "build", "create", "make a", "app that", "website that", "project", "startup"],
    "code": ["code", "command", "snippet", "function", "script", "api", "git", "npm", "pip", "sudo", "terminal", "debug"],
    "links": ["http://", "https://", "www.", ".com", ".org", ".io", "website", "link", "url", "resource"],
    "places": ["visit", "travel", "restaurant", "hotel", "cafe", "place", "destination", "trip", "location"],
    "people": ["person", "contact", "met", "talked to", "called", "phone number", "email"],
    "projects": ["project", "roadmap", "milestone", "sprint", "feature", "requirement"],
    "thoughts": ["thinking", "thought", "feel", "feeling", "wonder", "maybe", "perhaps", "opinion"],
    "important": ["important", "critical", "urgent", "crucial", "vital", "essential", "never forget"],
}


def suggest_category(text):
    """Simple keyword-based category suggestion. Returns slug or None."""
    text_lower = text.lower()
    scores = {}
    for slug, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[slug] = score
    if scores:
        return max(scores, key=scores.get)
    return None


def auto_title(content):
    """Generate a short title from content if none provided."""
    # Take first line or first 80 chars
    first_line = content.strip().split("\n")[0].strip()
    if len(first_line) <= 80:
        return first_line
    return first_line[:77] + "..."


# ── Dashboard ──────────────────────────────────────────────────────────
def dashboard(request):
    """Main dashboard — shows recent memories, pinned items, upcoming."""
    categories = Category.objects.filter(is_default=True)
    inbox_count = Memory.objects.filter(status=Memory.Status.INBOX, is_archived=False).count()
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
        "inbox_count": inbox_count,
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

    categories = Category.objects.filter(is_default=True)
    
    # Check if this is an HTMX request for just the memory grid
    if request.headers.get("HX-Request"):
        return render(request, "quotes/partials/memory_grid.html", {
            "memories": memories,
            "title": title,
        })

    return render(request, "quotes/memory_list.html", {
        "memories": memories,
        "title": title,
        "categories": categories,
        "active_filter": active_filter,
        "filter_value": filter_value,
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
            priority=priority,
            status=status,
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
    categories = Category.objects.filter(is_default=True)
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
    """View a single memory."""
    memory = get_object_or_404(Memory, pk=pk)
    categories = Category.objects.filter(is_default=True)
    return render(request, "quotes/memory_detail.html", {
        "memory": memory,
        "categories": categories,
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


@require_http_methods(["POST"])
def memory_delete(request, pk):
    """Permanently delete a memory."""
    memory = get_object_or_404(Memory, pk=pk)
    memory.delete()
    if request.headers.get("HX-Request"):
        return JsonResponse({"deleted": True})
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
        status=Memory.Status.INBOX,
    )
    return JsonResponse({"success": True, "id": memory.id})


# ── PWA Web Share Target ──────────────────────────────────────────────
@require_http_methods(["GET"])
def share_target(request):
    """PWA Web Share Target endpoint."""
    shared_text = request.GET.get("text", "").strip()
    shared_title = request.GET.get("title", "").strip()
    shared_url = request.GET.get("url", "").strip()

    body = shared_text or shared_title
    if body:
        Memory.objects.create(
            title=shared_title or auto_title(body),
            content=body,
            source_url=shared_url,
            status=Memory.Status.INBOX,
        )
    return redirect("dashboard")


# ── Seed default categories ───────────────────────────────────────────
def seed_categories():
    """Create default categories if they don't exist."""
    defaults = [
        {"name": "Thoughts", "slug": "thoughts", "emoji": "🧠", "color": "#a78bfa", "order": 1},
        {"name": "Ideas", "slug": "ideas", "emoji": "💡", "color": "#fbbf24", "order": 2},
        {"name": "Learn", "slug": "learn", "emoji": "📚", "color": "#34d399", "order": 3},
        {"name": "Save", "slug": "save", "emoji": "🔖", "color": "#60a5fa", "order": 4},
        {"name": "Links", "slug": "links", "emoji": "🔗", "color": "#38bdf8", "order": 5},
        {"name": "Watch", "slug": "watch", "emoji": "🎬", "color": "#f87171", "order": 6},
        {"name": "Read", "slug": "read", "emoji": "📖", "color": "#fb923c", "order": 7},
        {"name": "Buy", "slug": "buy", "emoji": "🛒", "color": "#4ade80", "order": 8},
        {"name": "Tasks", "slug": "tasks", "emoji": "✅", "color": "#22d3ee", "order": 9},
        {"name": "Reminders", "slug": "reminders", "emoji": "📅", "color": "#e879f9", "order": 10},
        {"name": "Places", "slug": "places", "emoji": "✈️", "color": "#2dd4bf", "order": 11},
        {"name": "Code", "slug": "code", "emoji": "💻", "color": "#a3e635", "order": 12},
        {"name": "People", "slug": "people", "emoji": "👤", "color": "#f472b6", "order": 13},
        {"name": "Projects", "slug": "projects", "emoji": "🚀", "color": "#818cf8", "order": 14},
        {"name": "Important", "slug": "important", "emoji": "❤️", "color": "#ef4444", "order": 15},
    ]
    for cat_data in defaults:
        Category.objects.get_or_create(
            slug=cat_data["slug"],
            defaults={**cat_data, "is_default": True}
        )
