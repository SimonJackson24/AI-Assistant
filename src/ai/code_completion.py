from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio
from pathlib import Path

from ..core.base_models import BaseModel, ModelConfig
from ..monitoring.metrics import MetricsTracker

@dataclass
class CompletionSuggestion:
    code: str
    confidence: float
    context: Dict[str, Any]
    source: str

class CodeCompletion:
    def __init__(self, model_config: Optional[ModelConfig] = None):
        self.model = BaseModel(model_config) if model_config else None
        self.metrics = MetricsTracker()
        self.context_window = 1000  # Characters of context to consider
        
    async def get_suggestions(self, 
                            code: str, 
                            cursor_position: int,
                            language: str,
                            max_suggestions: int = 5) -> List[CompletionSuggestion]:
        """Get code completion suggestions"""
        try:
            # Extract context around cursor
            context = self._extract_context(code, cursor_position)
            
            # Get model predictions
            start_time = self.metrics.time()
            predictions = await self._generate_completions(context, language)
            self.metrics.record('completion_time', self.metrics.time() - start_time)
            
            # Process and rank suggestions
            suggestions = await self._process_suggestions(predictions, context, language)
            
            return suggestions[:max_suggestions]
            
        except Exception as e:
            self.metrics.record_error('completion_error', str(e))
            return []
            
    def _extract_context(self, code: str, cursor_position: int) -> Dict[str, Any]:
        """Extract relevant context around cursor position"""
        start = max(0, cursor_position - self.context_window)
        end = min(len(code), cursor_position + self.context_window)
        
        return {
            'before': code[start:cursor_position],
            'after': code[cursor_position:end],
            'line': self._get_current_line(code, cursor_position),
            'indent': self._get_current_indent(code, cursor_position),
            'scope': self._detect_scope(code, cursor_position)
        }
        
    async def _generate_completions(self, 
                                  context: Dict[str, Any], 
                                  language: str) -> List[Dict[str, Any]]:
        """Generate completion candidates using the model"""
        if not self.model:
            return self._get_heuristic_completions(context, language)
            
        # Prepare model input
        model_input = self._prepare_model_input(context, language)
        
        # Get model predictions
        predictions = await self.model.infer(model_input)
        
        return predictions
        
    async def _process_suggestions(self,
                                 predictions: List[Dict[str, Any]],
                                 context: Dict[str, Any],
                                 language: str) -> List[CompletionSuggestion]:
        """Process and rank completion suggestions"""
        suggestions = []
        
        for pred in predictions:
            # Validate suggestion
            if not self._is_valid_completion(pred['code'], context, language):
                continue
                
            # Calculate confidence
            confidence = self._calculate_confidence(pred, context)
            
            suggestions.append(CompletionSuggestion(
                code=pred['code'],
                confidence=confidence,
                context=context,
                source='model' if self.model else 'heuristic'
            ))
            
        # Sort by confidence
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions
        
    def _get_heuristic_completions(self, 
                                 context: Dict[str, Any], 
                                 language: str) -> List[Dict[str, Any]]:
        """Generate completions using heuristic rules when model is unavailable"""
        completions = []
        
        # Common patterns based on context
        if context['line'].strip().endswith('if '):
            completions.append({'code': 'if condition:'})
        elif context['line'].strip().endswith('def '):
            completions.append({'code': 'def function_name(args):'})
        elif context['line'].strip().endswith('class '):
            completions.append({'code': 'class ClassName:'})
            
        return completions
        
    def _is_valid_completion(self, 
                           completion: str, 
                           context: Dict[str, Any], 
                           language: str) -> bool:
        """Validate if completion is syntactically correct"""
        try:
            combined_code = context['before'] + completion + context['after']
            # Basic syntax check - implement based on language
            return True
        except:
            return False
            
    def _calculate_confidence(self, 
                            prediction: Dict[str, Any], 
                            context: Dict[str, Any]) -> float:
        """Calculate confidence score for a completion"""
        # Implement confidence calculation based on:
        # - Model confidence if available
        # - Context match
        # - Complexity of completion
        # - Historical accuracy
        return 0.5  # Placeholder 