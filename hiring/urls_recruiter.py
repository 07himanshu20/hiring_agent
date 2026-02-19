<<<<<<< HEAD
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path('login/', LoginView.as_view(
        template_name='recruiter/login.html',
        redirect_authenticated_user=True
    ), name='recruiter_login'),
    
    path('logout/', LogoutView.as_view(), name='recruiter_logout'),
    path('dashboard/', views.recruiter_dashboard, name='recruiter_dashboard'),
    path('create_role/', views.create_hiring_request, name='create_hiring_request'),
    path('results/<uuid:request_id>/', views.view_results, name='view_results'),
    path('api/candidates/<uuid:request_id>/', views.get_candidate_results, name='get_candidate_results'),
=======
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path('login/', LoginView.as_view(
        template_name='recruiter/login.html',
        redirect_authenticated_user=True
    ), name='recruiter_login'),
    
    path('logout/', LogoutView.as_view(), name='recruiter_logout'),
    path('dashboard/', views.recruiter_dashboard, name='recruiter_dashboard'),
    path('create_role/', views.create_hiring_request, name='create_hiring_request'),
    path('results/<uuid:request_id>/', views.view_results, name='view_results'),
    path('api/candidates/<uuid:request_id>/', views.get_candidate_results, name='get_candidate_results'),
>>>>>>> 45714fc9bb77db1a37f345b9f3c925e550b03dcb
]