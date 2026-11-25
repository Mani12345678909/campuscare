from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from .models import MaintenanceRequest, TicketUpdate
from .forms import MaintenanceRequestForm, TicketStatusUpdateForm, TicketAssignForm
from facilities.models import Room, Asset
from accounts.models import User
from accounts.permissions import can_user_update_status, can_user_assign_ticket


@login_required
def ticket_list_view(request):
    """
    Search and filter maintenance tickets with role-based scoping and query optimizations.
    """
    user = request.user
    if user.is_authenticated:
        user.mark_feature_visited('tickets')
    scope = request.GET.get('scope', '')
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    category_filter = request.GET.get('category', '')
    room_filter = request.GET.get('room', '')
    search_query = request.GET.get('q', '').strip()

    # Base queryset with query optimization (select_related)
    tickets = MaintenanceRequest.objects.select_related(
        'room', 'asset', 'reported_by', 'assigned_to'
    ).order_by('-created_at')

    # Default scoping based on role if no explicit scope is passed
    if not scope:
        if user.is_reporter:
            scope = 'my'
        elif user.is_technician:
            scope = 'assigned'
        else:
            scope = 'all'

    if scope == 'my':
        tickets = tickets.filter(reported_by=user)
    elif scope == 'assigned':
        tickets = tickets.filter(assigned_to=user)
    elif scope == 'unassigned':
        tickets = tickets.filter(assigned_to__isnull=True)
    # 'all' shows all tickets

    # Filters
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if priority_filter:
        tickets = tickets.filter(priority=priority_filter)
    if category_filter:
        tickets = tickets.filter(category=category_filter)
    if room_filter:
        tickets = tickets.filter(room_id=room_filter)

    # Search
    if search_query:
        tickets = tickets.filter(
            Q(ticket_code__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(room__room_number__icontains=search_query) |
            Q(room__building_name__icontains=search_query) |
            Q(asset__name__icontains=search_query)
        )

    rooms = Room.objects.filter(is_active=True).order_by('building_code', 'room_number')

    return render(request, 'tickets/ticket_list.html', {
        'tickets': tickets,
        'scope': scope,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'category_filter': category_filter,
        'room_filter': room_filter,
        'search_query': search_query,
        'rooms': rooms,
        'statuses': MaintenanceRequest.Status.choices,
        'priorities': MaintenanceRequest.Priority.choices,
        'categories': MaintenanceRequest.Category.choices,
    })


@login_required
def ticket_create_view(request):
    """
    Submits a new maintenance request. Automatically links to the reporter,
    assigns initial SUBMITTED status and creates the first TicketUpdate timeline entry.
    """
    if request.method == 'POST':
        form = MaintenanceRequestForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.reported_by = request.user
            ticket.status = MaintenanceRequest.Status.SUBMITTED
            ticket.save()

            # Record initial ticket creation in history
            TicketUpdate.objects.create(
                ticket=ticket,
                author=request.user,
                old_status='',
                new_status=MaintenanceRequest.Status.SUBMITTED,
                comment=f"Ticket submitted by {request.user.get_full_name() or request.user.username}."
            )

            messages.success(
                request,
                f"Maintenance Request #{ticket.ticket_code} submitted successfully! Facilities staff will triage it shortly."
            )
            return redirect('tickets:ticket_detail', ticket_code=ticket.ticket_code)
        else:
            messages.error(request, "Please review the form errors below.")
    else:
        # Pre-select room or asset if supplied via query params
        initial = {}
        if 'room' in request.GET:
            initial['room'] = request.GET.get('room')
        if 'asset' in request.GET:
            initial['asset'] = request.GET.get('asset')
        form = MaintenanceRequestForm(initial=initial)

    return render(request, 'tickets/ticket_form.html', {
        'form': form,
    })


@login_required
def ticket_detail_view(request, ticket_code):
    if request.user.is_authenticated:
        request.user.mark_feature_visited('tickets')

    ticket = get_object_or_404(
        MaintenanceRequest.objects.select_related(
            'room', 'asset', 'reported_by', 'assigned_to'
        ).prefetch_related('updates__author'),
        ticket_code=ticket_code
    )

    can_update = can_user_update_status(request.user, ticket)
    can_assign = can_user_assign_ticket(request.user)

    status_form = None
    assign_form = None

    if can_update:
        status_form = TicketStatusUpdateForm(initial={
            'status': ticket.status,
            'resolution_notes': ticket.resolution_notes or '',
        })

    if can_assign:
        assign_form = TicketAssignForm(initial={
            'assigned_to': ticket.assigned_to,
            'priority': ticket.priority,
            'status': ticket.status,
        })

    # Find existing/related open tickets in the same room (excluding current ticket)
    related_tickets = MaintenanceRequest.objects.filter(
        room=ticket.room
    ).exclude(pk=ticket.pk).select_related('assigned_to').order_by('-created_at')[:5]

    return render(request, 'tickets/ticket_detail.html', {
        'ticket': ticket,
        'updates': ticket.updates.all(),
        'can_update': can_update,
        'can_assign': can_assign,
        'status_form': status_form,
        'assign_form': assign_form,
        'related_tickets': related_tickets,
    })


@login_required
def ticket_update_status_view(request, ticket_code):
    """
    POST-only action to update ticket status, resolution notes, and add a work comment.
    Enforces server-side permissions: technicians (assigned or claiming), managers, and admins only.
    """
    if request.method != 'POST':
        return redirect('tickets:ticket_detail', ticket_code=ticket_code)

    ticket = get_object_or_404(MaintenanceRequest, ticket_code=ticket_code)

    # Server-side authorization check
    if not can_user_update_status(request.user, ticket):
        raise PermissionDenied("You do not have permission to update this ticket's status.")

    form = TicketStatusUpdateForm(request.POST)
    if form.is_valid():
        old_status = ticket.status
        new_status = form.cleaned_data['status']
        comment = form.cleaned_data['comment']
        resolution_notes = form.cleaned_data.get('resolution_notes', '')

        # Auto-claim if technician updates an unassigned ticket
        if request.user.is_technician and ticket.assigned_to is None:
            ticket.assigned_to = request.user

        ticket.status = new_status
        if resolution_notes:
            ticket.resolution_notes = resolution_notes

        ticket.save()

        # Log TicketUpdate record
        TicketUpdate.objects.create(
            ticket=ticket,
            author=request.user,
            old_status=old_status,
            new_status=new_status,
            comment=comment
        )

        messages.success(
            request,
            f"Ticket #{ticket.ticket_code} updated from {dict(MaintenanceRequest.Status.choices).get(old_status, old_status)} to {ticket.get_status_display()}."
        )
    else:
        for error in form.errors.values():
            messages.error(request, error)

    return redirect('tickets:ticket_detail', ticket_code=ticket.ticket_code)


@login_required
def ticket_assign_view(request, ticket_code):
    """
    POST-only action for Managers/Admins to assign or reassign a technician
    and adjust priority or triage status.
    """
    if request.method != 'POST':
        return redirect('tickets:ticket_detail', ticket_code=ticket_code)

    ticket = get_object_or_404(MaintenanceRequest, ticket_code=ticket_code)

    if not can_user_assign_ticket(request.user):
        raise PermissionDenied("You do not have permission to assign or triage maintenance tickets.")

    form = TicketAssignForm(request.POST)
    if form.is_valid():
        old_assignee = ticket.assigned_to
        new_assignee = form.cleaned_data.get('assigned_to')
        new_priority = form.cleaned_data.get('priority')
        new_status = form.cleaned_data.get('status')
        comment = form.cleaned_data.get('comment', '').strip()

        changes = []
        old_status = ticket.status

        if old_assignee != new_assignee:
            old_name = old_assignee.username if old_assignee else "Unassigned"
            new_name = new_assignee.username if new_assignee else "Unassigned"
            changes.append(f"Assignment changed from {old_name} to {new_name}")
            ticket.assigned_to = new_assignee

        if ticket.priority != new_priority:
            changes.append(f"Priority changed from {ticket.get_priority_display()} to {dict(MaintenanceRequest.Priority.choices).get(new_priority)}")
            ticket.priority = new_priority

        if ticket.status != new_status:
            changes.append(f"Status changed from {ticket.get_status_display()} to {dict(MaintenanceRequest.Status.choices).get(new_status)}")
            ticket.status = new_status

        ticket.save()

        summary_comment = "; ".join(changes) if changes else "Ticket triage reviewed."
        if comment:
            summary_comment += f"\nNote: {comment}"

        TicketUpdate.objects.create(
            ticket=ticket,
            author=request.user,
            old_status=old_status,
            new_status=ticket.status,
            comment=summary_comment
        )

        messages.success(request, f"Ticket #{ticket.ticket_code} assignment and triage settings saved.")
    else:
        for error in form.errors.values():
            messages.error(request, error)

    return redirect('tickets:ticket_detail', ticket_code=ticket.ticket_code)


@login_required
def check_duplicates_api(request):
    """
    API endpoint returning existing open/recent tickets for a given room and/or asset.
    Allows live duplicate detection in the ticket submission form.
    """
    room_id = request.GET.get('room_id')
    asset_id = request.GET.get('asset_id')

    if not room_id and not asset_id:
        return JsonResponse({'tickets': []})

    q_filter = Q(status__in=[
        MaintenanceRequest.Status.SUBMITTED,
        MaintenanceRequest.Status.TRIAGED,
        MaintenanceRequest.Status.ASSIGNED,
        MaintenanceRequest.Status.IN_PROGRESS,
        MaintenanceRequest.Status.NEEDS_PARTS,
    ])

    if asset_id:
        q_filter &= (Q(asset_id=asset_id) | Q(room_id=room_id))
    elif room_id:
        q_filter &= Q(room_id=room_id)

    open_tickets = MaintenanceRequest.objects.filter(q_filter).select_related('room', 'asset')[:10]

    data = [
        {
            'ticket_code': t.ticket_code,
            'title': t.title,
            'room': f"{t.room.building_code} {t.room.room_number}",
            'asset': t.asset.name if t.asset else None,
            'priority': t.get_priority_display(),
            'status': t.get_status_display(),
            'created_at': t.created_at.strftime('%b %d, %Y'),
            'url': f"/tickets/{t.ticket_code}/",
        }
        for t in open_tickets
    ]

    return JsonResponse({'tickets': data})
