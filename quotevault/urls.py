from django.urls import path, include

urlpatterns = [
    path("", include("quotes.urls")),
]

handler404 = "quotes.views.custom_404_view"
handler500 = "quotes.views.custom_500_view"
handler403 = "quotes.views.custom_403_view"
handler400 = "quotes.views.custom_400_view"
