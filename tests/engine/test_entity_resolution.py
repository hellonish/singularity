from engine.entity_resolution import (
    EntityRef,
    EntityResolutionStatus,
    EntityScope,
    SourceEntityDecision,
    classify_source,
    lightweight_chat_scope,
    scope_search_query,
)


def test_bare_chat_name_is_ambiguous_but_identifier_resolves_it():
    assert lightweight_chat_scope("Search for Apple").status == EntityResolutionStatus.AMBIGUOUS
    scope = lightweight_chat_scope("Search for Apple at apple.com")
    assert scope.status == EntityResolutionStatus.RESOLVED
    assert scope.entities[0].identifiers == ["apple.com"]


def test_source_needs_frozen_anchor_and_scoped_query_uses_it():
    scope = EntityScope(
        status=EntityResolutionStatus.RESOLVED,
        entities=[EntityRef(
            entity_id="mercury-auto", mention="Mercury", canonical_name="Mercury",
            entity_type="automaker", anchors=["Ford"], confidence=0.95,
        )],
        resolution_mode="ask",
    )
    aligned = classify_source(
        {"title": "Ford Mercury vehicle history", "url": "https://example.test/mercury"}, scope
    )
    namesake = classify_source(
        {"title": "Mercury planet facts", "url": "https://example.test/planet"}, scope
    )

    assert aligned.decision == SourceEntityDecision.ALIGNED
    assert namesake.decision == SourceEntityDecision.UNCERTAIN
    assert "Mercury automaker Ford" in scope_search_query("sales history", scope)


def test_identifier_is_a_required_discriminator_when_no_anchor_exists():
    scope = lightweight_chat_scope("Search for Apple at apple.com")
    official = classify_source(
        {"title": "Apple", "url": "https://apple.com/newsroom"}, scope
    )
    namesake = classify_source(
        {"title": "Apple Records", "url": "https://example.test/music"}, scope
    )
    assert official.decision == SourceEntityDecision.ALIGNED
    assert namesake.decision == SourceEntityDecision.UNCERTAIN


def test_entity_discriminators_accept_typed_provider_objects():
    entity = EntityRef.model_validate({
        "entity_id": "singularity",
        "mention": "Singularity",
        "canonical_name": "Singularity",
        "identifiers": [{"type": "url", "value": "https://github.com/hellonish/singularity.git"}],
        "anchors": [{"type": "repository", "value": "hellonish/singularity"}],
    })
    assert entity.identifiers == ["https://github.com/hellonish/singularity.git"]
    assert entity.anchors == ["hellonish/singularity"]
