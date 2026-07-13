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


def test_caps_are_fixed_and_strength_only_changes_run_budget():
    caps = RunCaps.for_strength(3)
    assert caps.max_qa_suggestions_per_section == 2
    assert caps.max_tool_calls_per_node == 4
    assert RunCaps.for_strength(3).max_tool_calls_per_node == 4


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
