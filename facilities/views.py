from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Q
from django.contrib import messages
from .models import Room, Asset
from .forms import RoomForm, AssetForm
from accounts.permissions import manager_required


@login_required
def room_list_view(request):
    """
    Lists rooms with search, filters, asset counts, and active ticket counts.
    """
    search_query = request.GET.get('q', '').strip()
    building_filter = request.GET.get('building', '').strip()
    type_filter = request.GET.get('room_type', '').strip()

    rooms = Room.objects.annotate(
        asset_count=Count('assets', distinct=True),
        open_ticket_count=Count(
            'maintenance_requests',
            filter=~Q(maintenance_requests__status__in=['RESOLVED', 'CLOSED']),
            distinct=True
        )
    ).order_by('building_code', 'room_number')

    if search_query:
        rooms = rooms.filter(
            Q(building_name__icontains=search_query) |
            Q(building_code__icontains=search_query) |
            Q(room_number__icontains=search_query)
        )

    if building_filter:
        rooms = rooms.filter(building_code=building_filter)

    if type_filter:
        rooms = rooms.filter(room_type=type_filter)

    buildings = Room.objects.values('building_code', 'building_name').distinct()

    return render(request, 'facilities/room_list.html', {
        'rooms': rooms,
        'buildings': buildings,
        'search_query': search_query,
        'building_filter': building_filter,
        'type_filter': type_filter,
        'room_types': Room.RoomType.choices,
    })


@login_required
def room_detail_view(request, room_id):
    """
    Detailed view of a room, including all registered assets and maintenance tickets.
    """
    room = get_object_or_404(Room, pk=room_id)
    assets = room.assets.all().order_by('category', 'name')
    tickets = room.maintenance_requests.select_related('reported_by', 'assigned_to', 'asset').order_by('-created_at')

    return render(request, 'facilities/room_detail.html', {
        'room': room,
        'assets': assets,
        'tickets': tickets,
    })


@login_required
@manager_required
def room_create_view(request):
    """
    Managers/Admins can add new rooms.
    """
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save()
            messages.success(request, f"Room {room.building_code} {room.room_number} created successfully.")
            return redirect('facilities:room_detail', room_id=room.id)
    else:
        form = RoomForm()

    return render(request, 'facilities/room_form.html', {
        'form': form,
        'title': 'Add New Classroom / Facility',
    })


@login_required
@manager_required
def asset_create_view(request):
    """
    Managers/Admins can add an asset.
    """
    initial_data = {}
    room_id = request.GET.get('room')
    if room_id:
        initial_data['room'] = room_id

    if request.method == 'POST':
        form = AssetForm(request.POST)
        if form.is_valid():
            asset = form.save()
            messages.success(request, f"Asset '{asset.name}' [{asset.asset_tag}] registered successfully.")
            return redirect('facilities:room_detail', room_id=asset.room.id)
    else:
        form = AssetForm(initial=initial_data)

    return render(request, 'facilities/asset_form.html', {
        'form': form,
        'title': 'Register Room Equipment / Asset',
    })


@login_required
def room_assets_api(request, room_id):
    """
    API endpoint returning assets belonging to a specified room in JSON.
    Used for dynamic client-side filtering on ticket submission.
    """
    assets = Asset.objects.filter(room_id=room_id).order_by('name')
    data = [
        {
            'id': asset.id,
            'name': asset.name,
            'tag': asset.asset_tag,
            'category': asset.category,
            'status': asset.status,
            'status_display': asset.get_status_display(),
        }
        for asset in assets
    ]
    return JsonResponse({'assets': data})
