import pytest
import json
from pathlib import Path
from src.core.config_manager import ConfigManager, SystemConfig

@pytest.fixture
def config_manager(tmp_path):
    config_path = tmp_path / "test_config.json"
    return ConfigManager(str(config_path))

class TestConfigManager:
    def test_default_config(self, config_manager):
        assert isinstance(config_manager.config, SystemConfig)
        assert config_manager.config.max_memory == 7168
        assert config_manager.config.tpu_temp_threshold == 75.0
        
    def test_save_and_load(self, config_manager):
        # Modify config
        config_manager.update('max_memory', 8192)
        config_manager.update('log_level', 'DEBUG')
        
        # Create new instance to test loading
        new_config = ConfigManager(str(config_manager.config_path))
        
        assert new_config.get('max_memory') == 8192
        assert new_config.get('log_level') == 'DEBUG'
        
    def test_invalid_key(self, config_manager):
        with pytest.raises(KeyError):
            config_manager.update('invalid_key', 'value')
            
    def test_config_file_format(self, config_manager):
        config_manager.save_config()
        
        with open(config_manager.config_path) as f:
            config_data = json.load(f)
            
        assert isinstance(config_data, dict)
        assert 'max_memory' in config_data
        assert 'tpu_temp_threshold' in config_data 