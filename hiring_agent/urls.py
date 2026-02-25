from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('hiring.urls')),
    path('admin/', admin.site.urls),
    path('recruiter/', include('hiring.urls_recruiter')),
    path('candidate/', include('hiring.urls_candidate')),
    path('api/', include('hiring.urls_api')),
    path('accounts/profile/', RedirectView.as_view(url='/recruiter/dashboard/')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
