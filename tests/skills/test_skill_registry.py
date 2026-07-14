from pydantic import BaseModel

from engine.skills import SKILL_REGISTRY, SkillRegistry
from engine.tools import TOOL_REGISTRY


EXPECTED_SKILLS = {
    "query_decomposition",
    "tool_routing",
    "search_planning",
    "source_discovery",
    "source_extraction",
    "evidence_ranking",
    "deduplication",
    "claim_evidence_mapping",
    "contradiction_detection",
    "citation_verification",
    "research_sufficiency",
    "context_compression",
    "medical_research",
    "financial_research",
    "general_web_research",
    "quantitative_analysis",
    "temporal_reasoning",
    "repository_inspection",
    "dataset_analysis",
    "code_execution",
    "production_retrieval",
}


def test_registry_discovers_every_declared_skill():
    assert set(SKILL_REGISTRY.names()) == EXPECTED_SKILLS


def test_every_skill_has_config_instructions_and_pydantic_contracts():
    for definition in SKILL_REGISTRY.definitions():
        assert definition.root.name == definition.id
        assert definition.root.parent.name == "skills"
        assert (definition.root / "config.yaml").is_file()
        assert (definition.root / "instructions.md").is_file()
        assert (definition.root / "schemas.py").is_file()
        assert definition.instructions.startswith("# ")
        assert issubclass(definition.input_model, BaseModel)
        assert issubclass(definition.output_model, BaseModel)
        assert definition.input_model.model_json_schema()["type"] == "object"
        assert definition.output_model.model_json_schema()["type"] == "object"


def test_configured_tools_are_registered_and_bound_to_the_skill():
    for definition in SKILL_REGISTRY.definitions():
        configured = set(definition.config.tools)
        bound = {descriptor.name for descriptor in TOOL_REGISTRY.for_skill(definition.id)}
        assert configured == bound
        for tool_name in configured:
            assert TOOL_REGISTRY.create(tool_name).name == tool_name


def test_registry_can_be_rediscovered_idempotently():
    rediscovered = SkillRegistry.discover()
    assert rediscovered.names() == SKILL_REGISTRY.names()


def test_domain_skill_tool_sets_use_primary_sources():
    assert set(SKILL_REGISTRY.get("medical_research").config.tools) == {
        "pubmed",
        "clinicaltrials",
    }
    assert set(SKILL_REGISTRY.get("financial_research").config.tools) == {
        "sec_edgar",
        "web_search",
    }
