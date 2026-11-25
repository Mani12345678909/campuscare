from django.urls import path
from . import views

app_name = 'facilities'

urlpatterns = [
    path('rooms/', views.room_list_view, name='room_list'),
    path('rooms/create/', views.room_create_view, name='room_create'),
    path('rooms/<int:room_id>/', views.room_detail_view, name='room_detail'),
    path('assets/create/', views.asset_create_view, name='asset_create'),
    path('api/rooms/<int:room_id>/assets/', views.room_assets_api, name='room_assets_api'),
]

