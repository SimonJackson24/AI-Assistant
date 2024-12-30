import asyncio
import time
from typing import Dict, Any, List
import psutil
import numpy as np
from dataclasses import dataclass

@dataclass
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    tpu_utilization: List[float]  # One for each TPU
    temperature: float
    power_usage: float

class MetricsTracker:
    def __init__(self):
        self.metrics = {
            'model_load_time': [],
            'preview_latency': [],
            'memory_usage': [],
            'tpu_temperature': [],
            'generation_success_rate': []
        }
        self.alert_thresholds = {
            'temperature': 75.0,  # Celsius
            'memory': 90.0,  # Percent
            'latency': 2000,  # ms
        }
        self._subscribers = []
        
    async def track_metrics(self):
        """Track and analyze system performance"""
        while True:
            metrics = await self.collect_system_metrics()
            self.analyze_metrics(metrics)
            await self.alert_if_necessary(metrics)
            await asyncio.sleep(5)  # Check every 5 seconds
            
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        
        # Get TPU metrics (implement based on your TPU library)
        tpu_utils = self._get_tpu_utilization()
        temp = self._get_system_temperature()
        power = self._get_power_usage()
        
        return SystemMetrics(
            cpu_percent=cpu,
            memory_percent=memory,
            tpu_utilization=tpu_utils,
            temperature=temp,
            power_usage=power
        )
    
    def analyze_metrics(self, metrics: SystemMetrics):
        """Analyze collected metrics for patterns and potential issues"""
        self._update_moving_averages(metrics)
        self._detect_anomalies(metrics)
        self._update_performance_score(metrics)
        
    async def alert_if_necessary(self, metrics: SystemMetrics):
        """Check if any metrics exceed thresholds and alert if necessary"""
        alerts = []
        
        if metrics.temperature > self.alert_thresholds['temperature']:
            alerts.append(f"High temperature: {metrics.temperature}°C")
            
        if metrics.memory_percent > self.alert_thresholds['memory']:
            alerts.append(f"High memory usage: {metrics.memory_percent}%")
            
        if alerts:
            await self._notify_subscribers(alerts)
            
    def subscribe(self, callback):
        """Subscribe to metric alerts"""
        self._subscribers.append(callback)
        
    async def _notify_subscribers(self, alerts: List[str]):
        """Notify all subscribers of alerts"""
        for subscriber in self._subscribers:
            try:
                await subscriber(alerts)
            except Exception as e:
                print(f"Error notifying subscriber: {e}")
                
    def _get_tpu_utilization(self) -> List[float]:
        """Get TPU utilization percentages"""
        # Implement based on your TPU monitoring library
        return [0.0, 0.0]  # Placeholder
        
    def _get_system_temperature(self) -> float:
        """Get system temperature"""
        # Implement based on your hardware
        return 0.0  # Placeholder
        
    def _get_power_usage(self) -> float:
        """Get system power usage"""
        # Implement based on your hardware
        return 0.0  # Placeholder 