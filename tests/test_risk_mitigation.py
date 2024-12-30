import pytest
import asyncio
from src.risk.mitigation import RiskMitigation, SystemHealthMonitor, BackupService
from src.monitoring.metrics import SystemMetrics

@pytest.fixture
def risk_mitigation():
    return RiskMitigation()

@pytest.fixture
def health_monitor():
    return SystemHealthMonitor()

@pytest.fixture
def backup_service():
    return BackupService()

class TestRiskMitigation:
    @pytest.mark.asyncio
    async def test_thermal_emergency(self, risk_mitigation):
        # Simulate high temperature
        test_metrics = SystemMetrics(
            cpu_percent=50,
            memory_percent=50,
            tpu_utilization=[50, 50],
            temperature=85.0,  # Above critical threshold
            power_usage=10.0
        )
        
        handled = False
        async def mock_handle_thermal():
            nonlocal handled
            handled = True
            
        risk_mitigation._handle_thermal_emergency = mock_handle_thermal
        await risk_mitigation._check_and_mitigate_risks(test_metrics)
        
        assert handled
        
    @pytest.mark.asyncio
    async def test_memory_emergency(self, risk_mitigation):
        # Simulate high memory usage
        test_metrics = SystemMetrics(
            cpu_percent=50,
            memory_percent=96.0,  # Above critical threshold
            tpu_utilization=[50, 50],
            temperature=70.0,
            power_usage=10.0
        )
        
        handled = False
        async def mock_handle_memory():
            nonlocal handled
            handled = True
            
        risk_mitigation._handle_memory_emergency = mock_handle_memory
        await risk_mitigation._check_and_mitigate_risks(test_metrics)
        
        assert handled

class TestSystemHealthMonitor:
    @pytest.mark.asyncio
    async def test_health_status(self, health_monitor):
        assert health_monitor.is_healthy()
        metrics = await health_monitor.get_metrics()
        assert isinstance(metrics, SystemMetrics)

class TestBackupService:
    @pytest.mark.asyncio
    async def test_backup_creation(self, backup_service, tmp_path):
        backup_service.backup_path = tmp_path
        await backup_service.create_backup()
        
        # Check if backup was created
        backups = list(tmp_path.glob("*"))
        assert len(backups) == 1
        
    @pytest.mark.asyncio
    async def test_backup_rotation(self, backup_service, tmp_path):
        backup_service.backup_path = tmp_path
        backup_service.max_backups = 2
        
        # Create 3 backups
        for _ in range(3):
            await backup_service.create_backup()
            await asyncio.sleep(0.1)  # Ensure different timestamps
            
        # Check if only 2 most recent backups exist
        backups = list(tmp_path.glob("*"))
        assert len(backups) == 2 