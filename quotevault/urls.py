from django.contrib import admin
from django.urls import path, include

# Hidden admin URL — not the default /admin/ to prevent brute-force attacks
admin.site.site_header = "Memora Vault Control"
admin.site.site_title = "Memora Admin"
admin.site.index_title = "Database Management"

urlpatterns = [
    path("vault-control/", admin.site.urls),
    path("", include("quotes.urls")),
]
