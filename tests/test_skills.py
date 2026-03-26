import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from skills import SKILL_REGISTRY, _register_real_skills
from models import PlanNode, NodeStatus, ExecutionContext, RetrievalOutput, AnalysisOutput, QualityReport, OutputDocument

# Ensure registry is populated
_register_real_skills()

# We want to test all skills registered.
all_skills = list(SKILL_REGISTRY.keys())

# Mock LLM Client
class MockLLMClient:
    def __init__(self):
        self.model_name = "mock-model"
        self.generate_text = MagicMock(return_value="""
```json
{
  "summary": "Mock summary",
  "findings": [{"mock_key": "mock_val"}],
  "citations_used": ["[Mock2024]"],
  "confidence": 0.85,
  "coverage_gaps": [],
  "upstream_slots_consumed": [],
  "node_id": "n1",
  "axes_evaluated": ["factual_grounding"],
  "results": {
    "factual_grounding": {
      "axis": "factual_grounding",
      "passed": true,
      "score": 0.9,
      "reason": "mock reason",
      "threshold": 0.8
    }
  },
  "overall_pass": true,
  "overall_score": 0.9
}
```""")

    def generate_structured(self, prompt, system_prompt, schema, **kwargs):
        # We don't strictly use this in base classes, but just in case
        return schema(**{})

# Pytest fixture to mock tool calls globally
@pytest.fixture(autouse=True)
def mock_tools():
    # Mocking base tool call_with_retry so ALL tool executions are faked
    with patch("tools.base.ToolBase.call_with_retry", new_callable=AsyncMock) as mock_exec:
        class FakeToolResult:
            def __init__(self):
                self.ok = True
                self.error = None
                self.sources = [{"title": "Mock Title", "url": "http://mock", "snippet": "mock snippet", "source_type": "web", "credibility_base": 0.8, "date": "2024-01-01"}]
        mock_exec.return_value = FakeToolResult()
        yield mock_exec

@pytest.fixture
def mock_ctx():
    ctx = ExecutionContext()
    ctx.record(
        PlanNode(node_id="n0", description="mock desc", skill="academic_search", depends_on=[], acceptance=[], parallelizable=True, output_slot="n0_out"),
        result={"summary": "mock upstream summary"},
        credibility=0.9
    )
    return ctx

@pytest.fixture
def mock_node():
    return PlanNode(
        node_id="n1",
        description="mock description",
        skill="mock_skill",
        depends_on=["n0_out"],
        acceptance=["factual_grounding"],
        parallelizable=True,
        output_slot="n1_out"
    )

@pytest.mark.asyncio
@pytest.mark.parametrize("skill_name", all_skills)
async def test_skill_contract(skill_name, mock_ctx, mock_node):
    skill = SKILL_REGISTRY[skill_name]
    client = MockLLMClient()
    registry = mock_ctx.citation_registry

    # Special handling for fallback_router (returns SKIPPED)
    if skill_name == "fallback_router":
        result, status, conf = await skill.run(mock_node, mock_ctx, client, registry)
        assert status == NodeStatus.SKIPPED
        return

    # Special logic for TranslationSkill to avoid real translation API
    if skill_name == "translation":
        with patch("tools.translation.TranslationTool.call_with_retry") as mock_trans:
            class FakeTrans:
                content = "translated mock content"
                credibility_base = 0.9
            mock_trans.return_value = FakeTrans()
            result, status, conf = await skill.run(mock_node, mock_ctx, client, registry)
            assert status == NodeStatus.OK
            assert "findings" in result
            return

    # Run the skill
    result, status, conf = await skill.run(mock_node, mock_ctx, client, registry)

    # Assert return types match SkillReturn signature
    assert isinstance(result, dict)
    assert isinstance(status, NodeStatus)
    assert isinstance(conf, float)
    assert 0.0 <= conf <= 1.0

    # Validate depending on tier
    tier = skill.__module__.split(".")[1] # e.g. "tier1_retrieval"

    try:
        if tier == "tier1_retrieval":
            # Just ensure it conforms loosely to RetrievalOutput
            RetrievalOutput(**result)
        elif tier == "tier2_analysis":
            if skill_name == "quality_check":
                QualityReport(**result)
            else:
                AnalysisOutput(**result)
        elif tier == "tier3_output":
            OutputDocument(**result)
        else:
            pytest.fail(f"Unknown tier: {tier}")
    except Exception as e:
        pytest.fail(f"Validation failed for {skill_name}: {e}\nResult was: {result}")
