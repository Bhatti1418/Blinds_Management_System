# Generated by Django 5.1.1 on 2025-01-16 19:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0005_balance_total_amount_balance_total_square_foot'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('blind_name', models.CharField(max_length=50)),
                ('blind_price', models.FloatField(default=0)),
                ('length', models.FloatField(default=0)),
                ('width', models.FloatField(default=0)),
                ('square_foot', models.FloatField(default=0)),
                ('total_amount', models.FloatField(default=0)),
            ],
        ),
        migrations.RenameField(
            model_name='blind',
            old_name='blind_length',
            new_name='purchased_count',
        ),
        migrations.RenameField(
            model_name='blind',
            old_name='blind_width',
            new_name='total_amount',
        ),
        migrations.RenameField(
            model_name='blind',
            old_name='purchased_blind',
            new_name='total_square_foot',
        ),
        migrations.RemoveField(
            model_name='balance',
            name='total_amount',
        ),
        migrations.RemoveField(
            model_name='balance',
            name='total_square_foot',
        ),
        migrations.RemoveField(
            model_name='blind',
            name='square_foot',
        ),
    ]
