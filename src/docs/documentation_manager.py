from typing import Dict, Any, List, Optional
import logging
from pathlib import Path
import yaml
import markdown
import json
from dataclasses import dataclass
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

@dataclass
class DocConfig:
    """Documentation configuration"""
    title: str = "AI Code Assistant"
    version: str = "1.0.0"
    description: str = "AI-powered code analysis and generation tool"
    output_dir: str = "docs/build"
    template_dir: str = "docs/templates"
    enable_api_docs: bool = True
    enable_user_docs: bool = True
    enable_dev_docs: bool = True

class DocumentationManager:
    """Manages system documentation"""
    
    def __init__(self, config: Optional[DocConfig] = None):
        self.config = config or DocConfig()
        self.docs_path = Path(self.config.output_dir)
        self.template_env = Environment(
            loader=FileSystemLoader(self.config.template_dir)
        )
        
    async def generate_all_docs(self):
        """Generate all documentation"""
        if self.config.enable_api_docs:
            await self.generate_api_docs()
        if self.config.enable_user_docs:
            await self.generate_user_docs()
        if self.config.enable_dev_docs:
            await self.generate_dev_docs()
            
    async def generate_api_docs(self):
        """Generate API documentation"""
        api_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": self.config.title,
                "version": self.config.version,
                "description": self.config.description
            },
            "paths": await self._collect_api_routes(),
            "components": await self._collect_api_models()
        }
        
        # Save OpenAPI spec
        api_docs_path = self.docs_path / "api"
        api_docs_path.mkdir(parents=True, exist_ok=True)
        with open(api_docs_path / "openapi.json", "w") as f:
            json.dump(api_spec, f, indent=2)
            
    async def generate_user_docs(self):
        """Generate user documentation"""
        user_docs = {
            "getting_started": self._render_markdown("getting_started.md"),
            "features": self._render_markdown("features.md"),
            "tutorials": self._render_markdown("tutorials.md"),
            "faq": self._render_markdown("faq.md")
        }
        
        # Render user documentation
        template = self.template_env.get_template("user_docs.html")
        output = template.render(docs=user_docs)
        
        user_docs_path = self.docs_path / "user"
        user_docs_path.mkdir(parents=True, exist_ok=True)
        with open(user_docs_path / "index.html", "w") as f:
            f.write(output)
            
    async def generate_dev_docs(self):
        """Generate developer documentation"""
        dev_docs = {
            "architecture": self._render_markdown("architecture.md"),
            "api_reference": self._render_markdown("api_reference.md"),
            "contributing": self._render_markdown("contributing.md"),
            "deployment": self._render_markdown("deployment.md")
        }
        
        # Render developer documentation
        template = self.template_env.get_template("dev_docs.html")
        output = template.render(docs=dev_docs)
        
        dev_docs_path = self.docs_path / "dev"
        dev_docs_path.mkdir(parents=True, exist_ok=True)
        with open(dev_docs_path / "index.html", "w") as f:
            f.write(output)
            
    def _render_markdown(self, filename: str) -> str:
        """Render markdown file to HTML"""
        try:
            md_path = Path(self.config.template_dir) / "markdown" / filename
            with open(md_path) as f:
                return markdown.markdown(f.read())
        except Exception as e:
            logger.error(f"Failed to render markdown {filename}: {e}")
            return ""
            
    async def _collect_api_routes(self) -> Dict[str, Any]:
        """Collect API route information"""
        # Implement route collection logic
        return {}
        
    async def _collect_api_models(self) -> Dict[str, Any]:
        """Collect API model schemas"""
        # Implement model collection logic
        return {}
        
    def mount_docs(self, app: FastAPI):
        """Mount documentation in FastAPI app"""
        app.mount("/docs/static", StaticFiles(directory=str(self.docs_path)), name="docs") 