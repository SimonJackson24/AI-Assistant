import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class SystemConfig:
    max_memory: int = 7168  # MB
    tpu_temp_threshold: float = 75.0  # Celsius
    preview_port: int = 8765
    log_level: str = "INFO"
    cache_dir: str = "cache"
    model_dir: str = "models"
    backup_dir: str = "backups"

class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> SystemConfig:
        """Load configuration from file or create default"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                config_dict = json.load(f)
                return SystemConfig(**config_dict)
        return SystemConfig()
        
    def save_config(self):
        """Save current configuration to file"""
        config_dict = {
            key: getattr(self.config, key)
            for key in self.config.__annotations__
        }
        with open(self.config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
            
    def get(self, key: str) -> Any:
        """Get configuration value"""
        return getattr(self.config, key)
        
    def update(self, key: str, value: Any):
        """Update configuration value"""
        if hasattr(self.config, key):
            setattr(self.config, key, value)
            self.save_config()
        else:
            raise KeyError(f"Unknown configuration key: {key}") 