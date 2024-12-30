import pytest
import asyncio
from src.monitoring.metrics import MetricsTracker, SystemMetrics

@pytest.fixture
def metrics_tracker():
    return MetricsTracker()

class TestMetricsTracker:
    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, metrics_tracker):
        metrics = await metrics_tracker.collect_system_metrics()
        
        assert isinstance(metrics, SystemMetrics)
        assert 0 <= metrics.cpu_percent <= 100
        assert 0 <= metrics.memory_percent <= 100
        assert len(metrics.tpu_utilization) == 2  # Two TPUs
        assert metrics.temperature >= 0
        assert metrics.power_usage >= 0
        
    @pytest.mark.asyncio
    async def test_alert_thresholds(self, metrics_tracker):
        alerts = []
        
        async def alert_handler(alert_msgs):
            alerts.extend(alert_msgs)
            
        metrics_tracker.subscribe(alert_handler)
        
        # Simulate high temperature
        class HighTempMetrics(SystemMetrics):
            @property
            def temperature(self):
                return 80.0
                
        await metrics_tracker.alert_if_necessary(HighTempMetrics(
            cpu_percent=50,
            memory_percent=50,
            tpu_utilization=[50, 50],
            temperature=80.0,
            power_usage=10.0
        ))
        
        assert any("temperature" in alert.lower() for alert in alerts)
        
    def test_metrics_recording(self, metrics_tracker):
        metrics_tracker.metrics['model_load_time'].append(1.0)
        metrics_tracker.metrics['preview_latency'].append(0.5)
        
        assert len(metrics_tracker.metrics['model_load_time']) == 1
        assert len(metrics_tracker.metrics['preview_latency']) == 1 