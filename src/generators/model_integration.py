from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import asyncio
from pathlib import Path

from ..core.base_models import BaseModel, EdgeTPUModel, CPUModel, ModelConfig
from ..monitoring.metrics import MetricsTracker
from .code_analyzer import CodeAnalyzer, CodeMetrics

@dataclass
class ModelSuggestion:
    code_snippet: str
    confidence: float
    explanation: str
    metadata: Dict[str, Any]

@dataclass
class GenerationContext:
    language: str
    framework: str
    component_type: str
    existing_code: Optional[str] = None
    requirements: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None

class ModelIntegration:
    def __init__(self, model_config: Optional[ModelConfig] = None):
        self.metrics = MetricsTracker()
        self.analyzer = CodeAnalyzer()
        
        # Initialize models
        if model_config:
            self.model = EdgeTPUModel(model_config)
        else:
            self.model = CPUModel()
            
        # Load generation templates and patterns
        self.patterns = self._load_patterns()
        
    async def generate_code(self, context: GenerationContext) -> List[ModelSuggestion]:
        """Generate code suggestions using the ML model"""
        try:
            # Prepare input for model
            model_input = await self._prepare_model_input(context)
            
            # Get model predictions
            start_time = self.metrics.time()
            predictions = await self.model.infer(model_input)
            self.metrics.record('model_inference_time', self.metrics.time() - start_time)
            
            # Process predictions into suggestions
            suggestions = await self._process_predictions(predictions, context)
            
            # Validate and rank suggestions
            return await self._rank_suggestions(suggestions, context)
            
        except Exception as e:
            self.metrics.record_error('model_generation_error', str(e))
            return []
            
    async def enhance_code(self, code: str, context: GenerationContext) -> ModelSuggestion:
        """Enhance existing code using the model"""
        try:
            # Analyze existing code
            analysis = await self.analyzer.analyze(code, context.language)
            
            # Generate improvements
            improvements = await self._generate_improvements(code, analysis, context)
            
            # Apply improvements
            enhanced_code = await self._apply_improvements(code, improvements)
            
            return ModelSuggestion(
                code_snippet=enhanced_code,
                confidence=improvements['confidence'],
                explanation=improvements['explanation'],
                metadata=improvements['metadata']
            )
            
        except Exception as e:
            self.metrics.record_error('code_enhancement_error', str(e))
            return ModelSuggestion(
                code_snippet=code,
                confidence=0.0,
                explanation=f"Error enhancing code: {str(e)}",
                metadata={}
            )
            
    async def _prepare_model_input(self, context: GenerationContext) -> Dict[str, Any]:
        """Prepare input for the model"""
        return {
            'language': context.language,
            'framework': context.framework,
            'component_type': context.component_type,
            'existing_code': context.existing_code or '',
            'requirements': context.requirements or {},
            'constraints': context.constraints or {},
            'patterns': self.patterns.get(context.language, {})
        }
        
    async def _process_predictions(self, 
                                 predictions: Any, 
                                 context: GenerationContext) -> List[ModelSuggestion]:
        """Process model predictions into code suggestions"""
        suggestions = []
        
        for pred in predictions:
            # Extract code and metadata from prediction
            code = self._extract_code(pred)
            metadata = self._extract_metadata(pred)
            
            # Calculate confidence
            confidence = self._calculate_confidence(pred, context)
            
            # Generate explanation
            explanation = await self._generate_explanation(code, metadata, context)
            
            suggestions.append(ModelSuggestion(
                code_snippet=code,
                confidence=confidence,
                explanation=explanation,
                metadata=metadata
            ))
            
        return suggestions
        
    async def _rank_suggestions(self, 
                              suggestions: List[ModelSuggestion], 
                              context: GenerationContext) -> List[ModelSuggestion]:
        """Rank and filter code suggestions"""
        # Score suggestions based on multiple criteria
        scored_suggestions = []
        for suggestion in suggestions:
            score = await self._calculate_score(suggestion, context)
            scored_suggestions.append((score, suggestion))
            
        # Sort by score and return top suggestions
        scored_suggestions.sort(reverse=True, key=lambda x: x[0])
        return [s[1] for s in scored_suggestions[:5]]
        
    def _load_patterns(self) -> Dict[str, Any]:
        """Load code generation patterns and templates"""
        patterns_path = Path(__file__).parent / 'patterns'
        patterns = {}
        
        if patterns_path.exists():
            for pattern_file in patterns_path.glob('*.json'):
                language = pattern_file.stem
                with open(pattern_file) as f:
                    patterns[language] = json.load(f)
                    
        return patterns
        
    async def _generate_improvements(self, 
                                   code: str, 
                                   analysis: CodeMetrics, 
                                   context: GenerationContext) -> Dict[str, Any]:
        """Generate code improvements based on analysis"""
        # Prepare improvement prompt
        prompt = self._create_improvement_prompt(code, analysis, context)
        
        # Get model suggestions
        improvements = await self.model.infer(prompt)
        
        return {
            'changes': improvements.get('changes', []),
            'confidence': improvements.get('confidence', 0.0),
            'explanation': improvements.get('explanation', ''),
            'metadata': improvements.get('metadata', {})
        }
        
    async def _apply_improvements(self, code: str, improvements: Dict[str, Any]) -> str:
        """Apply suggested improvements to code"""
        enhanced_code = code
        
        for change in improvements['changes']:
            if change['type'] == 'replace':
                enhanced_code = enhanced_code.replace(
                    change['old'],
                    change['new']
                )
            elif change['type'] == 'insert':
                position = change['position']
                enhanced_code = (
                    enhanced_code[:position] + 
                    change['code'] + 
                    enhanced_code[position:]
                )
                
        return enhanced_code 