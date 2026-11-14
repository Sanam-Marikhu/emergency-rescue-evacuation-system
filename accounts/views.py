
import json
import uuid
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404,JsonResponse
from django.contrib.staticfiles.finders import find

from .forms import RegisterForm,IncidentForm
from .models import Profile,Incident,IncidentStatusHistory

def service_worker(request):
    file_path = find('accounts/service-worker.js')

    if not file_path:
        raise Http404("Service worker file not found.")

    with open(file_path, 'rb') as file:
        response = HttpResponse(
            file.read(),
            content_type='application/javascript'
        )

    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'

    return response

def redirect_user(user):
    """Redirect users according to their role."""

    if user.is_superuser or user.is_staff:
        return redirect('/admin/')

    try:
        role = user.profile.role
    except Profile.DoesNotExist:
        return redirect('home')

    if role == 'citizen':
        return redirect('citizen_dashboard')

    if role == 'rescue':
        return redirect('rescue_dashboard')

    return redirect('home')


def register_view(request):
    if request.user.is_authenticated:
        return redirect_user(request.user)

    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                Profile.objects.create(user=user, role='citizen')

            login(request, user)
            messages.success(
                request,
                'Your account was created successfully.'
            )
            return redirect_user(user)

    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect_user(request.user)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            messages.success(request, 'You are now logged in.')
            return redirect_user(user)

    else:
        form = AuthenticationForm(request)

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have logged out.')
        return redirect('login')

    return redirect_user(request.user)


def home_view(request):
    return render(request, 'accounts/home.html')



@login_required
def citizen_dashboard(request):

    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')

    if not hasattr(request.user, 'profile'):
        raise PermissionDenied

    if request.user.profile.role != 'citizen':
        raise PermissionDenied

    # Get incidents reported by the logged-in citizen.
    incidents = Incident.objects.filter(
        reporter=request.user
    )

    # Calculate report statistics.
    total_reports = incidents.count()

    pending_reports = incidents.filter(
        status='pending'
    ).count()

    resolved_reports = incidents.filter(
        status='resolved'
    ).count()

    # Get the five most recent reports.
    recent_reports = incidents.order_by(
        '-created_at'
    )[:5]
    # Count unread status notifications.
    unread_notifications = IncidentStatusHistory.objects.filter(
        incident__reporter=request.user,
        is_read=False
    ).exclude(
    updated_by=request.user
    ).count()

    context = {
        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'resolved_reports': resolved_reports,
        'recent_reports': recent_reports,
        'unread_notifications': unread_notifications,
    }

    return render(
        request,
        'accounts/citizen_dashboard.html',
        context
    )



@login_required
def rescue_dashboard(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')

    if not hasattr(request.user, 'profile'):
        raise PermissionDenied

    if request.user.profile.role != 'rescue':
        raise PermissionDenied

    return render(
        request,
        'accounts/rescue_dashboard.html'
    )


@login_required
def report_incident(request):

    # Only citizens can submit incident reports.
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')

    if not hasattr(request.user, 'profile'):
        raise PermissionDenied

    if request.user.profile.role != 'citizen':
        raise PermissionDenied

    if request.method == 'POST':
        form = IncidentForm(request.POST)

        if form.is_valid():
            incident = form.save(commit=False)

            # Automatically assign the logged-in citizen.
            incident.reporter = request.user

            # Save the incident.
            with transaction.atomic():

              incident.status = 'pending'

              # Calculate incident priority
              incident.calculate_priority()

              incident.save()

              # Create initial status history
              IncidentStatusHistory.objects.create(
                incident=incident,
                status='pending',
                message='Your emergency report has been successfully submitted.',
                updated_by=request.user
            )

            messages.success(
                request,
                'Your emergency report has been submitted successfully.'
            )

            return redirect('citizen_dashboard')

    else:
        form = IncidentForm()

    return render(
        request,
        'accounts/report_incident.html',
        {'form': form}
    )

@login_required
@require_POST
def sync_offline_report(request):

    # Only citizens can synchronize incident reports.
    if request.user.is_staff or request.user.is_superuser:
        return JsonResponse(
            {'success': False, 'message': 'Access denied.'},
            status=403
        )

    if not hasattr(request.user, 'profile'):
        return JsonResponse(
            {'success': False, 'message': 'Citizen profile not found.'},
            status=403
        )

    if request.user.profile.role != 'citizen':
        return JsonResponse(
            {'success': False, 'message': 'Access denied.'},
            status=403
        )

    # Read the submitted JSON.
    try:
        payload = json.loads(request.body)

        submission_id = uuid.UUID(str(payload.get('submission_id')))
        report_data = payload.get('data')

        if not isinstance(report_data, dict):
            raise ValueError("Invalid report data.")

    except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
        return JsonResponse(
            {'success': False, 'message': 'Invalid submission data.'},
            status=400
        )

    # Check whether this report was already synchronized.
    existing = Incident.objects.filter(
        submission_id=submission_id
    ).first()

    if existing:
        if existing.reporter_id != request.user.id:
            return JsonResponse(
                {'success': False, 'message': 'Submission ID conflict.'},
                status=409
            )

        return JsonResponse({
            'success': True,
            'duplicate': True,
            'incident_id': existing.id,
            'message': 'This report was already synchronized.'
        })

    # Validate using the existing incident form.
    form = IncidentForm(report_data)

    if not form.is_valid():
        return JsonResponse({
            'success': False,
            'message': 'Please check the submitted report.',
            'errors': form.errors.get_json_data()
        }, status=400)

    try:
        with transaction.atomic():

            incident = form.save(commit=False)
            incident.reporter = request.user
            incident.submission_id = submission_id
            incident.status = 'pending'

            # Use the existing priority calculation.
            incident.calculate_priority()
            incident.save()

            # Create the initial status history.
            IncidentStatusHistory.objects.create(
                incident=incident,
                status='pending',
                message='Your emergency report has been successfully submitted.',
                updated_by=request.user
            )

    except Exception as error:
        # Handle a possible simultaneous duplicate submission.
        existing = Incident.objects.filter(
            submission_id=submission_id
        ).first()

        if existing and existing.reporter_id == request.user.id:
            return JsonResponse({
                'success': True,
                'duplicate': True,
                'incident_id': existing.id,
                'message': 'This report was already synchronized.'
            })

        raise error

    return JsonResponse({
        'success': True,
        'duplicate': False,
        'incident_id': incident.id,
        'message': 'Offline report synchronized successfully.'
    }, status=201)


@login_required
def my_reports(request):

    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')

    if not hasattr(request.user, 'profile'):
        raise PermissionDenied

    if request.user.profile.role != 'citizen':
        raise PermissionDenied

    # Retrieve all reports submitted by this citizen.
    incidents = Incident.objects.filter(
        reporter=request.user
    ).order_by('-created_at')

    # Display 10 reports per page.
    paginator = Paginator(incidents, 10)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_reports': incidents.count(),
    }

    return render(
        request,
        'accounts/my_reports.html',
        context
    )

@login_required
def incident_detail(request, incident_id):

    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')

    if not hasattr(request.user, 'profile'):
        raise PermissionDenied

    if request.user.profile.role != 'citizen':
        raise PermissionDenied

    incident = get_object_or_404(
        Incident,
        id=incident_id,
        reporter=request.user
    )

    # Mark status updates as read when the citizen opens the report.
    IncidentStatusHistory.objects.filter(
        incident=incident,
        is_read=False
    ).exclude(
        updated_by=request.user
    ).update(is_read=True)

    context = {
        'incident': incident,
    }

    return render(
        request,
        'accounts/incident_detail.html',
        context
    )
@login_required
def notifications(request):

    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')

    if not hasattr(request.user, 'profile'):
        raise PermissionDenied

    if request.user.profile.role != 'citizen':
        raise PermissionDenied

    # Get all status updates for this citizen's incidents.
    notification_list = IncidentStatusHistory.objects.filter(
        incident__reporter=request.user
    ).exclude(
        updated_by=request.user
    ).select_related(
        'incident',
        'updated_by'
    ).order_by('-created_at')

    context = {
        'notifications': notification_list,
        'unread_notifications': notification_list.filter(
            is_read=False
        ).count(),
    }

    return render(
        request,
        'accounts/notifications.html',
        context
    )