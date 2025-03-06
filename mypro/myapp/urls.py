# myapp/urls.py
from django.contrib import admin
from django.urls import path
from . import views  # Import all views from the current directory

app_name = 'myapp'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('addblind/', views.addblind, name='addblind'),
    path('sellblind/', views.sellblind, name='sellblind'),
    path('searchblind/', views.searchblind, name='searchblind'),
    path('transactions/', views.transactions_view, name='transactions'),
    path('update/<int:pk>/', views.update_item, name='update_item'),
    path('update-payment-status/<int:id>/', views.update_payment_status, name='update_payment_status'),
    path('get-sales-data/', views.get_sales_data, name='get_sales_data'),
    path('generate-bill/<int:transaction_id>/', views.generate_bill, name='generate_bill'),
    path('update-transaction/<int:transaction_id>/', views.update_transaction, name='update_transaction'),  # Add this line
]