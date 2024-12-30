from typing import Optional, Dict, Any
import asyncio
from aiohttp import web
import logging
import numpy as np
from src.core.base_models import BaseModel
from src.core.resource_manager import ResourceManager, ResourceLimits

logger = logging.getLogger(__name__)

class ModelService:
    def __init__(self, 
                 model: BaseModel,
                 host: str = "localhost",
                 port: int = 8000,
                 resource_limits: Optional[ResourceLimits] = None):
        self.model = model
        self.host = host
        self.port = port
        self.resource_manager = ResourceManager(resource_limits)
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        self.app.router.add_get("/health", self.health_check)
        self.app.router.add_post("/infer", self.inference)
        self.app.router.add_get("/metrics", self.get_metrics)
        
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint with resource metrics"""
        metrics = await self.model.get_performance_metrics()
        resources = await self.resource_manager.check_resources()
        
        return web.json_response({
            "status": "healthy" if resources["is_healthy"] else "degraded",
            "load": metrics.get("avg_time", 0) * self.model.total_inferences,
            "resources": resources
        })
        
    async def inference(self, request: web.Request) -> web.Response:
        """Inference endpoint with resource management"""
        try:
            data = await request.json()
            input_data = np.array(data["input"])
            
            # Check resource availability
            batch_size = input_data.shape[0] if len(input_data.shape) > 1 else 1
            if not await self.resource_manager.can_accept_batch(batch_size):
                return web.json_response(
                    {"error": "System overloaded, try again later"},
                    status=503
                )
                
            # Get connection from pool
            conn = await self.resource_manager.acquire_connection()
            try:
                # Use thread pool for CPU-bound operations
                thread_pool = self.resource_manager.get_thread_pool()
                result = await asyncio.get_event_loop().run_in_executor(
                    thread_pool,
                    self.model.infer,
                    input_data
                )
                return web.json_response({"result": result.tolist()})
            finally:
                await self.resource_manager.release_connection(conn)
                
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500
            )
            
    async def get_metrics(self, request: web.Request) -> web.Response:
        """Get all metrics including resource usage"""
        metrics = await self.model.get_performance_metrics()
        resources = await self.resource_manager.check_resources()
        
        return web.json_response({
            "model_metrics": metrics,
            "resource_metrics": resources
        })
            
    async def start(self):
        """Start the service with resource management"""
        await self.resource_manager.start()
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"Model service started at http://{self.host}:{self.port}") 