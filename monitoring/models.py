from django.db import models


class MetricType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.unit})"

class Metric(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='metrics')
    metric_type = models.ForeignKey(MetricType, on_delete=models.CASCADE)
    value = models.FloatField()
    timestamp = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['device', 'metric_type', 'timestamp']),
        ]

class ResourceMetrics(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='resource_metrics')
    timestamp = models.DateTimeField()
    
    # CPU Metrics
    cpu_percent = models.FloatField()
    cpu_cores_used = models.FloatField()
    cpu_frequency = models.FloatField(null=True)  # MHz
    
    # Memory Metrics
    memory_total = models.BigIntegerField()  # bytes
    memory_used = models.BigIntegerField()  # bytes
    memory_available = models.BigIntegerField()  # bytes
    memory_percent = models.FloatField()
    swap_used = models.BigIntegerField(null=True)  # bytes
    
    # Disk Metrics
    disk_total = models.BigIntegerField()  # bytes
    disk_used = models.BigIntegerField()  # bytes
    disk_free = models.BigIntegerField()  # bytes
    disk_percent = models.FloatField()
    
    # Network Metrics
    network_bytes_sent = models.BigIntegerField()
    network_bytes_recv = models.BigIntegerField()
    network_packets_sent = models.BigIntegerField()
    network_packets_recv = models.BigIntegerField()
    network_errors_in = models.IntegerField()
    network_errors_out = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=['device', 'timestamp']),
        ]

class MetricThreshold(models.Model):
    SEVERITY_LEVELS = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
        ('ERROR', 'Error'),
    ]

    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    metric_type = models.ForeignKey(MetricType, on_delete=models.CASCADE)
    warning_threshold = models.FloatField()
    critical_threshold = models.FloatField()
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['device', 'metric_type']