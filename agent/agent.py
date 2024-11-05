import wx
import wx.adv
import psutil
import requests
import json
import os
import sys
import logging
import threading
import time
import platform
import socket
import statistics
from datetime import datetime, timedelta
from collections import defaultdict
import zlib
import sqlite3
from pathlib import Path

TRAY_ICON_GREEN = "icons/connected.ico"
TRAY_ICON_RED = "icons/disconnected.ico"
TRAY_TOOLTIP = "CHSys Monitor Agent"

class MetricBuffer:
    def __init__(self, buffer_interval=300):
        self.buffer_interval = buffer_interval
        self.metrics_buffer = []
        self.last_send_time = datetime.now()
        self.max_buffer_size = 1000  # Add maximum buffer size
        self.disk_usage_threshold = 0.9  # 90% disk usage threshold
    
    def add_metrics(self, metrics):
        # Check buffer size and disk space before adding
        if len(self.metrics_buffer) >= self.max_buffer_size:
            # Remove oldest entries if buffer is full
            self.metrics_buffer = self.metrics_buffer[-(self.max_buffer_size//2):]
            logging.warning("Buffer size exceeded, truncating old data")
        
        # Add timestamp if not present
        if 'collected_at' not in metrics:
            metrics['collected_at'] = datetime.now().isoformat()
        
        self.metrics_buffer.append(metrics)
    
    def should_send(self):
        return (datetime.now() - self.last_send_time).total_seconds() >= self.buffer_interval
    
    def aggregate_metrics(self):
        if not self.metrics_buffer:
            return None
            
        system_info = self.metrics_buffer[-1]['system_info']
        
        # Initialize with the latest metrics instead of zeros
        latest_metrics = self.metrics_buffer[-1]['metrics']
        aggregated = {
            'timestamp': datetime.utcnow().isoformat(),
            'system_info': system_info,
            'metrics': {
                'cpu': {
                    'usage_percent': latest_metrics['cpu']['usage_percent'],
                    'core_count': latest_metrics['cpu']['core_count'],
                    'frequency_mhz': latest_metrics['cpu']['frequency_mhz'],
                    'per_core': latest_metrics['cpu']['per_core'],
                    'min': latest_metrics['cpu']['usage_percent'],
                    'max': latest_metrics['cpu']['usage_percent'],
                    'std_dev': 0
                },
                'memory': {
                    'total': latest_metrics['memory']['total'],
                    'used': latest_metrics['memory']['used'],  # Add current used memory
                    'percent': latest_metrics['memory']['percent'],  # Add current percent
                    'used_avg': 0,
                    'percent_avg': 0,
                    'peak_usage': latest_metrics['memory']['used']
                },
                'disk': {
                    'total': latest_metrics['disk']['total'],
                    'used': latest_metrics['disk']['used'],  # Add current used disk
                    'percent': latest_metrics['disk']['percent'],  # Add current percent
                    'used_avg': 0,
                    'percent_avg': 0
                },
                'network': {
                    'bytes_sent': latest_metrics['network']['bytes_sent'],
                    'bytes_recv': latest_metrics['network']['bytes_recv'],
                    'packets_sent': latest_metrics['network']['packets_sent'],
                    'packets_recv': latest_metrics['network']['packets_recv'],
                    'errin': latest_metrics['network']['errin'],
                    'errout': latest_metrics['network']['errout']
                }
            }
        }
        
        cpu_usages = []
        memory_percentages = []
        disk_percentages = []
        memory_used = []
        disk_used = []
        
        start_time = datetime.fromisoformat(self.metrics_buffer[0]['timestamp'])
        end_time = datetime.fromisoformat(self.metrics_buffer[-1]['timestamp'])
        time_span = (end_time - start_time).total_seconds()
        
        for metric in self.metrics_buffer:
            cpu_usages.append(metric['metrics']['cpu']['usage_percent'])
            memory_percentages.append(metric['metrics']['memory']['percent'])
            disk_percentages.append(metric['metrics']['disk']['percent'])
            memory_used.append(metric['metrics']['memory']['used'])
            disk_used.append(metric['metrics']['disk']['used'])
            
            # Update network totals
            network_key_mapping = {
                'bytes_sent_total': 'bytes_sent',
                'bytes_recv_total': 'bytes_recv',
                'packets_sent_total': 'packets_sent',
                'packets_recv_total': 'packets_recv',
                'errors_in_total': 'errin',
                'errors_out_total': 'errout'
            }
            
            for agg_key, metric_key in network_key_mapping.items():
                aggregated['metrics']['network'][agg_key] = metric['metrics']['network'][metric_key]
        
        # Calculate statistics
        aggregated['metrics']['cpu'].update({
            'min': min(cpu_usages),
            'max': max(cpu_usages),
            'std_dev': statistics.stdev(cpu_usages) if len(cpu_usages) > 1 else 0
        })
        
        aggregated['metrics']['memory'].update({
            'used_avg': statistics.mean(memory_used),
            'percent_avg': statistics.mean(memory_percentages),
            'peak_usage': max(memory_used)
        })
        
        aggregated['metrics']['disk'].update({
            'used_avg': statistics.mean(disk_used),
            'percent_avg': statistics.mean(disk_percentages)
        })
        
        # Calculate network rates
        if time_span > 0:
            aggregated['metrics']['network'].update({
                'transfer_rate_send': aggregated['metrics']['network']['bytes_sent_total'] / time_span,
                'transfer_rate_recv': aggregated['metrics']['network']['bytes_recv_total'] / time_span
            })
        
        self.metrics_buffer = []
        self.last_send_time = datetime.now()
        
        return aggregated

class StatusDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="CHSys Monitor Status", size=(500, 600))
        self.parent = parent
        self.init_ui()
        self.update_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_status)
        self.update_timer.Start(1000)

    def init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # System Information
        sys_box = wx.StaticBox(panel, label="System Information")
        sys_sizer = wx.StaticBoxSizer(sys_box, wx.VERTICAL)
        
        self.hostname_text = wx.StaticText(panel, label=f"Hostname: {socket.gethostname()}")
        self.ip_text = wx.StaticText(panel, label=f"IP Address: {socket.gethostbyname(socket.gethostname())}")
        self.os_text = wx.StaticText(panel, label=f"OS: {platform.system()} {platform.version()}")
        
        sys_sizer.Add(self.hostname_text, 0, wx.ALL, 5)
        sys_sizer.Add(self.ip_text, 0, wx.ALL, 5)
        sys_sizer.Add(self.os_text, 0, wx.ALL, 5)

        # Connection Status
        conn_box = wx.StaticBox(panel, label="Connection Status")
        conn_sizer = wx.StaticBoxSizer(conn_box, wx.VERTICAL)
        
        self.status_text = wx.StaticText(panel, label="Status: Checking...")
        self.server_text = wx.StaticText(panel, label=f"Server: {self.parent.config['server_url']}")
        self.last_update = wx.StaticText(panel, label="Last Update: Never")
        self.buffer_status = wx.StaticText(panel, label="Buffer Status: Empty")
        self.next_send = wx.StaticText(panel, label="Next Send: Calculating...")
        
        conn_sizer.Add(self.status_text, 0, wx.ALL, 5)
        conn_sizer.Add(self.server_text, 0, wx.ALL, 5)
        conn_sizer.Add(self.last_update, 0, wx.ALL, 5)
        conn_sizer.Add(self.buffer_status, 0, wx.ALL, 5)
        conn_sizer.Add(self.next_send, 0, wx.ALL, 5)

        # Resource Metrics
        metrics_box = wx.StaticBox(panel, label="System Metrics")
        metrics_sizer = wx.StaticBoxSizer(metrics_box, wx.VERTICAL)
        
        # CPU
        cpu_box = wx.BoxSizer(wx.HORIZONTAL)
        self.cpu_gauge = wx.Gauge(panel, range=100, size=(150, 25))
        self.cpu_text = wx.StaticText(panel, label="CPU: 0%")
        cpu_box.Add(wx.StaticText(panel, label="CPU Usage:"), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        cpu_box.Add(self.cpu_gauge, 1, wx.EXPAND|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        cpu_box.Add(self.cpu_text, 0, wx.ALIGN_CENTER_VERTICAL)
        
        # Memory
        mem_box = wx.BoxSizer(wx.HORIZONTAL)
        self.mem_gauge = wx.Gauge(panel, range=100, size=(150, 25))
        self.mem_text = wx.StaticText(panel, label="Memory: 0%")
        mem_box.Add(wx.StaticText(panel, label="Memory Usage:"), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        mem_box.Add(self.mem_gauge, 1, wx.EXPAND|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        mem_box.Add(self.mem_text, 0, wx.ALIGN_CENTER_VERTICAL)
        
        # Disk
        disk_box = wx.BoxSizer(wx.HORIZONTAL)
        self.disk_gauge = wx.Gauge(panel, range=100, size=(150, 25))
        self.disk_text = wx.StaticText(panel, label="Disk: 0%")
        disk_box.Add(wx.StaticText(panel, label="Disk Usage:"), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        disk_box.Add(self.disk_gauge, 1, wx.EXPAND|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        disk_box.Add(self.disk_text, 0, wx.ALIGN_CENTER_VERTICAL)
        
        metrics_sizer.Add(cpu_box, 0, wx.ALL|wx.EXPAND, 5)
        metrics_sizer.Add(mem_box, 0, wx.ALL|wx.EXPAND, 5)
        metrics_sizer.Add(disk_box, 0, wx.ALL|wx.EXPAND, 5)

        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        configure_btn = wx.Button(panel, label="Configure")
        configure_btn.Bind(wx.EVT_BUTTON, self.on_configure)
        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        button_sizer.Add(configure_btn, 0, wx.RIGHT, 5)
        button_sizer.Add(close_btn)

        main_sizer.Add(sys_sizer, 0, wx.ALL|wx.EXPAND, 5)
        main_sizer.Add(conn_sizer, 0, wx.ALL|wx.EXPAND, 5)
        main_sizer.Add(metrics_sizer, 0, wx.ALL|wx.EXPAND, 5)
        main_sizer.Add(button_sizer, 0, wx.ALL|wx.ALIGN_RIGHT, 10)

        panel.SetSizer(main_sizer)
        
    def format_bytes(self, bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        
    def update_status(self, event):
        # Update metrics
        cpu_percent = psutil.cpu_percent()
        self.cpu_gauge.SetValue(int(cpu_percent))
        self.cpu_text.SetLabel(f"CPU: {cpu_percent}%")
        
        mem = psutil.virtual_memory()
        self.mem_gauge.SetValue(int(mem.percent))
        self.mem_text.SetLabel(f"Memory: {mem.percent}% (Used: {self.format_bytes(mem.used)} / Total: {self.format_bytes(mem.total)})")
        
        disk = psutil.disk_usage('/')
        self.disk_gauge.SetValue(int(disk.percent))
        self.disk_text.SetLabel(f"Disk: {disk.percent}% (Used: {self.format_bytes(disk.used)} / Total: {self.format_bytes(disk.total)})")
        
        # Update connection status
        status = "Connected" if self.parent.last_connection_successful else "Disconnected"
        status_color = "green" if self.parent.last_connection_successful else "red"
        self.status_text.SetLabel(f"Status: {status}")
        self.status_text.SetForegroundColour(status_color)
        
        # Update buffer status
        if hasattr(self.parent.monitoring_thread, 'metric_buffer'):
            buffer_size = len(self.parent.monitoring_thread.metric_buffer.metrics_buffer)
            self.buffer_status.SetLabel(f"Buffer Status: {buffer_size} samples")
            
            # Calculate next send time
            if self.parent.monitoring_thread.metric_buffer.last_send_time:
                next_send = self.parent.monitoring_thread.metric_buffer.last_send_time + \
                           timedelta(seconds=self.parent.monitoring_thread.metric_buffer.buffer_interval)
                time_to_next = (next_send - datetime.now()).total_seconds()
                if time_to_next > 0:
                    self.next_send.SetLabel(f"Next Send: {time_to_next:.0f} seconds")
                else:
                    self.next_send.SetLabel("Next Send: Due now")
        
        if hasattr(self.parent, 'last_connection_time'):
            self.last_update.SetLabel(f"Last Update: {self.parent.last_connection_time.strftime('%Y-%m-%d %H:%M:%S')}")

    def on_configure(self, event):
        self.parent.on_configure(event)
        self.server_text.SetLabel(f"Server: {self.parent.config['server_url']}")

    def on_close(self, event):
        self.update_timer.Stop()
        self.Hide()

class ConfigDialog(wx.Dialog):
    def __init__(self, parent, config):
        super().__init__(parent, title="Agent Configuration", size=(400, 300))
        self.parent = parent
        self.config = config.copy()
        self.init_ui()

    def init_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Server URL
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        st1 = wx.StaticText(panel, label='Server URL:')
        hbox1.Add(st1, flag=wx.RIGHT, border=8)
        self.tc1 = wx.TextCtrl(panel, value=self.config.get('server_url', ''))
        hbox1.Add(self.tc1, proportion=1)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        # API Key
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        st2 = wx.StaticText(panel, label='API Key:')
        hbox2.Add(st2, flag=wx.RIGHT, border=8)
        self.tc2 = wx.TextCtrl(panel, value=self.config.get('api_key', ''))
        hbox2.Add(self.tc2, proportion=1)
        vbox.Add(hbox2, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        # Collection Interval
        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        st3 = wx.StaticText(panel, label='Collection Interval (s):')
        hbox3.Add(st3, flag=wx.RIGHT, border=8)
        self.tc3 = wx.TextCtrl(panel, value=str(self.config.get('collection_interval', 30)))
        hbox3.Add(self.tc3, proportion=1)
        vbox.Add(hbox3, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        # Buffer Interval
        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        st4 = wx.StaticText(panel, label='Buffer Interval (s):')
        hbox4.Add(st4, flag=wx.RIGHT, border=8)
        self.tc4 = wx.TextCtrl(panel, value=str(self.config.get('buffer_interval', 300)))
        hbox4.Add(self.tc4, proportion=1)
        vbox.Add(hbox4, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        # Test Connection Button
        test_btn = wx.Button(panel, label='Test Connection')
        test_btn.Bind(wx.EVT_BUTTON, self.on_test_connection)
        vbox.Add(test_btn, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        # Status text for test results
        self.test_status = wx.StaticText(panel, label="")
        vbox.Add(self.test_status, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        # Buttons
        btnbox = wx.BoxSizer(wx.HORIZONTAL)
        saveBtn = wx.Button(panel, label='Save')
        saveBtn.Bind(wx.EVT_BUTTON, self.on_save)
        cancelBtn = wx.Button(panel, label='Cancel')
        cancelBtn.Bind(wx.EVT_BUTTON, self.on_cancel)
        btnbox.Add(saveBtn)
        btnbox.Add(cancelBtn, flag=wx.LEFT, border=5)
        vbox.Add(btnbox, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)

        panel.SetSizer(vbox)

    def on_test_connection(self, event):
        self.test_status.SetLabel("Testing connection...")
        self.test_status.SetForegroundColour(wx.BLACK)
        
        try:
            # Get the current metrics using the parent's collect_metrics method
            current_metrics = self.parent.collect_metrics()
            
            if not current_metrics:
                self.test_status.SetLabel("Failed to collect system metrics")
                self.test_status.SetForegroundColour(wx.RED)
                return
                
            test_url = self.tc1.GetValue().strip()
            api_key = self.tc2.GetValue().strip()
            
            print("\n=== Test Connection Request ===")
            print(f"URL: {test_url}")
            print(f"API Key: {api_key}")
            print("Sending current metrics...")
            print(json.dumps(current_metrics, indent=2))
            print("========================\n")

            # Send current metrics
            response = requests.post(
                test_url,
                headers={
                    'Content-Type': 'application/json',
                    'X-API-Key': api_key
                },
                json=current_metrics,
                timeout=10
            )

            if response.status_code == 200:
                self.test_status.SetLabel("Success! Current metrics sent to server")
                self.test_status.SetForegroundColour(wx.Colour(0, 128, 0))  # Green
                
                # Try to send buffered data if available
                if hasattr(self.parent.monitoring_thread, 'metric_buffer'):
                    buffer = self.parent.monitoring_thread.metric_buffer
                    if buffer.metrics_buffer:
                        self.test_status.SetLabel("Sending buffered data...")
                        aggregated_metrics = buffer.aggregate_metrics()
                        if aggregated_metrics:
                            print("\n=== Sending Buffered Data ===")
                            print(json.dumps(aggregated_metrics, indent=2))
                            print("========================\n")
                            
                            buffer_response = requests.post(
                                test_url,
                                headers={
                                    'Content-Type': 'application/json',
                                    'X-API-Key': api_key
                                },
                                json=aggregated_metrics,
                                timeout=10
                            )
                            if buffer_response.status_code == 200:
                                self.test_status.SetLabel("Success! All data sent to server")
                            else:
                                self.test_status.SetLabel(f"Buffer send failed: {buffer_response.status_code}")
            else:
                self.test_status.SetLabel(f"Failed to send metrics. Status: {response.status_code}")
                self.test_status.SetForegroundColour(wx.RED)
                
        except Exception as e:
            self.test_status.SetLabel(f"Connection failed: {str(e)}")
            self.test_status.SetForegroundColour(wx.RED)
            logging.error(f"Test connection error: {e}")

    def validate_intervals(self):
        try:
            collection_interval = int(self.tc3.GetValue())
            buffer_interval = int(self.tc4.GetValue())
            
            if collection_interval < 10:
                wx.MessageBox('Collection interval must be at least 10 seconds', 'Error', wx.OK | wx.ICON_ERROR)
                return False
                
            if buffer_interval < collection_interval:
                wx.MessageBox('Buffer interval must be greater than collection interval', 'Error', wx.OK | wx.ICON_ERROR)
                return False
                
            if buffer_interval < 60:
                wx.MessageBox('Buffer interval must be at least 60 seconds', 'Error', wx.OK | wx.ICON_ERROR)
                return False
                
            return True
        except ValueError:
            wx.MessageBox('Invalid interval values', 'Error', wx.OK | wx.ICON_ERROR)
            return False

    def on_save(self, event):
        if not self.validate_intervals():
            return
            
        # Get new values
        new_collection_interval = int(self.tc3.GetValue())
        new_buffer_interval = int(self.tc4.GetValue())
        
        # Update config
        self.config['server_url'] = self.tc1.GetValue().strip()
        self.config['api_key'] = self.tc2.GetValue().strip()
        self.config['collection_interval'] = new_collection_interval
        self.config['buffer_interval'] = new_buffer_interval
        
        # Apply changes to parent's config
        self.parent.config.update(self.config)
        self.parent.save_config()
        
        # Update existing monitoring thread with new intervals
        if self.parent.monitoring_thread:
            self.parent.monitoring_thread.collection_interval = new_collection_interval
            self.parent.monitoring_thread.metric_buffer.buffer_interval = new_buffer_interval
            
            # Force a buffer send if interval was decreased
            if new_buffer_interval < self.parent.config.get('buffer_interval', 300):
                wx.CallAfter(self.force_buffer_send)
        
        self.EndModal(wx.ID_OK)

    def force_buffer_send(self):
        """Force send the current buffer data"""
        try:
            if self.parent.monitoring_thread and self.parent.monitoring_thread.metric_buffer.metrics_buffer:
                aggregated_metrics = self.parent.monitoring_thread.metric_buffer.aggregate_metrics()
                if aggregated_metrics:
                    self.parent.send_metrics(aggregated_metrics)
        except Exception as e:
            logging.error(f"Error forcing buffer send: {e}")

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)

class MetricsManager:
    def __init__(self, max_retries=3, retry_delay=60):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.failed_sends = []
        self.storage = LocalStorage()

    def send_with_retry(self, metrics, agent):
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                success = agent.send_metrics(metrics)
                if success:
                    return True
                retry_count += 1
                time.sleep(self.retry_delay)
            except Exception as e:
                logging.error(f"Send attempt {retry_count + 1} failed: {e}")
                retry_count += 1
                time.sleep(self.retry_delay)
        
        # Store failed metrics locally
        self.storage.store_metrics(metrics)
        return False

class MonitoringThread(threading.Thread):
    def __init__(self, agent):
        threading.Thread.__init__(self)
        self.agent = agent
        self.daemon = True
        self.running = True
        self.metric_buffer = MetricBuffer(buffer_interval=self.agent.config.get('buffer_interval', 300))
        self.metrics_manager = MetricsManager()
        self.collection_interval = self.agent.config.get('collection_interval', 30)
        self._interval_check_time = time.time()
        self.last_collection_success = True

    def run(self):
        while self.running:
            try:
                current_time = time.time()
                if current_time - self._interval_check_time >= self.collection_interval:
                    self._interval_check_time = current_time
                    
                    # Collect metrics with error handling
                    try:
                        metrics = self.agent.collect_metrics()
                        if metrics:
                            self.metric_buffer.add_metrics(metrics)
                            self.last_collection_success = True
                    except Exception as e:
                        logging.error(f"Metrics collection failed: {e}")
                        self.last_collection_success = False
                    
                    # Check if it's time to send buffered metrics
                    if self.metric_buffer.should_send():
                        aggregated_metrics = self.metric_buffer.aggregate_metrics()
                        if aggregated_metrics:
                            success = self.metrics_manager.send_with_retry(
                                aggregated_metrics, 
                                self.agent
                            )
                            wx.CallAfter(self.agent.update_connection_status, success)
                
                # Update UI status based on collection success
                wx.CallAfter(self.agent.update_connection_status, 
                           self.last_collection_success)
                
            except Exception as e:
                logging.error(f"Monitoring error: {e}")
                wx.CallAfter(self.agent.update_connection_status, False)
            
            time.sleep(min(1, self.collection_interval))

    def stop(self):
        if self.metric_buffer.metrics_buffer:
            try:
                aggregated_metrics = self.metric_buffer.aggregate_metrics()
                if aggregated_metrics:
                    self.agent.send_metrics(aggregated_metrics)
            except Exception as e:
                logging.error(f"Error sending final metrics: {e}")
        
        self.running = False

class MonitorAgent(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Channab Sys Agent")
        self.config = None
        self.last_connection_successful = False
        self.last_connection_time = None
        self.monitoring_thread = None
        self.status_dialog = None
        
        # Initialize the agent
        self.init_config()
        self.setup_logging()
        self.init_ui()
        self.start_monitoring()

    def init_config(self):
        """Initialize configuration"""
        try:
            config_path = os.path.join(os.path.dirname(sys.executable), 'config.json')
            if not os.path.exists(config_path):
                config_path = 'config.json'
            
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            # Use default config if loading fails
            self.config = {
                'server_url': 'http://localhost:8000/api/metrics',
                'api_key': '',
                'collection_interval': 30,
                'buffer_interval': 300,
                'log_level': 'INFO'
            }
            self.save_config()

    def init_ui(self):
        """Initialize user interface"""
        self.Hide()  # Hide main window
        self.tb_icon = TaskBarIcon(self)  # Create system tray icon

    def save_config(self):
        """Save configuration to file"""
        try:
            config_path = os.path.join(os.path.dirname(sys.executable), 'config.json')
            if not os.path.exists(os.path.dirname(config_path)):
                config_path = 'config.json'
                
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving config: {e}")

    def setup_logging(self):
        """Set up logging configuration"""
        try:
            log_dir = os.path.join(os.path.dirname(sys.executable), 'logs')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            log_file = os.path.join(log_dir, f'agent_{datetime.now().strftime("%Y%m%d")}.log')
            logging.basicConfig(
                level=getattr(logging, self.config.get('log_level', 'INFO')),
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
        except Exception as e:
            print(f"Error setting up logging: {e}")
            # Fallback to basic logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )

    def collect_metrics(self):
        """Collect system metrics"""
        try:
            # Get CPU info
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Get Memory info
            memory = psutil.virtual_memory()
            
            # Get Disk info
            disk = psutil.disk_usage('/')
            
            # Get Network info
            network = psutil.net_io_counters()
            
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'system_info': {
                    'hostname': socket.gethostname(),
                    'ip_address': socket.gethostbyname(socket.gethostname()),
                    'os': f"{platform.system()} {platform.version()}",
                    'platform': platform.platform(),
                    'processor': platform.processor(),
                    'machine': platform.machine()
                },
                'metrics': {
                    'cpu': {
                        'usage_percent': cpu_percent,
                        'core_count': cpu_count,
                        'frequency_mhz': cpu_freq.current if cpu_freq else None,
                        'per_core': psutil.cpu_percent(percpu=True)
                    },
                    'memory': {
                        'total': memory.total,
                        'available': memory.available,
                        'used': memory.used,
                        'percent': memory.percent,
                        'swap_used': psutil.swap_memory().used if hasattr(psutil, 'swap_memory') else None
                    },
                    'disk': {
                        'total': disk.total,
                        'used': disk.used,
                        'free': disk.free,
                        'percent': disk.percent
                    },
                    'network': {
                        'bytes_sent': network.bytes_sent,
                        'bytes_recv': network.bytes_recv,
                        'packets_sent': network.packets_sent,
                        'packets_recv': network.packets_recv,
                        'errin': network.errin,
                        'errout': network.errout
                    }
                }
            }
            
            logging.debug(f"Collected metrics: {json.dumps(metrics, indent=2)}")
            return metrics
            
        except Exception as e:
            logging.error(f"Error collecting metrics: {e}")
            return None

    def send_metrics(self, metrics):
        """Send metrics to server"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': self.config['api_key']
            }
            
            response = requests.post(
                self.config['server_url'],
                json=metrics,
                headers=headers,
                timeout=10
            )
            
            self.last_connection_successful = response.status_code == 200
            self.last_connection_time = datetime.now()
            
            if self.last_connection_successful:
                logging.debug("Successfully sent metrics to server")
            else:
                logging.error(f"Failed to send metrics. Status code: {response.status_code}")
            
            return self.last_connection_successful
            
        except Exception as e:
            logging.error(f"Error sending metrics: {e}")
            self.last_connection_successful = False
            return False

    def start_monitoring(self):
        """Start monitoring thread"""
        if self.monitoring_thread is None:
            self.monitoring_thread = MonitoringThread(self)
            self.monitoring_thread.start()

    def restart_monitoring(self):
        """Restart monitoring thread"""
        if self.monitoring_thread:
            self.monitoring_thread.stop()
            self.monitoring_thread.join()
        self.start_monitoring()

    def show_status(self):
        """Show status dialog"""
        if not self.status_dialog:
            self.status_dialog = StatusDialog(self)
        self.status_dialog.Show()
        self.status_dialog.Raise()

    def update_connection_status(self, connected):
        """Update connection status"""
        self.tb_icon.set_icon(connected)

    def on_configure(self, event):
        """Show configuration dialog"""
        dlg = ConfigDialog(self, self.config)
        if dlg.ShowModal() == wx.ID_OK:
            pass  # Configuration is updated in ConfigDialog.on_save
        dlg.Destroy()

    def on_exit(self, event):
        """Handle application exit"""
        msg = "Are you sure you want to exit? The agent will stop monitoring."
        dlg = wx.MessageDialog(None, msg, "Confirm Exit",
                             wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        
        if dlg.ShowModal() == wx.ID_YES:
            if self.monitoring_thread:
                self.monitoring_thread.stop()
            self.tb_icon.RemoveIcon()
            self.tb_icon.Destroy()
            self.Destroy()
            sys.exit(0)
        
        dlg.Destroy()

class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame):
        super().__init__()
        self.frame = frame
        self.connected = False
        self.set_icon(False)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_click)
        self.Bind(wx.adv.EVT_TASKBAR_RIGHT_DOWN, self.on_right_click)

    def set_icon(self, connected):
        self.connected = connected
        icon = wx.Icon(TRAY_ICON_GREEN if connected else TRAY_ICON_RED)
        self.SetIcon(icon, TRAY_TOOLTIP)

    def on_left_click(self, event):
        self.frame.show_status()

    def on_right_click(self, event):
        menu = wx.Menu()
        status = "Connected" if self.connected else "Disconnected"
        menu.Append(wx.ID_ANY, f"Status: {status}").Enable(False)
        menu.AppendSeparator()
        
        show_item = menu.Append(wx.ID_ANY, "Show Status")
        self.Bind(wx.EVT_MENU, self.on_show_status, show_item)
        
        config_item = menu.Append(wx.ID_ANY, "Configure")
        self.Bind(wx.EVT_MENU, self.frame.on_configure, config_item)
        
        menu.AppendSeparator()
        exit_item = menu.Append(wx.ID_ANY, "Exit")
        self.Bind(wx.EVT_MENU, self.frame.on_exit, exit_item)
        
        self.PopupMenu(menu)

    def on_show_status(self, event):
        self.frame.show_status()

class LocalStorage:
    def __init__(self, db_path='metrics.db'):
        self.db_path = Path(db_path)
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    data BLOB,
                    sent INTEGER DEFAULT 0
                )
            ''')

    def store_metrics(self, metrics):
        compressed_data = zlib.compress(json.dumps(metrics).encode())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT INTO metrics (timestamp, data) VALUES (?, ?)',
                (metrics['timestamp'], compressed_data)
            )

def main():
    app = wx.App()
    agent = MonitorAgent()
    app.MainLoop()

if __name__ == '__main__':
    main()