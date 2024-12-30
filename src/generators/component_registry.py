from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from dataclasses import dataclass, asdict
import asyncio
from datetime import datetime

@dataclass
class ComponentMetadata:
    name: str
    type: str
    language: str
    framework: str
    created_at: str
    updated_at: str
    dependencies: List[str]
    tags: List[str]

class ComponentRegistry:
    def __init__(self, registry_path: str = "src/components/registry.json"):
        self.registry_path = Path(registry_path)
        self.components: Dict[str, ComponentMetadata] = {}
        self._load_registry()
        
    def _load_registry(self):
        """Load component registry from file"""
        if self.registry_path.exists():
            with open(self.registry_path) as f:
                data = json.load(f)
                self.components = {
                    name: ComponentMetadata(**meta)
                    for name, meta in data.items()
                }
                
    def _save_registry(self):
        """Save component registry to file"""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, 'w') as f:
            json.dump(
                {name: asdict(meta) for name, meta in self.components.items()},
                f,
                indent=2
            )
            
    async def register_component(self, metadata: ComponentMetadata) -> bool:
        """Register a new component"""
        if metadata.name in self.components:
            return False
            
        self.components[metadata.name] = metadata
        self._save_registry()
        return True
        
    async def update_component(self, name: str, updates: Dict[str, Any]) -> bool:
        """Update component metadata"""
        if name not in self.components:
            return False
            
        metadata = self.components[name]
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
                
        metadata.updated_at = datetime.now().isoformat()
        self._save_registry()
        return True
        
    async def get_component(self, name: str) -> Optional[ComponentMetadata]:
        """Get component metadata"""
        return self.components.get(name)
        
    async def search_components(self, 
                              language: Optional[str] = None,
                              framework: Optional[str] = None,
                              tags: Optional[List[str]] = None) -> List[ComponentMetadata]:
        """Search components by criteria"""
        results = []
        
        for component in self.components.values():
            if language and component.language != language:
                continue
                
            if framework and component.framework != framework:
                continue
                
            if tags and not all(tag in component.tags for tag in tags):
                continue
                
            results.append(component)
            
        return results
        
    async def delete_component(self, name: str) -> bool:
        """Delete component from registry"""
        if name not in self.components:
            return False
            
        del self.components[name]
        self._save_registry()
        return True 