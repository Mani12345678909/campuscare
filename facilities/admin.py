from django.contrib import admin
from .models import Room, Asset


class AssetInline(admin.TabularInline):
    model = Asset
    extra = 1
    fields = ('name', 'asset_tag', 'category', 'status', 'installed_on')


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        'building_code',
        'room_number',
        'building_name',
        'room_type',
        'operational_status',
        'floor',
        'capacity',
        'is_active',
    )
    list_filter = ('operational_status', 'building_name', 'room_type', 'is_active', 'floor')
    search_fields = ('building_name', 'building_code', 'room_number')
    ordering = ('building_code', 'room_number')
    inlines = [AssetInline]


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        'asset_tag',
        'name',
        'room',
        'category',
        'status',
        'installed_on',
    )
    list_filter = ('category', 'status', 'room__building_name')
    search_fields = ('name', 'asset_tag', 'room__room_number', 'room__building_name')
    ordering = ('room', 'name')
