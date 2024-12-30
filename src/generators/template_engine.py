from typing import Dict, Any, Optional
from pathlib import Path
import jinja2
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dataclasses import dataclass

@dataclass
class TemplateContext:
    language: str
    framework: str
    style: Dict[str, Any]
    components: Dict[str, Any]
    config: Dict[str, Any]

class TemplateEngine:
    def __init__(self, template_dir: str = "src/templates"):
        self.template_dir = Path(template_dir)
        self.env = self._setup_environment()
        self._load_filters()
        
    def _setup_environment(self) -> Environment:
        """Setup Jinja2 environment with custom settings"""
        return Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
    def _load_filters(self) -> None:
        """Load custom template filters"""
        self.env.filters.update({
            'camelcase': self._to_camel_case,
            'snakecase': self._to_snake_case,
            'kebabcase': self._to_kebab_case
        })
        
    def render(self, template_name: str, context: TemplateContext) -> str:
        """Render a template with given context"""
        template = self.env.get_template(template_name)
        return template.render(**context.__dict__)
        
    def create_component(self, 
                        name: str, 
                        component_type: str, 
                        context: Optional[Dict[str, Any]] = None) -> str:
        """Create a new component from template"""
        context = context or {}
        template_name = f"components/{component_type}.{context.get('language', 'py')}.j2"
        
        full_context = TemplateContext(
            language=context.get('language', 'python'),
            framework=context.get('framework', 'default'),
            style=context.get('style', {}),
            components=context.get('components', {}),
            config=context.get('config', {})
        )
        
        return self.render(template_name, full_context)
        
    @staticmethod
    def _to_camel_case(value: str) -> str:
        """Convert string to camelCase"""
        components = value.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
        
    @staticmethod
    def _to_snake_case(value: str) -> str:
        """Convert string to snake_case"""
        import re
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        return pattern.sub('_', value).lower()
        
    @staticmethod
    def _to_kebab_case(value: str) -> str:
        """Convert string to kebab-case"""
        return TemplateEngine._to_snake_case(value).replace('_', '-') 