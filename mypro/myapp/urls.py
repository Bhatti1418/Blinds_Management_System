# myapp/urls.py
from django.contrib import admin
from django.urls import path
from . import views  # Import all views from the current directory

app_name = 'myapp'

urlpatterns = [
    path('homepage/', views.homepage, name='homepage'),
    path('mylogin/', views.mylogin, name='mylogin'),
    path('addblind/', views.addblind, name='addblind'),
    path('', views.sellblind, name='sellblind'),  # root path
    path('sellblind/', views.sellblind, name='sellblind'),  # explicitly add this
    path('searchblind/', views.searchblind, name='searchblind'),
    path('transactions/', views.transactions_view, name='transactions'),
    path('update/<int:pk>/', views.update_item, name='update_item'),
    path('update-payment-status/<int:id>/', views.update_payment_status, name='update_payment_status'),
    path('get-sales-data/', views.get_sales_data, name='get_sales_data'),
    path('generate-bill/<int:transaction_id>/', views.generate_bill, name='generate_bill'),
    path('search-transaction/', views.searchtransaction, name='search_transaction'),
    path('get-blind-quantity/', views.get_blind_quantity, name='get_blind_quantity'),
    path('balance/', views.balance_view, name='balance'),
    path('update-item/<int:pk>/', views.update_transaction_item, name='update_transaction_item'),
    path('transaction/delete/<int:id>/', views.delete_transaction, name='delete_transaction'),

]
