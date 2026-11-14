
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path(
        'citizen/dashboard/',
        views.citizen_dashboard,
        name='citizen_dashboard'
    ),

    path(
        'rescue/dashboard/',
        views.rescue_dashboard,
        name='rescue_dashboard'
    ),
    path(
        'citizen/report-incident/',
        views.report_incident,
        name='report_incident'
    ),
    path(
        'citizen/sync-offline-report/',
        views.sync_offline_report,
        name='sync_offline_report'
    ),

    path(
    'citizen/my-reports/',
    views.my_reports,
    name='my_reports'
    ),
    path(
    'citizen/my-reports/<int:incident_id>/',
    views.incident_detail,
    name='incident_detail'
    ),
    path(
    'citizen/notifications/',
    views.notifications,
    name='notifications'
    ),
]
