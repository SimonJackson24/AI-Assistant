class CodeGenerator:
    def __init__(self):
        self.template_engine = TemplateEngine()
        self.syntax_validator = SyntaxValidator()
        self.style_enforcer = StyleEnforcer()
        
    async def generate_component(self, spec: dict):
        """Generate code with proper styling and validation"""
        template = self.template_engine.get_template(spec['type'])
        code = await self.generate_from_template(template, spec)
        return self.syntax_validator.validate(code) 