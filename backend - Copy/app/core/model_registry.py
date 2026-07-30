import importlib
import pkgutil
from pathlib import Path
import app  # or your top-level package


def discover_models():
    """Dynamically imports all modules in app.models (or subpackages)

    so SQLAlchemy/Tortoise models register with Base metadata.
    """
    # 1. Safely resolve the directory path for the 'app' package
    if getattr(app, "__file__", None):
        package_path = Path(app.__file__).parent
    elif hasattr(app, "__path__"):
        # Namespace package fallback
        package_path = Path(list(app.__path__)[0])
    else:
        # Absolute fallback relative to this file (app/core/model_registry.py -> app/)
        package_path = Path(__file__).resolve().parent.parent

    # 2. Path to the models directory
    models_dir = package_path / "models"

    if not models_dir.exists():
        return []

    discovered = []
    # 3. Iterate and import all modules inside app/models/
    for module_info in pkgutil.iter_modules([str(models_dir)]):
        module_name = f"app.models.{module_info.name}"
        module = importlib.import_module(module_name)
        discovered.append(module)

    return discovered