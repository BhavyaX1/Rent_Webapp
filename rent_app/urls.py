from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    # Property
    path('property/add/', views.add_property, name='add_property'),
    path('property/<int:pk>/', views.property_detail, name='property_detail'),
    path('property/<int:pk>/edit/', views.edit_property, name='edit_property'),
    path('property/<int:pk>/delete/', views.delete_property, name='delete_property'),

    # Tenant
    path('property/<int:property_id>/add-tenant/', views.add_tenant, name='add_tenant'),
    path('tenant/<int:tenant_id>/', views.tenant_detail, name='tenant_detail'),
    path('tenant/<int:tenant_id>/edit/', views.edit_tenant, name='edit_tenant'),
    path('tenant/<int:tenant_id>/archive/', views.archive_tenant, name='archive_tenant'),
    path('tenant/<int:tenant_id>/delete/', views.delete_tenant, name='delete_tenant'),
    
    # Meter
    path('meters/add/', views.add_meter, name='add_meter'),
    
    # Actions
    path('bulk-rent/', views.bulk_rent, name='bulk_rent'),
    path('reports/', views.reports, name='reports'),
    
    path('past-tenants/', views.past_tenants, name='past_tenants'),
]