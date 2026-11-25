from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    path('timetable/', views.timetable_view, name='timetable'),
    path('timetable/new/', views.timetable_slot_create_view, name='timetable_slot_create'),
    path('activity-logs/', views.activity_log_list_view, name='activity_log_list'),
    path('activity-logs/new/', views.activity_log_create_view, name='activity_log_create'),
    path('attendance/', views.attendance_dashboard_view, name='attendance_dashboard'),
    path('attendance/mark/', views.attendance_mark_view, name='attendance_mark'),
    path('exams/', views.exam_list_view, name='exam_list'),
    path('exams/new/', views.exam_create_view, name='exam_create'),
    path('exams/<int:exam_id>/toggle-readiness/', views.exam_toggle_readiness_view, name='exam_toggle_readiness'),
]

