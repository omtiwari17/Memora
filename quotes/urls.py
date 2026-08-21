from django.urls import path
from . import views

urlpatterns = [
    # Auth, Landing, Health Ping & Favicon
    path("welcome/", views.landing_page, name="landing"),
    path("landing/", views.landing_page, name="landing_page"),
    path("about/", views.landing_page, name="about"),
    path("healthz/", views.health_check, name="health_check"),
    path("ping/", views.health_check, name="ping"),
    path("login/", views.vault_login, name="login"),
    path("logout/", views.vault_logout, name="logout"),
    path("favicon.ico", views.favicon_view, name="favicon"),

    # Custom Admin Console & Dedicated Login
    path("ctrl/login/", views.admin_vault_login, name="admin_vault_login"),
    path("ctrl/logout/", views.admin_vault_logout, name="admin_vault_logout"),
    path("ctrl/", views.custom_admin_panel, name="custom_admin_panel"),
    path("ctrl/user/<int:user_id>/toggle-staff/", views.admin_toggle_staff, name="admin_toggle_staff"),

    # Dashboard
    path("", views.dashboard, name="dashboard"),
    
    # Search
    path("search/", views.search_memories, name="search_memories"),
    
    # Capture
    path("capture/", views.capture, name="capture"),
    path("api/capture/", views.capture_api, name="capture_api"),
    path("api/suggest-category/", views.suggest_category_api, name="suggest_category"),
    
    # Memory actions
    path("memory/<int:pk>/", views.memory_detail, name="memory_detail"),
    path("memory/<int:pk>/edit/", views.memory_edit, name="memory_edit"),
    path("memory/<int:pk>/pin/", views.memory_pin, name="memory_pin"),
    path("memory/<int:pk>/archive/", views.memory_archive, name="memory_archive"),
    path("memory/<int:pk>/status/", views.memory_status, name="memory_status"),
    path("memory/<int:pk>/watch-status/", views.memory_watch_status, name="memory_watch_status"),
    path("memory/<int:pk>/delete/", views.memory_delete, name="memory_delete"),
    
    # Filtered views
    path("inbox/", views.memory_list, {"filter_type": "inbox"}, name="inbox"),
    path("important/", views.memory_list, {"filter_type": "important"}, name="important"),
    path("tasks/", views.memory_list, {"filter_type": "tasks"}, name="tasks"),
    path("reminders/", views.memory_list, {"filter_type": "reminders"}, name="reminders"),
    path("priority/<str:filter_value>/", views.memory_list, {"filter_type": "priority"}, name="priority_filter"),
    path("archive/", views.memory_list, {"filter_type": "archive"}, name="archive"),
    path("today/", views.memory_list, {"filter_type": "today"}, name="today"),
    path("week/", views.memory_list, {"filter_type": "week"}, name="week"),
    path("category/<slug:filter_value>/", views.memory_list, {"filter_type": "category"}, name="category_filter"),
    path("tag/<slug:filter_value>/", views.memory_list, {"filter_type": "tag"}, name="tag_filter"),
    
    # Category Management
    path("categories/", views.category_manage, name="category_manage"),
    path("categories/create/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("categories/<int:pk>/reorder/<str:direction>/", views.category_reorder, name="category_reorder"),
    
    # Phase 5 — Memory Features
    path("random/", views.random_memory, name="random_memory"),
    path("on-this-day/", views.memory_list, {"filter_type": "on_this_day"}, name="on_this_day"),
    path("recently-viewed/", views.recently_viewed, name="recently_viewed"),
    
    # PWA
    path("share/", views.share_target, name="share_target"),
]
