from django.contrib import admin
from .models import Property, Tenant, Meter, Transaction, RecurringCharge

class RecurringChargeInline(admin.TabularInline):
    model = RecurringCharge
    extra = 1

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'property', 'phone', 'due_amount', 'is_archived')
    inlines = [RecurringChargeInline]

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'tenant', 'type', 'amount', 'mode')

admin.site.register(Property)
admin.site.register(Meter)