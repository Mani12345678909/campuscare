from django.urls import path
from . import views

app_name = 'notices'

urlpatterns = [
    path('announcements/', views.announcement_list_view, name='announcement_list'),
    path('announcements/new/', views.announcement_create_view, name='announcement_create'),
    path('announcements/<int:announcement_id>/', views.announcement_detail_view, name='announcement_detail'),
    path('fees/', views.fee_tracker_view, name='fee_tracker'),
    path('fees/new/', views.fee_create_view, name='fee_create'),
    path('feed/', views.live_feed_view, name='live_feed'),
    path('reports/', views.reports_hub_view, name='reports_hub'),
    path('reports/maintenance/csv/', views.export_maintenance_csv, name='export_maintenance_csv'),
    path('reports/attendance/csv/', views.export_attendance_csv, name='export_attendance_csv'),
    path('reports/teacher-activity/csv/', views.export_teacher_activity_csv, name='export_teacher_activity_csv'),
]

