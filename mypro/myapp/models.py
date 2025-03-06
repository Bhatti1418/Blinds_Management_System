from django.db import models
from django.contrib.auth.models import User

class Client(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    person_name = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.person_name

class Blind(models.Model):
    blind_name = models.CharField(max_length=50, unique=True)
    blind_entry_date = models.DateField(null=True, blank=True)
    blind_price = models.FloatField(default=0)
    blind_quantity = models.FloatField(default=0)
    remaining_quantity = models.FloatField(default=0)
    purchased_count = models.FloatField(default=0)
    total_square_foot = models.FloatField(default=0)
    total_amount = models.FloatField(default=0)

    def __str__(self):
        return self.blind_name


class Transaction(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(
        max_length=10,
        choices=[('Pending', 'Payment Pending'), ('Paid', 'Payment Done')],
        default='Pending'
    )

    def __str__(self):
        return f"Transaction {self.id} - {self.client.person_name if self.client else 'Unknown'}"

class TransactionItem(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    blind = models.ForeignKey(Blind, on_delete=models.CASCADE)
    width = models.FloatField()
    length = models.FloatField()
    square_foot = models.FloatField()
    price = models.FloatField()
    total_price = models.FloatField()
