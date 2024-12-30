from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import ast
import asyncio
from pathlib import Path

from ..core.base_models import BaseModel, ModelConfig
from ..monitoring.metrics import MetricsTracker
from .code_analyzer import CodeAnalyzer, CodeMetrics

@dataclass
class BugReport:
    severity: str  # 'critical', 'high', 'medium', 'low'
    bug_type: str
    description: str
    location: Dict[str, Any]  # file, line, column
    suggested_fix: Optional[str]
    confidence: float
    context: Dict[str, Any]

class BugDetector:
    def __init__(self, model_config: Optional[ModelConfig] = None):
        self.model = BaseModel(model_config) if model_config else None
        self.analyzer = CodeAnalyzer()
        self.metrics = MetricsTracker()
        
    async def scan_code(self, 
                       code: str, 
                       language: str,
                       context: Optional[Dict[str, Any]] = None) -> List[BugReport]:
        """Scan code for potential bugs"""
        try:
            bugs = []
            
            # Static analysis
            static_bugs = await self._static_analysis(code, language)
            bugs.extend(static_bugs)
            
            # Pattern-based detection
            pattern_bugs = await self._pattern_analysis(code, language)
            bugs.extend(pattern_bugs)
            
            # Model-based detection
            if self.model:
                model_bugs = await self._model_analysis(code, language, context)
                bugs.extend(model_bugs)
                
            # Deduplicate and rank bugs
            return self._prioritize_bugs(bugs)
            
        except Exception as e:
            self.metrics.record_error('bug_detection_error', str(e))
            return []
            
    async def _static_analysis(self, code: str, language: str) -> List[BugReport]:
        """Perform static code analysis"""
        bugs = []
        
        if language == 'python':
            try:
                tree = ast.parse(code)
                
                # Check for common issues
                bugs.extend(self._check_exception_handling(tree))
                bugs.extend(self._check_resource_management(tree))
                bugs.extend(self._check_null_references(tree))
                bugs.extend(self._check_type_safety(tree))
                
            except SyntaxError as e:
                bugs.append(BugReport(
                    severity='critical',
                    bug_type='syntax_error',
                    description=str(e),
                    location={'line': e.lineno, 'column': e.offset},
                    suggested_fix=None,
                    confidence=1.0,
                    context={'code': code}
                ))
                
        return bugs
        
    async def _pattern_analysis(self, code: str, language: str) -> List[BugReport]:
        """Detect bugs using known patterns"""
        patterns = self._load_bug_patterns(language)
        bugs = []
        
        for pattern in patterns:
            matches = pattern['detector'](code)
            for match in matches:
                bugs.append(BugReport(
                    severity=pattern['severity'],
                    bug_type=pattern['type'],
                    description=pattern['description'],
                    location=match['location'],
                    suggested_fix=pattern['fix_template'].format(**match),
                    confidence=pattern['confidence'],
                    context={'match': match}
                ))
                
        return bugs
        
    async def _model_analysis(self, 
                            code: str, 
                            language: str,
                            context: Optional[Dict[str, Any]]) -> List[BugReport]:
        """Use ML model to detect potential bugs"""
        if not self.model:
            return []
            
        # Prepare input for model
        model_input = self._prepare_model_input(code, language, context)
        
        # Get model predictions
        predictions = await self.model.infer(model_input)
        
        # Process predictions into bug reports
        return self._process_model_predictions(predictions, code)
        
    def _check_exception_handling(self, tree: ast.AST) -> List[BugReport]:
        """Check for exception handling issues"""
        bugs = []
        
        for node in ast.walk(tree):
            # Check for bare except clauses
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                bugs.append(BugReport(
                    severity='medium',
                    bug_type='bare_except',
                    description='Bare except clause found',
                    location=self._get_node_location(node),
                    suggested_fix='Specify exception type(s) to catch',
                    confidence=0.9,
                    context={'node': node}
                ))
                
            # Check for pass in except blocks
            if (isinstance(node, ast.ExceptHandler) and 
                any(isinstance(n, ast.Pass) for n in node.body)):
                bugs.append(BugReport(
                    severity='medium',
                    bug_type='pass_in_except',
                    description='Pass statement in except block',
                    location=self._get_node_location(node),
                    suggested_fix='Handle or log the exception appropriately',
                    confidence=0.8,
                    context={'node': node}
                ))
                
        return bugs
        
    def _check_resource_management(self, tree: ast.AST) -> List[BugReport]:
        """Check for resource management issues"""
        bugs = []
        
        for node in ast.walk(tree):
            # Check for file operations without context manager
            if (isinstance(node, ast.Call) and 
                isinstance(node.func, ast.Name) and
                node.func.id == 'open'):
                if not self._is_in_with_context(node):
                    bugs.append(BugReport(
                        severity='high',
                        bug_type='resource_leak',
                        description='File opened without context manager',
                        location=self._get_node_location(node),
                        suggested_fix='Use "with open(...) as f:" pattern',
                        confidence=0.9,
                        context={'node': node}
                    ))
                    
        return bugs
        
    def _prioritize_bugs(self, bugs: List[BugReport]) -> List[BugReport]:
        """Prioritize and deduplicate bug reports"""
        # Remove duplicates
        unique_bugs = self._remove_duplicates(bugs)
        
        # Sort by severity and confidence
        severity_weights = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        
        return sorted(
            unique_bugs,
            key=lambda x: (severity_weights[x.severity], x.confidence),
            reverse=True
        )
        
    def _get_node_location(self, node: ast.AST) -> Dict[str, Any]:
        """Get location information for an AST node"""
        return {
            'line': getattr(node, 'lineno', 0),
            'column': getattr(node, 'col_offset', 0),
            'end_line': getattr(node, 'end_lineno', 0),
            'end_column': getattr(node, 'end_col_offset', 0)
        } 