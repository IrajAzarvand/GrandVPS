from django import forms
from django.contrib.auth.models import User
from .models import VPSPlan, VPSInstance
from .services.doprax_client import DopraxClient, DopraxAPIError
import logging

logger = logging.getLogger(__name__)


class VPSCreationForm(forms.Form):
    """Form for creating a new VPS instance"""

    plan = forms.ModelChoiceField(
        queryset=VPSPlan.objects.filter(is_active=True),
        empty_label="Select a plan",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    location = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    operating_system = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    vm_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter VPS name (optional)'
        }),
        required=False,
        help_text="Leave empty for auto-generated name"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._load_dynamic_choices()

    def _load_dynamic_choices(self):
        """Load dynamic choices from Doprax API"""
        try:
            client = DopraxClient()

            # Load locations
            data = client.get_locations_and_plans()
            locations = data.get('locationsList', [])
            location_choices = []
            for loc in locations:
                location_choices.append((
                    loc['locationCode'],
                    f"{loc['name']} ({loc.get('country', 'Unknown')}) - {loc.get('provider', 'Unknown')}"
                ))
            self.fields['location'].choices = location_choices

            # Load operating systems
            os_data = client.get_operating_systems()
            os_choices = []
            for provider, os_list in os_data.items():
                for os_item in os_list:
                    os_choices.append((
                        os_item['slug'],
                        f"{os_item['name']} ({provider})"
                    ))
            self.fields['operating_system'].choices = os_choices

        except DopraxAPIError as e:
            logger.error(f"Failed to load dynamic choices: {str(e)}")
            # Set default empty choices if API fails
            self.fields['location'].choices = [('', 'Unable to load locations')]
            self.fields['operating_system'].choices = [('', 'Unable to load operating systems')]

    def clean_vm_name(self):
        """Validate and generate VM name if not provided"""
        vm_name = self.cleaned_data.get('vm_name')
        if not vm_name:
            # Generate a unique name
            import uuid
            vm_name = f"vps-{uuid.uuid4().hex[:8]}"
        return vm_name

    def clean(self):
        """Validate the entire form"""
        cleaned_data = super().clean()
        plan = cleaned_data.get('plan')
        location = cleaned_data.get('location')

        if plan and location:
            # Additional validation can be added here
            # For example, check if the selected plan is available in the selected location
            pass

        return cleaned_data


class VPSActionForm(forms.Form):
    """Form for VPS management actions"""

    ACTION_CHOICES = [
        ('start', 'Start VPS'),
        ('stop', 'Stop VPS'),
        ('restart', 'Restart VPS'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, vps_instance=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vps_instance = vps_instance

    def clean(self):
        """Validate action based on current VPS status"""
        cleaned_data = super().clean()
        action = cleaned_data.get('action')

        if self.vps_instance and action:
            current_status = self.vps_instance.status

            # Prevent invalid actions based on status
            if action == 'start' and current_status == 'active':
                raise forms.ValidationError("VPS is already running")
            elif action == 'stop' and current_status == 'stopped':
                raise forms.ValidationError("VPS is already stopped")
            elif action in ['start', 'stop', 'restart'] and current_status == 'terminated':
                raise forms.ValidationError("Cannot perform actions on terminated VPS")

        return cleaned_data