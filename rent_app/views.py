from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from .models import Property, Tenant, Meter, Transaction, RecurringCharge 
from .forms import PropertyForm, TenantForm, RecurringChargeFormSet, MeterForm, TransactionForm

# 1. Dashboard
def dashboard(request):
    properties = Property.objects.filter(is_archived=False)
    total_income = Transaction.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'properties': properties, 
        'total_income': total_income,
        'active_tenants': Tenant.objects.filter(is_archived=False).count(),
        'active_meters': Meter.objects.filter(assigned_tenant__isnull=False).count(),
        'property_form': PropertyForm(),
        'meter_form': MeterForm(),
    }
    return render(request, 'dashboard.html', context)

# --- PROPERTY MANAGEMENT ---

def add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    return render(request, 'form_base.html', {'form': PropertyForm(), 'title': 'Add Property'})

def edit_property(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        form = PropertyForm(request.POST, instance=prop)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = PropertyForm(instance=prop)
    return render(request, 'form_base.html', {'form': form, 'title': 'Edit Property'})

def delete_property(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        prop.delete()
        return redirect('dashboard')
    return render(request, 'confirm_delete.html', {'object': prop})

def property_detail(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    tenants = prop.tenants.filter(is_archived=False)
    
    tenant_form = TenantForm()
    tenant_form.fields['meter'].queryset = Meter.objects.filter(property=prop, assigned_tenant__isnull=True)
    
    context = {
        'property': prop, 
        'tenants': tenants,
        'tenant_form': tenant_form,
        'charge_formset': RecurringChargeFormSet(queryset=RecurringCharge.objects.none())
    }
    return render(request, 'property_detail.html', context)

# --- METER MANAGEMENT ---

def add_meter(request):
    if request.method == 'POST':
        form = MeterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard') 
    return render(request, 'form_base.html', {'form': MeterForm(), 'title': 'Add Meter'})

# --- TENANT MANAGEMENT ---

def add_tenant(request, property_id):
    property_obj = get_object_or_404(Property, pk=property_id)
    if request.method == 'POST':
        form = TenantForm(request.POST)
        formset = RecurringChargeFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            tenant = form.save(commit=False)
            tenant.property = property_obj
            tenant.save()
            
            formset.instance = tenant
            formset.save()
            
            if tenant.meter:
                tenant.meter.save() 
                
            return redirect('property_detail', pk=property_id)
            
    else:
        form = TenantForm()
        formset = RecurringChargeFormSet()
    
    return render(request, 'add_tenant.html', {'form': form, 'formset': formset, 'property': property_obj, 'title': 'Add New Tenant'})

def edit_tenant(request, tenant_id):
    tenant = get_object_or_404(Tenant, pk=tenant_id)
    if request.method == 'POST':
        form = TenantForm(request.POST, instance=tenant)
        formset = RecurringChargeFormSet(request.POST, instance=tenant)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect('property_detail', pk=tenant.property.id)
    else:
        form = TenantForm(instance=tenant)
        formset = RecurringChargeFormSet(instance=tenant)
    
    return render(request, 'add_tenant.html', {'form': form, 'formset': formset, 'title': 'Edit Tenant'})

def tenant_detail(request, tenant_id):
    # This view now works for both Active and Archived tenants!
    tenant = get_object_or_404(Tenant, pk=tenant_id)
    transactions = tenant.transactions.all().order_by('-date')
    
    if request.method == 'POST' and not tenant.is_archived:
        form = TransactionForm(request.POST, request.FILES)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.tenant = tenant
            extra = form.cleaned_data.get('extra_charge', 0)
            if extra:
                tenant.due_amount += extra
            
            tenant.due_amount -= transaction.amount
            
            transaction.save()
            tenant.save() 
            return redirect('tenant_detail', tenant_id=tenant.id)
    else:
        form = TransactionForm()

    return render(request, 'tenant_detail.html', {
        'tenant': tenant, 
        'transactions': transactions,
        'form': form
    })

def archive_tenant(request, tenant_id):
    tenant = get_object_or_404(Tenant, pk=tenant_id)
    tenant.is_archived = True
    tenant.left_date = timezone.now()
    
    if tenant.meter:
        tenant.meter.assigned_tenant = None 
        tenant.meter.save()
        tenant.meter = None
        
    tenant.save()
    return redirect('property_detail', pk=tenant.property.id)

def delete_tenant(request, tenant_id):
    tenant = get_object_or_404(Tenant, pk=tenant_id)
    property_id = tenant.property.id
    if request.method == 'POST':
        tenant.delete()
        return redirect('property_detail', pk=property_id)
    return render(request, 'confirm_delete.html', {'object': tenant})

# --- PAST TENANTS (NEW FEATURE) ---
def past_tenants(request):
    archived_tenants = Tenant.objects.filter(is_archived=True).order_by('-left_date')
    return render(request, 'past_tenants.html', {'tenants': archived_tenants})


# --- BULK ACTIONS ---

def bulk_rent(request):
    active_tenants = Tenant.objects.filter(is_archived=False).select_related('meter').prefetch_related('recurring_charges')
    
    if request.method == 'POST':
        for tenant in active_tenants:
            if request.POST.get(f'select_{tenant.id}'):
                
                # --- BUG FIX: Handle empty strings gracefully ---
                amt_str = request.POST.get(f'amount_{tenant.id}', '')
                amount_paid = float(amt_str) if amt_str.strip() else 0.0
                
                extra_str = request.POST.get(f'extra_{tenant.id}', '')
                extra_charge = float(extra_str) if extra_str.strip() else 0.0
                
                new_reading_val = request.POST.get(f'reading_{tenant.id}')
                # -----------------------------------------------
                
                mode = request.POST.get(f'mode_{tenant.id}')
                proof_file = request.FILES.get(f'proof_{tenant.id}')
                notes = request.POST.get('common_notes', 'Bulk Payment')

                elec_cost = 0
                
                # A. Handle Electricity Logic
                if new_reading_val and new_reading_val.strip() and tenant.meter and tenant.include_electricity:
                    try:
                        current_reading = float(new_reading_val)
                        prev_reading = float(tenant.meter.current_reading)
                        
                        if current_reading > prev_reading:
                            units = current_reading - prev_reading
                            elec_rate = 10.0 # Rate per unit
                            elec_cost = units * elec_rate
                            
                            Transaction.objects.create(
                                tenant=tenant, amount=elec_cost, type='ELEC', mode=mode,
                                proof_image=proof_file, notes=f"{notes} (Elec: {units} units)",
                                meter_reading=current_reading, units_consumed=units, date=timezone.now()
                            )
                            tenant.meter.current_reading = current_reading
                            tenant.meter.save()
                    except ValueError:
                        pass

                # B. Handle Rent Transaction (Remainder)
                rent_part = amount_paid - elec_cost
                if rent_part > 0:
                    Transaction.objects.create(
                        tenant=tenant, amount=rent_part, type='RENT', mode=mode,
                        proof_image=proof_file, notes=notes, date=timezone.now()
                    )

                # C. Update Due Amount
                monthly_base = float(tenant.total_monthly_rent())
                total_bill_for_month = monthly_base + elec_cost + extra_charge
                
                tenant.due_amount = float(tenant.due_amount) + total_bill_for_month - amount_paid
                tenant.save()

        return redirect('dashboard')

    return render(request, 'bulk_rent.html', {'tenants': active_tenants})

# --- REPORTS ---

def reports(request):
    tenants = Tenant.objects.filter(is_archived=False)
    return render(request, 'reports.html', {'tenants': tenants})