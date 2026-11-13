
from django.contrib import admin
from .models import Profile, Incident, IncidentStatusHistory


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'role',
        'preferred_language',
        'theme',
        'created_at',
    )

    list_filter = (
        'role',
        'preferred_language',
        'theme',
    )

    search_fields = (
        'user__username',
        'user__email',
    )


class IncidentStatusHistoryInline(admin.TabularInline):

    model = IncidentStatusHistory
    extra = 1

    fields = (
        'status',
        'message',
        'updated_by',
        'created_at',
    )

    readonly_fields = ('created_at',)


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'incident_type',
        'reporter',
        'severity',
        'priority_level',
        'priority_score',
        'status',
        'location',
        'created_at',
    )

    list_filter = (
        'incident_type',
        'severity',
        'priority_level',
        'status',
        'created_at',
    )

    search_fields = (
        'reporter__username',
        'description',
        'location',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    ordering = ('-created_at',)

    inlines = [IncidentStatusHistoryInline]

    def save_model(self, request, obj, form, change):
        obj.calculate_priority()
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        history_changed = bool(instances)

        for instance in instances:
            if isinstance(instance, IncidentStatusHistory):
                if not instance.updated_by:
                    instance.updated_by = request.user

                instance.save()

        formset.save_m2m()

        if history_changed:
            latest_update = form.instance.status_history.order_by(
                '-created_at'
            ).first()

            if latest_update:
                form.instance.status = latest_update.status
                form.instance.save(
                    update_fields=['status', 'updated_at']
                )
