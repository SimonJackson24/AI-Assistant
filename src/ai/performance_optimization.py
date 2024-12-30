from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import ast
import cProfile
import pstats
import asyncio
from pathlib import Path

from ..core.base_models import BaseModel, ModelConfig
from ..monitoring.metrics import MetricsTracker
from .code_analyzer import CodeAnalyzer, CodeMetrics

@dataclass
class OptimizationSuggestion:
    category: str  # 'algorithm', 'memory', 'io', 'concurrency'
    description: str
    impact: str  # Estimated performance impact
    changes: List[Dict[str, Any]]
    complexity_change: str
    memory_change: str
    confidence: float

class PerformanceOptimizer:
    def __init__(self, model_config: Optional[ModelConfig] = None):
        self.model = BaseModel(model_config) if model_config else None
        self.analyzer = CodeAnalyzer()
        self.metrics = MetricsTracker()
        
    async def analyze_performance(self, 
                                code: str,
                                language: str,
                                profile_data: Optional[Dict[str, Any]] = None) -> List[OptimizationSuggestion]:
        """Analyze code for performance optimizations"""
        try:
            suggestions = []
            
            # Static analysis for performance issues
            static_suggestions = await self._static_analysis(code, language)
            suggestions.extend(static_suggestions)
            
            # Algorithm optimization suggestions
            algo_suggestions = await self._analyze_algorithms(code)
            suggestions.extend(algo_suggestions)
            
            # Memory optimization suggestions
            memory_suggestions = await self._analyze_memory_usage(code)
            suggestions.extend(memory_suggestions)
            
            # I/O and concurrency optimization suggestions
            if profile_data:
                runtime_suggestions = await self._analyze_runtime_performance(
                    code, profile_data
                )
                suggestions.extend(runtime_suggestions)
                
            return self._prioritize_suggestions(suggestions)
            
        except Exception as e:
            self.metrics.record_error('performance_analysis_error', str(e))
            return []
            
    async def _static_analysis(self, code: str, language: str) -> List[OptimizationSuggestion]:
        """Perform static analysis for performance issues"""
        suggestions = []
        
        try:
            tree = ast.parse(code)
            
            # Check for inefficient list operations
            suggestions.extend(self._check_list_operations(tree))
            
            # Check for inefficient string operations
            suggestions.extend(self._check_string_operations(tree))
            
            # Check for unnecessary computations
            suggestions.extend(self._check_computation_efficiency(tree))
            
        except Exception as e:
            self.metrics.record_error('static_analysis_error', str(e))
            
        return suggestions
        
    async def _analyze_algorithms(self, code: str) -> List[OptimizationSuggestion]:
        """Analyze and suggest algorithm optimizations"""
        suggestions = []
        
        try:
            tree = ast.parse(code)
            
            # Check for nested loops
            suggestions.extend(self._check_nested_loops(tree))
            
            # Check for recursive functions
            suggestions.extend(self._check_recursion(tree))
            
            # Check for inefficient data structures
            suggestions.extend(self._check_data_structures(tree))
            
        except Exception as e:
            self.metrics.record_error('algorithm_analysis_error', str(e))
            
        return suggestions
        
    async def _analyze_memory_usage(self, code: str) -> List[OptimizationSuggestion]:
        """Analyze memory usage and suggest optimizations"""
        suggestions = []
        
        try:
            tree = ast.parse(code)
            
            # Check for memory leaks
            suggestions.extend(self._check_memory_leaks(tree))
            
            # Check for large object creation
            suggestions.extend(self._check_object_creation(tree))
            
            # Check for efficient data handling
            suggestions.extend(self._check_data_handling(tree))
            
        except Exception as e:
            self.metrics.record_error('memory_analysis_error', str(e))
            
        return suggestions
        
    async def _analyze_runtime_performance(self, 
                                        code: str,
                                        profile_data: Dict[str, Any]) -> List[OptimizationSuggestion]:
        """Analyze runtime performance data"""
        suggestions = []
        
        try:
            # Analyze bottlenecks
            bottlenecks = self._identify_bottlenecks(profile_data)
            
            for bottleneck in bottlenecks:
                if bottleneck['type'] == 'io_bound':
                    suggestions.extend(
                        self._suggest_io_optimizations(bottleneck)
                    )
                elif bottleneck['type'] == 'cpu_bound':
                    suggestions.extend(
                        self._suggest_computation_optimizations(bottleneck)
                    )
                elif bottleneck['type'] == 'memory_bound':
                    suggestions.extend(
                        self._suggest_memory_optimizations(bottleneck)
                    )
                    
        except Exception as e:
            self.metrics.record_error('runtime_analysis_error', str(e))
            
        return suggestions
        
    def _check_nested_loops(self, tree: ast.AST) -> List[OptimizationSuggestion]:
        """Check for and suggest optimizations for nested loops"""
        suggestions = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                nested_loops = self._find_nested_loops(node)
                if nested_loops:
                    suggestions.append(OptimizationSuggestion(
                        category='algorithm',
                        description='Nested loops detected - consider optimization',
                        impact='High - O(n²) or worse complexity',
                        changes=[{
                            'type': 'refactor',
                            'location': self._get_node_location(node),
                            'suggestion': 'Consider using a more efficient data structure or algorithm'
                        }],
                        complexity_change='O(n²) -> O(n log n) potential',
                        memory_change='No significant change',
                        confidence=0.8
                    ))
                    
        return suggestions 