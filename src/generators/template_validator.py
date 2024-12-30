from typing import Dict, List, Any, Optional
from pathlib import Path
import jinja2
from jinja2 import Environment, meta
from dataclasses import dataclass

@dataclass
class TemplateValidationResult:
    is_valid: bool
    missing_variables: List[str]
    undefined_filters: List[str]
    syntax_errors: List[str]
    warnings: List[str]

class TemplateValidator:
    def __init__(self, template_dir: str = "src/templates"):
        self.template_dir = Path(template_dir)
        self.env = Environment()
        self.required_variables = {
            'python_class': {'name', 'docstring', 'methods'},
            'react_component': {'name', 'props', 'style'},
            'vue_component': {'name', 'props', 'template'}
        }
        
    async def validate_template(self, template_name: str, template_type: str) -> TemplateValidationResult:
        """Validate a template file"""
        template_path = self.template_dir / f"components/{template_name}"
        
        try:
            with open(template_path) as f:
                template_source = f.read()
                
            # Parse template
            ast = self.env.parse(template_source)
            
            # Get variables
            variables = meta.find_undeclared_variables(ast)
            required = self.required_variables.get(template_type, set())
            missing = required - variables
            
            # Check filters
            undefined_filters = self._check_undefined_filters(ast)
            
            # Validate syntax
            syntax_errors = self._validate_syntax(template_source)
            
            # Check for potential issues
            warnings = self._check_for_warnings(template_source)
            
            return TemplateValidationResult(
                is_valid=len(missing) == 0 and len(syntax_errors) == 0,
                missing_variables=list(missing),
                undefined_filters=undefined_filters,
                syntax_errors=syntax_errors,
                warnings=warnings
            )
            
        except Exception as e:
            return TemplateValidationResult(
                is_valid=False,
                missing_variables=[],
                undefined_filters=[],
                syntax_errors=[str(e)],
                warnings=[]
            )
            
    def _check_undefined_filters(self, ast) -> List[str]:
        """Check for undefined filters in template"""
        undefined = []
        for node in ast.find_all(jinja2.nodes.Filter):
            if node.name not in self.env.filters:
                undefined.append(node.name)
        return undefined
        
    def _validate_syntax(self, template_source: str) -> List[str]:
        """Validate template syntax"""
        errors = []
        try:
            self.env.parse(template_source)
        except Exception as e:
            errors.append(str(e))
        return errors
        
    def _check_for_warnings(self, template_source: str) -> List[str]:
        """Check for potential issues in template"""
        warnings = []
        
        # Check for hardcoded values
        if '"' in template_source or "'" in template_source:
            warnings.append("Template contains hardcoded strings")
            
        # Check for nested loops
        if "{% for" in template_source and "{% for" in template_source[template_source.find("{% for")+1:]:
            warnings.append("Template contains nested loops which may impact performance")
            
        return warnings 