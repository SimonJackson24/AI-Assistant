class ThermalManager:
    def __init__(self):
        self.temp_monitor = TemperatureMonitor()
        self.fan_controller = FanController()
        
    async def manage_temperature(self):
        """Active thermal management"""
        temp = await self.temp_monitor.get_temperature()
        if temp > 70:  # Celsius
            await self.fan_controller.increase_speed()
            await self.reduce_workload() 