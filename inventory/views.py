from django.views.generic import ListView, DetailView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import models
from .models import Device, SystemResources, SystemMetricsHistory
import json
from ipware import get_client_ip
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from datetime import timedelta

class DeviceListView(ListView):
    model = Device
    template_name = 'inventory/device_list.html'
    context_object_name = 'devices'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_counts'] = {
            'total': Device.objects.count(),
            'pending': Device.objects.filter(status='pending').count(),
            'active': Device.objects.filter(status='active').count(),
            'rejected': Device.objects.filter(status='rejected').count(),
        }
        return context

    def post(self, request, *args, **kwargs):
        device_id = request.POST.get('device_id')
        action = request.POST.get('action')
        
        device = get_object_or_404(Device, id=device_id)
        if action == 'accept':
            device.status = 'active'
        elif action == 'reject':
            device.status = 'rejected'
        device.save()
        
        return JsonResponse({'status': 'success'})

@method_decorator(csrf_exempt, name='dispatch')
class MetricsAPIView(View):
    def validate_api_key(self, request):
        api_key = request.headers.get('X-Api-Key')
        expected_key = getattr(settings, 'API_KEY', 'your-default-api-key-here')  # Replace with your actual API key
        
        print("\n=== API Key Validation ===")
        print(f"Received API Key: {api_key}")
        print(f"Expected API Key: {expected_key}")
        print("========================\n")
        
        return api_key == expected_key

    def get(self, request, *args, **kwargs):
        print("\n=== Metrics API GET Request ===")
        print("Headers:", dict(request.headers))
        print("========================\n")
        
        if not self.validate_api_key(request):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid or missing API key'
            }, status=401)
        
        # Return example format for valid API keys
        return JsonResponse({
            'status': 'success',
            'message': 'API is working. Use POST method to submit metrics.',
            'example_format': {
                'system_info': {
                    'hostname': 'example-host',
                    'ip_address': '192.168.1.1',
                    'os': 'Windows 10',
                    'platform': 'Windows-10-10.0.19041-SP0',
                    'processor': 'Intel64 Family 6'
                },
                'metrics': {
                    'cpu': {
                        'usage_percent': 25.0,
                        'core_count': 4
                    },
                    'memory': {
                        'total': 8589934592,
                        'available': 4294967296
                    },
                    'disk': {
                        'total': 256060514304,
                        'used': 128030257152
                    }
                }
            }
        })

    def post(self, request, *args, **kwargs):
        try:
            print("\n=== Received Metrics Data ===")
            print("Client IP:", get_client_ip(request)[0])
            print("Headers:", dict(request.headers))
            
            if not self.validate_api_key(request):
                print("API Key validation failed")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid or missing API key'
                }, status=401)
                
            try:
                data = json.loads(request.body)
                
                # Print system information
                system_info = data.get('system_info', {})
                print("\nSystem Information:")
                print(f"Hostname: {system_info.get('hostname')}")
                print(f"IP Address: {system_info.get('ip_address')}")
                print(f"OS: {system_info.get('os')}")
                print(f"Platform: {system_info.get('platform')}")
                print(f"Processor: {system_info.get('processor')}")
                
                # Print metrics
                metrics = data.get('metrics', {})
                print("\nMetrics:")
                print("CPU:")
                print(f"  Usage: {metrics.get('cpu', {}).get('usage_percent')}%")
                print(f"  Cores: {metrics.get('cpu', {}).get('core_count')}")
                print(f"  Frequency: {metrics.get('cpu', {}).get('frequency_mhz')} MHz")
                
                print("\nMemory:")
                memory = metrics.get('memory', {})
                total_gb = memory.get('total', 0) / (1024**3)
                used_gb = memory.get('used', 0) / (1024**3)
                print(f"  Total: {total_gb:.2f} GB")
                print(f"  Used: {used_gb:.2f} GB")
                print(f"  Usage: {memory.get('percent')}%")
                
                print("\nDisk:")
                disk = metrics.get('disk', {})
                total_gb = disk.get('total', 0) / (1024**3)
                used_gb = disk.get('used', 0) / (1024**3)
                print(f"  Total: {total_gb:.2f} GB")
                print(f"  Used: {used_gb:.2f} GB")
                print(f"  Usage: {disk.get('percent')}%")
                
                print("\nNetwork:")
                network = metrics.get('network', {})
                print(f"  Bytes Sent: {network.get('bytes_sent', 0)}")
                print(f"  Bytes Received: {network.get('bytes_recv', 0)}")
                print("========================\n")
                
                # Continue with existing processing...
                device, created = Device.objects.get_or_create(
                    ip_address=system_info.get('ip_address'),
                    defaults={
                        'hostname': system_info.get('hostname'),
                        'name': system_info.get('hostname'),
                        'device_type': 'WORKSTATION',
                        'platform': system_info.get('platform'),
                        'processor': system_info.get('processor'),
                        'os_version': system_info.get('os'),
                    }
                )
                
                # Rest of your existing code...
                
                # Get or create device
                system_info = data.get('system_info', {})
                metrics = data.get('metrics', {})
                
                device, created = Device.objects.get_or_create(
                    ip_address=system_info.get('ip_address'),
                    defaults={
                        'hostname': system_info.get('hostname'),
                        'name': system_info.get('hostname'),
                        'device_type': 'WORKSTATION',
                        'platform': system_info.get('platform'),
                        'processor': system_info.get('processor'),
                        'os_version': system_info.get('os'),
                    }
                )
                
                # Update current metrics in SystemResources
                resources, _ = SystemResources.objects.get_or_create(device=device)
                
                # Update CPU information
                cpu_metrics = metrics.get('cpu', {})
                resources.cpu_cores = cpu_metrics.get('core_count', 0)
                resources.cpu_usage = cpu_metrics.get('usage_percent', 0)
                resources.cpu_frequency = cpu_metrics.get('frequency_mhz', 0)
                
                # Update Memory information
                memory_metrics = metrics.get('memory', {})
                resources.total_memory = memory_metrics.get('total', 0)
                resources.used_memory = memory_metrics.get('used', 0)
                resources.memory_usage = memory_metrics.get('percent', 0)
                
                # Update Disk information
                disk_metrics = metrics.get('disk', {})
                resources.total_disk_space = disk_metrics.get('total', 0)
                resources.used_disk_space = disk_metrics.get('used', 0)
                resources.disk_usage = disk_metrics.get('percent', 0)
                
                # Update Network information
                network_metrics = metrics.get('network', {})
                resources.bytes_sent = network_metrics.get('bytes_sent', 0)
                resources.bytes_received = network_metrics.get('bytes_recv', 0)
                
                resources.save()
                
                # Store historical metrics
                SystemMetricsHistory.objects.create(
                    device=device,
                    # CPU metrics
                    cpu_usage=float(cpu_metrics.get('usage_percent', 0)),
                    cpu_frequency=float(cpu_metrics.get('frequency_mhz', 0)),
                    cpu_cores=int(cpu_metrics.get('core_count', 0)),
                    cpu_min=float(cpu_metrics.get('min', 0)),
                    cpu_max=float(cpu_metrics.get('max', 0)),
                    cpu_std_dev=float(cpu_metrics.get('std_dev', 0)),
                    
                    # Memory metrics
                    memory_used=int(memory_metrics.get('used', 0)),
                    memory_total=int(memory_metrics.get('total', 0)),
                    memory_percent=float(memory_metrics.get('percent', 0)),
                    memory_peak=int(memory_metrics.get('peak_usage', 0)),
                    
                    # Disk metrics
                    disk_used=int(disk_metrics.get('used', 0)),
                    disk_total=int(disk_metrics.get('total', 0)),
                    disk_percent=float(disk_metrics.get('percent', 0)),
                    
                    # Network metrics
                    network_bytes_sent=int(network_metrics.get('bytes_sent', 0)),
                    network_bytes_recv=int(network_metrics.get('bytes_recv', 0)),
                    network_packets_sent=int(network_metrics.get('packets_sent', 0)),
                    network_packets_recv=int(network_metrics.get('packets_recv', 0)),
                    network_errin=int(network_metrics.get('errors_in', 0)),
                    network_errout=int(network_metrics.get('errors_out', 0))
                )

                device.last_seen = timezone.now()
                device.save()

                return JsonResponse({'status': 'success', 'device_id': str(device.id)})
                
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                print("Raw request body:", request.body)
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            except Exception as e:
                print(f"Error processing metrics: {e}")
                return JsonResponse({'error': str(e)}, status=500)
                
        except Exception as e:
            print(f"Unexpected error: {e}")
            return JsonResponse({'error': 'Internal server error'}, status=500)

class DeviceActionView(View):
    def post(self, request, device_id):
        try:
            print("\n=== Device Action Request ===")
            print(f"Device ID: {device_id}")
            print(f"POST data: {request.POST}")
            print("Headers:", dict(request.headers))
            print("========================\n")
            
            device = get_object_or_404(Device, id=device_id)
            action = request.POST.get('action')
            
            print(f"Processing action '{action}' for device: {device.hostname or device.name}")
            
            if action == 'accept':
                device.status = 'active'
                print("Setting status to 'active'")
            elif action == 'reject':
                device.status = 'rejected'
                print("Setting status to 'rejected'")
            else:
                print(f"Invalid action received: {action}")
                return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)
            
            device.save()
            print("Device status updated successfully")
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            print(f"Error processing device action: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

class DeviceDetailView(LoginRequiredMixin, DetailView):
    model = Device
    template_name = 'inventory/device_detail.html'
    context_object_name = 'device'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        device = self.get_object()
        
        # Get time range from request with more options
        time_range = self.request.GET.get('range', '1h')
        end_time = timezone.now()
        
        # Calculate start time based on range
        time_ranges = {
            '30m': timedelta(minutes=30),
            '1h': timedelta(hours=1),
            '3h': timedelta(hours=3),
            '12h': timedelta(hours=12),
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7),
        }
        
        start_time = end_time - time_ranges.get(time_range, time_ranges['1h'])
            
        # Get current resources
        try:
            resources = device.resources
            context['current_resources'] = {
                'cpu_cores': resources.cpu_cores,
                'cpu_usage': resources.cpu_usage,
                'total_memory': resources.total_memory,
                'memory_usage': resources.memory_usage,
                'total_disk_space': resources.total_disk_space,
                'disk_usage': resources.disk_usage,
            }
        except SystemResources.DoesNotExist:
            context['current_resources'] = None

        # Get historical metrics
        metrics = SystemMetricsHistory.objects.filter(
            device=device,
            timestamp__range=(start_time, end_time)
        ).order_by('timestamp')

        # Calculate statistics
        if metrics.exists():
            stats = {
                'cpu': {
                    'max': metrics.aggregate(models.Max('cpu_usage'))['cpu_usage__max'],
                    'min': metrics.aggregate(models.Min('cpu_usage'))['cpu_usage__min'],
                    'avg': metrics.aggregate(models.Avg('cpu_usage'))['cpu_usage__avg'],
                },
                'memory': {
                    'max': metrics.aggregate(models.Max('memory_percent'))['memory_percent__max'],
                    'min': metrics.aggregate(models.Min('memory_percent'))['memory_percent__min'],
                    'avg': metrics.aggregate(models.Avg('memory_percent'))['memory_percent__avg'],
                },
                'disk': {
                    'max': metrics.aggregate(models.Max('disk_percent'))['disk_percent__max'],
                    'min': metrics.aggregate(models.Min('disk_percent'))['disk_percent__min'],
                    'avg': metrics.aggregate(models.Avg('disk_percent'))['disk_percent__avg'],
                }
            }
        else:
            stats = None

        # Initialize chart data
        chart_data = {
            'timestamps': [],
            'cpu': {'usage': [], 'min': [], 'max': []},
            'memory': {'usage': [], 'used': []},
            'disk': {'usage': []},
            'network': {'bytes_sent': [], 'bytes_recv': []}
        }
        
        # Populate chart data
        for metric in metrics:
            timestamp = metric.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            chart_data['timestamps'].append(timestamp)
            
            # CPU data
            chart_data['cpu']['usage'].append(float(metric.cpu_usage))
            chart_data['cpu']['min'].append(float(metric.cpu_min or 0))
            chart_data['cpu']['max'].append(float(metric.cpu_max or 0))
            
            # Memory data (convert to GB)
            memory_used_gb = float(metric.memory_used) / (1024 ** 3)
            chart_data['memory']['usage'].append(float(metric.memory_percent))
            chart_data['memory']['used'].append(round(memory_used_gb, 2))
            
            # Disk data
            chart_data['disk']['usage'].append(float(metric.disk_percent))

        context.update({
            'chart_data': chart_data,
            'time_range': time_range,
            'stats': stats,
            'time_ranges': time_ranges.keys(),
        })
        
        return context
