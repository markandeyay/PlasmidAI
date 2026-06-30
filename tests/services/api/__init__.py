from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[3]


def _load_real_module(name: str) -> None:
    module_name = f"services.api.{name}"
    if module_name in sys.modules:
        return
    path = _ROOT / "services" / "api" / f"{name}.py"
    if not path.exists():
        return
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)


_load_real_module("app")
_load_real_module("local_app")

create_app = sys.modules["services.api.app"].create_app

__all__ = ["create_app"]
