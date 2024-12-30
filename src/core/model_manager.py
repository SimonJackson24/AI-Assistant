import asyncio
from typing import Dict, Optional
import time
from .base_models import EdgeTPUModel, CPUModel

class ModelManager:
    def __init__(self):
        self.code_model = EdgeTPUModel(
            model_path="models/codellama-7b-quantized.tflite",
            device=0,
            cache_size=512  # MB
        )
        
        self.ui_model = EdgeTPUModel(
            model_path="models/stable-llm-2b.tflite",
            device=1,
            cache_size=256
        )
        
        self.schema_model = CPUModel(
            model_path="models/schema-designer-1.5b.tflite"
        )
        
        self.model_usage_times: Dict[str, float] = {}
        self.loaded_shards: Dict[str, Any] = {}
        
    async def load_model_shard(self, model_type: str):
        """Dynamic model loading to optimize memory usage"""
        if model_type not in self.loaded_shards:
            try:
                model = self._get_model_by_type(model_type)
                shard = await self._load_shard(model)
                self.loaded_shards[model_type] = shard
                self.model_usage_times[model_type] = time.time()
            except Exception as e:
                raise RuntimeError(f"Failed to load model shard: {e}")
        return self.loaded_shards[model_type]
    
    def unload_inactive_models(self, threshold_minutes: int = 30):
        """Unload models that haven't been used recently"""
        current_time = time.time()
        for model_type, last_used in self.model_usage_times.items():
            if (current_time - last_used) / 60 > threshold_minutes:
                if model_type in self.loaded_shards:
                    del self.loaded_shards[model_type]
                    
    async def _load_shard(self, model: Any):
        """Helper method to load model shard"""
        # Implement model-specific shard loading logic
        pass
    
    def _get_model_by_type(self, model_type: str):
        """Get model instance by type"""
        models = {
            'code': self.code_model,
            'ui': self.ui_model,
            'schema': self.schema_model
        }
        return models.get(model_type) 