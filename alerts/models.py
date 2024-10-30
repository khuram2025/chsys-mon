from django.db import models

class Alert(models.Model):
    ALERT_STATES = [
        ('NEW', 'New'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('RESOLVED', 'Resolved'),
        ('IGNORED', 'Ignored'),
    ]

    device = models.ForeignKey('inventory.Device', on_delete=models.CASCADE)
    metric = models.ForeignKey('monitoring.Metric', on_delete=models.CASCADE)
    threshold = models.ForeignKey('monitoring.MetricThreshold', on_delete=models.CASCADE)
    message = models.TextField()
    state = models.CharField(max_length=20, choices=ALERT_STATES, default='NEW')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    acknowledged_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
