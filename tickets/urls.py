from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.ticket_list_view, name='ticket_list'),
    path('new/', views.ticket_create_view, name='ticket_create'),
    path('api/check-duplicates/', views.check_duplicates_api, name='check_duplicates_api'),
    path('<str:ticket_code>/', views.ticket_detail_view, name='ticket_detail'),
    path('<str:ticket_code>/update-status/', views.ticket_update_status_view, name='ticket_update_status'),
    path('<str:ticket_code>/assign/', views.ticket_assign_view, name='ticket_assign'),
]

