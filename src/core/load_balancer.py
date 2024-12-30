from typing import List, Dict, Optional, Any
import asyncio
from dataclasses import dataclass
import logging
from datetime import datetime
import aiohttp
import json
from src.monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

@dataclass
class ServiceNode:
    """Represents a service instance in the cluster"""
    id: str
    host: str
    port: int
    healthy: bool = True
    last_health_check: datetime = datetime.now()
    current_load: float = 0.0
    max_load: float = 100.0

@dataclass
class LoadBalancerConfig:
    """Load balancer configuration"""
    check_interval: int = 30  # Health check interval in seconds
    max_retries: int = 3
    timeout: float = 5.0
    algorithm: str = "round_robin"  # or "least_connections" or "weighted_round_robin"
    sticky_sessions: bool = False

class LoadBalancer:
    def __init__(self, config: Optional[LoadBalancerConfig] = None):
        self.config = config or LoadBalancerConfig()
        self.nodes: List[ServiceNode] = []
        self.metrics = MetricsCollector()
        self._current_index = 0
        self._health_check_task = None
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Start the load balancer and health checks"""
        self._session = aiohttp.ClientSession()
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Load balancer started")
        
    async def stop(self):
        """Stop the load balancer and cleanup"""
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._session:
            await self._session.close()
        logger.info("Load balancer stopped")
        
    async def add_node(self, node: ServiceNode):
        """Add a new service node"""
        self.nodes.append(node)
        await self.metrics.increment("lb.nodes.total")
        logger.info(f"Added node {node.id} at {node.host}:{node.port}")
        
    async def remove_node(self, node_id: str):
        """Remove a service node"""
        self.nodes = [n for n in self.nodes if n.id != node_id]
        await self.metrics.decrement("lb.nodes.total")
        logger.info(f"Removed node {node_id}")
        
    async def get_next_node(self) -> Optional[ServiceNode]:
        """Get the next available node based on the selected algorithm"""
        if not self.nodes:
            return None
            
        healthy_nodes = [n for n in self.nodes if n.healthy]
        if not healthy_nodes:
            logger.error("No healthy nodes available")
            return None
            
        if self.config.algorithm == "least_connections":
            return min(healthy_nodes, key=lambda n: n.current_load)
        elif self.config.algorithm == "weighted_round_robin":
            # Implement weighted selection based on node load
            weights = [1 - (n.current_load / n.max_load) for n in healthy_nodes]
            total_weight = sum(weights)
            if total_weight == 0:
                return healthy_nodes[0]
            
            r = asyncio.random.random() * total_weight
            for node, weight in zip(healthy_nodes, weights):
                r -= weight
                if r <= 0:
                    return node
            return healthy_nodes[-1]
        else:  # round_robin
            self._current_index = (self._current_index + 1) % len(healthy_nodes)
            return healthy_nodes[self._current_index]
            
    async def _health_check_loop(self):
        """Continuous health check loop"""
        while True:
            try:
                await self._check_all_nodes()
                await asyncio.sleep(self.config.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(1)
                
    async def _check_all_nodes(self):
        """Check health of all nodes"""
        for node in self.nodes:
            try:
                async with self._session.get(
                    f"http://{node.host}:{node.port}/health",
                    timeout=self.config.timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        node.healthy = True
                        node.current_load = data.get("load", 0.0)
                        await self.metrics.increment("lb.health_checks.success")
                    else:
                        node.healthy = False
                        await self.metrics.increment("lb.health_checks.failed")
            except Exception as e:
                logger.warning(f"Health check failed for node {node.id}: {e}")
                node.healthy = False
                await self.metrics.increment("lb.health_checks.failed")
            
            node.last_health_check = datetime.now()
            
    async def get_status(self) -> Dict[str, Any]:
        """Get current load balancer status"""
        return {
            "total_nodes": len(self.nodes),
            "healthy_nodes": len([n for n in self.nodes if n.healthy]),
            "algorithm": self.config.algorithm,
            "metrics": await self.metrics.get_metrics("lb.*")
        } 