from typing import Dict, Any, Optional, List, Tuple, Set
from pathlib import Path
import re
from dataclasses import dataclass
import black
import isort
from .code_validator import CodeValidator
import ast
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import json
from datetime import datetime
from src.monitoring.metrics import MetricsCollector
from src.risk.mitigation import RiskAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class StyleMetrics:
    """Metrics collected during style enforcement"""
    complexity_scores: Dict[str, int]
    style_violations: List[str]
    formatting_time: float
    timestamp: str = datetime.now().isoformat()
    
@dataclass
class StyleConfig:
    max_line_length: int = 88
    indent_size: int = 4
    quote_style: str = "double"
    enforce_docstrings: bool = True
    sort_imports: bool = True
    remove_unused_imports: bool = True
    max_complexity: int = 10  # McCabe complexity threshold
    parallel_processing: bool = True
    team_id: Optional[str] = None
    project_id: Optional[str] = None
    collect_metrics: bool = True
    sync_changes: bool = True
    store_history: bool = True

class StyleEnforcer:
    def __init__(self, config: Optional[StyleConfig] = None):
        self.config = config or StyleConfig()
        self.validator = CodeValidator()
        self._executor = ThreadPoolExecutor() if self.config.parallel_processing else None
        self.metrics_collector = MetricsCollector()
        self.risk_analyzer = RiskAnalyzer()
        self._style_history: List[StyleMetrics] = []
        
    async def enforce_style(self, code: str, language: str, file_path: Optional[str] = None) -> Tuple[str, List[str]]:
        """
        Enforce coding style standards with team collaboration support
        
        Args:
            code: Source code to format
            language: Programming language of the code
            file_path: Optional path to the file being formatted
            
        Returns:
            Tuple containing:
            - Formatted code
            - List of style warnings/suggestions
        """
        start_time = datetime.now()
        warnings = []
        metrics = StyleMetrics(
            complexity_scores={},
            style_violations=[],
            formatting_time=0
        )
        
        try:
            enforcers = {
                'python': self._enforce_python_style,
                'typescript': self._enforce_typescript_style,
                'javascript': self._enforce_javascript_style
            }
            
            enforcer = enforcers.get(language, self._enforce_default_style)
            formatted_code = await enforcer(code)
            
            # Analyze complexity
            if language == 'python':
                warnings.extend(await self._check_complexity(formatted_code))
                
            # Collect metrics
            if self.config.collect_metrics:
                metrics.complexity_scores = await self._analyze_complexity_metrics(formatted_code, language)
                metrics.style_violations = warnings
                metrics.formatting_time = (datetime.now() - start_time).total_seconds()
                
                # Store metrics
                await self._store_metrics(metrics, file_path)
                
            # Sync changes if enabled
            if self.config.sync_changes and file_path:
                await self._sync_changes(file_path, formatted_code, metrics)
                
            return formatted_code, warnings
            
        except Exception as e:
            logger.error(f"Style enforcement error: {str(e)}")
            warnings.append(f"Style enforcement failed: {str(e)}")
            return code, warnings
            
    async def _store_metrics(self, metrics: StyleMetrics, file_path: Optional[str] = None):
        """Store style enforcement metrics"""
        if self.config.store_history:
            self._style_history.append(metrics)
            
        if self.config.team_id and file_path:
            await self.metrics_collector.store_style_metrics(
                team_id=self.config.team_id,
                project_id=self.config.project_id,
                file_path=file_path,
                metrics=metrics
            )
            
    async def _sync_changes(self, file_path: str, formatted_code: str, metrics: StyleMetrics):
        """Sync style changes with team members"""
        if self.config.team_id:
            await self.metrics_collector.record_style_change(
                team_id=self.config.team_id,
                file_path=file_path,
                changes={
                    'formatted_code': formatted_code,
                    'metrics': metrics.__dict__,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
    async def get_team_metrics(self) -> Dict[str, Any]:
        """Get team-wide style metrics"""
        if not self.config.team_id:
            return {}
            
        return await self.metrics_collector.get_team_style_metrics(
            team_id=self.config.team_id,
            project_id=self.config.project_id
        )
        
    async def get_style_history(self, file_path: Optional[str] = None) -> List[StyleMetrics]:
        """Get style enforcement history"""
        if file_path and self.config.team_id:
            return await self.metrics_collector.get_file_style_history(
                team_id=self.config.team_id,
                file_path=file_path
            )
        return self._style_history

    async def _check_complexity(self, code: str) -> List[str]:
        """Check code complexity metrics"""
        warnings = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    complexity = self._calculate_complexity(node)
                    if complexity > self.config.max_complexity:
                        warnings.append(
                            f"Function '{node.name}' has complexity of {complexity}, "
                            f"exceeding threshold of {self.config.max_complexity}"
                        )
        except Exception as e:
            logger.warning(f"Complexity check failed: {str(e)}")
        return warnings

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate McCabe complexity for an AST node"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    async def _enforce_python_style(self, code: str) -> str:
        """Enforce Python coding style"""
        # Format with black
        try:
            code = black.format_str(
                code,
                mode=black.FileMode(
                    line_length=self.config.max_line_length
                )
            )
        except Exception as e:
            print(f"Black formatting error: {e}")
            
        # Sort imports
        if self.config.sort_imports:
            try:
                code = isort.code(
                    code,
                    config=isort.Config(
                        profile="black",
                        line_length=self.config.max_line_length,
                        force_single_line=True
                    )
                )
            except Exception as e:
                print(f"Import sorting error: {e}")
                
        # Enforce docstrings
        if self.config.enforce_docstrings:
            code = self._enforce_docstrings(code)
            
        return code
        
    def _enforce_docstrings(self, code: str) -> str:
        """Ensure all functions and classes have docstrings"""
        tree = ast.parse(code)
        
        def should_have_docstring(node):
            return isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module))
            
        def has_docstring(node):
            return (ast.get_docstring(node) is not None)
            
        def insert_docstring(node):
            if isinstance(node, ast.FunctionDef):
                return f'"""{node.name} function"""\n'
            elif isinstance(node, ast.ClassDef):
                return f'"""{node.name} class"""\n'
            return '"""Module docstring"""\n'
            
        # Convert tree to source lines
        lines = code.splitlines()
        insertions = []
        
        for node in ast.walk(tree):
            if should_have_docstring(node) and not has_docstring(node):
                # Get the line number where we should insert the docstring
                insert_line = node.lineno
                # Get the indentation of the current line
                indentation = len(lines[insert_line - 1]) - len(lines[insert_line - 1].lstrip())
                # Create the properly indented docstring
                docstring = " " * indentation + insert_docstring(node)
                insertions.append((insert_line, docstring))
                
        # Apply insertions from bottom to top to maintain line numbers
        for line_no, docstring in sorted(insertions, reverse=True):
            lines.insert(line_no, docstring)
            
        return "\n".join(lines)
        
    async def _enforce_typescript_style(self, code: str) -> str:
        """Enforce TypeScript coding style"""
        # Basic formatting
        lines = code.splitlines()
        formatted_lines = []
        indent = 0
        
        for line in lines:
            # Handle indentation
            if re.search(r'[{]\s*$', line):
                formatted_lines.append(" " * (indent * self.config.indent_size) + line.strip())
                indent += 1
            elif re.search(r'^[}\])]', line.strip()):
                indent = max(0, indent - 1)
                formatted_lines.append(" " * (indent * self.config.indent_size) + line.strip())
            else:
                formatted_lines.append(" " * (indent * self.config.indent_size) + line.strip())
                
        code = "\n".join(formatted_lines)
        
        # Enforce quote style
        if self.config.quote_style == "double":
            code = re.sub(r"(?<!\\)'([^'\\]*(?:\\.[^'\\]*)*)'", r'"\1"', code)
        else:
            code = re.sub(r'(?<!\\)"([^"\\]*(?:\\.[^"\\]*)*)"', r"'\1'", code)
            
        return code
        
    async def _enforce_javascript_style(self, code: str) -> str:
        """Enforce JavaScript coding style"""
        # Reuse TypeScript formatting for JavaScript
        return await self._enforce_typescript_style(code)
        
    async def _enforce_default_style(self, code: str) -> str:
        """Default style enforcement"""
        return code 