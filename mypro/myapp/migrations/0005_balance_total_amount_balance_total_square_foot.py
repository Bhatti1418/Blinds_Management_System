# Generated by Django 5.1.1 on 2025-01-16 16:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0004_alter_client_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='balance',
            name='total_amount',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='balance',
            name='total_square_foot',
            field=models.FloatField(default=0),
        ),
    ]
