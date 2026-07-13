"""Deterministic demo collaborators for the research workflow.

These fakes exercise the exact graph, cap, QA, writer, and checkpoint path
without a provider key, Modal deployment, or public-network request. The live
collaborators live one level up in :mod:`engine.research_workflow.agents`.
"""

from .agents import DemoLead, DemoPlanner, DemoQA, DemoWriter, demo_resolver

__all__ = ["DemoLead", "DemoPlanner", "DemoQA", "DemoWriter", "demo_resolver"]
