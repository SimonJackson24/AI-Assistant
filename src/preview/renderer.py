import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import json
from dataclasses import dataclass
from ..monitoring.metrics import MetricsTracker

@dataclass
class RenderConfig:
    template_dir: str = "src/templates"
    static_dir: str = "src/static"
    cache_dir: str = "src/preview/cache"
    max_cache_size: int = 100  # Number of files to cache

class PreviewRenderer:
    def __init__(self, config: Optional[RenderConfig] = None):
        self.config = config or RenderConfig()
        self.metrics = MetricsTracker()
        self.cache: Dict[str, str] = {}
        self._setup_directories()
        
    def _setup_directories(self):
        """Ensure required directories exist"""
        for dir_path in [self.config.template_dir, 
                        self.config.static_dir, 
                        self.config.cache_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            
    async def render_preview(self, file_path: str, content: str) -> Dict[str, Any]:
        """Render preview for a file"""
        try:
            file_type = Path(file_path).suffix.lower()
            renderer = self._get_renderer(file_type)
            
            start_time = self.metrics.time()
            result = await renderer(content)
            self.metrics.record('preview_render_time', self.metrics.time() - start_time)
            
            return {
                'status': 'success',
                'preview': result,
                'metadata': self._get_metadata(file_path)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'metadata': self._get_metadata(file_path)
            }
            
    def _get_renderer(self, file_type: str):
        """Get appropriate renderer for file type"""
        renderers = {
            '.py': self._render_python,
            '.html': self._render_html,
            '.css': self._render_css,
            '.js': self._render_javascript,
            '.jsx': self._render_react,
            '.tsx': self._render_react,
            '.vue': self._render_vue,
            '.sql': self._render_sql
        }
        return renderers.get(file_type, self._render_default)
        
    async def _render_python(self, content: str) -> Dict[str, Any]:
        """Render Python code preview"""
        try:
            # Basic syntax check
            compile(content, '<string>', 'exec')
            
            return {
                'code': content,
                'ast': self._generate_ast(content),
                'dependencies': self._extract_dependencies(content)
            }
        except Exception as e:
            return {'error': str(e)}
            
    async def _render_html(self, content: str) -> Dict[str, Any]:
        """Render HTML preview"""
        return {
            'html': content,
            'dom': self._parse_html(content)
        }
        
    async def _render_react(self, content: str) -> Dict[str, Any]:
        """Render React component preview"""
        try:
            # Parse JSX/TSX
            ast = await self._parse_react(content)
            
            return {
                'code': content,
                'ast': ast,
                'preview': await self._generate_react_preview(content)
            }
        except Exception as e:
            return {'error': str(e)}
            
    def _get_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get metadata for file"""
        path = Path(file_path)
        return {
            'name': path.name,
            'extension': path.suffix,
            'size': path.stat().st_size if path.exists() else 0,
            'last_modified': path.stat().st_mtime if path.exists() else 0
        }
        
    async def _generate_ast(self, content: str) -> Dict[str, Any]:
        """Generate AST for code"""
        # Implement AST generation
        pass
        
    async def _parse_react(self, content: str) -> Dict[str, Any]:
        """Parse React component"""
        # Implement React parsing
        pass
        
    async def _generate_react_preview(self, content: str) -> str:
        """Generate preview HTML for React component"""
        # Implement React preview generation
        pass 