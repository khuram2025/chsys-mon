from django.contrib import admin
from .models import Device, SystemResources, SystemMetricsHistory

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'hostname', 'ip_address', 'device_type', 'status', 'last_seen')
    list_filter = ('device_type', 'status')
    search_fields = ('name', 'hostname', 'ip_address')

@admin.register(SystemResources)
class SystemResourcesAdmin(admin.ModelAdmin):
    list_display = ('device', 'cpu_cores', 'cpu_usage', 'memory_usage', 'disk_usage', 'last_updated')
    list_filter = ('device__device_type',)
    search_fields = ('device__name', 'device__hostname')

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]
    
    def last_updated(self, obj):
        return obj.updated_at
    last_updated.short_description = 'Last Updated'

@admin.register(SystemMetricsHistory)
class SystemMetricsHistoryAdmin(admin.ModelAdmin):
    list_display = ('device', 'timestamp', 'cpu_usage', 'memory_percent', 'disk_percent')
    list_filter = ('device', 'timestamp', 'device__device_type')
    search_fields = ('device__name', 'device__hostname')
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Device Info', {
            'fields': ('device', 'timestamp')
        }),
        ('CPU Metrics', {
            'fields': ('cpu_usage', 'cpu_frequency', 'cpu_cores', 'cpu_min', 'cpu_max', 'cpu_std_dev')
        }),
        ('Memory Metrics', {
            'fields': ('memory_used', 'memory_total', 'memory_percent', 'memory_peak')
        }),
        ('Disk Metrics', {
            'fields': ('disk_used', 'disk_total', 'disk_percent')
        }),
        ('Network Metrics', {
            'fields': (
                'network_bytes_sent', 'network_bytes_recv',
                'network_packets_sent', 'network_packets_recv',
                'network_errin', 'network_errout'
            )
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]
