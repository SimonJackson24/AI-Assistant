import pytest
import asyncio
from pathlib import Path

from src.generators.pipeline import GenerationPipeline
from src.generators.component_generator import ComponentSpec

@pytest.mark.integration
class TestModelIntegrationE2E:
    @pytest.mark.asyncio
    async def test_full_generation_pipeline(self, tmp_path):
        pipeline = GenerationPipeline()
        
        spec = ComponentSpec(
            name="UserService",
            type="class",
            language="python",
            framework="fastapi",
            props={},
            style={},
            config={
                "requirements": {
                    "async": True,
                    "database": True
                }
            }
        )
        
        result = await pipeline.generate(spec)
        
        assert result.success
        assert result.component_path.exists()
        assert len(result.model_suggestions) > 0
        assert result.validation_results["code"].is_valid
        
    @pytest.mark.asyncio
    async def test_model_enhancement_pipeline(self, tmp_path):
        pipeline = GenerationPipeline()
        
        # First generate basic component
        basic_spec = ComponentSpec(
            name="DataService",
            type="class",
            language="python",
            framework="flask",
            props={},
            style={},
            config={}
        )
        
        basic_result = await pipeline.generate(basic_spec)
        assert basic_result.success
        
        # Now enhance it with async capabilities
        enhanced_spec = ComponentSpec(
            name="DataService",
            type="class",
            language="python",
            framework="asyncio",
            props={},
            style={},
            config={
                "requirements": {"async": True}
            }
        )
        
        enhanced_result = await pipeline.generate(enhanced_spec)
        assert enhanced_result.success
        assert "async" in enhanced_result.model_suggestions[0].code_snippet 