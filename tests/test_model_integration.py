import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any

from src.generators.model_integration import (
    ModelIntegration, 
    ModelSuggestion, 
    GenerationContext
)
from src.core.base_models import ModelConfig

@pytest.fixture
def model_integration():
    config = ModelConfig(
        model_path="models/test_model.tflite",
        device=0,
        cache_size=100,
        input_shape=(1, 512),
        quantized=True
    )
    return ModelIntegration(config)

@pytest.fixture
def test_context():
    return GenerationContext(
        language="python",
        framework="fastapi",
        component_type="class",
        requirements={
            "async": True,
            "database": True,
            "validation": True
        }
    )

class TestModelIntegration:
    @pytest.mark.asyncio
    async def test_code_generation(self, model_integration, test_context):
        suggestions = await model_integration.generate_code(test_context)
        
        assert len(suggestions) > 0
        assert all(isinstance(s, ModelSuggestion) for s in suggestions)
        
        top_suggestion = suggestions[0]
        assert top_suggestion.code_snippet
        assert 0 <= top_suggestion.confidence <= 1.0
        assert top_suggestion.explanation
        assert isinstance(top_suggestion.metadata, dict)
        
    @pytest.mark.asyncio
    async def test_code_enhancement(self, model_integration, test_context):
        test_code = """
        class UserService:
            def get_user(self, user_id: int):
                return db.query(User).filter_by(id=user_id).first()
        """
        
        enhanced = await model_integration.enhance_code(test_code, test_context)
        
        assert isinstance(enhanced, ModelSuggestion)
        assert "async" in enhanced.code_snippet
        assert "typing" in enhanced.code_snippet
        assert enhanced.confidence > 0
        
    @pytest.mark.asyncio
    async def test_pattern_loading(self, model_integration):
        patterns = model_integration.patterns
        
        assert "python" in patterns
        assert "class" in patterns["python"]
        assert "function" in patterns["python"]
        assert "common_imports" in patterns["python"]
        
    @pytest.mark.asyncio
    async def test_error_handling(self, model_integration, test_context):
        # Test with invalid context
        invalid_context = GenerationContext(
            language="invalid",
            framework="invalid",
            component_type="invalid"
        )
        
        suggestions = await model_integration.generate_code(invalid_context)
        assert len(suggestions) == 0
        
        # Test with invalid code
        result = await model_integration.enhance_code("invalid python code }", test_context)
        assert result.confidence == 0.0
        assert "Error" in result.explanation
        
    @pytest.mark.asyncio
    async def test_suggestion_ranking(self, model_integration, test_context):
        suggestions = await model_integration.generate_code(test_context)
        
        if len(suggestions) > 1:
            assert suggestions[0].confidence >= suggestions[1].confidence
            
    @pytest.mark.asyncio
    async def test_model_metrics(self, model_integration, test_context):
        await model_integration.generate_code(test_context)
        
        metrics = model_integration.metrics.get_metrics()
        assert 'model_inference_time' in metrics
        assert len(metrics['model_inference_time']) > 0 