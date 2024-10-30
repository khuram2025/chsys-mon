from django.db import models
import uuid

class Device(models.Model):
    DEVICE_TYPES = [
        ('ROUTER', 'Router'),
        ('SWITCH', 'Switch'),
        ('SERVER', 'Server'),
        ('FIREWALL', 'Firewall'),
        ('WORKSTATION', 'Workstation'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('UP', 'Up'),
        ('DOWN', 'Down'),
        ('MAINTENANCE', 'Maintenance'),
        ('UNKNOWN', 'Unknown'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, blank=True, null=True)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    ip_address = models.GenericIPAddressField(unique=True)
    mac_address = models.CharField(max_length=17, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    os_version = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNKNOWN')
    last_seen = models.DateTimeField(null=True, blank=True)
    api_key = models.CharField(max_length=100, unique=True)
    hostname = models.CharField(max_length=255, blank=True, null=True)
    platform = models.CharField(max_length=255, blank=True, null=True)
    processor = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_seen']

class SystemResources(models.Model):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='resources')
    cpu_cores = models.IntegerField(default=0)
    cpu_threads = models.IntegerField(default=0)
    total_memory = models.BigIntegerField(default=0)  # in bytes
    total_disk_space = models.BigIntegerField(default=0)  # in bytes
    updated_at = models.DateTimeField(auto_now=True)

    