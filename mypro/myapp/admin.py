from django.contrib import admin
from .models import Client, Blind, Transaction, TransactionItem

class TransactionItemInline(admin.TabularInline):  # Use StackedInline for a different layout
    model = TransactionItem
    extra = 1  # Number of empty fields for new items

class TransactionAdmin(admin.ModelAdmin):
    inlines = [TransactionItemInline]  # Attach TransactionItem inside Transaction

admin.site.register(Client)
admin.site.register(Blind)
admin.site.register(Transaction, TransactionAdmin)
# admin.site.register(TransactionItem)
