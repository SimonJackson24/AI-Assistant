from typing import Dict, Optional, Any, List
import asyncio
import psutil
import logging
from dataclasses import dataclass
import time
from concurrent.futures import ThreadPoolExecutor
import threading
from src.monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

@dataclass
class ResourceLimits:
    max_memory_percent: float = 80.0
    max_cpu_percent: float = 90.0
    max_connections: int = 100
    max_threads: int = 32
    connection_timeout: float = 30.0
    max_batch_size: int = 64

class ConnectionPool:
    """Manages a pool of reusable connections"""
    
    def __init__(self, max_size: int, timeout: float):
        self.max_size = max_size
        self.timeout = timeout
        self._available = asyncio.Queue()
        self._in_use = set()
        self._lock = asyncio.Lock()
        
    async def acquire(self):
        """Acquire a connection from the pool"""
        try:
            # Try to get an available connection
            async with asyncio.timeout(self.timeout):
                while True:
                    try:
                        conn = await self._available.get()
                        if self._validate_connection(conn):
                            self._in_use.add(conn)
                            return conn
                    except asyncio.QueueEmpty:
                        if len(self._in_use) < self.max_size:
                            # Create new connection if under limit
                            conn = await self._create_connection()
                            self._in_use.add(conn)
                            return conn
                        # Wait for available connection
                        await asyncio.sleep(0.1)
        except TimeoutError:
            raise ConnectionError("Connection pool timeout")
            
    async def release(self, conn):
        """Release a connection back to the pool"""
        self._in_use.remove(conn)
        if self._validate_connection(conn):
            await self._available.put(conn)
        else:
            await self._close_connection(conn)
            
    def _validate_connection(self, conn) -> bool:
        """Validate if connection is still usable"""
        return True  # Implement actual validation logic
        
    async def _create_connection(self):
        """Create a new connection"""
        return object()  # Implement actual connection creation
        
    async def _close_connection(self, conn):
        """Close a connection"""
        pass  # Implement actual connection closing

class ResourceManager:
    """Manages system resources and enforces limits"""
    
    def __init__(self, limits: Optional[ResourceLimits] = None):
        self.limits = limits or ResourceLimits()
        self.metrics = MetricsCollector()
        self._connection_pool = ConnectionPool(
            self.limits.max_connections,
            self.limits.connection_timeout
        )
        self._thread_pool = ThreadPoolExecutor(max_workers=self.limits.max_threads)
        self._monitor_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start resource monitoring"""
        self._monitor_task = asyncio.create_task(self._monitor_resources())
        logger.info("Resource manager started")
        
    async def stop(self):
        """Stop resource monitoring and cleanup"""
        if self._monitor_task:
            self._monitor_task.cancel()
        self._thread_pool.shutdown(wait=True)
        logger.info("Resource manager stopped")
        
    async def check_resources(self) -> Dict[str, Any]:
        """Check current resource usage"""
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "available_connections": self._connection_pool._available.qsize(),
            "active_connections": len(self._connection_pool._in_use),
            "active_threads": len(threading.enumerate()),
            "is_healthy": self._check_health(cpu_percent, memory.percent)
        }
        
    def _check_health(self, cpu_percent: float, memory_percent: float) -> bool:
        """Check if resource usage is within limits"""
        return (
            cpu_percent < self.limits.max_cpu_percent and
            memory_percent < self.limits.max_memory_percent
        )
        
    async def acquire_connection(self):
        """Acquire a connection from the pool"""
        return await self._connection_pool.acquire()
        
    async def release_connection(self, conn):
        """Release a connection back to the pool"""
        await self._connection_pool.release(conn)
        
    def get_thread_pool(self) -> ThreadPoolExecutor:
        """Get thread pool for CPU-bound tasks"""
        return self._thread_pool
        
    async def _monitor_resources(self):
        """Continuous resource monitoring loop"""
        while True:
            try:
                metrics = await self.check_resources()
                
                # Record metrics
                await self.metrics.record_metrics("resource_usage", {
                    "cpu_percent": metrics["cpu_percent"],
                    "memory_percent": metrics["memory_percent"],
                    "active_connections": metrics["active_connections"],
                    "active_threads": metrics["active_threads"]
                })
                
                # Check for resource warnings
                if metrics["cpu_percent"] > self.limits.max_cpu_percent * 0.8:
                    logger.warning(f"High CPU usage: {metrics['cpu_percent']}%")
                if metrics["memory_percent"] > self.limits.max_memory_percent * 0.8:
                    logger.warning(f"High memory usage: {metrics['memory_percent']}%")
                    
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(1)
                
    async def can_accept_batch(self, batch_size: int) -> bool:
        """Check if system can handle the given batch size"""
        if batch_size > self.limits.max_batch_size:
            return False
            
        metrics = await self.check_resources()
        return (
            metrics["is_healthy"] and
            metrics["cpu_percent"] < self.limits.max_cpu_percent * 0.9 and
            metrics["memory_percent"] < self.limits.max_memory_percent * 0.9
        ) 