# -*- coding: utf-8 -*-
"""Compatibility facade for the repository's canonical JSON generator.

The production regeneration pipeline and all three apps must execute exactly the
same morphology rules.  The implementation therefore lives only in
``_analysis_20260625/gen_replacement.py``; this historical module name remains
as a stable import surface for callers that used it directly.
"""
from pathlib import Path
import importlib.util
import sys

_ANALYSIS_DIR = Path(__file__).resolve().parents[1] / "_analysis_20260625"
_CANONICAL = _ANALYSIS_DIR / "gen_replacement.py"
if not _CANONICAL.is_file():
    raise ImportError(
        "Canonical generator is missing. Use esp_generation_module.py from the "
        "complete esperanto-radiko-cjk-annotator repository."
    )

def _resolved_module_path(module):
    try:
        return Path(module.__file__).resolve()
    except (AttributeError, OSError, TypeError):
        return None


# Reuse only a module loaded from the exact canonical file.  A plain
# ``from gen_replacement import *`` can silently bind to an unrelated module
# with the same generic name when a host process populated sys.modules first.
_module = next(
    (m for m in tuple(sys.modules.values()) if m is not None and _resolved_module_path(m) == _CANONICAL),
    None,
)
if _module is None:
    _module_name = "_esperanto_canonical_gen_replacement"
    _module = sys.modules.get(_module_name)
    if _module is not None and _resolved_module_path(_module) != _CANONICAL:
        raise ImportError(f"Canonical generator module-name collision: {_resolved_module_path(_module)}")
    if _module is None:
        _spec = importlib.util.spec_from_file_location(_module_name, _CANONICAL)
        if _spec is None or _spec.loader is None:
            raise ImportError(f"Cannot load canonical generator: {_CANONICAL}")
        _module = importlib.util.module_from_spec(_spec)
        sys.modules[_module_name] = _module
        try:
            _spec.loader.exec_module(_module)
        except Exception:
            sys.modules.pop(_module_name, None)
            raise

__all__ = [name for name in vars(_module) if not name.startswith("_")]
globals().update({name: getattr(_module, name) for name in __all__})
