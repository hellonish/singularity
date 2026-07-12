from .pipeline import run_pipeline
from skills.registry import _register_real_skills

_register_real_skills()

__all__ = ["run_pipeline"]
