import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

class ModelConfigLoader:
    def __init__(self):
        self.config_path = Path(__file__).parent / "model_config.yaml"
        self._config_data = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self._config_data:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, 'r') as f:
                self._config_data = yaml.safe_load(f)
        
        return self._config_data
    
    def get_model_config(self, config_name: Optional[str] = None) -> Dict[str, Any]:
        """Get model configuration by name, merged with default config"""
        config_data = self._load_config()
        
        # Start with default configuration
        result = config_data.get('default_config', {}).copy()
        
        if config_name:
            # If a specific configuration is requested, merge it with defaults
            if config_name not in config_data.get('model_configs', {}):
                raise ValueError(f"Model configuration '{config_name}' not found")
            
            model_config = config_data['model_configs'][config_name]
            result.update(model_config)
        
        return result
    
    def list_available_configs(self) -> list:
        """List all available model configurations"""
        config_data = self._load_config()
        return list(config_data.get('model_configs', {}).keys())

# Create a global instance
model_config_loader = ModelConfigLoader() 