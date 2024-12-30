import pytest
import numpy as np
from src.core.base_models import ModelConfig, BaseModel, EdgeTPUModel, CPUModel

@pytest.fixture
def model_config():
    return ModelConfig(
        model_path="models/test_model.tflite",
        device=0,
        cache_size=512,
        input_shape=(1, 512),
        quantized=True
    )

@pytest.fixture
def base_model():
    return BaseModel()

class TestBaseModel:
    def test_initial_metrics(self, base_model):
        metrics = base_model.get_performance_metrics()
        assert metrics['avg_time'] == 0
        assert metrics['total_inferences'] == 0
        
    def test_metrics_tracking(self, base_model):
        # Simulate some inferences
        base_model.inference_times = [0.1, 0.2, 0.3]
        base_model.total_inferences = 3
        
        metrics = base_model.get_performance_metrics()
        assert metrics['avg_time'] == 0.2
        assert metrics['total_inferences'] == 3

class TestEdgeTPUModel:
    @pytest.mark.asyncio
    async def test_model_caching(self, model_config):
        model = EdgeTPUModel(
            model_path=model_config.model_path,
            device=model_config.device,
            cache_size=2  # Small cache for testing
        )
        
        # Test input data
        input_data = np.zeros((1, 512), dtype=np.float32)
        
        # First inference should cache
        result1 = await model.infer(input_data)
        assert hash(input_data.tobytes()) in model.cache
        
        # Second inference should use cache
        result2 = await model.infer(input_data)
        assert np.array_equal(result1, result2)
        
        # Test cache size limit
        input_data2 = np.ones((1, 512), dtype=np.float32)
        input_data3 = np.full((1, 512), 2, dtype=np.float32)
        
        await model.infer(input_data2)
        await model.infer(input_data3)
        
        # First input should be evicted from cache
        assert hash(input_data.tobytes()) not in model.cache 