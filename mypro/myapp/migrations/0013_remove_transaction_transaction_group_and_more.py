# Generated by Django 5.1.1 on 2025-01-24 19:45

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0012_transaction_transaction_group'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='transaction_group',
        ),
        migrations.AddField(
            model_name='transaction',
            name='batch_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
