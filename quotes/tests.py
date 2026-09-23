"""
Memora Test Suite
=================
Comprehensive tests for models, views, authentication, URL routing,
template rendering, and API endpoints. These run in CI to prevent
broken deploys from reaching production.
"""

import json
from django.test import TestCase, Client, override_settings
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from django.utils import timezone

from quotes.models import Memory, Category, Tag, Collection, PushSubscription
from quotes.views import suggest_category, extract_title, seed_categories


# Use simple static storage during tests to avoid WhiteNoise manifest issues
TEST_STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(STORAGES=TEST_STORAGES)
class LandingPageTest(TestCase):
    """Test the product landing page view and home root."""

    def test_home_root_renders_landing_page_for_unauthenticated(self):
        client = Client()
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "quotes/landing.html")

    def test_landing_page_routes_render_successfully(self):
        client = Client()
        for route_name in ["landing", "landing_page", "about"]:
            resp = client.get(reverse(route_name))
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, "quotes/landing.html")


@override_settings(STORAGES=TEST_STORAGES)
class CustomErrorPagesTest(TestCase):
    """Test custom glassmorphic error handlers (404, 500, 403, 400)."""

    def test_custom_404_view_renders(self):
        client = Client()
        for invalid_path in ["/sc", "/ct", "/non-existent-random-route-12345/"]:
            resp = client.get(invalid_path)
            self.assertEqual(resp.status_code, 404)
            self.assertTemplateUsed(resp, "404.html")

    def test_custom_error_views_direct_render(self):
        from quotes.views import custom_404_view, custom_500_view, custom_403_view, custom_400_view
        client = Client()
        req = client.get("/").wsgi_request

        self.assertEqual(custom_404_view(req).status_code, 404)
        self.assertEqual(custom_500_view(req).status_code, 500)
        self.assertEqual(custom_403_view(req).status_code, 403)
        self.assertEqual(custom_400_view(req).status_code, 400)


@override_settings(STORAGES=TEST_STORAGES)
class HealthCheckTest(TestCase):
    """Test unauthenticated uptime health check endpoints."""

    def test_healthz_returns_200_ok_json(self):
        client = Client()
        resp = client.get(reverse("health_check"), headers={"accept": "application/json"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

    def test_healthz_returns_200_ok_html(self):
        client = Client()
        resp = client.get(reverse("health_check"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "quotes/health_check.html")

    def test_ping_returns_200_ok(self):
        client = Client()
        resp = client.get(reverse("ping"), headers={"accept": "application/json"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")


class CategoryModelTest(TestCase):
    """Test the Category model."""

    def test_create_category(self):
        cat = Category.objects.create(name="Test", slug="test", color="#ff0000")
        self.assertEqual(str(cat), "Test")
        self.assertEqual(cat.slug, "test")
        self.assertFalse(cat.is_default)

    def test_category_ordering(self):
        Category.objects.create(name="B", slug="b", order=2)
        Category.objects.create(name="A", slug="a", order=1)
        cats = list(Category.objects.values_list("name", flat=True))
        self.assertEqual(cats[0], "A")

    def test_user_scoped_category(self):
        user = User.objects.create_user(username="tester", password="123456")
        cat = Category.objects.create(name="Personal", slug="personal", user=user)
        self.assertEqual(cat.user, user)


class TagModelTest(TestCase):
    """Test the Tag model."""

    def test_create_tag(self):
        tag = Tag.objects.create(name="python", slug="python")
        self.assertEqual(str(tag), "python")

    def test_tag_unique_constraint(self):
        Tag.objects.create(name="unique", slug="unique")
        with self.assertRaises(Exception):
            Tag.objects.create(name="unique", slug="unique")


class CollectionModelTest(TestCase):
    """Test the Collection model."""

    def test_create_collection(self):
        col = Collection.objects.create(name="2026 Goals")
        self.assertEqual(str(col), "2026 Goals")


class MemoryModelTest(TestCase):
    """Test the Memory model."""

    def test_create_memory_minimal(self):
        mem = Memory.objects.create(content="Remember this")
        self.assertEqual(str(mem), "Remember this")
        self.assertEqual(mem.status, "inbox")
        self.assertEqual(mem.priority, "none")
        self.assertFalse(mem.is_pinned)
        self.assertFalse(mem.is_archived)

    def test_create_memory_with_title(self):
        mem = Memory.objects.create(title="My Title", content="Body text")
        self.assertEqual(str(mem), "My Title")

    def test_memory_with_category(self):
        cat = Category.objects.create(name="Ideas", slug="ideas", color="#fbbf24")
        mem = Memory.objects.create(content="Big idea", category=cat)
        self.assertEqual(mem.category.name, "Ideas")

    def test_memory_with_tags(self):
        tag1 = Tag.objects.create(name="django", slug="django")
        tag2 = Tag.objects.create(name="python", slug="python")
        mem = Memory.objects.create(content="Django tip")
        mem.tags.add(tag1, tag2)
        self.assertEqual(mem.tags.count(), 2)

    def test_memory_user_scoping(self):
        user1 = User.objects.create_user(username="alice", password="123456")
        user2 = User.objects.create_user(username="bob", password="654321")
        Memory.objects.create(content="Alice's thought", user=user1)
        Memory.objects.create(content="Bob's thought", user=user2)
        self.assertEqual(Memory.objects.filter(user=user1).count(), 1)
        self.assertEqual(Memory.objects.filter(user=user2).count(), 1)

    def test_memory_status_choices(self):
        mem = Memory.objects.create(content="Test", status="done")
        self.assertEqual(mem.status, "done")

    def test_memory_priority_choices(self):
        mem = Memory.objects.create(content="Urgent!", priority="urgent")
        self.assertEqual(mem.priority, "urgent")

    def test_memory_preserves_em_dash_and_en_dash_content(self):
        mem = Memory.objects.create(
            title="Alpha — Beta",
            content="Use – and — exactly as typed",
            author="Jane — Doe",
        )
        self.assertEqual(mem.title, "Alpha — Beta")
        self.assertEqual(mem.content, "Use – and — exactly as typed")
        self.assertEqual(mem.author, "Jane — Doe")


# ═══════════════════════════════════════════════════════════════════════════════
# SEED CATEGORIES TEST
# ═══════════════════════════════════════════════════════════════════════════════

class SeedCategoriesTest(TestCase):
    """Test that default categories are seeded correctly."""

    def test_seed_creates_16_categories(self):
        seed_categories()
        self.assertEqual(Category.objects.filter(is_default=True).count(), 16)

    def test_seed_is_idempotent(self):
        seed_categories()
        seed_categories()  # Run twice
        self.assertEqual(Category.objects.filter(is_default=True).count(), 16)

    def test_seeded_categories_have_correct_slugs(self):
        seed_categories()
        expected_slugs = [
            "quotes", "thoughts", "ideas", "learn", "save", "links",
            "cinema", "read", "buy", "tasks", "reminders", "places",
            "code", "people", "projects", "important",
        ]
        for slug in expected_slugs:
            self.assertTrue(
                Category.objects.filter(slug=slug).exists(),
                f"Missing seeded category: {slug}"
            )

    def test_seed_does_not_migrate_or_delete_custom_watch_category(self):
        user = User.objects.create_user(username="watcher")
        custom_watch = Category.objects.create(
            name="Watchlist",
            slug="watch",
            user=user,
            is_default=False,
        )
        memory = Memory.objects.create(user=user, content="Custom watch memory", category=custom_watch)

        seed_categories()

        custom_watch.refresh_from_db()
        memory.refresh_from_db()
        self.assertEqual(memory.category_id, custom_watch.id)


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-CATEGORIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class AutoCategorizationTest(TestCase):
    """Test the suggest_category() auto-categorization engine."""

    def setUp(self):
        seed_categories()

    def test_detects_code_html(self):
        self.assertEqual(suggest_category("<div class='test'>Hello</div>"), "code")

    def test_detects_code_python(self):
        self.assertEqual(suggest_category("def my_function(self):"), "code")

    def test_detects_code_javascript(self):
        self.assertEqual(suggest_category("const x = async () => await fetch()"), "code")

    def test_detects_links(self):
        self.assertEqual(suggest_category("https://github.com/omtiwari17"), "links")

    def test_detects_tasks(self):
        self.assertEqual(suggest_category("todo: finish CI pipeline"), "tasks")

    def test_detects_watch_as_cinema(self):
        self.assertEqual(suggest_category("watch youtube video documentary"), "cinema")

    def test_detects_cinema(self):
        self.assertEqual(suggest_category("watch Inception movie tonight"), "cinema")

    def test_detects_shows_as_cinema(self):
        self.assertEqual(suggest_category("watch Stranger Things tv show series"), "cinema")

    def test_detects_buy(self):
        self.assertEqual(suggest_category("need to buy milk and eggs"), "buy")

    def test_detects_places(self):
        self.assertEqual(suggest_category("visit the new restaurant downtown"), "places")

    def test_plain_text_defaults_to_inbox(self):
        """Plain text with no pattern match defaults to 'inbox'."""
        result = suggest_category("hello world this is plain text")
        self.assertEqual(result, "inbox")

    def test_short_text_returns_none(self):
        """Very short text (< 5 chars) returns None."""
        result = suggest_category("hi")
        self.assertIsNone(result)


class AutoTitleTest(TestCase):
    """Test the extract_title() auto-titling engine."""

    def test_url_title_extraction(self):
        title = extract_title("https://github.com/omtiwari17/Memora")
        self.assertIn("github.com", title.lower())

    def test_html_title_extraction(self):
        html = '<html><head><title>My Page</title></head></html>'
        self.assertEqual(extract_title(html), "My Page")

    def test_plain_text_truncation(self):
        long_text = "This is a very long sentence " * 10
        title = extract_title(long_text)
        self.assertLessEqual(len(title), 120)


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(STORAGES=TEST_STORAGES)
class VaultAuthTest(TestCase):
    """Test the Vault Handle + 6-Digit PIN authentication system."""

    def setUp(self):
        self.client = Client()
        seed_categories()

    def test_login_page_loads(self):
        resp = self.client.get(reverse("login"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Vault")

    def test_register_new_user(self):
        resp = self.client.post(reverse("login"), {
            "handle": "testuser",
            "pin": "123456",
        })
        self.assertEqual(resp.status_code, 302)  # Redirect to dashboard
        self.assertTrue(User.objects.filter(username="testuser").exists())

    def test_login_existing_user(self):
        User.objects.create_user(username="existing", password="654321")
        resp = self.client.post(reverse("login"), {
            "handle": "existing",
            "pin": "654321",
        })
        self.assertEqual(resp.status_code, 302)

    def test_login_wrong_pin(self):
        User.objects.create_user(username="locked", password="111111")
        resp = self.client.post(reverse("login"), {
            "handle": "locked",
            "pin": "999999",
        })
        self.assertEqual(resp.status_code, 200)  # Stay on login page
        self.assertContains(resp, "Incorrect")

    def test_login_short_handle(self):
        resp = self.client.post(reverse("login"), {
            "handle": "x",
            "pin": "123456",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "at least 2 characters")

    def test_login_invalid_pin_format(self):
        resp = self.client.post(reverse("login"), {
            "handle": "testuser",
            "pin": "abc",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "6-digit")

    def test_logout(self):
        User.objects.create_user(username="bye", password="123456")
        self.client.login(username="bye", password="123456")
        resp = self.client.get(reverse("logout"))
        self.assertEqual(resp.status_code, 302)

    def test_handle_strips_at_symbol(self):
        resp = self.client.post(reverse("login"), {
            "handle": "@cleanhandle",
            "pin": "123456",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username="cleanhandle").exists())

    def test_authenticated_user_redirected_from_login(self):
        User.objects.create_user(username="authed", password="123456")
        self.client.login(username="authed", password="123456")
        resp = self.client.get(reverse("login"))
        self.assertEqual(resp.status_code, 302)


# ═══════════════════════════════════════════════════════════════════════════════
# URL ROUTING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class URLRoutingTest(TestCase):
    """Test that all URL patterns resolve correctly."""

    def test_home_root_url(self):
        self.assertEqual(resolve("/").url_name, "home_root")

    def test_dashboard_url(self):
        self.assertEqual(resolve("/app/").url_name, "dashboard")

    def test_login_url(self):
        self.assertEqual(resolve("/login/").url_name, "login")

    def test_logout_url(self):
        self.assertEqual(resolve("/logout/").url_name, "logout")

    def test_favicon_url(self):
        self.assertEqual(resolve("/favicon.ico").url_name, "favicon")

    def test_search_url(self):
        self.assertEqual(resolve("/search/").url_name, "search_memories")

    def test_capture_url(self):
        self.assertEqual(resolve("/capture/").url_name, "capture")

    def test_api_capture_url(self):
        self.assertEqual(resolve("/api/capture/").url_name, "capture_api")

    def test_api_suggest_category_url(self):
        self.assertEqual(resolve("/api/suggest-category/").url_name, "suggest_category")

    def test_memory_detail_url(self):
        self.assertEqual(resolve("/memory/1/").url_name, "memory_detail")

    def test_memory_edit_url(self):
        self.assertEqual(resolve("/memory/1/edit/").url_name, "memory_edit")

    def test_memory_pin_url(self):
        self.assertEqual(resolve("/memory/1/pin/").url_name, "memory_pin")

    def test_memory_archive_url(self):
        self.assertEqual(resolve("/memory/1/archive/").url_name, "memory_archive")

    def test_memory_status_url(self):
        self.assertEqual(resolve("/memory/1/status/").url_name, "memory_status")

    def test_memory_delete_url(self):
        self.assertEqual(resolve("/memory/1/delete/").url_name, "memory_delete")

    def test_inbox_url(self):
        self.assertEqual(resolve("/inbox/").url_name, "inbox")

    def test_important_url(self):
        self.assertEqual(resolve("/important/").url_name, "important")

    def test_tasks_url(self):
        self.assertEqual(resolve("/tasks/").url_name, "tasks")

    def test_reminders_url(self):
        self.assertEqual(resolve("/reminders/").url_name, "reminders")

    def test_archive_url(self):
        self.assertEqual(resolve("/archive/").url_name, "archive")

    def test_today_url(self):
        self.assertEqual(resolve("/today/").url_name, "today")

    def test_week_url(self):
        self.assertEqual(resolve("/week/").url_name, "week")

    def test_category_filter_url(self):
        self.assertEqual(resolve("/category/quotes/").url_name, "category_filter")

    def test_tag_filter_url(self):
        self.assertEqual(resolve("/tag/python/").url_name, "tag_filter")

    def test_random_url(self):
        self.assertEqual(resolve("/random/").url_name, "random_memory")

    def test_on_this_day_url(self):
        self.assertEqual(resolve("/on-this-day/").url_name, "on_this_day")

    def test_recently_viewed_url(self):
        self.assertEqual(resolve("/recently-viewed/").url_name, "recently_viewed")

    def test_categories_manage_url(self):
        self.assertEqual(resolve("/categories/").url_name, "category_manage")

    def test_categories_create_url(self):
        self.assertEqual(resolve("/categories/create/").url_name, "category_create")

    def test_share_url(self):
        self.assertEqual(resolve("/share/").url_name, "share_target")

    def test_priority_filter_url(self):
        self.assertEqual(resolve("/priority/high/").url_name, "priority_filter")


# ═══════════════════════════════════════════════════════════════════════════════
# VIEW & TEMPLATE RENDERING TESTS (authenticated)
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(STORAGES=TEST_STORAGES)
class AuthenticatedViewTest(TestCase):
    """Test that all pages render correctly for authenticated users."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="om", password="123456")
        self.client.login(username="om", password="123456")
        seed_categories()

    def test_dashboard_renders(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Memora")

    def test_inbox_renders(self):
        resp = self.client.get(reverse("inbox"))
        self.assertEqual(resp.status_code, 200)

    def test_important_renders(self):
        resp = self.client.get(reverse("important"))
        self.assertEqual(resp.status_code, 200)

    def test_tasks_renders(self):
        resp = self.client.get(reverse("tasks"))
        self.assertEqual(resp.status_code, 200)

    def test_reminders_renders(self):
        resp = self.client.get(reverse("reminders"))
        self.assertEqual(resp.status_code, 200)

    def test_archive_renders(self):
        resp = self.client.get(reverse("archive"))
        self.assertEqual(resp.status_code, 200)

    def test_today_renders(self):
        resp = self.client.get(reverse("today"))
        self.assertEqual(resp.status_code, 200)

    def test_week_renders(self):
        resp = self.client.get(reverse("week"))
        self.assertEqual(resp.status_code, 200)

    def test_category_filter_renders(self):
        resp = self.client.get(reverse("category_filter", args=["quotes"]))
        self.assertEqual(resp.status_code, 200)

    def test_random_memory_renders(self):
        resp = self.client.get(reverse("random_memory"))
        self.assertEqual(resp.status_code, 200)

    def test_recently_viewed_renders(self):
        resp = self.client.get(reverse("recently_viewed"))
        self.assertEqual(resp.status_code, 200)

    def test_category_manage_renders(self):
        resp = self.client.get(reverse("category_manage"))
        self.assertEqual(resp.status_code, 200)

    def test_search_empty_query(self):
        resp = self.client.get(reverse("search_memories"), {"q": ""})
        self.assertEqual(resp.status_code, 200)

    def test_search_with_query(self):
        Memory.objects.create(content="Django is great", user=self.user)
        resp = self.client.get(reverse("search_memories"), {"q": "Django"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Django")

    def test_capture_form_renders(self):
        resp = self.client.get(reverse("capture"))
        self.assertEqual(resp.status_code, 200)

    def test_on_this_day_renders(self):
        resp = self.client.get(reverse("on_this_day"))
        self.assertEqual(resp.status_code, 200)

    def test_priority_filter_renders(self):
        resp = self.client.get(reverse("priority_filter", args=["high"]))
        self.assertEqual(resp.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# UNAUTHENTICATED ACCESS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class UnauthenticatedAccessTest(TestCase):
    """Test that protected pages redirect to login for unauthenticated users."""

    def setUp(self):
        self.client = Client()

    def test_dashboard_requires_auth(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_inbox_requires_auth(self):
        resp = self.client.get(reverse("inbox"))
        self.assertEqual(resp.status_code, 302)

    def test_capture_requires_auth(self):
        resp = self.client.get(reverse("capture"))
        self.assertEqual(resp.status_code, 302)

    def test_category_manage_requires_auth(self):
        resp = self.client.get(reverse("category_manage"))
        self.assertEqual(resp.status_code, 302)

    def test_random_memory_requires_auth(self):
        resp = self.client.get(reverse("random_memory"))
        self.assertEqual(resp.status_code, 302)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(STORAGES=TEST_STORAGES)
class MemoryCRUDTest(TestCase):
    """Test memory capture, edit, pin, archive, status, and delete actions."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="crudtest", password="123456")
        self.client.login(username="crudtest", password="123456")
        seed_categories()

    def test_capture_memory_post(self):
        resp = self.client.post(reverse("capture"), {
            "content": "Test memory from CI",
        })
        self.assertIn(resp.status_code, [200, 302])
        self.assertTrue(Memory.objects.filter(content="Test memory from CI").exists())

    def test_memory_detail_page(self):
        mem = Memory.objects.create(content="Detail test", user=self.user)
        resp = self.client.get(reverse("memory_detail", args=[mem.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Detail test")

    def test_pin_memory(self):
        mem = Memory.objects.create(content="Pin me", user=self.user)
        resp = self.client.post(reverse("memory_pin", args=[mem.pk]))
        mem.refresh_from_db()
        self.assertTrue(mem.is_pinned)

    def test_archive_memory(self):
        mem = Memory.objects.create(content="Archive me", user=self.user)
        resp = self.client.post(reverse("memory_archive", args=[mem.pk]))
        mem.refresh_from_db()
        self.assertTrue(mem.is_archived)

    def test_delete_memory(self):
        mem = Memory.objects.create(content="Delete me", user=self.user)
        pk = mem.pk
        # memory_delete requires POST method
        resp = self.client.post(reverse("memory_delete", args=[pk]))
        self.assertFalse(Memory.objects.filter(pk=pk).exists())

    def test_update_memory_status(self):
        mem = Memory.objects.create(content="Mark done", user=self.user)
        resp = self.client.post(reverse("memory_status", args=[mem.pk]), {
            "status": "done",
        })
        mem.refresh_from_db()
        self.assertEqual(mem.status, "done")

    def test_user_cannot_see_other_users_memory(self):
        other = User.objects.create_user(username="stranger", password="654321")
        mem = Memory.objects.create(content="Secret", user=other)
        resp = self.client.get(reverse("memory_detail", args=[mem.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_capture_memory_htmx_oob_swaps(self):
        resp = self.client.post(
            reverse("capture"),
            {"content": "New memory via HTMX"},
            HTTP_HX_REQUEST="true"
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('hx-swap-oob="afterbegin"', content)
        self.assertIn('id="stat-total-count"', content)
        self.assertIn("New memory via HTMX", content)

    def test_pin_memory_detail_target(self):
        mem = Memory.objects.create(content="Pin detail test", user=self.user)
        resp = self.client.post(
            reverse("memory_pin", args=[mem.pk]),
            HTTP_HX_TARGET="detail-pin-btn"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Unpin", resp.content.decode())

    def test_archive_memory_detail_redirect(self):
        mem = Memory.objects.create(content="Archive detail test", user=self.user)
        resp = self.client.post(
            reverse("memory_archive", args=[mem.pk]),
            HTTP_HX_REQUEST="true",
            HTTP_HX_CURRENT_URL=f"http://testserver/memory/{mem.pk}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("HX-Redirect"), reverse("dashboard"))

    def test_delete_memory_detail_redirect(self):
        mem = Memory.objects.create(content="Delete detail test", user=self.user)
        resp = self.client.post(
            reverse("memory_delete", args=[mem.pk]),
            HTTP_HX_REQUEST="true",
            HTTP_HX_CURRENT_URL=f"http://testserver/memory/{mem.pk}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("HX-Redirect"), reverse("dashboard"))

    def test_update_memory_status_detail_target(self):
        tasks_cat = Category.objects.filter(slug="tasks").first()
        mem = Memory.objects.create(content="Task item", user=self.user, category=tasks_cat)
        resp = self.client.post(
            reverse("memory_status", args=[mem.pk]),
            {"status": "done"},
            HTTP_HX_TARGET="detail-status-btn"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Undo Done", resp.content.decode())


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY MANAGEMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(STORAGES=TEST_STORAGES)
class CategoryManagementTest(TestCase):
    """Test category CRUD and reordering."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="catman", password="123456")
        self.client.login(username="catman", password="123456")
        seed_categories()

    def test_create_category(self):
        resp = self.client.post(reverse("category_create"), {
            "name": "Custom Cat",
            "color": "#ff00ff",
        })
        self.assertIn(resp.status_code, [200, 302])
        self.assertTrue(Category.objects.filter(name="Custom Cat").exists())

    def test_cannot_create_duplicate_matching_default_category(self):
        """Cannot create a category with the same name or slug as a default category."""
        resp = self.client.post(reverse("category_create"), {
            "name": "Quotes",
            "color": "#ee5253",
        })
        self.assertEqual(resp.status_code, 302)
        # Should still be exactly 1 Quotes category (the default one)
        self.assertEqual(Category.objects.filter(name__iexact="Quotes").count(), 1)

    def test_cannot_create_duplicate_custom_category(self):
        """Cannot create two custom categories with the same name."""
        self.client.post(reverse("category_create"), {
            "name": "Unique Tag Cat",
            "color": "#38bdf8",
        })
        self.assertEqual(Category.objects.filter(name="Unique Tag Cat").count(), 1)

        # Attempt to create duplicate (case-insensitive)
        resp = self.client.post(reverse("category_create"), {
            "name": "unique tag cat",
            "color": "#f472b6",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Category.objects.filter(name__iexact="Unique Tag Cat").count(), 1)

    def test_cannot_edit_category_to_duplicate_name(self):
        """Cannot edit a category to a name that already exists."""
        cat_a = Category.objects.create(name="Alpha", slug="alpha", user=self.user)
        cat_b = Category.objects.create(name="Beta", slug="beta", user=self.user)

        resp = self.client.post(reverse("category_edit", args=[cat_b.pk]), {
            "name": "Alpha",
            "color": "#a78bfa",
        })
        self.assertEqual(resp.status_code, 302)
        cat_b.refresh_from_db()
        self.assertEqual(cat_b.name, "Beta")  # Name should remain Beta

    def test_delete_category(self):
        cat = Category.objects.create(
            name="Deletable", slug="deletable", user=self.user
        )
        resp = self.client.post(reverse("category_delete", args=[cat.pk]))
        self.assertFalse(Category.objects.filter(pk=cat.pk).exists())

    def test_cannot_edit_another_users_category(self):
        other_user = User.objects.create_user(username="othercat")
        other_cat = Category.objects.create(name="Other", slug="other", user=other_user)

        resp = self.client.post(reverse("category_edit", args=[other_cat.pk]), {
            "name": "Renamed",
            "color": "#a78bfa",
        })

        self.assertEqual(resp.status_code, 404)
        other_cat.refresh_from_db()
        self.assertEqual(other_cat.name, "Other")

    def test_cannot_delete_another_users_category(self):
        other_user = User.objects.create_user(username="otherdelete")
        other_cat = Category.objects.create(name="OtherDelete", slug="other-delete", user=other_user)

        resp = self.client.post(reverse("category_delete", args=[other_cat.pk]))

        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Category.objects.filter(pk=other_cat.pk).exists())


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class APIEndpointTest(TestCase):
    """Test the JSON API endpoints."""

    def setUp(self):
        self.client = Client()
        seed_categories()

    def test_capture_api_creates_memory(self):
        import json
        resp = self.client.post(
            reverse("capture_api"),
            json.dumps({"content": "API test memory"}),
            content_type="application/json",
        )
        # capture_api returns 201 on success
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertIsNotNone(data.get("memory_id"))

    def test_capture_api_rejects_empty_content(self):
        import json
        resp = self.client.post(
            reverse("capture_api"),
            json.dumps({"content": ""}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_capture_api_rejects_get(self):
        resp = self.client.get(reverse("capture_api"))
        self.assertEqual(resp.status_code, 405)

    @override_settings(STORAGES=TEST_STORAGES)
    def test_suggest_category_api(self):
        self.user = User.objects.create_user(username="apitest", password="123456")
        self.client.login(username="apitest", password="123456")
        # suggest_category_api uses 'content' param and returns {"suggestion": {...}}
        resp = self.client.get(
            reverse("suggest_category"),
            {"content": "need to buy milk and eggs"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        suggestion = data.get("suggestion")
        self.assertIsNotNone(suggestion)
        self.assertEqual(suggestion.get("slug"), "buy")


# ═══════════════════════════════════════════════════════════════════════════════
# FAVICON & STATIC TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class FaviconTest(TestCase):
    """Test that the favicon endpoint serves the SVG logo."""

    def test_favicon_serves_svg(self):
        resp = self.client.get("/favicon.ico")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "image/svg+xml")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA ISOLATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(STORAGES=TEST_STORAGES)
class DataIsolationTest(TestCase):
    """Ensure memories, categories, and collections are user-scoped."""

    def setUp(self):
        self.user_a = User.objects.create_user(username="alice", password="123456")
        self.user_b = User.objects.create_user(username="bob", password="654321")
        seed_categories()

        Memory.objects.create(content="Alice secret", user=self.user_a)
        Memory.objects.create(content="Bob secret", user=self.user_b)

    def test_user_only_sees_own_memories_on_dashboard(self):
        client = Client()
        client.login(username="alice", password="123456")
        resp = client.get(reverse("dashboard"))
        self.assertContains(resp, "Alice secret")
        self.assertNotContains(resp, "Bob secret")

    def test_search_is_user_scoped(self):
        client = Client()
        client.login(username="bob", password="654321")
        resp = client.get(reverse("search_memories"), {"q": "Alice"})
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertNotIn("Alice secret", content)


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM ADMIN CONSOLE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(STORAGES=TEST_STORAGES)
class CustomAdminConsoleTest(TestCase):
    """Test custom glassmorphic admin dashboard and access control."""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(username="staffadmin", password="123456", is_staff=True)
        self.normal_user = User.objects.create_user(username="regularuser", password="123456")
        seed_categories()

    def test_custom_admin_accessible_by_staff(self):
        self.client.post(reverse("admin_vault_login"), {"handle": "staffadmin", "pin": "123456"})
        resp = self.client.get(reverse("custom_admin_panel"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Control Console")

    def test_custom_admin_redirects_normal_user_to_admin_login(self):
        self.client.login(username="regularuser", password="123456")
        resp = self.client.get(reverse("custom_admin_panel"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("ctrl/login", resp.url)

    def test_admin_login_rejects_normal_user(self):
        resp = self.client.post(reverse("admin_vault_login"), {
            "handle": "regularuser",
            "pin": "123456",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Access Denied")

    def test_admin_login_authenticates_staff(self):
        resp = self.client.post(reverse("admin_vault_login"), {
            "handle": "staffadmin",
            "pin": "123456",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("ctrl", resp.url)

    def test_admin_logout(self):
        self.client.login(username="staffadmin", password="123456")
        resp = self.client.get(reverse("admin_vault_logout"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("ctrl/login", resp.url)


# ═══════════════════════════════════════════════════════════════════════════════
# MOVIE & WATCH STATUS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(STORAGES=TEST_STORAGES)
class MovieWatchStatusTest(TestCase):
    """Test movie watch status options and star rating functionality."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="moviebuff", password="123456")
        self.client.login(username="moviebuff", password="123456")
        seed_categories()
        self.cinema_cat = Category.objects.get(slug="cinema")

    def test_create_movie_with_watch_status_and_rating(self):
        memory = Memory.objects.create(
            user=self.user,
            title="Inception",
            content="Great sci-fi thriller",
            category=self.cinema_cat,
            watch_status=Memory.WatchStatus.WATCHED,
            rating=5
        )
        self.assertEqual(memory.watch_status, "watched")
        self.assertEqual(memory.rating, 5)

    def test_update_watch_status_via_htmx(self):
        memory = Memory.objects.create(
            user=self.user,
            title="Interstellar",
            content="Space exploration movie",
            category=self.cinema_cat,
            watch_status=Memory.WatchStatus.WANT_TO_WATCH,
        )
        resp = self.client.post(
            reverse("memory_watch_status", kwargs={"pk": memory.pk}),
            {"watch_status": "watched", "rating": "5"},
        )
        self.assertEqual(resp.status_code, 200)
        memory.refresh_from_db()
        self.assertEqual(memory.watch_status, "watched")
        self.assertEqual(memory.rating, 5)
        self.assertContains(resp, "Watched")


@override_settings(STORAGES=TEST_STORAGES)
class IconAndFaviconAssetsTest(TestCase):
    """Test favicon endpoint and static icon availability for PWA and mobile shortcuts."""

    def test_favicon_endpoint_serves_logo_svg(self):
        client = Client()
        resp = client.get(reverse("favicon"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "image/svg+xml")
        content = b"".join(resp.streaming_content)
        self.assertIn(b"svg", content)


@override_settings(STORAGES=TEST_STORAGES)
class WebPushNotificationTest(TestCase):
    """Test Web Push API endpoints and subscription lifecycle."""

    def setUp(self):
        self.user = User.objects.create_user(username="pushuser", password="password123")
        self.client = Client()
        self.client.force_login(self.user)

    def test_vapid_public_key_endpoint(self):
        resp = self.client.get(reverse("vapid_public_key"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("public_key", data)

    def test_push_subscribe_and_unsubscribe(self):
        # Subscribe
        payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test-token-123",
            "keys": {
                "p256dh": "test-p256dh-key",
                "auth": "test-auth-key"
            }
        }
        resp = self.client.post(
            reverse("push_subscribe"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PushSubscription.objects.count(), 1)
        sub = PushSubscription.objects.first()
        self.assertEqual(sub.user, self.user)
        self.assertEqual(sub.p256dh, "test-p256dh-key")

        # Unsubscribe
        unsub_payload = {"endpoint": "https://fcm.googleapis.com/fcm/send/test-token-123"}
        resp = self.client.post(
            reverse("push_unsubscribe"),
            data=json.dumps(unsub_payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_due_reminders_api(self):
        from datetime import timedelta
        now = timezone.now()
        Memory.objects.create(
            user=self.user,
            title="Important Meeting",
            content="Project sync with team",
            reminder_at=now - timedelta(minutes=10)
        )
        resp = self.client.get(reverse("due_reminders_api"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["due_reminders"][0]["title"], "Important Meeting")

    def test_service_worker_endpoint(self):
        resp = self.client.get(reverse("service_worker"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/javascript")
        self.assertEqual(resp["Service-Worker-Allowed"], "/")

    def test_trigger_due_reminders_get_and_post(self):
        # GET request
        resp_get = self.client.get(reverse("trigger_due_reminders"))
        self.assertEqual(resp_get.status_code, 200)
        data_get = resp_get.json()
        self.assertIn("status", data_get)

        # POST request
        resp_post = self.client.post(reverse("trigger_due_reminders"))
        self.assertEqual(resp_post.status_code, 200)
        data_post = resp_post.json()
        self.assertIn("status", data_post)

    def test_trigger_reminders_command(self):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command("trigger_reminders", stdout=out)
        self.assertIn("Reminders dispatched successfully", out.getvalue())

    def test_reminder_sent_flag_and_reset(self):
        from datetime import timedelta
        from unittest.mock import patch
        from quotes.views import dispatch_due_reminders

        now = timezone.now()
        mem = Memory.objects.create(
            user=self.user,
            title="Dentist Appointment",
            content="Checkup at 3pm",
            reminder_at=now - timedelta(minutes=5),
            reminder_sent=False
        )
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://fcm.googleapis.com/fcm/send/test-token",
            p256dh="test_p256dh",
            auth="test_auth"
        )

        with patch("pywebpush.webpush") as mock_push:
            mock_push.return_value = None
            res = dispatch_due_reminders()
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["sent_notifications"], 1)

        mem.refresh_from_db()
        self.assertTrue(mem.reminder_sent)

        # Updating reminder date resets reminder_sent
        resp = self.client.post(reverse("memory_edit", args=[mem.id]), {
            "content": "Checkup at 4pm",
            "title": "Dentist Appointment",
            "due_date": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
        })
        self.assertEqual(resp.status_code, 200)
        mem.refresh_from_db()
        self.assertFalse(mem.reminder_sent)


class CinemaWatchStatusSortAndFilterTests(TestCase):
    """Test suite for Cinema watch status filtering and sorting."""

    def setUp(self):
        self.user = User.objects.create_user(username="cinemafan", password="testpassword123")
        self.other_user = User.objects.create_user(username="othercritic", password="testpassword123")
        self.client.force_login(self.user)

        self.cinema_cat, _ = Category.objects.get_or_create(
            slug="cinema",
            defaults={"name": "Cinema", "color": "#e11d48", "is_default": True}
        )

        self.movie_want = Memory.objects.create(
            user=self.user,
            title="Dune: Part Two",
            content="Epic sci-fi continuation by Denis Villeneuve",
            category=self.cinema_cat,
            watch_status=Memory.WatchStatus.WANT_TO_WATCH,
            rating=None
        )
        self.movie_watching = Memory.objects.create(
            user=self.user,
            title="Shogun",
            content="Historical drama series set in feudal Japan",
            category=self.cinema_cat,
            watch_status=Memory.WatchStatus.WATCHING,
            rating=None
        )
        self.movie_watched_top = Memory.objects.create(
            user=self.user,
            title="Oppenheimer",
            content="Biographical drama masterpiece",
            category=self.cinema_cat,
            watch_status=Memory.WatchStatus.WATCHED,
            rating=5
        )
        self.movie_watched_mid = Memory.objects.create(
            user=self.user,
            title="Random Action Movie",
            content="Average weekend popcorn flick",
            category=self.cinema_cat,
            watch_status=Memory.WatchStatus.WATCHED,
            rating=3
        )

        # Other user's memory (for isolation tests)
        self.other_movie = Memory.objects.create(
            user=self.other_user,
            title="Secret Movie",
            content="Private watchlist item",
            category=self.cinema_cat,
            watch_status=Memory.WatchStatus.WATCHING,
            rating=5
        )

    def test_cinema_view_stats_and_context(self):
        """Cinema category view provides cinema_stats and is_cinema_view flag."""
        resp = self.client.get(reverse("category_filter", kwargs={"filter_value": "cinema"}))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["is_cinema_view"])
        stats = resp.context["cinema_stats"]
        self.assertEqual(stats["all"], 4)
        self.assertEqual(stats["want_to_watch"], 1)
        self.assertEqual(stats["watching"], 1)
        self.assertEqual(stats["watched"], 2)
        self.assertContains(resp, "Want to Watch")
        self.assertContains(resp, "Watching")
        self.assertContains(resp, "Watched")

    def test_cinema_filter_by_want_to_watch(self):
        """Filtering by watch_status=want_to_watch returns only want_to_watch movies."""
        resp = self.client.get(
            reverse("category_filter", kwargs={"filter_value": "cinema"}),
            {"watch_status": "want_to_watch"}
        )
        self.assertEqual(resp.status_code, 200)
        memories = list(resp.context["memories"])
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].id, self.movie_want.id)

    def test_cinema_filter_by_watching(self):
        """Filtering by watch_status=watching returns only currently watching movies."""
        resp = self.client.get(
            reverse("category_filter", kwargs={"filter_value": "cinema"}),
            {"watch_status": "watching"}
        )
        self.assertEqual(resp.status_code, 200)
        memories = list(resp.context["memories"])
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].id, self.movie_watching.id)

    def test_cinema_filter_by_watched(self):
        """Filtering by watch_status=watched returns only watched movies."""
        resp = self.client.get(
            reverse("category_filter", kwargs={"filter_value": "cinema"}),
            {"watch_status": "watched"}
        )
        self.assertEqual(resp.status_code, 200)
        memories = list(resp.context["memories"])
        self.assertEqual(len(memories), 2)
        self.assertIn(self.movie_watched_top, memories)
        self.assertIn(self.movie_watched_mid, memories)

    def test_cinema_sort_by_want_to_watch_first(self):
        """Sorting with sort=want_to_watch orders want_to_watch first, then watching, then watched."""
        resp = self.client.get(
            reverse("category_filter", kwargs={"filter_value": "cinema"}),
            {"sort": "want_to_watch"}
        )
        self.assertEqual(resp.status_code, 200)
        memories = list(resp.context["memories"])
        self.assertEqual(memories[0].id, self.movie_want.id)
        self.assertEqual(memories[1].id, self.movie_watching.id)
        self.assertEqual(memories[2].watch_status, Memory.WatchStatus.WATCHED)
        self.assertEqual(memories[3].watch_status, Memory.WatchStatus.WATCHED)

    def test_cinema_sort_by_watching_first(self):
        """Sorting with sort=watching orders watching first, then want_to_watch, then watched."""
        resp = self.client.get(
            reverse("category_filter", kwargs={"filter_value": "cinema"}),
            {"sort": "watching"}
        )
        self.assertEqual(resp.status_code, 200)
        memories = list(resp.context["memories"])
        self.assertEqual(memories[0].id, self.movie_watching.id)
        self.assertEqual(memories[1].id, self.movie_want.id)
        self.assertEqual(memories[2].watch_status, Memory.WatchStatus.WATCHED)
        self.assertEqual(memories[3].watch_status, Memory.WatchStatus.WATCHED)

    def test_cinema_sort_by_watched_first(self):
        """Sorting with sort=watched orders watched first, then watching, then want_to_watch."""
        resp = self.client.get(
            reverse("category_filter", kwargs={"filter_value": "cinema"}),
            {"sort": "watched"}
        )
        self.assertEqual(resp.status_code, 200)
        memories = list(resp.context["memories"])
        self.assertEqual(memories[0].watch_status, Memory.WatchStatus.WATCHED)
        self.assertEqual(memories[1].watch_status, Memory.WatchStatus.WATCHED)
        self.assertEqual(memories[2].id, self.movie_watching.id)
        self.assertEqual(memories[3].id, self.movie_want.id)

    def test_cinema_sort_by_rating(self):
        """Sorting by rating orders highest rated first (5 stars before 3 stars)."""
        resp = self.client.get(
            reverse("category_filter", kwargs={"filter_value": "cinema"}),
            {"sort": "rating"}
        )
        self.assertEqual(resp.status_code, 200)
        memories = list(resp.context["memories"])
        self.assertEqual(memories[0].id, self.movie_watched_top.id)
        self.assertEqual(memories[1].id, self.movie_watched_mid.id)

    def test_cinema_htmx_partial_swap(self):
        """HTMX requests targeted at cinema-container return cinema_container.html partial."""
        resp = self.client.get(
            reverse("category_filter", kwargs={"filter_value": "cinema"}),
            {"watch_status": "watching"},
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="cinema-container"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "quotes/partials/cinema_container.html")
        self.assertContains(resp, "Shogun")

    def test_cinema_search_with_watch_status_and_sort(self):
        """Search inside cinema respects watch_status filter."""
        resp = self.client.get(
            reverse("search_memories"),
            {"q": "drama", "category": "cinema", "watch_status": "watched"}
        )
        self.assertEqual(resp.status_code, 200)
        memories = list(resp.context["memories"])
        # Oppenheimer and Random Action Movie both might match or Oppenheimer matches 'drama'
        self.assertIn(self.movie_watched_top, memories)
        self.assertNotIn(self.movie_watching, memories)  # Shogun is watching, not watched

    def test_cinema_user_data_isolation(self):
        """Cinema memories and stats are strictly user-isolated."""
        resp = self.client.get(reverse("category_filter", kwargs={"filter_value": "cinema"}))
        self.assertEqual(resp.status_code, 200)
        memories = list(resp.context["memories"])
        self.assertNotIn(self.other_movie, memories)
        stats = resp.context["cinema_stats"]
        self.assertEqual(stats["watching"], 1)  # Only self.movie_watching, not other_user's


