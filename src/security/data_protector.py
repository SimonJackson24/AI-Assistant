class DataProtector:
    def __init__(self):
        self.encryption_service = EncryptionService()
        self.access_manager = AccessManager()
        
    async def secure_data(self, data: Any):
        """Ensure data security"""
        if self.access_manager.requires_encryption(data):
            return await self.encryption_service.encrypt(data) 