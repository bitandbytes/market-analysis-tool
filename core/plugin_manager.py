import importlib
import os
import inspect
import sys
from typing import List, Type, Dict
from .interfaces import DataSourceInterface, AnalysisPluginInterface

class PluginManager:
    def __init__(self, plugin_package: str = "plugins"):
        self.plugin_package = plugin_package
        self.data_sources: Dict[str, DataSourceInterface] = {}
        self.analysis_plugins: Dict[str, AnalysisPluginInterface] = {}

    def discover_plugins(self):
        """Discovers and loads plugins from the plugins directory."""
        # Check if running as a frozen application (PyInstaller)
        if getattr(sys, 'frozen', False):
            base_path = os.path.join(sys._MEIPASS, "plugins")
        else:
            # We assume the code is running from the root directory
            base_path = os.path.join(os.getcwd(), "plugins")
        
        # Load Data Sources
        ds_path = os.path.join(base_path, "data_sources")
        self._load_plugins_from_dir(ds_path, DataSourceInterface, self.data_sources)

        # Load Analysis Plugins
        an_path = os.path.join(base_path, "analysis")
        self._load_plugins_from_dir(an_path, AnalysisPluginInterface, self.analysis_plugins)

    def _load_plugins_from_dir(self, directory: str, base_class: Type, storage: Dict):
        if not os.path.exists(directory):
            return

        sys.path.append(directory) 
        
        for filename in os.listdir(directory):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                try:
                    # Construct module path relative to the package
                    # Note: This is a bit tricky with dynamic paths. 
                    # Simpler approach: use importlib.util.spec_from_file_location
                    
                    spec = importlib.util.spec_from_file_location(module_name, os.path.join(directory, filename))
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        for name, obj in inspect.getmembers(module):
                            if inspect.isclass(obj) and issubclass(obj, base_class) and obj is not base_class:
                                instance = obj()
                                storage[instance.get_name()] = instance
                                print(f"Loaded plugin: {instance.get_name()}")
                except Exception as e:
                    print(f"Failed to load plugin {filename}: {e}")

    def get_data_source(self, name: str) -> DataSourceInterface:
        return self.data_sources.get(name)

    def get_all_data_sources(self) -> List[str]:
        return list(self.data_sources.keys())

    def get_analysis_plugin(self, name: str) -> AnalysisPluginInterface:
        return self.analysis_plugins.get(name)

    def get_all_analysis_plugins(self) -> List[str]:
        return list(self.analysis_plugins.keys())
