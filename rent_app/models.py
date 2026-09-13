from django.db import models
from django.utils import timezone
from django.db.models import Sum

# 1. Property Model
class Property(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# 2. Meter Model
class Meter(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='meters')
    room_number = models.CharField(max_length=20)
    meter_number = models.CharField(max_length=50, help_text="Serial Number")
    current_reading = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Room {self.room_number} - {self.meter_number}"

# 3. Tenant Model
class Tenant(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='tenants')
    meter = models.OneToOneField(Meter, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tenant')
    
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    
    base_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rent_due_date = models.IntegerField(default=1, null=True, blank=True, help_text="Day of the month (1-31)")
    
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    include_electricity = models.BooleanField(default=True)
    
    joined_date = models.DateField(default=timezone.now)
    is_archived = models.BooleanField(default=False)
    left_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name

    def total_monthly_rent(self):
        if not self.pk:
            return self.base_rent
        try:
            charges = self.recurring_charges.aggregate(total=Sum('amount'))['total'] or 0
        except Exception:
            charges = 0
        return self.base_rent + charges

# 4. Recurring Charges
class RecurringCharge(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='recurring_charges')
    name = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=8, decimal_places=2)

# 5. Transactions
class Transaction(models.Model):
    PAYMENT_TYPES = [('RENT', 'Rent'), ('ELEC', 'Electricity')]
    PAYMENT_MODES = [('UPI', 'UPI'), ('CASH', 'Cash'), ('BANK', 'Bank Transfer'), ('CHECK', 'Check')]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=10, choices=PAYMENT_TYPES, default='RENT')
    mode = models.CharField(max_length=10, choices=PAYMENT_MODES, default='UPI')
    
    proof_image = models.ImageField(upload_to='payment_proofs/', null=True, blank=True)
    notes = models.TextField(blank=True)

    meter_reading = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    units_consumed = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)