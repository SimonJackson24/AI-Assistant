class Deployer:
    def __init__(self):
        self.container_manager = ContainerManager()
        self.health_checker = HealthChecker()
        self.backup_service = BackupService()
        
    async def deploy(self, config: DeploymentConfig):
        """Handle deployment with safety checks"""
        await self.backup_service.create_backup()
        if await self.health_checker.is_healthy():
            return await self.container_manager.deploy(config) 