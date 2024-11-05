from django.db import models
import uuid
from django.utils import timezone

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
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('rejected', 'Rejected'),
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    last_seen = models.DateTimeField(null=True, blank=True)
    hostname = models.CharField(max_length=255, blank=True, null=True)
    platform = models.CharField(max_length=255, blank=True, null=True)
    processor = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_seen']

class SystemResources(models.Model):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='resources')
    
    # CPU metrics
    cpu_cores = models.IntegerField(default=0)
    cpu_threads = models.IntegerField(default=0)
    cpu_usage = models.FloatField(default=0)  # percentage
    cpu_frequency = models.FloatField(default=0)  # MHz
    
    # Memory metrics
    total_memory = models.BigIntegerField(default=0)  # in bytes
    used_memory = models.BigIntegerField(default=0)  # in bytes
    memory_usage = models.FloatField(default=0)  # percentage
    
    # Disk metrics
    total_disk_space = models.BigIntegerField(default=0)  # in bytes
    used_disk_space = models.BigIntegerField(default=0)  # in bytes
    disk_usage = models.FloatField(default=0)  # percentage
    
    # Network metrics
    bytes_sent = models.BigIntegerField(default=0)
    bytes_received = models.BigIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Resources for {self.device.hostname or self.device.name}"

    class Meta:
        verbose_name_plural = "System Resources"

class SystemMetricsHistory(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='metrics_history')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # CPU metrics
    cpu_usage = models.FloatField(default=0)
    cpu_frequency = models.FloatField(default=0)
    cpu_cores = models.IntegerField(default=0)
    cpu_min = models.FloatField(default=0)
    cpu_max = models.FloatField(default=0)
    cpu_std_dev = models.FloatField(default=0)
    
    # Memory metrics
    memory_used = models.BigIntegerField(default=0)
    memory_total = models.BigIntegerField(default=0)
    memory_percent = models.FloatField(default=0)
    memory_peak = models.BigIntegerField(default=0)
    
    # Disk metrics
    disk_used = models.BigIntegerField(default=0)
    disk_total = models.BigIntegerField(default=0)
    disk_percent = models.FloatField(default=0)
    
    # Network metrics
    network_bytes_sent = models.BigIntegerField(default=0)
    network_bytes_recv = models.BigIntegerField(default=0)
    network_packets_sent = models.BigIntegerField(default=0)
    network_packets_recv = models.BigIntegerField(default=0)
    network_errin = models.BigIntegerField(default=0)
    network_errout = models.BigIntegerField(default=0)

    class Meta:
        ordering = ['-timestamp']
        get_latest_by = 'timestamp'
        indexes = [
            models.Index(fields=['device', 'timestamp']),
        ]

    