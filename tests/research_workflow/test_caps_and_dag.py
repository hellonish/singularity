from engine.research_workflow.caps import RunCaps, format_runtime_seconds
from engine.research_workflow.dag import ResearchDAG, ResearchNode


def node(node_id: str, *, section: str = "s1", depends_on=None, level=0):
    return ResearchNode(
        node_id=node_id,
        question=f"Question {node_id}",
        section_id=section,
        level=level,
        depends_on=depends_on or [],
    )


def test_qa_suggestion_cap_is_fixed_while_depth_scales_with_strength():
    # QA suggestions stay fixed (a coverage knob), but the per-node tool-call
    # and fetch budgets grow with strength (depth knobs), bounded by ceilings.
    assert RunCaps.for_strength(1).max_qa_suggestions_per_section == 2
    assert RunCaps.for_strength(3).max_qa_suggestions_per_section == 2

    tool_calls = [RunCaps.for_strength(s).max_tool_calls_per_node for s in (1, 2, 3)]
    fetches = [RunCaps.for_strength(s).max_fetches for s in (1, 2, 3)]
    assert tool_calls == sorted(tool_calls) and tool_calls[0] < tool_calls[-1]
    assert fetches == sorted(fetches) and fetches[0] < fetches[-1]
    assert tool_calls[-1] <= RunCaps.MAX_TOOL_CALLS_CEILING
    assert fetches[-1] <= RunCaps.MAX_FETCHES_CEILING
    # Every tier must leave a search call after its fetch budget.
    assert all(
        RunCaps.for_strength(s).max_fetches <= RunCaps.for_strength(s).max_tool_calls_per_node - 1
        for s in (1, 2, 3)
    )


def test_content_budgets_grow_with_strength():
    quick = RunCaps.for_strength(1)
    deep = RunCaps.for_strength(3)
    assert deep.max_nodes > quick.max_nodes
    assert deep.section_completion_tokens > quick.section_completion_tokens
    assert deep.subsection_completion_tokens > quick.subsection_completion_tokens
    assert deep.max_source_chars > quick.max_source_chars


def test_quick_research_keeps_a_bounded_decomposition_and_skips_qa():
    caps = RunCaps.for_strength(1)

    assert caps.max_nodes == 6
    assert caps.qa_cycles == 0
    assert caps.llm_step_timeout_seconds == 360
    assert caps.max_runtime_seconds == 1_200
    assert format_runtime_seconds(caps.max_runtime_seconds) == "20m"


def test_deeper_research_has_generous_but_bounded_stage_deadlines():
    standard = RunCaps.for_strength(2)
    deep = RunCaps.for_strength(3)

    assert (standard.llm_step_timeout_seconds, standard.max_runtime_seconds) == (450, 1_800)
    assert (deep.llm_step_timeout_seconds, deep.max_runtime_seconds) == (600, 3_600)


def test_dag_rejects_cycles_and_limits_qa_suggestions():
    caps = RunCaps.for_strength(3)
    dag = ResearchDAG()
    dag.add_node(node("root"), caps)
    dag.add_node(node("child", depends_on=["root"], level=1), caps)

    first = node("gap-1", section="s1", depends_on=["child"], level=2)
    second = node("gap-2", section="s1", depends_on=["child"], level=2)
    third = node("gap-3", section="s1", depends_on=["child"], level=2)
    accepted, rejected = dag.add_suggestions("s1", [first, second, third], caps)
    assert accepted == ["gap-1", "gap-2"]
    assert rejected == ["gap-3"]

    dag.nodes["root"].depends_on = ["child"]
    try:
        dag.validate_acyclic()
    except ValueError as exc:
        assert "cycle" in str(exc).lower()
    else:
        raise AssertionError("expected cycle rejection")
