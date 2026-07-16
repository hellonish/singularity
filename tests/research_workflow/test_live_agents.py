import asyncio

import pytest

from engine.research_workflow.caps import RunCaps
from engine.research_workflow.dag import ResearchDAG, ResearchNode, ResearchNodeStatus
from engine.research_workflow.agents import LLMLead, LLMPlanner, LLMQA, LLMWriter
from engine.llm.groq import ProviderError
from engine.research_workflow.runner import TerminalResearchModel


class CapturingProvider:
    def __init__(self) -> None:
        self.config = None

    async def complete(self, *, config, **kwargs):
        self.config = config
        return type("Completion", (), {"content": '{"ok":true}'})()


class FakeModel:
    async def complete(self, prompt: str, *, max_output_tokens: int) -> str:
        if "Preserve the user's intent" in prompt:
            return '{"query":"bounded research","audience":"engineer","constraints":["cited"]}'
        if "Perspective:" in prompt:
            return '{"nodes":[{"question":"What is the bounded workflow?","rationale":"scope","section_id":"overview","level":0,"acceptance_criteria":["cited"],"expected_evidence":["primary"]}]}'
        if "Suggest at most two focused gaps" in prompt:
            return '{"passed":false,"score":0.4,"gaps":["missing limits"],"suggestions":[{"question":"What is the tool limit?","rationale":"bound"},{"question":"What is the QA limit?","rationale":"bound"},{"question":"A third question must be capped","rationale":"bound"}]}'
        if "Design a coherent report outline" in prompt:
            return '''{
                "title":"Bounded research",
                "limitations":[],
                "sections":[{"section_id":"overview","title":"Overview","node_ids":["root"]}]
            }'''
        if "a single ResearchDocumentV1 section object" in prompt:
            return '''{
                "section_id":"overview",
                "title":"Overview",
                "blocks":[{"kind":"paragraph","text":"The workflow is bounded.","reference_ids":["S1234567890"]}]
            }'''
        if "ResearchDocumentV1" in prompt:
            return '''{
                "schema_version":"research-document-v1",
                "title":"Bounded research",
                "query":"bounded research",
                "sections":[{"section_id":"overview","title":"Overview","blocks":[{"kind":"paragraph","text":"The workflow is bounded.","reference_ids":["S1234567890"]}]}],
                "references":[{"tag":"S1234567890","name":"Primary source","title":"Primary source","url":"https://example.test/source"}],
                "limitations":[]
            }'''
        raise AssertionError(f"unexpected prompt: {prompt}")


def test_terminal_research_uses_low_reasoning_for_quick_gpt_oss_completions() -> None:
    provider = CapturingProvider()
    model = TerminalResearchModel(
        api_key="test-key",
        model_id="openai/gpt-oss-20b",
        caps=RunCaps.for_strength(1),
        strength=1,
        provider=provider,
    )

    content = asyncio.run(model.complete("Return JSON only", max_output_tokens=500))

    assert content == '{"ok":true}'
    assert provider.config.reasoning_effort == "low"
    assert provider.config.max_output_tokens == 6_000


def test_terminal_research_raises_reasoning_effort_for_deep_gpt_oss_completions() -> None:
    provider = CapturingProvider()
    model = TerminalResearchModel(
        api_key="test-key",
        model_id="openai/gpt-oss-20b",
        caps=RunCaps.for_strength(3),
        strength=3,
        provider=provider,
    )

    asyncio.run(model.complete("Return JSON only", max_output_tokens=500))

    # Deep research lets the reasoning model deliberate before it answers.
    assert provider.config.reasoning_effort == "high"


def test_terminal_research_omits_reasoning_effort_for_other_models() -> None:
    provider = CapturingProvider()
    model = TerminalResearchModel(
        api_key="test-key",
        provider_name="openrouter",
        model_id="openai/gpt-4.1-mini",
        caps=RunCaps.for_strength(1),
        provider=provider,
    )

    asyncio.run(model.complete("Return JSON only", max_output_tokens=500))

    assert provider.config.provider == "openrouter"
    assert provider.config.model_id == "openai/gpt-4.1-mini"
    assert provider.config.max_output_tokens == 1_200
    assert provider.config.reasoning_effort is None


def test_terminal_research_retries_retryable_failures_with_raised_budget() -> None:
    class FlakyProvider:
        def __init__(self) -> None:
            self.budgets = []

        async def complete(self, *, config, **kwargs):
            self.budgets.append(config.max_output_tokens)
            if len(self.budgets) == 1:
                raise ProviderError(code="provider_invalid_structured_output", message="bad JSON", retryable=True)
            return type("Completion", (), {"content": '{"ok":true}'})()

    provider = FlakyProvider()
    model = TerminalResearchModel(
        api_key="test-key",
        provider_name="openrouter",
        model_id="deepseek/deepseek-v4-flash",
        caps=RunCaps.for_strength(1),
        provider=provider,
    )

    content = asyncio.run(model.complete("Return JSON only", max_output_tokens=1_200))

    assert content == '{"ok":true}'
    assert provider.budgets == [1_200, 2_400]


def test_terminal_research_does_not_retry_non_retryable_failures() -> None:
    class DeadProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, **kwargs):
            self.calls += 1
            raise ProviderError(code="provider_credential_invalid", message="bad key", retryable=False)

    provider = DeadProvider()
    model = TerminalResearchModel(
        api_key="test-key",
        provider_name="openrouter",
        model_id="deepseek/deepseek-v4-flash",
        caps=RunCaps.for_strength(1),
        provider=provider,
    )

    try:
        asyncio.run(model.complete("Return JSON only", max_output_tokens=500))
    except ProviderError:
        pass
    else:
        raise AssertionError("non-retryable failure must propagate")
    assert provider.calls == 1


def test_planner_runs_three_named_perspectives_and_lead_deduplicates_nodes() -> None:
    planner = LLMPlanner(FakeModel())
    polished = asyncio.run(planner.polish_prompt("  bounded research  "))
    proposals = asyncio.run(planner.parallel_proposals(polished["query"]))
    dag = asyncio.run(LLMLead().merge(polished["query"], proposals, RunCaps.for_strength(1)))

    assert [proposal["perspective"] for proposal in proposals] == ["coverage", "evidence-risk", "narrative"]
    assert len(dag.nodes) == 1


def test_planner_can_limit_perspectives_for_quick_research() -> None:
    proposals = asyncio.run(LLMPlanner(FakeModel(), max_perspectives=1).parallel_proposals("bounded research"))

    assert [proposal["perspective"] for proposal in proposals] == ["coverage"]


def test_qa_accepts_no_more_than_two_suggestions_per_section() -> None:
    caps = RunCaps.for_strength(2)
    dag = ResearchDAG()
    dag.add_node(
        ResearchNode(
            node_id="root", question="What is bounded research?", section_id="overview", level=0,
            status=ResearchNodeStatus.ANSWERED, answer="A bounded workflow.",
        ),
        caps,
    )

    reviews = asyncio.run(LLMQA(FakeModel()).review(dag, caps))

    assert len(reviews[0]["accepted_suggestions"]) == 2
    assert len(dag.nodes) == 3
    assert dag.nodes["root"].status == ResearchNodeStatus.QA_FAILED


def test_writer_keeps_valid_citable_source_references() -> None:
    caps = RunCaps.for_strength(1)
    dag = ResearchDAG()
    dag.add_node(
        ResearchNode(
            node_id="root", question="What is bounded research?", section_id="overview", level=0,
            status=ResearchNodeStatus.PASSED, answer="A bounded workflow.",
            source_records=[{
                "tag": "S1234567890", "name": "Primary source", "title": "Primary source",
                "url": "https://example.test/source", "source_type": "web",
            }],
        ),
        caps,
    )

    document = asyncio.run(LLMWriter(FakeModel()).write(dag, "bounded research"))

    assert document["references"][0]["tag"] == "S1234567890"
    assert document["sections"][0]["blocks"][0]["reference_ids"] == ["S1234567890"]


def test_writer_falls_back_to_completed_cited_evidence_after_provider_failure(caplog) -> None:
    class FailingModel:
        async def complete(self, prompt: str, *, max_output_tokens: int) -> str:
            raise ProviderError(code="provider_invalid_json_response", message="invalid JSON", retryable=True)

    caps = RunCaps.for_strength(1)
    dag = ResearchDAG()
    dag.add_node(ResearchNode(
        node_id="root", question="What happened?", section_id="overview", level=0,
        status=ResearchNodeStatus.ANSWERED, answer="A supported finding.",
        source_records=[{"tag": "S1234567890", "name": "Primary", "title": "Primary", "url": "https://example.test/source", "source_type": "web"}],
    ), caps)

    with caplog.at_level("WARNING", logger="engine.research_workflow.agents"):
        document = asyncio.run(LLMWriter(FailingModel()).write(dag, "What happened?"))

    # The reader-facing report is grounded only in the researched evidence and
    # is free of pipeline machinery: no "fallback assembly" title suffix, no
    # "writer model failed" limitation. An assistant answering from this report
    # must not be able to report on the agent's internal behaviour.
    assert document["title"] == "What happened?"
    assert document["limitations"] == []
    report_text = str(document).lower()
    assert "fallback" not in report_text
    assert "writer model failed" not in report_text
    assert "research nodes" not in report_text
    assert document["sections"][0]["blocks"][0]["reference_ids"] == ["S1234567890"]
    # The degradation must still be observable to operators: a swallowed writer
    # failure logs why, naming the exception type, so it can be root-caused —
    # that visibility lives in the logs, never in the report content.
    assert any(
        record.levelname == "WARNING" and "ProviderError" in record.getMessage()
        for record in caplog.records
    )


def test_writer_does_not_turn_missing_citable_evidence_into_an_empty_report() -> None:
    class FailingModel:
        async def complete(self, prompt: str, *, max_output_tokens: int) -> str:
            raise ProviderError(code="provider_invalid_json_response", message="invalid JSON", retryable=True)

    caps = RunCaps.for_strength(1)
    dag = ResearchDAG()
    dag.add_node(
        ResearchNode(node_id="root", question="What happened?", section_id="overview", level=0),
        caps,
    )

    with pytest.raises(ValueError, match="at least one cited section"):
        asyncio.run(LLMWriter(FailingModel()).write(dag, "What happened?"))


def _answered_dag(caps: RunCaps) -> ResearchDAG:
    dag = ResearchDAG()
    dag.add_node(
        ResearchNode(
            node_id="root", question="What is bounded research?", section_id="overview", level=0,
            status=ResearchNodeStatus.ANSWERED, answer="A bounded workflow.",
            source_records=[{
                "tag": "S1234567890", "name": "Primary source", "title": "Primary source",
                "url": "https://example.test/source", "source_type": "web",
            }],
        ),
        caps,
    )
    return dag


_OUTLINE_JSON = '{"title":"T","limitations":[],"sections":[{"section_id":"overview","title":"Overview","node_ids":["root"]}]}'
_SECTION_JSON = '{"section_id":"overview","title":"Overview","blocks":[{"kind":"paragraph","text":"Repaired.","reference_ids":["S1234567890"]}]}'


class _RepairableModel:
    """Returns a broken section body once, then a valid one on the repair retry."""

    def __init__(self, first_section_response: str) -> None:
        self.first_section_response = first_section_response
        self.section_calls = 0

    async def complete(self, prompt: str, *, max_output_tokens: int) -> str:
        if "Design a coherent report outline" in prompt:
            return _OUTLINE_JSON
        if "a single ResearchDocumentV1 section object" in prompt:
            self.section_calls += 1
            if "was rejected" in prompt:
                return _SECTION_JSON
            return self.first_section_response
        raise AssertionError(f"unexpected prompt: {prompt}")


def test_writer_repairs_a_truncated_section_instead_of_dropping_it() -> None:
    model = _RepairableModel('{"section_id":"overview","title":"Over')  # truncated JSON

    document = asyncio.run(LLMWriter(model).write(_answered_dag(RunCaps.for_strength(1)), "bounded research"))

    assert model.section_calls == 2
    assert document["sections"][0]["blocks"][0]["text"] == "Repaired."


def test_writer_rejects_a_hollow_section_and_repairs_it() -> None:
    """A heading with no blocks and no children must not ship as a section."""
    model = _RepairableModel('{"section_id":"overview","title":"Overview","blocks":[],"children":[]}')

    document = asyncio.run(LLMWriter(model).write(_answered_dag(RunCaps.for_strength(1)), "bounded research"))

    assert model.section_calls == 2
    assert document["sections"][0]["blocks"][0]["text"] == "Repaired."


def test_writer_excludes_unanswered_nodes_from_the_prompt() -> None:
    """Failed nodes and unresolved QA suggestions carry no evidence; their
    ``answer: None`` records must not dilute the outline or section prompts."""

    class CapturingModel:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        async def complete(self, prompt: str, *, max_output_tokens: int) -> str:
            self.prompts.append(prompt)
            if "Design a coherent report outline" in prompt:
                return _OUTLINE_JSON
            return _SECTION_JSON

    caps = RunCaps.for_strength(1)
    dag = _answered_dag(caps)
    dag.add_node(
        ResearchNode(
            node_id="ghost", question="An unanswered ghost question?", section_id="overview",
            level=1, depends_on=["root"],
        ),
        caps,
    )
    model = CapturingModel()

    document = asyncio.run(LLMWriter(model).write(dag, "bounded research"))

    assert document["sections"]
    assert all("ghost" not in prompt for prompt in model.prompts)
