from django import forms
from .models import Property, Tenant, Meter, Transaction, RecurringCharge
from django.db.models import Q

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['name', 'address']

class MeterForm(forms.ModelForm):
    class Meta:
        model = Meter
        fields = ['property', 'room_number', 'meter_number', 'current_reading']

class TenantForm(forms.ModelForm):
    meter = forms.ModelChoiceField(
        queryset=Meter.objects.filter(assigned_tenant__isnull=True), 
        required=False,
        label="Assign Meter/Room"
    )

    class Meta:
        model = Tenant
        fields = ['name', 'phone', 'base_rent', 'rent_due_date', 'joined_date', 'include_electricity', 'meter']
        widgets = {
            'joined_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.meter:
            self.fields['meter'].queryset = Meter.objects.filter(
                Q(assigned_tenant__isnull=True) | Q(pk=self.instance.meter.pk)
            )

RecurringChargeFormSet = forms.inlineformset_factory(
    Tenant, RecurringCharge, fields=('name', 'amount'), extra=1, can_delete=True
)

class TransactionForm(forms.ModelForm):
    extra_charge = forms.DecimalField(required=False, initial=0, label="Add Due/Charge")

    class Meta:
        model = Transaction
        fields = ['date', 'amount', 'type', 'mode', 'proof_image', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }