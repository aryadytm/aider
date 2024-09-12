import os
import importlib.util
from typing import Any


class ExtensionLoader:
    def __init__(self, coder: Any):
        self.coder = coder
        self.extensions = []

    def load_extensions(self) -> None:
        print("\033[94mLoading extensions...")
        
        extensions_dir = os.path.join(os.path.dirname(__file__), 'extensions')
        for root, dirs, files in os.walk(extensions_dir):
            for file_name in files:
                if file_name.endswith('.py') and not file_name.startswith('__'):
                    self._load_extension(root, file_name)

    def _load_extension(self, root: str, file_name: str) -> None:
        full_path = os.path.join(root, file_name)
        module_name = f"aider.extensions.{os.path.splitext(file_name)[0]}"
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, full_path)
            if spec is None:
                raise ImportError(f"Failed to create spec for {full_path}")
            
            module = importlib.util.module_from_spec(spec)
            if spec.loader is None:
                raise ImportError(f"Failed to get loader for {full_path}")
            
            spec.loader.exec_module(module)

            if hasattr(module, 'setup_extension'):
                print(f"\033[94mSetting up extension: {module_name}\033[0m")
                extension = module.setup_extension(self.coder)
                self.extensions.append(extension)
                print(f"\033[92mSuccessfully set up extension: {module_name}\033[0m")
            else:
                print(f"Extension {module_name} does not have a setup_extension function")
        except Exception as e:
            print(f"Error loading extension {module_name}: {str(e)}")

    def cleanup_extensions(self) -> None:
        for extension in self.extensions:
            if hasattr(extension, 'cleanup'):
                extension.cleanup()
    

# Apply patches
def apply_patches():
    print("\033[94mApplying patches...\033[0m")
    
    extensions_dir = os.path.join(os.path.dirname(__file__), 'extensions')
    for root, dirs, files in os.walk(extensions_dir):
        for file_name in files:
            if file_name.endswith('.py') and not file_name.startswith('__'):
                full_path = os.path.join(root, file_name)
                module_name = f"aider.extensions.{os.path.splitext(file_name)[0]}"
                
                try:
                    spec = importlib.util.spec_from_file_location(module_name, full_path)
                    if spec is None:
                        raise ImportError(f"Failed to create spec for {full_path}")
                    
                    module = importlib.util.module_from_spec(spec)
                    if spec.loader is None:
                        raise ImportError(f"Failed to get loader for {full_path}")
                    
                    spec.loader.exec_module(module)

                    if hasattr(module, 'apply_patch'):
                        print(f"\033[94mApplying patch: {module_name}\033[0m")
                        module.apply_patch()
                        print(f"\033[92mSuccessfully applied patch: {module_name}\033[0m")
                    else:
                        print(f"Extension {module_name} does not have an apply_patch function")
                except Exception as e:
                    print(f"Error applying patch for {module_name}: {str(e)}")