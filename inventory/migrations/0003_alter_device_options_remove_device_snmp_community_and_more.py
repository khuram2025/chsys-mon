# Generated by Django 5.1.2 on 2024-10-30 06:31

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_alter_device_location_alter_device_manufacturer_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='device',
            options={'ordering': ['-last_seen']},
        ),
        migrations.RemoveField(
            model_name='device',
            name='snmp_community',
        ),
        migrations.RemoveField(
            model_name='device',
            name='ssh_password',
        ),
        migrations.RemoveField(
            model_name='device',
            name='ssh_username',
        ),
        migrations.AddField(
            model_name='device',
            name='hostname',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='device',
            name='last_seen',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='device',
            name='platform',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='device',
            name='processor',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.CreateModel(
            name='SystemResources',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cpu_cores', models.IntegerField(default=0)),
                ('cpu_threads', models.IntegerField(default=0)),
                ('total_memory', models.BigIntegerField(default=0)),
                ('total_disk_space', models.BigIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('device', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='resources', to='inventory.device')),
            ],
        ),
    ]
