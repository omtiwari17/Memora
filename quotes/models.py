from django.db import models
from django.contrib.auth.models import User
import random


class Category(models.Model):
    """User-defined or system-default categories for organizing memories."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="categories")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    emoji = models.CharField(max_length=10, default="")
    color = models.CharField(max_length=7, default="#a78bfa")  # hex color for UI
    is_default = models.BooleanField(default=False)  # True for system categories
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Tags for cross-cutting concerns. Categories = what kind, Tags = what about."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Collection(models.Model):
    """Named groups of related memories (e.g. 'Trip to Goa', '2026 Projects')."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="collections")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class Memory(models.Model):
    """The core model — anything worth remembering."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="memories")

    class Status(models.TextChoices):
        INBOX = "inbox", "Inbox"
        ACTIVE = "active", "Active"
        DONE = "done", "Done"
        ARCHIVED = "archived", "Archived"

    class Priority(models.TextChoices):
        NONE = "none", "None"
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class WatchStatus(models.TextChoices):
        WANT_TO_WATCH = "want_to_watch", "Want to Watch"
        WATCHING = "watching", "Watching"
        WATCHED = "watched", "Watched"

    # Core content
    title = models.CharField(max_length=500, blank=True)
    content = models.TextField()

    # Classification
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="memories"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="memories")
    collections = models.ManyToManyField(Collection, blank=True, related_name="memories")

    # Movie / Watch specific
    watch_status = models.CharField(
        max_length=20, choices=WatchStatus.choices, default=WatchStatus.WANT_TO_WATCH, blank=True
    )
    rating = models.IntegerField(null=True, blank=True)  # 1 to 5 stars

    # Source / provenance
    source_url = models.URLField(max_length=2000, blank=True)
    source_title = models.CharField(max_length=500, blank=True)
    author = models.CharField(max_length=255, blank=True)

    # Temporal
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)
    reminder_at = models.DateTimeField(null=True, blank=True)

    # State
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.INBOX
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.NONE
    )
    is_pinned = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "memories"

    def __str__(self):
        return self.title or self.content[:80]

    @classmethod
    def random_memory(cls):
        """Return a random non-archived memory for the 'Remember This' feature."""
        memories = cls.objects.filter(is_archived=False)
        count = memories.count()
        if count == 0:
            return None
        return memories[random.randint(0, count - 1)]
