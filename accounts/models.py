import uuid
from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):

    ROLE_CHOICES = [
        ('citizen', 'Citizen'),
        ('rescue', 'Rescue Team'),
    ]

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ne', 'Nepali'),
    ]

    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='citizen'
    )

    preferred_language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='en'
    )

    theme = models.CharField(
        max_length=5,
        choices=THEME_CHOICES,
        default='light'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class Incident(models.Model):

    INCIDENT_TYPES = [
        ('flood', 'Flood'),
        ('fire', 'Fire'),
        ('landslide', 'Landslide'),
        ('earthquake', 'Earthquake'),
        ('road_accident', 'Road Accident'),
        ('building_collapse', 'Building Collapse'),
        ('other', 'Other'),
    ]

    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('assigned', 'Rescue Team Assigned'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    ]
    priority_score = models.PositiveIntegerField(default=0)

    PRIORITY_CHOICES = [
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'),
        ('high', 'High Priority'),
        ('critical', 'Critical Priority'),
    ]

    priority_level = models.CharField(
       max_length=10,
       choices=PRIORITY_CHOICES,
       default='medium'
    )

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reported_incidents'
    )
    submission_id = models.UUIDField(
    default=None,
    null=True,
    blank=True,
    unique=True,
    editable=False)

    incident_type = models.CharField(
        max_length=30,
        choices=INCIDENT_TYPES
    )

    description = models.TextField()

    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        default='medium'
    )
    people_affected = models.PositiveIntegerField(
    default=1,
    help_text="Estimated number of people affected by this incident."
    )

    people_trapped = models.BooleanField(
    default=False,
    help_text="Are any people trapped and requiring rescue?"
    )

    people_injured = models.BooleanField(
    default=False,
    help_text="Are any people injured?"
    )

    location = models.CharField(max_length=255)

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def calculate_priority(self):

        # 1. Severity score
        severity_scores = {
            'low': 10,
            'medium': 25,
            'high': 50,
            'critical': 70,
        }

        score = severity_scores.get(self.severity, 10)

        # 2. Number of people affected
        if self.people_affected <= 5:
            score += 5
        elif self.people_affected <= 20:
            score += 10
        else:
            score += 15

        # 3. Injured people
        if self.people_injured:
            score += 10

        # 4. Trapped people
        if self.people_trapped:
            score += 15

        # 5. Determine priority level
        if score >= 70:
            priority = 'critical'
        elif score >= 50:
            priority = 'high'
        elif score >= 25:
            priority = 'medium'
        else:
            priority = 'low'

        self.priority_score = score
        self.priority_level = priority

        return score


    def __str__(self):
        return f"{self.get_incident_type_display()} - {self.reporter.username}"

class IncidentStatusHistory(models.Model):

    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name='status_history'
    )

    status = models.CharField(
        max_length=20,
        choices=Incident.STATUS_CHOICES
    )

    message = models.TextField(
        blank=True,
        help_text="Optional message about this status update."
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incident_status_updates'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Incident #{self.incident.id} - {self.get_status_display()}"