# Generated by Django 5.1.2 on 2024-11-03 07:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_systemmetricshistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemmetricshistory',
            name='cpu_cores',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='systemmetricshistory',
            name='cpu_frequency',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='systemmetricshistory',
            name='cpu_max',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='systemmetricshistory',
            name='cpu_min',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='systemmetricshistory',
            name='cpu_std_dev',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='systemmetricshistory',
            name='memory_peak',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='systemmetricshistory',
            name='network_errin',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='systemmetricshistory',
            name='network_errout',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='systemmetricshistory',
            name='network_packets_recv',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='systemmetricshistory',
            name='network_packets_sent',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddIndex(
            model_name='systemmetricshistory',
            index=models.Index(fields=['device', 'timestamp'], name='inventory_s_device__51a2a6_idx'),
        ),
    ]
