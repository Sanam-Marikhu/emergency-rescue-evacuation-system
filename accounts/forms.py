
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import Incident


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']

        if commit:
            user.save()

        return user


class IncidentForm(forms.ModelForm):

    class Meta:
        model = Incident

        fields = [
            'incident_type',
            'severity',
            'description',
            'location',
            'latitude',
            'longitude',
            'people_affected',
            'people_trapped',
            'people_injured',
        ]

        widgets = {
            'incident_type': forms.Select(attrs={
                'class': 'form-control',
            }),

            'severity': forms.Select(attrs={
                'class': 'form-control',
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe the emergency and people affected...',
            }),

            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your location or nearby landmark',
            }),

            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any',
                'placeholder': 'Optional GPS latitude',
            }),

            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any',
                'placeholder': 'Optional GPS longitude',
            }),
        }
