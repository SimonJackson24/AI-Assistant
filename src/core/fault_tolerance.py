class FaultTolerance:
    def __init__(self):
        self.health_monitor = SystemHealthMonitor()
        self.backup_service = BackupService()
        
    async def watch_system_health(self):
        while True:
            metrics = await self.health_monitor.get_metrics()
            if metrics.temperature > 75:  # Celsius
                await self.throttle_processing() 