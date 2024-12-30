from dataclasses import dataclass
from typing import Any, Optional, Dict, Union
import numpy as np
import time
from collections import OrderedDict
import redis
from functools import lru_cache
import logging
from src.monitoring.metrics import MetricsCollector
from src.core.load_balancer import LoadBalancer, LoadBalancerConfig, ServiceNode

logger = logging.getLogger(__name__)

@dataclass
class CacheConfig:
    enabled: bool = True
    local_size: int = 1000  # Number of items in local LRU cache
    redis_url: Optional[str] = None  # Redis connection URL
    ttl: int = 3600  # Time to live for cached items (1 hour)
    compression: bool = True

@dataclass
class ModelConfig:
    model_path: str
    device: int
    cache_config: Optional[CacheConfig] = None
    input_shape: tuple = (1, 512)  # Default shape
    quantized: bool = True

class CacheManager:
    """Manages both local and distributed caching"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.metrics = MetricsCollector()
        self._local_cache = OrderedDict()
        self._redis_client = None
        
        if config.redis_url:
            try:
                self._redis_client = redis.from_url(config.redis_url)
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
    
    async def get(self, key: str) -> Optional[np.ndarray]:
        """Get item from cache, trying local first then Redis"""
        # Check local cache
        if key in self._local_cache:
            self.metrics.increment("cache.local.hits")
            return self._local_cache[key]
            
        # Check Redis if available
        if self._redis_client:
            try:
                cached_data = self._redis_client.get(key)
                if cached_data:
                    self.metrics.increment("cache.redis.hits")
                    result = np.frombuffer(cached_data, dtype=np.float32)
                    self._update_local_cache(key, result)
                    return result
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                
        self.metrics.increment("cache.misses")
        return None
        
    async def set(self, key: str, value: np.ndarray):
        """Store item in both local and Redis cache"""
        self._update_local_cache(key, value)
        
        if self._redis_client:
            try:
                self._redis_client.setex(
                    key,
                    self.config.ttl,
                    value.tobytes(),
                )
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                
    def _update_local_cache(self, key: str, value: np.ndarray):
        """Update local LRU cache"""
        self._local_cache[key] = value
        if len(self._local_cache) > self.config.local_size:
            self._local_cache.popitem(last=False)
            
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "local_cache_size": len(self._local_cache),
            "local_cache_hits": await self.metrics.get_count("cache.local.hits"),
            "redis_cache_hits": await self.metrics.get_count("cache.redis.hits"),
            "cache_misses": await self.metrics.get_count("cache.misses"),
        }

class BaseModel:
    def __init__(self):
        self.inference_times: list = []
        self.total_inferences: int = 0
        self.metrics = MetricsCollector()
        
    async def get_performance_metrics(self) -> Dict[str, float]:
        if not self.inference_times:
            return {'avg_time': 0, 'total_inferences': 0}
            
        metrics = {
            'avg_time': sum(self.inference_times) / len(self.inference_times),
            'total_inferences': self.total_inferences,
            'cache_stats': await self.cache.get_stats() if hasattr(self, 'cache') else {}
        }
        
        await self.metrics.record_metrics("model_performance", metrics)
        return metrics

class EdgeTPUModel(BaseModel):
    def __init__(self, model_path: str, device: int, cache_config: Optional[CacheConfig] = None):
        super().__init__()
        self.config = ModelConfig(model_path, device, cache_config or CacheConfig())
        self.model = None
        self.cache = CacheManager(self.config.cache_config)
        self._initialize_model()
    
    def _initialize_model(self):
        try:
            from tflite_runtime.interpreter import Interpreter
            from tflite_runtime.interpreter import load_delegate
            
            edge_tpu_delegate = load_delegate('libedgetpu.so.1')
            self.model = Interpreter(
                model_path=self.config.model_path,
                experimental_delegates=[edge_tpu_delegate],
                num_threads=4
            )
            self.model.allocate_tensors()
            self._input_details = self.model.get_input_details()
            self._output_details = self.model.get_output_details()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize EdgeTPU model: {e}")
            
    async def infer(self, input_data: np.ndarray) -> np.ndarray:
        """Run inference on the model with enhanced caching"""
        start_time = time.time()
        try:
            # Generate cache key
            cache_key = hash(input_data.tobytes())
            
            # Check cache
            cached_result = await self.cache.get(str(cache_key))
            if cached_result is not None:
                return cached_result
            
            # Run inference
            self.model.set_tensor(self._input_details[0]['index'], input_data)
            self.model.invoke()
            result = self.model.get_tensor(self._output_details[0]['index'])
            
            # Update cache
            await self.cache.set(str(cache_key), result)
            
            return result
        finally:
            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)
            self.total_inferences += 1
            await self.metrics.record_metric("inference_time", inference_time)

class CPUModel:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        try:
            from tflite_runtime.interpreter import Interpreter
            self.model = Interpreter(model_path=self.model_path, num_threads=4)
            self.model.allocate_tensors()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize CPU model: {e}") 

# Initialize load balancer
config = LoadBalancerConfig(
    check_interval=30,
    algorithm="least_connections",
    sticky_sessions=True
)
balancer = LoadBalancer(config)

# Add service nodes
await balancer.add_node(ServiceNode(
    id="node1",
    host="localhost",
    port=8000
))
await balancer.add_node(ServiceNode(
    id="node2",
    host="localhost",
    port=8001
))

# Start load balancer
await balancer.start()

# Get next available node
node = await balancer.get_next_node() 