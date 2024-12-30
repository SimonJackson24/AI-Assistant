from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
from dataclasses import dataclass
from datetime import datetime

from .template_engine import TemplateEngine
from .template_validator import TemplateValidator
from .component_generator import ComponentGenerator, ComponentSpec
from .code_validator import CodeValidator
from .style_enforcer import StyleEnforcer
from .code_analyzer import CodeAnalyzer
from .component_registry import ComponentRegistry, ComponentMetadata
from .model_integration import ModelIntegration, GenerationContext, ModelSuggestion

@dataclass
class GenerationResult:
    success: bool
    component_path: Optional[Path]
    validation_results: Dict[str, Any]
    analysis_results: Dict[str, Any]
    model_suggestions: List[ModelSuggestion]
    errors: List[str]

class GenerationPipeline:
    def __init__(self):
        self.template_engine = TemplateEngine()
        self.template_validator = TemplateValidator()
        self.component_generator = ComponentGenerator()
        self.code_validator = CodeValidator()
        self.style_enforcer = StyleEnforcer()
        self.code_analyzer = CodeAnalyzer()
        self.registry = ComponentRegistry()
        self.model_integration = ModelIntegration()
        
    async def generate(self, spec: ComponentSpec) -> GenerationResult:
        """Run the complete generation pipeline"""
        errors = []
        model_suggestions = []
        
        try:
            # 1. Validate template
            template_validation = await self.template_validator.validate_template(
                f"{spec.type}.{spec.language}.j2",
                spec.type
            )
            
            if not template_validation.is_valid:
                return GenerationResult(
                    success=False,
                    component_path=None,
                    validation_results={"template": template_validation},
                    analysis_results={},
                    model_suggestions=[],
                    errors=template_validation.syntax_errors
                )
                
            # 2. Get model suggestions
            context = GenerationContext(
                language=spec.language,
                framework=spec.framework,
                component_type=spec.type,
                requirements=spec.config.get('requirements'),
                constraints=spec.config.get('constraints')
            )
            
            model_suggestions = await self.model_integration.generate_code(context)
            
            # Use top suggestion if available
            if model_suggestions:
                spec.props.update(model_suggestions[0].metadata.get('props', {}))
 
            # 2. Generate component
            component_path = await self.component_generator.generate_component(spec)
            
            # 3. Validate generated code
            with open(component_path) as f:
                code = f.read()
                
            code_validation = await self.code_validator.validate(code, spec.language)
            
            # 4. Enforce style
            if code_validation.is_valid:
                code = await self.style_enforcer.enforce_style(code, spec.language)
                with open(component_path, 'w') as f:
                    f.write(code)
                    
            # 5. Analyze code
            analysis = await self.code_analyzer.analyze(code, spec.language)
            
            # 6. Register component
            await self.registry.register_component(
                ComponentMetadata(
                    name=spec.name,
                    type=spec.type,
                    language=spec.language,
                    framework=spec.framework,
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat(),
                    dependencies=analysis.metrics.dependencies,
                    tags=spec.config.get('tags', [])
                )
            )
            
            return GenerationResult(
                success=True,
                component_path=component_path,
                validation_results={
                    "template": template_validation,
                    "code": code_validation
                },
                analysis_results=analysis,
                model_suggestions=model_suggestions,
                errors=[]
            )
            
        except Exception as e:
            errors.append(str(e))
            return GenerationResult(
                success=False,
                component_path=None,
                validation_results={},
                analysis_results={},
                model_suggestions=[],
                errors=errors
            ) 