from typing import Dict, Any, Optional
from pathlib import Path
import asyncio
from dataclasses import dataclass
from .template_engine import TemplateEngine, TemplateContext

@dataclass
class ComponentSpec:
    name: str
    type: str
    language: str
    framework: str
    props: Dict[str, Any]
    style: Dict[str, Any]
    config: Dict[str, Any]

class ComponentGenerator:
    def __init__(self, output_dir: str = "src/components"):
        self.output_dir = Path(output_dir)
        self.template_engine = TemplateEngine()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def generate_component(self, spec: ComponentSpec) -> Path:
        """Generate a new component from specification"""
        # Create component context
        context = TemplateContext(
            language=spec.language,
            framework=spec.framework,
            style=spec.style,
            components={"props": spec.props},
            config=spec.config
        )
        
        # Generate component code
        code = self.template_engine.create_component(
            name=spec.name,
            component_type=spec.type,
            context=context.__dict__
        )
        
        # Determine output path
        extension = self._get_extension(spec.language, spec.framework)
        output_path = self.output_dir / f"{spec.name}{extension}"
        
        # Write component to file
        await self._write_component(output_path, code)
        
        # Generate additional files (e.g., styles, tests)
        await asyncio.gather(
            self._generate_styles(spec, output_path),
            self._generate_tests(spec, output_path)
        )
        
        return output_path
        
    async def _write_component(self, path: Path, content: str) -> None:
        """Write component content to file"""
        async with asyncio.Lock():
            path.write_text(content)
            
    async def _generate_styles(self, spec: ComponentSpec, component_path: Path) -> Optional[Path]:
        """Generate component styles if needed"""
        if not spec.style.get('css_module'):
            return None
            
        style_path = component_path.with_suffix('.module.css')
        style_content = self.template_engine.render(
            'styles/component.css.j2',
            TemplateContext(
                language=spec.language,
                framework=spec.framework,
                style=spec.style,
                components={"name": spec.name},
                config=spec.config
            )
        )
        
        await self._write_component(style_path, style_content)
        return style_path
        
    async def _generate_tests(self, spec: ComponentSpec, component_path: Path) -> Optional[Path]:
        """Generate component tests if needed"""
        if not spec.config.get('generate_tests', True):
            return None
            
        test_path = component_path.parent / 'tests' / f"{spec.name}.test{component_path.suffix}"
        test_content = self.template_engine.render(
            f'tests/component.{spec.language}.j2',
            TemplateContext(
                language=spec.language,
                framework=spec.framework,
                style=spec.style,
                components={"name": spec.name, "props": spec.props},
                config=spec.config
            )
        )
        
        test_path.parent.mkdir(parents=True, exist_ok=True)
        await self._write_component(test_path, test_content)
        return test_path
        
    @staticmethod
    def _get_extension(language: str, framework: str) -> str:
        """Get appropriate file extension based on language and framework"""
        extensions = {
            'python': '.py',
            'typescript': '.tsx',
            'javascript': '.jsx',
            'vue': '.vue'
        }
        return extensions.get(language, '.txt') 