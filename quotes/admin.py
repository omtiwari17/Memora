from django.contrib import admin
from .models import Memory, Category, Tag, Collection


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("emoji", "name", "slug", "is_default", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")


@admin.register(Memory)
class MemoryAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "priority", "is_pinned", "created_at")
    list_filter = ("category", "status", "priority", "is_pinned", "is_archived")
    search_fields = ("title", "content", "author", "source_url")
    filter_horizontal = ("tags", "collections")
